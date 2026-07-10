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

def get_VisCoder_chat(prompt):

    import requests
    base_url = "http://210.40.16.205:34093"
    data = {
        "model": "VisCoder-7B",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }

    response = requests.post(f"{base_url}/v1/chat/completions", json=data, stream=False).json()
    content = response['choices'][0]['message']['content']

    return parse_llm_json(content)