#!/usr/bin/env python
# coding: utf-8

# In[ ]:
import argparse
import pandas as pd
from tqdm import tqdm
from model.llm import get_messages
from model.Agentic.Agentic_Framework import agentic_respomce
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
    parser.add_argument("--input",  default=r"C:\Users\wxf\Desktop\Text2Vis-main\data\Text2Vis.xlsx", help="Path to input Excel file")
    parser.add_argument("--output", default="C:\\Users\wxf\Desktop\Text2Vis-main\model\Agentic\\result_7b_second.xlsx", help="Path to save output Excel file")
    args = parser.parse_args()

    # === 1. 优先读取 output（断点续跑）===
    # if os.path.exists(args.output):
    #     print("🔁 Resume from existing output file")
    #     df = pd.read_excel(args.output)
    # else:
    #     print("🆕 Start from input file")
    #     df = pd.read_excel(args.input)[340:]

    df = pd.read_excel(args.input)[1805:]
    df = df.reset_index(drop=True)

    # 预先创建列，便于中途写盘
    if "Generated Answer" not in df.columns:
        df["Generated Answer"] = ""
    if "Generated Code" not in df.columns:
        df["Generated Code"] = ""

    start_idx = find_resume_index(df)
    print(f"🚀 Resume from row: {start_idx}")

    for i in tqdm(range(start_idx, len(df)), desc="Processing"):

        row = df.iloc[i]

        prompt = row["Prompt"]
        Table_Data=row["Table Data"]
        Question=row["Question"]
        result=get_messages(prompt)
        result=agentic_respomce(Table_Data,Question,result)

        df.at[row.name, "Generated Answer"] = result.get("Answer", "")
        import codecs

        code = result.get("Visualization Code") or ""
        code = codecs.decode(code, "unicode_escape", errors="backslashreplace")
        df.at[row.name, "Generated Code"] = code

        # 每 3 条写一次
        from openpyxl.utils.exceptions import IllegalCharacterError
        import os

        try:
            row_df = df.iloc[[row.name]]

            # 如果文件不存在，写入并包含表头
            if not os.path.exists(args.output):
                row_df.to_excel(args.output, index=False)
            else:
                # 追加写入（不写表头）
                from openpyxl import load_workbook

                with pd.ExcelWriter(
                        args.output,
                        engine="openpyxl",
                        mode="a",
                        if_sheet_exists="overlay"
                ) as writer:
                    start_row = writer.sheets["Sheet1"].max_row
                    row_df.to_excel(
                        writer,
                        index=False,
                        header=False,
                        startrow=start_row
                    )

            print(f"✅ 第 {i} 行写入成功")

        except IllegalCharacterError:
            print(f"❌ 第 {i} 行写入失败，已跳过")
            continue



if __name__ == "__main__":
    main()
