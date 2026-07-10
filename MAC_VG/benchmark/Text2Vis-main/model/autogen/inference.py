#!/usr/bin/env python
# coding: utf-8

# In[ ]:
import argparse
import pandas as pd
from tqdm import tqdm
from model.autogen.call import get_autogen_answer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",  default="C:\\Users\wxf\Desktop\Text2Vis-main\data\Text2Vis.xlsx", help="Path to input Excel file")
    parser.add_argument("--output", default="C:\\Users\wxf\Desktop\Text2Vis-main\\results_fuxian\\autogen\\autogen_results_14b.xlsx", help="Path to save output Excel file")
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
        Table_data = row["Table Data"]
        Question = row["Question"]



        prompt = f"""Datatable: 
        {Table_data}

        Question: 
        {Question}"""
        answer,code=get_autogen_answer(prompt)

        df.at[row.name, "Generated Answer"] = answer

        print(code)
        df.at[row.name, "Generated Code"] = code

        # 每 3 条写一次
        if i % 3 == 0:
            df.to_excel(args.output, index=False)

    # 兜底：确保最后不足 3 条也被写入
    df.to_excel(args.output, index=False)

if __name__ == "__main__":
    main()
