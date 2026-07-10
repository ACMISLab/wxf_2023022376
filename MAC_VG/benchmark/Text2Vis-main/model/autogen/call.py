from model.autogen.autogen import autogen_pipeline
import asyncio
import json,re


def extract_answer_and_code1(output):
    for msg in reversed(output.get("messages", [])):
        if not isinstance(msg, str):
            continue

        if '"answer"' in msg and '"code"' in msg:

            # 提取 answer
            answer_match = re.search(r'"answer"\s*:\s*"([^"]+)"', msg)

            # 提取 code（三引号包裹）
            code_match = re.search(r'"code"\s*:\s*"""(.*?)"""', msg, re.DOTALL)

            if answer_match and code_match:
                answer = answer_match.group(1)
                code = code_match.group(1)
                return answer, code

    return None, None


def extract_answer_and_code(messages):
    answer = "none"
    code = "none"

    # 第一次：从后往前找 InsightAgent 的 answer
    for msg in reversed(messages):
        if getattr(msg, "source", None) == "InsightAgent":
            content = getattr(msg, "content", "")
            try:
                data = json.loads(content)
                if isinstance(data, dict) and "answer" in data:
                    answer = data["answer"]
            except json.JSONDecodeError:
                # 如果不是标准 JSON，可以退回正则兜底
                match = re.search(r'"answer"\s*:\s*"(.*?)"', content, re.DOTALL)
                if match:
                    answer = match.group(1)
            break

    # 第二次：从后往前找 CodeAgent 的 python 代码
    for msg in reversed(messages):
        if getattr(msg, "source", None) == "CodeAgent":
            content = getattr(msg, "content", "")
            match = re.search(r"```python\s*(.*?)```", content, re.DOTALL)
            if match:
                code = match.group(1).strip()
            break

    return answer, code

def get_autogen_answer(instruction):

    model_config = {
        'model': "qwen2.5-14b-instruct",
        'api_key': "sk-f9f4c1673a7d4f3e8f1731a35946a276",
        'base_url': "https://dashscope.aliyuncs.com/compatible-mode/v1",
        'parameters': {'temperature': 0},
    }

    # instruction = """
    # You are a data science assistant.
    #
    # Given the following:
    # - A datatable:
    # Entity, 1986, 1988, 1990, 1992, 1994, 1996, 1998, 2000, 2002
    # First child, 107.3, 107.2, 108.6, 106.3, 106.1, 105.2, 106.2, 106.3, 106.5
    # Second child, 111.2, 113.3, 117.2, 112.6, 114.3, 109.8, 107.7, 107.4, 107.3
    # Third child, 138.6, 165.4, 190.8, 194.1, 205.9, 164.0, 144.1, 141.9, 140.1
    # Fourth child & higher, 149.9, 183.3, 214.1, 220.1, 237.7, 183.2, 152.0, 167.6, 153.3
    #
    # - A question:
    # Between 1986 and 2002, which entity experienced the greatest percentage decrease in value from its 1994 peak to 2002?
    #
    # Please:
    # 1. Carefully analyze the datatable and think step by step to answer the question.
    # 2. Provide the answer in the shortest possible form (e.g., a number, a word, or a short list of words or numbers separated by commas).
    # 3. Generate Python code that visualizes the result using **matplotlib only**.
    #
    # Return your response strictly in the following JSON format **without any extra explanation**:
    #
    # {
    #   "answer": "<short answer>",
    #   "code": "<matplotlib code for visualization>"
    # }
    #
    # The code should be complete, include axis labels and a title, and work without modification.
    # """

    result = asyncio.run(
        autogen_pipeline(
            instruction=instruction,
            savedir="C:\\Users\wxf\Desktop\Text2Vis-main\\result",
            model_config=model_config
        )
    )

    answer, code = extract_answer_and_code(result)
    print("********************************************")
    print(answer)
    print(code)
    return answer,code

