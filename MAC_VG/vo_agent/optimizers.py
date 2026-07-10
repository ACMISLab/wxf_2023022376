import json
import ast
import re
from typing import Any, Dict, List
from vo_agent.tool import encode_vis_image
from model.mllm import get_vllm_messages
from model.llm import get_messages
from vo_agent.tool import extract_json_from_llm_output

def extract_json(text: str) -> Dict[str, Any]:
    """
    兼容模型输出：
    - 纯 JSON
    - JSON 前后带解释
    - ```json ... ```
    """
    if not text:
        return {}

    # 优先找 ```json ... ```
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass

    # 再找第一个 { ... } 块
    m = re.search(r"(\{.*\})", text, flags=re.S)
    if m:
        candidate = m.group(1)
        # 尝试修复常见尾逗号
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except Exception:
            return {}

    return {}
def check_task_fulfillment(
    chart_base64: str,
    code:str,
    question: str,
    answer: str,
) -> Dict[str, Any]:

    prompt = f"""
你是一个严格的“可视化评审器”。你会看到一张可视化图表，以及问题与答案。
你的任务：判断该图表对“答案”是否进行了突出展示。

判定标准（满足才算 pass=true）：
-展示答案的数据在可视化图表中被标注/高亮/注释；
-颜色、大小、位置是否有区分度

请只输出 JSON，格式如下：
{{
  "pass": true/false,
  "reason": "简要说明",
}}

问题：
{question}

答案：
{answer}
""".strip()

    result = get_vllm_messages(prompt,chart_base64)
    if isinstance(result, dict):
        return result

    parsed = extract_json(str(result))
    return parsed
def get_repair_info(
    chart_base64: str,
    question: str,
    answer: str,
) -> Dict[str, Any]:

    prompt = f"""
你是一个严格且专业的“可视化改进评审器”。
你会看到一张可视化图表，以及与之对应的问题和答案。

你的任务：
基于当前问题与答案，提出具体、可执行的图表修改建议，以提升用户从图表中获得该答案的准确性和理解效果。

要求：
1. 只提出“修改建议”。
2. 建议必须具体、可执行，避免空泛表达。
3. 可以从以下角度提出建议：
   - 高亮关键数据
   - 增加或删除标签、注释、参考线
   - 调整排序
   - 调整颜色编码、图例、坐标轴
   - 调整布局或信息层次
   - 更换图表类型
   - 突出答案相关的比较对象、趋势、异常点或极值
4. 给出1-2个建议即可。
5. 当任务不匹配时，才需要更换图表类型。
6. 输出必须是合法 JSON，不要输出任何额外文字。

请严格按照以下 JSON 格式输出：
{{
  "s1": "xxx",
  "s2": "xxxx"
}}

    问题：
    {question}

    答案：
    {answer}
    """.strip()

    data = get_vllm_messages(prompt, chart_base64)

    return data
def repaire_code(
    vis_code: str,
    re_info: str,
) -> str:
    """
    输入：原可视化代码 + 修改建议
    输出：结构化补丁信息（纯文本）
    """

    prompt = f"""
你是一个专业的 Python 可视化代码差分编辑助手。

你的任务：
根据“原始可视化代码”和“修改建议”，生成最小化的代码编辑补丁。
不要返回完整代码，只返回可程序处理的差分编辑结果。

你只能使用以下两种操作之一：
1. replace —— 替换已有代码片段
2. insert_after —— 在某段锚点代码之后插入代码

输出格式必须严格如下：

ACTION: <replace|insert_after>
TARGET:
<原代码中需要定位的代码片段，若是 replace 则填待替换片段，若是 insert_* 则填锚点片段>
NEW_CODE:
<替换后的代码或新增代码>

规则：
1. 优先选择 replace；只有在明显需要新增逻辑时才使用 insert_after。
2. TARGET 必须从原始代码中精确摘取，保证能被程序定位。
3. 不要输出解释、分析、原因、注释说明。
4. 不要输出 markdown 代码块。
5. 不要返回完整代码。
6. 不要修改与需求无关的任何代码。
7. 若修改建议可以通过局部参数调整完成，不要重写整段逻辑。

原始可视化代码：
{vis_code}

修改建议：
{re_info}

请严格按照指定格式输出。
""".strip()

    new_code = get_messages(prompt)

    return new_code

