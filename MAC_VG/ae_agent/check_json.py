import json
import re
import ast

def check_json(text: str) -> str:
    """
    将 LLM 输出尽可能修复为可 json.loads 的 JSON 字符串。
    - 成功解析：返回规范化后的 JSON 字符串（json.dumps）
    - 无法修复：返回 {"raw": 原始输出} 的 JSON 字符串，保证可解析
    """
    raw = "" if text is None else str(text)

    # 0) 快速路径：本来就是合法 JSON
    obj = _try_json_load(raw)
    if obj is not None:
        return json.dumps(obj, ensure_ascii=False)

    # 1) 基础清洗：去 BOM / 去 markdown code fence / 去多余包裹
    s = _strip_bom(raw).strip()
    s = _strip_code_fences(s).strip()

    # 再试一次（有时输出就是 ```json ... ```）
    obj = _try_json_load(s)
    if obj is not None:
        return json.dumps(obj, ensure_ascii=False)

    # 2) 从混杂文本中提取“最可能的 JSON 块”（支持 {...} 或 [...]）
    candidate = _extract_json_like_block(s)
    if candidate:
        obj = _try_json_load(candidate)
        if obj is not None:
            return json.dumps(obj, ensure_ascii=False)

    # 3) 对候选块做常见修复（若没有 candidate 就对 s 修复）
    target = candidate if candidate else s
    repaired = _repair_common_json_issues(target)

    obj = _try_json_load(repaired)
    if obj is not None:
        return json.dumps(obj, ensure_ascii=False)

    # 4) 使用 Python literal_eval 作为兜底（处理单引号 dict 等）
    obj = _try_literal_eval(repaired)
    if obj is not None:
        return json.dumps(obj, ensure_ascii=False)

    # 5) 最终兜底：保证输出一定是合法 JSON
    return json.dumps({"raw": raw}, ensure_ascii=False)


# ----------------------- helpers -----------------------

def _try_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None

def _strip_bom(s: str) -> str:
    return s.lstrip("\ufeff")

def _strip_code_fences(s: str) -> str:
    """
    去掉 ```json ... ``` / ``` ... ``` 包裹。
    """
    # 形如 ```json\n...\n```
    fence = re.compile(r"^\s*```(?:json|JSON)?\s*\n([\s\S]*?)\n\s*```\s*$")
    m = fence.match(s)
    if m:
        return m.group(1)
    return s

def _extract_json_like_block(s: str) -> str | None:
    """
    从字符串中提取第一个完整的 JSON 对象/数组块（平衡括号，考虑字符串引号）。
    """
    # 找第一个 { 或 [
    start_idx = None
    start_ch = None
    for i, ch in enumerate(s):
        if ch in "{[":
            start_idx = i
            start_ch = ch
            break
    if start_idx is None:
        return None

    end_ch = "}" if start_ch == "{" else "]"
    stack = [start_ch]
    in_string = False
    escape = False

    for j in range(start_idx + 1, len(s)):
        ch = s[j]

        if in_string:
            if escape:
                escape = False
                continue
            if ch == "\\":
                escape = True
                continue
            if ch == '"':
                in_string = False
            continue

        # not in string
        if ch == '"':
            in_string = True
            continue
        if ch in "{[":
            stack.append(ch)
            continue
        if ch in "}]":
            if not stack:
                break
            top = stack[-1]
            if (top == "{" and ch == "}") or (top == "[" and ch == "]"):
                stack.pop()
                if not stack:
                    return s[start_idx : j + 1].strip()
            else:
                # 括号不匹配，直接放弃
                return None

    return None

def _repair_common_json_issues(s: str) -> str:
    """
    修复常见 JSON 格式问题：
    - 智能引号 “ ” ‘ ’ -> " '
    - 中文标点 ： ， -> : ,
    - 末尾多余逗号： { "a":1, } / [1,2,]
    - 未加引号的 key： {a:1} -> {"a":1}
    - 单引号字符串/键： {'a': 'b'} -> {"a": "b"}（尽量不伤害内容）
    - Python 常量：None/True/False -> null/true/false
    """
    t = s.strip()

    # 智能引号/全角符号
    t = (t.replace("“", '"').replace("”", '"')
           .replace("‘", "'").replace("’", "'")
           .replace("：", ":").replace("，", ",")
           .replace("（", "(").replace("）", ")"))

    # 去掉行首/行尾多余说明文字常见分隔（不强依赖）
    # 不做激进删除，避免误删内容

    # 替换 Python 常量为 JSON 常量（在不破坏引号内内容的前提下很难完美，这里走“轻度修复”）
    # 先保守：只替换明显的 token（前后是分隔符）
    t = re.sub(r'(?<!")\bNone\b(?!")', 'null', t)
    t = re.sub(r'(?<!")\bTrue\b(?!")', 'true', t)
    t = re.sub(r'(?<!")\bFalse\b(?!")', 'false', t)

    # 去掉尾逗号： , }  或 , ]
    t = re.sub(r",\s*([}\]])", r"\1", t)

    # 给未加引号的 key 加引号： {a:1, b_c:2} -> {"a":1, "b_c":2}
    # 仅处理对象 key（{ 或 , 后面跟 key 再跟 :）
    t = re.sub(r'([{\s,])([A-Za-z_][A-Za-z0-9_\-]*)(\s*):', r'\1"\2"\3:', t)

    # 尝试把单引号包裹的 key/value 转成双引号（针对类似 Python dict）
    # 这一步可能不完美，但能覆盖大量 LLM 输出。
    # 先把 key: 'xxx' 形式转成 key: "xxx"
    t = re.sub(r':\s*\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', r': "\1"', t)
    # 再把 {'k': ...} 的 key 转成 "k"
    t = re.sub(r'([{\s,])\'([^\'\\]*(?:\\.[^\'\\]*)*)\'\s*:', r'\1"\2":', t)

    # 有些模型会输出多行字符串中包含裸换行，严格 JSON 不允许；尽量不改内容，仅压成 \n
    # 这里采取保守策略：只有在明显是 value 串里出现未转义换行时才很难准确修。
    # 先不强制替换所有换行，避免破坏结构；json.loads 失败会走 literal_eval 或 raw 兜底。

    return t

def _try_literal_eval(s: str):
    """
    使用 ast.literal_eval 解析 Python 风格字面量：
    - {'a': 'b'} / {"a": "b"} / [1,2]
    然后再转 JSON。
    """
    try:
        obj = ast.literal_eval(s)
        # 仅允许 dict/list 作为结构化输出；其他类型也可包一层
        if isinstance(obj, (dict, list)):
            return obj
        return {"value": obj}
    except Exception:
        return None
