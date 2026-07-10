from ana_agent.exe_analysis import run_task_list
import argparse
from tqdm import tqdm
from ae_agent.answer_eval import answer_judge
from ana_agent.exe_visualiztion import generate_visualization
from vo_agent.optimizers import optimize_visualization_agent

import os
import pandas as pd

def find_resume_index(df):
    """
    从后往前查找恢复执行的位置：
    当前行三列全空 && 上一行至少一个不为空
    """
    cols = ["Generated Answer", "Generated Code"]

    for i in range(len(df) - 1, 0, -1):
        current_empty = all(
            pd.isna(df.iloc[i][c]) or df.iloc[i][c] == ""
            for c in cols
        )

        prev_not_empty = any(
            not (pd.isna(df.iloc[i - 1][c]) or df.iloc[i - 1][c] == "")
            for c in cols
        )

        if current_empty and prev_not_empty:
            return i

    # 如果没找到，说明：
    # 1. 可能从头开始
    # 2. 或全部已完成
    return 0
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="data/Text2Vis.xlsx")
    parser.add_argument("--output", default="results/result.xlsx")
    args = parser.parse_args()

    if os.path.exists(args.output):
        print("Resume from existing output file")
        df = pd.read_excel(args.output)
    else:
        print("Start from input file")
        df = pd.read_excel(args.input)

    for col in ["Generated Answer", "Generated Code"]:
        if col not in df.columns:
            df[col] = ""
    start_idx = find_resume_index(df)
    print(f"🚀 Resume from row: {start_idx}")

    print()
    for i in tqdm(range(start_idx, len(df)), desc="Processing"):
        row = df.iloc[i]
        data = row["Table Data"]
        question = row["Question"]

        print(f"[{i}] start answer_judge")
        o = answer_judge(question, data)

        if not o:
            a = None
        else:
            print(f"[{i}] start run_task_list")
            task_list = [{
                "task": question,
                "task_type": "analysis"
            }]
            initial_result = run_task_list(task_list, data, question)
            a = initial_result.get("final_result", "")

        df.at[i, "Generated Answer"] = a if a else "Unanswerable"
        print(f"[{i}] start generate_visualization")
        v_code = generate_visualization(data, question)

        if a is None:  # a = ∅
            optimized_code = v_code
        else:
            print(f"[{i}] start optimize_visualization")
            optimized_code, v_t, O_t = optimize_visualization_agent(
                vis_code=v_code,
                question=question,
                answer=a,
                max_iters=3
            )
            print(optimized_code)

        df.at[i, "Generated Code"] = optimized_code
        if i % 3 == 0:
            df.to_excel(args.output, index=False)
    df.to_excel(args.output, index=False)


if __name__ == "__main__":
    main()



