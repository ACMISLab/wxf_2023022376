#!/usr/bin/env python
# coding: utf-8

# In[ ]:
import argparse
import pandas as pd
from tqdm import tqdm
from model.Viscoder.VisCoder_7B import get_VisCoder_chat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="data/Text2Vis.xlsx", help="Path to input Excel file")
    parser.add_argument("--output", default="", help="Path to save output Excel file")
    args = parser.parse_args()
    df = pd.read_excel(args.input)
    # 预先创建列，便于中途写盘
    if "Generated Answer" not in df.columns:
        df["Generated Answer"] = ""
    if "Generated Code" not in df.columns:
        df["Generated Code"] = ""

    for i, (_, row) in enumerate(
        tqdm(df.iterrows(), total=len(df), desc="Processing"),
        start=1
    ):

        prompt = row["Prompt"]
        result=get_VisCoder_chat(prompt)

        df.at[row.name, "Generated Answer"] = result.get("Answer", "")
        """df.at[row.name, "Generated Code"] = (
            result.get("Visualization Code", "")
        ).encode().decode("unicode_escape")"""
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

            print(f"第 {i} 行写入成功")

        except IllegalCharacterError:
            print(f"第 {i} 行写入失败，已跳过")
            continue



if __name__ == "__main__":
    main()
