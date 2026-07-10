from openai import OpenAI
import json
import re

def parse_llm_json(content: str) -> dict:
    """
    Robustly parse model output that is *supposed* to be JSON:
    - Removes markdown code fences ```json ... ```
    - Extracts the first {...} object if extra text exists
    - Converts Python triple-quoted code value to a JSON string
    - Falls back to regex extraction for answer/code if needed
    """
    if not content:
        return {}

    text = content.strip()

    # 1) Remove Markdown code fences if present
    # Handles ```json ... ``` or ``` ... ```
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)

    # 2) If there's extra text around, extract the first JSON object block
    # This is a simple brace-based heuristic.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1].strip()
    else:
        candidate = text

    # 3) Fix the common failure: code value uses Python triple quotes """..."""
    # Turn: "code": """ ... """  -->  "code": " ... "
    # (Also works if key is "code" but spacing differs)
    def _triple_quote_repl(m: re.Match) -> str:
        key = m.group(1)  # "code"
        body = m.group(2) # inside triple quotes
        # Escape as a valid JSON string
        body_escaped = json.dumps(body)[1:-1]  # remove surrounding quotes
        return f'"{key}": "{body_escaped}"'

    candidate_fixed = re.sub(
        r'"(code)"\s*:\s*"""\s*(.*?)\s*"""',
        _triple_quote_repl,
        candidate,
        flags=re.DOTALL
    )

    # 4) Try strict JSON parse now
    try:
        obj = json.loads(candidate_fixed)
        # Normalize keys to match your downstream expectations
        # (your script expects "Answer" and "Visualization Code")
        if "Answer" not in obj and "answer" in obj:
            obj["Answer"] = obj.get("answer", "")
        if "Visualization Code" not in obj and "code" in obj:
            obj["Visualization Code"] = obj.get("code", "")
        return obj
    except json.JSONDecodeError:
        pass

    # 5) Fallback: regex extract answer + code (handles even worse formatting)
    answer_match = re.search(r'"answer"\s*:\s*"([^"]*)"', candidate, flags=re.DOTALL)
    code_match = re.search(r'"code"\s*:\s*"(.*?)"', candidate, flags=re.DOTALL)
    triple_code_match = re.search(r'"code"\s*:\s*"""\s*(.*?)\s*"""', candidate, flags=re.DOTALL)

    answer = answer_match.group(1).strip() if answer_match else ""
    if code_match:
        code = code_match.group(1)
        # Unescape JSON-style backslashes if it was captured raw
        try:
            code = json.loads(f'"{code}"')
        except Exception:
            pass
    elif triple_code_match:
        code = triple_code_match.group(1)
    else:
        code = ""

    return {"Answer": answer, "Visualization Code": code}

def get_initial_responce(prompt):
    client = OpenAI(
        api_key="sk-30c2641a1f804eb2b3384b7bdde52c87",  # 请替换为你的 Qwen API Key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    try:
        completion = client.chat.completions.create(
            model="qwen2.5-7b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        raw_json_data = completion.model_dump_json()
        json_data = raw_json_data.strip("'")
        data = json.loads(json_data)  # 解析 JSON 数据
        content = data["choices"][0]["message"]["content"]
        result = parse_llm_json(content)
        return result

    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        return content
    except Exception as e:
        print(f"Error: {e}")
        return {}

def extract_target_json(llm_output: str):
    """
    从大模型输出中提取：
    {"Answer": "...", "Visualization Code": "..."}
    """

    # 1️⃣ 优先提取 ```json 代码块
    codeblock_pattern = re.compile(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        re.DOTALL | re.IGNORECASE
    )
    codeblocks = codeblock_pattern.findall(llm_output)

    candidates = []

    # 2️⃣ 如果存在代码块，优先解析代码块
    if codeblocks:
        candidates.extend(codeblocks)

    # 3️⃣ 如果没有代码块，尝试全文搜索 JSON
    if not candidates:
        brace_pattern = re.compile(r"\{.*?\}", re.DOTALL)
        candidates.extend(brace_pattern.findall(llm_output))

    # 4️⃣ 逐个尝试解析
    for candidate in candidates:
        cleaned = candidate.strip()

        # 修复常见错误
        cleaned = cleaned.replace("“", '"').replace("”", '"')
        cleaned = cleaned.replace("‘", "'").replace("’", "'")

        try:
            parsed = json.loads(cleaned)

            # 验证是否为目标格式
            if (
                isinstance(parsed, dict)
                and "Answer" in parsed
                and "Visualization Code" in parsed
            ):
                return parsed

        except json.JSONDecodeError:
            continue

    # 5️⃣ 失败时抛出异常
    print(llm_output)
    return llm_output

import json

def ensure_dict(obj):
    if isinstance(obj, dict):
        return obj

    if isinstance(obj, str):
        obj = obj.strip()

        # 空字符串
        if not obj:
            return {"Answer": "", "Visualization Code": ""}

        # 去掉 ```json 包裹
        if obj.startswith("```"):
            obj = obj.strip("`")
            obj = obj.replace("json", "", 1).strip()

        try:
            return json.loads(obj)
        except json.JSONDecodeError as e:
            print("JSON parse failed:", e)
            print("Raw content:", repr(obj))
            return {"Answer": obj, "Visualization Code": ""}

    return {"Answer": "", "Visualization Code": ""}



def agentic_respomce(Table_Data,Question,response) -> str:
    """
    调用通义千问(Qwen)并返回纯文本回复
    """
    prompt_template = """
    You are an expert in model response validation and refinement. Given a structured data table, Ground truth answer, a user-generated question, and an initial model response, your task is to validate and refihe model output for accuracy, correctness, and completeness.

    Input Data:
    * Data Table:{Table_Data}
    * Question:{Question}
    * Initial Model Response:{response}

    Task:
    1. Answer Validation: Verify correctness and identify errors if any.
    2. Visualization Code Validation: Check for syntax errors, readability issues, or execution problems.
    3. Refinement Task:
       * Based on the feedback, refine the model response to correct errors.
       * Ensure the response is precise, formatted correctly, and adheres to the required JSON format.

    Output Requirements:
    * Ensure the final output is in a valid JSON format without extra text or markdown formatting
    * The JSON structure must strictly follow the format below.

    Expected JSON Output Format:
    {{"Answer": "...", "Visualization Code": "..."}}
    """
    prompt = prompt_template.format(
        Table_Data=Table_Data,
        Question=Question,
        response=response
    )
    client = OpenAI(
        api_key="sk-f9f4c1673a7d4f3e8f1731a35946a276",  # 请替换为你的 Qwen API Key
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    completion = client.chat.completions.create(
        model="qwen2.5-7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        timeout=60,
        temperature=1
    )
    content=completion.choices[0].message.content
    content=extract_target_json(content)
    content=ensure_dict(content)
    return content


