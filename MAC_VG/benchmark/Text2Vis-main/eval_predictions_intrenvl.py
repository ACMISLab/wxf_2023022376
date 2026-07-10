#!/usr/bin/env python
# coding: utf-8
import os
import json
import base64
import argparse
import openai
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from openai import OpenAI
import os
import numpy as np
import matplotlib.pyplot as plt
import multiprocessing as mp
from pathlib import Path
import shutil
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def safe_int_conversion(response_text):
    try:
        return int(response_text.strip())
    except:
        return 0

def call_internvl(messages, top_p=0.8):
    """
    调用 InternVL 模型统一接口
    messages: OpenAI 格式的 message 列表
    return: 模型返回的文本内容
    """

    client = OpenAI(
        api_key="YOUR_API_KEY",
        base_url="base_url"
    )

    model_name = client.models.list().data[0].id

    response = client.chat.completions.create(
        model="InternVL3_5-38B",
        messages=messages,
        temperature=0,
        top_p=top_p
    )

    return response.choices[0].message.content

def evaluate_row(row, image_folder):

    # ========= 1️文本答案匹配 =========
    answer_prompt = f"""
    You are an expert evaluator. Based on the following rules, determine if the predicted answer matches the ground truth:

    Ground Truth Answer: "{row['Answer']}"
    Generated Answer: "{row['Generated Answer']}"

    Evaluation Criteria:
    1. Match if numbers are close (e.g., "48.77" vs "48.73") or equivalent percentages (e.g., "100%" vs "100").
    2. Match if ground truth appears within the generated response (e.g., "100" in "The result is 100").
    3. Match if core meaning remains the same, even with different phrasing for long answers.
    4. Allow minor spelling differences or abbreviations (e.g., "Albenia" vs "Albania", "USA" vs "United States").
    5. Do NOT match if meaning changes significantly (e.g., "Fragile" vs "Extreme fragility").

    Return only 1 if matched, else return 0. No explanation.
    """

    response_text = call_internvl(
        messages=[{
            "role": "user",
            "content": answer_prompt
        }]
    )

    answer_match = safe_int_conversion(response_text)

    # ========= 2图像评分 =========
    image_path = os.path.join(image_folder, f"{row['ID']}.png")

    if os.path.exists(image_path):

        encoded_img = encode_image(image_path)

        vis_prompt = f"""
            You are a visualization expert. Given the following, score the chart using the criteria below:

            Query: "{row['Question']}"
            Data Table: {row['Table Data']}

            Scoring:

            1. Readability and Quality Score (0–5)
                - Labels and Titles: Clear and positioned correctly?
                - Layout Spacing: Organized, uncluttered?
                - Color Accessibility: Are colors distinct and friendly?
                - Axis Scaling: Labeled and proportional?
                - Chart Type Suitability: Matches data type?
                - Font and Legends: Readable and aligned?
                - Annotations: Clear and non-overlapping?

            2. Chart Correctness Score (0–5)
                - Query Alignment: Chart answers the query?
                - Data Integrity: Values accurately shown?
                - Insight Representation: Insights clearly conveyed?
                - Missing Data Handling: Any misleading gaps?
                - Complexity Handling: Logical for multi-step queries?

            Scoring Guide:
            5.0 – Excellent: Clear, accurate, no issues.
            4.5 – Very Good: Minor issues, still clear.
            4.0 – Good: Small flaws, mostly fine.
            3.5 – Decent: Some clarity or accuracy issues.
            3.0 – Average: Noticeable issues affect clarity.
            2.5 – Below Avg: Issues may mislead.
            2.0 – Poor: Major clarity issues.
            1.5 – Very Poor: Nearly unreadable or wrong.
            1.0 – Unusable: Very unclear or misleading.
            0.0 – Failed: Completely irrelevant or broken.

            Return in strict JSON format only:
            {{"Readability and Quality Score": "...", "Chart Correctness Score": "..."}}"""

        vis_messages = [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": vis_prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{encoded_img}"
                    }
                }
            ]
        }]

        vis_response_text = call_internvl(vis_messages)

        try:
            if vis_response_text.startswith("```json"):
                vis_response_text = vis_response_text[7:-3].strip()

            parsed = json.loads(vis_response_text)

            readability_score = float(parsed.get("Readability and Quality Score", 0))
            correctness_score = float(parsed.get("Chart Correctness Score", 0))

        except Exception as e:
            print(f"JSON parse error for ID {row['ID']}: {e}")
            readability_score = 0
            correctness_score = 0

    else:
        readability_score = 0
        correctness_score = 0

    return pd.Series([answer_match, readability_score, correctness_score])

