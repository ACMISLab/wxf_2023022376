import io
import re
import json
import textwrap
import traceback
import contextlib
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from model.llm import get_messages
import multiprocessing

def _exec_target(queue, code, g):
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(code, g, g)
        queue.put(("ok", buf.getvalue()))
    except Exception:
        queue.put(("err", traceback.format_exc()))
def _exec_with_timeout(code: str, g: Dict[str, Any], timeout=10) -> str:
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_exec_target, args=(queue, code, g))
    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError("Code execution timeout")

    if not queue.empty():
        status, result = queue.get()
        if status == "ok":
            return result
        else:
            raise Exception(result)

    return ""
def _extract_code(text: str) -> str:
    m = re.search(r"```(?:python|py)?\s*([\s\S]*?)```", text or "", re.I)
    return (m.group(1) if m else text).strip()
def _normalize(out: Any) -> str:
    if isinstance(out, dict):
        return out.get("content") or out.get("message") or str(out)
    if isinstance(out, list):
        return "\n".join(map(str, out))
    return str(out)
def _exec(code: str, g: Dict[str, Any]) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, g, g)
    return buf.getvalue()
@dataclass
class StepRecord:
    task: str
    prompt: str
    code: str
    stdout: str
    error: Optional[str] = None
def _build_step_prompt(task, data, history, last_error=None) -> str:
    prompt = {
        "role": "developer",
        "instruction": {
            "goal": "生成Python代码完成当前任务。",
            "rules": [
                "只输出Python代码",
                "只能使用给定的 data",
                "结果用 print 输出"
            ],
            "context": {
                "data": data,
                "task": task.get("task"),
                "history": [
                    {"task": h.task, "stdout": h.stdout, "error": h.error}
                    for h in history
                ],
                "last_error": last_error
            }
        }
    }
    return json.dumps(prompt, ensure_ascii=False)
def _build_judge_prompt(question, records) -> str:
    prompt = {
        "role": "developer",
        "instruction": {
            "goal": "根据任务执行输出在语义上判断是否能回答问题。",
            "output": {"answered": "bool", "answer": "string"},
            "rules": ["只输出JSON"],
            "context": {
                "task": question,
                "output": records[-1].stdout if records else ""
            }
        }
    }
    return json.dumps(prompt, ensure_ascii=False)
def run_task_list(
    task_list: List[Dict[str, Any]],
    data: Any,
    question: Any,
    max_retries_per_task: int = 3,
) -> Dict[str, Any]:

    if not isinstance(task_list, list):
        return {"ok": False, "answered": False, "error": "task_list must be list"}

    records, all_code = [], []
    g = {"data": data, "question": question}

    for idx, task in enumerate(task_list):
        last_error = None

        for attempt in range(max_retries_per_task):
            prompt = _build_step_prompt(task, data, records, last_error)
            text = _normalize(get_messages(prompt))
            code = textwrap.dedent(_extract_code(text))

            rec = StepRecord(str(task.get("task", "")), prompt, code, "")

            try:
                #stdout = _exec(code, g)
                stdout = _exec_with_timeout(code, g, timeout=30)
                rec.stdout = stdout

                records.append(rec)
                all_code.append(code)
                break

            except TimeoutError:
                last_error = "Execution timeout"
                rec.error = last_error

                if attempt == max_retries_per_task - 1:
                    records.append(rec)
                    all_code.append(code)
                    return {
                        "ok": False,
                        "answered": False,
                        "error": f"task {idx} failed: {last_error}",
                        "final_output": None,
                    }

            except Exception:
                last_error = traceback.format_exc()
                rec.error = last_error

                if attempt == max_retries_per_task - 1:
                    records.append(rec)
                    all_code.append(code)
                    return {
                        "ok": False,
                        "answered": False,
                        "error": f"task {idx} failed: {last_error}",
                        "final_output": None,
                    }

    # judge
    judge_prompt=_build_judge_prompt(question, records)
    judge_ouput=get_messages(judge_prompt)
    judge_text = _normalize(judge_ouput)

    try:
        m = re.search(r"\{[\s\S]*\}", judge_text)
        judge_json = json.loads(m.group(0) if m else judge_text)
        answered = bool(judge_json.get("answered", False))
        answer = judge_json.get("answer", "")
    except Exception:
        answered, answer = False, ""

    return {
        "ok": True,
        "answered": answered,
        "answer": answer,
        "records": records,
        "all_code": all_code,
        "final_result": records[-1].stdout if records else "",
    }
