import json
from model.llm import get_messages
from ae_agent.check_json import check_json


# =========================
# Stage 1: 初步判定（o1, r1）
# =========================
def stage1_agent(question, schema):
    prompt = f"""
你是一个数据分析任务可回答性判断器。

你的任务是判断问题是否可以在给定数据中执行，并输出严格 JSON。

【判断标准】
1. 问题所需字段是否存在于 schema 中
2. 所需计算/操作（聚合、排序、趋势、分组等）是否可执行
3. 不允许引入外部数据

【输出必须严格 JSON 格式】
{{
  "o1": 0 or 1,
  "r1": "判断理由（必须引用schema字段）"
}}

定义：
- o1 = 1 表示可回答
- o1 = 0 表示不可回答

【输入】
Schema:
{schema}

Question:
{question}
"""
    result = get_messages(prompt)
    result = check_json(result)
    return json.loads(result)

# =========================
# Stage 2: 复核（仅针对 o1=0）
# =========================
def stage2_verifier(question, schema, r1):
    prompt = f"""
你是一个“不可回答性结论复核器”。

你的任务：
仅判断第一阶段给出的“不可回答(o1=0)”是否合理，而不是重新判断问题本身。

【输入】
Schema:
{schema}

Question:
{question}

Reason r1:
{r1}

【审核任务】
检查：
1. r1 是否正确引用 schema 字段
2. 是否存在误判（其实可以计算）
3. 是否逻辑一致

【输出严格 JSON】
{{
  "o2": 0 or 1,
  "explanation": "复核理由"
}}

定义：
- o2 = 1 → 支持不可回答结论
- o2 = 0 → 不支持不可回答结论
"""
    result = get_messages(prompt)
    result = check_json(result)
    return json.loads(result)
def AE_Agent(question, schema):
    # ---------- Stage 1 ----------
    stage1 = stage1_agent(question, schema)

    o1 = int(stage1.get("o1", 0))
    r1 = stage1.get("r1", "")

    # ---------- Stage 2 (conditional) ----------
    if o1 == 0:
        stage2 = stage2_verifier(question, schema, r1)
        o2 = int(stage2.get("o2", 0))
    else:
        o2 = 0  # 按报告约定：o1=1时不触发复核

    return o1, r1, o2
def coordinator(o1, o2):
    if o1 == 0 and o2 == 1:
        return 0
    return 1
def pipeline(question, schema):
    o1, r1, o2 = AE_Agent(question, schema)
    final_label = coordinator(o1, o2)

    return {
        "o1": o1,
        "r1": r1,
        "o2": o2,
        "label": final_label
    }
def answer_judge(question, schema):
    try:
        result = pipeline(question, schema)
        if not isinstance(result, dict):
            return True
        return False if result.get("label") == 0 else True

    except Exception as e:
        # 记录日志更重要
        print(f"[WARN] pipeline failed: {e}")
        return True