# ==============================
# 🔹 生成图表
# ==============================
# ---------- 子进程执行函数 ----------
def _exec_code(code, id_val, output_folder, queue):
    try:
        plt.close('all')

        def custom_show():
            fig_nums = plt.get_fignums()
            if fig_nums:
                fig = plt.figure(fig_nums[0])
                filename = os.path.join(output_folder, f"{id_val}.png")
                fig.savefig(filename)
                plt.close(fig)

        exec_env = {"plt": plt, "np": np}
        exec_env["plt"].show = custom_show

        exec(code, exec_env)

        # 防止用户没调用 show()
        if plt.get_fignums():
            custom_show()

        queue.put(("success", None))

    except Exception as e:
        queue.put(("error", str(e)))

# ---------- 主函数 ----------
def generate_charts(df, output_folder):
    error_ids = []
    os.makedirs(output_folder, exist_ok=True)

    for index, row in df.iterrows():
        code = row['Generated Code']
        id_val = row['ID']
        plt.close('all')
        print(id_val)

        def custom_show():
            try:
                fig_nums = plt.get_fignums()
                if fig_nums:
                    fig = plt.figure(fig_nums[0])
                    filename = os.path.join(output_folder, f"{id_val}.png")
                    fig.savefig(filename)
                    plt.close(fig)
            except Exception as e:
                print(f"Error saving figure for ID {id_val}: {e}")
                raise

        exec_env = {"plt": plt, "np": np}
        exec_env["plt"].show = custom_show

        try:
            exec(code, exec_env)
        except Exception as e:
            print(f"Execution error for ID {id_val}: {e}")
            error_ids.append(id_val)
            continue

        if plt.get_fignums():
            try:
                custom_show()
            except Exception as e:
                print(f"Saving error for ID {id_val}: {e}")
                error_ids.append(id_val)
                plt.close('all')
                continue

    return error_ids

# ==============================
# 🔹 主函数
# ==============================
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--chart_dir", default="t")
    args = parser.parse_args()

    df = pd.read_excel(args.input)
    error_ids = generate_charts(df, args.chart_dir)

    df["execution_result"] = df.index.to_series().apply(
        lambda idx: 0 if idx in error_ids else 1
    )

    for col in [
        "Answer Match",
        "Readability and Quality Score",
        "Chart Correctness Score",
        "Final Score"
    ]:
        if col not in df.columns:
            df[col] = np.nan

    N = 10

    for i, (idx, row) in enumerate(df.iterrows(), start=1):

        ans_match, rq_score, chart_score = evaluate_row(row, args.chart_dir)

        df.at[idx, "Answer Match"] = ans_match
        df.at[idx, "Readability and Quality Score"] = rq_score
        df.at[idx, "Chart Correctness Score"] = chart_score

        df.at[idx, "Final Score"] = 1 if (
            (df.at[idx, "Answer Match"] == 1) and
            (df.at[idx, "execution_result"] == 1) and
            (df.at[idx, "Readability and Quality Score"] >= 3.5) and
            (df.at[idx, "Chart Correctness Score"] >= 3.5)
        ) else 0

        df.to_excel(args.output, index=False)

        if (i % N == 0) or (i == len(df)):
            print(f"[{i}/{len(df)}] progress saved. last_row_index={idx}")

    print(f"Evaluation complete. Saved to {args.output}")
    # ===== 新增功能：重命名 chart_dir =====
    chart_path = Path(args.chart_dir)
    input_name = Path(args.input).stem  # 获取文件名（无扩展名）

    new_chart_path = chart_path.parent / f"chart_{input_name}"

    # 如果目标已存在，先删除（避免报错）
    if new_chart_path.exists():
        shutil.rmtree(new_chart_path)

    # 重命名目录
    chart_path.rename(new_chart_path)

    print(f"Chart directory renamed to: {new_chart_path}")



if __name__ == "__main__":
    main()
