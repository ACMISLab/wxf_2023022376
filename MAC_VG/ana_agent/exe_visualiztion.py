import traceback
from typing import Any
from model.llm import get_messages
import re
import textwrap

def build_prompt(table: Any, task: str) -> str:
    """
    构造给 LLM 的提示词。
    要求 LLM 仅返回可直接执行的 Python 可视化代码，不要包含解释。
    """
    return f"""
你是一个数据可视化代码生成助手。

给定以下数据（table）和任务描述（task），请生成可直接执行的 Python 可视化代码。

要求：
1. 使用 pandas 处理数据。
2. 使用 matplotlib 进行可视化。
3. 不要输出解释，只输出完整可执行代码。
4. 代码最后必须包含 plt.show()。
5. 可视化简单一点。

数据：
{table}

任务描述：
{task}
"""

def execute_code(code: str, global_vars: dict) -> bool:
    """
    执行生成的代码。
    返回 True 表示成功，False 表示失败。
    彻底禁止弹出GUI窗口（强制使用无界面后端 + 移除 plt.show()）。
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # 强制无GUI后端（关键）
        import matplotlib.pyplot as plt

        # 保存原始代码
        original_code = code

        # 移除所有 plt.show()，仅用于执行阶段避免阻塞
        code_to_run = original_code.replace("plt.show()", "")

        exec(code_to_run, global_vars)

        # 执行成功后不修改原始代码（返回的仍然包含 plt.show()）

        # 执行完成后清理
        plt.close('all')
        return True

    except Exception:
        print("代码执行失败：")
        print(traceback.format_exc())
        try:
            import matplotlib.pyplot as plt
            plt.close('all')
        except Exception:
            pass
        return False

def _extract_code_block(text: str) -> str:
    """尽量从LLM输出中提取python代码块；若无代码块则返回原文。"""
    if not isinstance(text, str):
        return ""

    m = re.search(r"```(?:python|py)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text.strip()

def generate_visualization(table, task: str) -> str:
    """
    主函数：
    - 输入: table (DataFrame), task (str)
    - 输出: 成功执行的可视化代码 (str)
    - 过程:
        1. 调用 LLM 生成代码
        2. 尝试执行
        3. 若失败，附带错误信息重新请求 LLM
        4. 最多重试 max_retries 次
    """

    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns

    prompt = build_prompt(table, task)

    for attempt in range(1, 4):
        code = get_messages(prompt)
        code = _extract_code_block(code)
        code = textwrap.dedent(code).strip()  # 去除所有行的公共前导空白

        print("\nLLM 生成的代码：\n")
        print(code)

        global_vars = {
            "table": table,
            "pd": pd,
            "plt": plt,
            "sns": sns,
        }

        success = execute_code(code, global_vars)
        if success:
            print("\n代码执行成功！")
            return code

        # 如果失败，将错误信息追加到 prompt 中
        error_info = traceback.format_exc()
        prompt += f"""
上一次生成的代码执行失败，错误信息如下：
{error_info}
请修复代码并重新生成完整可执行代码。
"""
    print("\n已达到最大重试次数，仍未成功执行代码。返回最后一次生成的代码。")
    return None
