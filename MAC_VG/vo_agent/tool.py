import io
import base64
import matplotlib
matplotlib.use("Agg")  # 强制一致 backend
import matplotlib.pyplot as plt
from PIL import Image
import re
from typing import Optional
import json
import re
import ast
from typing import Any



def extract_json_from_llm_output(text: str) -> Any:
    """
    从 LLM 输出中提取 JSON 数据并解析成 Python 对象。

    处理场景：
    1. 纯 JSON
    2. ```json ... ``` 代码块
    3. JSON 前后带解释文本
    4. 整段 JSON 被包成字符串
    5. 使用中文/弯引号
    6. 单引号形式的伪 JSON
    7. 末尾多余逗号

    返回：
        Python 对象（dict / list / str / int ...）

    异常：
        ValueError: 无法提取或解析 JSON
    """
    if not isinstance(text, str):
        raise TypeError("text 必须是字符串")

    s = text.strip()
    if not s:
        raise ValueError("输入为空")

    # 1) 统一一些常见的非标准引号
    s = (
        s.replace("“", '"')
         .replace("”", '"')
         .replace("‘", "'")
         .replace("’", "'")
    )

    # 2) 优先提取 markdown 代码块中的内容
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s, re.IGNORECASE)
    if code_block_match:
        candidate = code_block_match.group(1).strip()
        result = _try_parse_json_like(candidate)
        if result is not None:
            return result

    # 3) 直接整体解析
    result = _try_parse_json_like(s)
    if result is not None:
        return result

    # 4) 从文本中提取第一个完整的 {...} 或 [...]
    candidate = _find_first_balanced_json_fragment(s)
    if candidate:
        result = _try_parse_json_like(candidate)
        if result is not None:
            return result

    # 5) 尝试提取所有候选片段，找到第一个可解析的
    for candidate in _find_all_possible_json_fragments(s):
        result = _try_parse_json_like(candidate)
        if result is not None:
            return result
    return None
    raise ValueError("无法从 LLM 输出中提取有效 JSON")


def _try_parse_json_like(s: str) -> Any | None:
    """
    尝试用多种方式解析 JSON / 类 JSON。
    成功返回对象，失败返回 None。
    """
    s = s.strip()
    if not s:
        return None

    # A. 标准 JSON
    try:
        return json.loads(s)
    except Exception:
        pass

    # B. 如果本身是一个被引号包住的 JSON 字符串，先解一层
    try:
        unwrapped = json.loads(f'"{s}"')
        if isinstance(unwrapped, str):
            try:
                return json.loads(unwrapped)
            except Exception:
                pass
    except Exception:
        pass

    # C. 处理可能的尾随逗号
    cleaned = _remove_trailing_commas(s)
    if cleaned != s:
        try:
            return json.loads(cleaned)
        except Exception:
            pass

    # D. 单引号 / Python dict 风格，尝试 ast.literal_eval
    try:
        obj = ast.literal_eval(cleaned)
        if isinstance(obj, (dict, list, tuple, str, int, float, bool, type(None))):
            return obj
    except Exception:
        pass

    # E. 如果整个内容是字符串，再递归解一层
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {"'", '"'}:
        inner = s[1:-1].strip()
        try:
            return json.loads(inner)
        except Exception:
            try:
                return ast.literal_eval(inner)
            except Exception:
                pass

    return None


def _remove_trailing_commas(s: str) -> str:
    """
    去掉对象或数组中末尾多余逗号：
    {"a": 1,} -> {"a": 1}
    [1,2,] -> [1,2]
    """
    return re.sub(r",\s*([}\]])", r"\1", s)


def _find_first_balanced_json_fragment(text: str) -> str | None:
    """
    从文本中寻找第一个括号平衡的 JSON 片段，支持 {} 或 []。
    会忽略字符串内部的括号。
    """
    for opening, closing in [("{", "}"), ("[", "]")]:
        start_positions = [i for i, ch in enumerate(text) if ch == opening]
        for start in start_positions:
            fragment = _extract_balanced(text, start, opening, closing)
            if fragment is not None:
                return fragment
    return None


def _find_all_possible_json_fragments(text: str) -> list[str]:
    """
    提取文本中所有可能的平衡 JSON 片段。
    """
    results = []
    seen = set()

    for opening, closing in [("{", "}"), ("[", "]")]:
        for i, ch in enumerate(text):
            if ch == opening:
                fragment = _extract_balanced(text, i, opening, closing)
                if fragment and fragment not in seen:
                    seen.add(fragment)
                    results.append(fragment)

    return results


def _extract_balanced(text: str, start: int, opening: str, closing: str) -> str | None:
    """
    从 start 开始提取一个括号平衡片段，忽略字符串中的括号。
    """
    if start >= len(text) or text[start] != opening:
        return None

    depth = 0
    in_string = False
    escape = False
    quote_char = ""

    for i in range(start, len(text)):
        ch = text[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                quote_char = ch
            elif ch == opening:
                depth += 1
            elif ch == closing:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]

    return None


def encode_vis_image(code_str, dpi=300):
    buffer = io.BytesIO()
    plt.close("all")

    # 禁止 show 阻塞
    def dummy_show():
        pass

    original_show = plt.show
    plt.show = dummy_show

    try:
        exec_env = {"plt": plt, "__builtins__": __builtins__}
        exec(code_str, exec_env)

        # 强制保存参数一致
        plt.savefig(
            buffer,
            format="png",
            dpi=dpi,
            bbox_inches=None,  # 不要 tight
            pad_inches=0
        )

        buffer.seek(0)

        base64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
        pil_img = Image.open(buffer).convert("RGB")

    finally:
        plt.show = original_show
        plt.close("all")

    return base64_img, pil_img


def extract_code(text: str) -> Optional[str]:
    """
    从 LLM 输出中提取第一份 python 代码块
    只返回一个字符串，找不到返回 None
    """
    pattern = r"<CODE>(?:python)?\s*(.*?)</CODE>"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()

    pattern = r"```(?:python)?\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

    if match:
        return match.group(1).strip()

    return None