def parse_patch_text(patch_text: str) -> List[Dict[str, str]]:

    if not patch_text or not patch_text.strip():
        return None

    patch_text = re.sub(r"^```[a-zA-Z]*\s*", "", patch_text.strip())
    patch_text = re.sub(r"\s*```$", "", patch_text.strip())
    patch_text = patch_text.replace("\r\n", "\n").replace("\r", "\n")

    blocks = re.split(r"(?=^ACTION:\s*(?:replace|insert_before|insert_after)\s*$)", patch_text, flags=re.MULTILINE)

    patches = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        action_match = re.search(
            r"^ACTION:\s*(replace|insert_before|insert_after)\s*$",
            block,
            flags=re.MULTILINE,
        )
        if not action_match:
            return None

        action = action_match.group(1).strip()

        target_match = re.search(r"^TARGET:\s*$", block, flags=re.MULTILINE)
        new_code_match = re.search(r"^NEW_CODE:\s*$", block, flags=re.MULTILINE)

        if not target_match or not new_code_match:
            return None

        if target_match.end() > new_code_match.start():
            return None

        target = block[target_match.end():new_code_match.start()].strip("\n")
        new_code = block[new_code_match.end():].strip("\n")

        if not target or not new_code:
            return None

        patches.append({
            "action": action,
            "target": target,
            "new_code": new_code,
        })

    if not patches:
        return None

    return patches
def apply_single_patch_safe(vis_code: str, patch: Dict[str, str]) -> str:
    action = patch["action"]
    target = patch["target"]
    new_code = patch["new_code"]

    if vis_code.count(target) != 1:
        return vis_code

    if action == "replace":
        updated_code = vis_code.replace(target, new_code, 1)
    elif action == "insert_after":
        updated_code = vis_code.replace(target, target + "\n" + new_code, 1)
    else:
        return vis_code

    try:
        ast.parse(updated_code)
    except:
        return vis_code
    return updated_code
def apply_patches_safe(vis_code: str, patches: List[Dict[str, str]]) -> str:

    updated_code = vis_code
    for i, patch in enumerate(patches, start=1):
        try:
            updated_code = apply_single_patch_safe(updated_code, patch)
        except Exception as e:
            return vis_code
    return updated_code

def optimize_visualization_agent(
    vis_code: str,
    question: str,
    answer: str,
    max_iters: int = 3
) :
    """
    输入：待优化代码
    返回：优化后的代码
    """

    Cv_t = vis_code
    v_t = None
    O_t = []

    for t in range(max_iters):

        # -------------------------
        # 生成图表 v(t)
        # -------------------------
        try:
            chart_base64, chart_image = encode_vis_image(Cv_t)
            v_t = chart_base64
        except Exception:
            return Cv_t, v_t, O_t

        eval_result = check_task_fulfillment(v_t, Cv_t, question, answer)
        is_pass = eval_result.get("pass", False)


        if is_pass:
            O_t.append({})
            return Cv_t, v_t, O_t

        repair_info = get_repair_info(v_t, question, answer)
        repair_json = extract_json_from_llm_output(repair_info)

        # 若无建议直接退出
        if not repair_json:
            O_t.append({})
            return Cv_t, v_t, O_t

        O_t.append(repair_json)

        #修复
        new_code = Cv_t
        for value in repair_json.values():
            patch_text = repaire_code(new_code, value)
            patches = parse_patch_text(patch_text)
            if patches:
                new_code = apply_patches_safe(new_code, patches)

        # 若无变化则终止
        if new_code == Cv_t:
            return Cv_t, v_t, O_t

        Cv_t = new_code

    return Cv_t, v_t, O_t