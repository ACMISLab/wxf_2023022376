# -*- coding: utf-8 -*-

from pathlib import Path
import numpy as np
import pandas as pd


FILES = {

    "LLM-only": {
        "gpt": "gpt_eval_result_path",
        "internvl": "internvl_eval_result_path",
    },
    "VisCoder": {
        "gpt": "gpt_eval_result_path",
        "internvl": "internvl_eval_result_path",
    },
    "Agentic Inference": {
        "gpt": "gpt_eval_result_path",
        "internvl": "internvl_eval_result_path",
    },
    "Ours": {
        "gpt": "gpt_eval_result_path",
        "internvl": "internvl_eval_result_path",
    },
}

OUTPUT_FILE = "reliability_results.xlsx"

COLUMN_ALIASES = {
    "am": ["Answer Match"],
    "vcr": ["Readability and Quality Score"],
    "cc": ["Chart Correctness Score"],
    "fpr": ["Final Score"],
    # 如果文件里还有样本id，建议加上，会更稳
    "sample_id": ["ID"],
}


def normalize_col_name(col: str) -> str:
    return str(col).strip().lower().replace("\n", " ").replace("_", " ")


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    将原始表头标准化为 sample_id / am / vcr / cc / fpr
    """
    rename_map = {}
    norm_cols = {c: normalize_col_name(c) for c in df.columns}

    for std_name, aliases in COLUMN_ALIASES.items():
        alias_set = {normalize_col_name(a) for a in aliases}
        for raw_col, norm_col in norm_cols.items():
            if norm_col in alias_set:
                rename_map[raw_col] = std_name
                break

    df = df.rename(columns=rename_map)
    return df


def read_eval_file(path: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")

    df = pd.read_excel(path)
    df = standardize_columns(df)

    required = ["am", "vcr", "cc", "fpr"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name} 缺少字段: {missing}")

    keep_cols = [c for c in ["sample_id", "am", "vcr", "cc", "fpr"] if c in df.columns]
    df = df[keep_cols].copy()

    # 转为数值
    for col in ["am", "vcr", "cc", "fpr"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 如果 sample_id 存在，则保留；否则后面按行号对齐
    if "sample_id" in df.columns:
        df["sample_id"] = df["sample_id"].astype(str)

    return df


def align_two_results(df_gpt: pd.DataFrame, df_ivl: pd.DataFrame) -> pd.DataFrame:
    """
    优先按 sample_id 对齐；若无 sample_id，则按行号对齐
    输出字段：
    am_gpt, am_internvl, vcr_gpt, vcr_internvl, cc_gpt, cc_internvl, fpr_gpt, fpr_internvl
    """
    gpt = df_gpt.copy()
    ivl = df_ivl.copy()

    if "sample_id" in gpt.columns and "sample_id" in ivl.columns:
        merged = pd.merge(
            gpt,
            ivl,
            on="sample_id",
            how="inner",
            suffixes=("_gpt", "_internvl")
        )
    else:
        min_len = min(len(gpt), len(ivl))
        gpt = gpt.iloc[:min_len].reset_index(drop=True)
        ivl = ivl.iloc[:min_len].reset_index(drop=True)

        merged = pd.DataFrame({
            "row_id": np.arange(min_len),
            "am_gpt": gpt["am"],
            "am_internvl": ivl["am"],
            "vcr_gpt": gpt["vcr"],
            "vcr_internvl": ivl["vcr"],
            "cc_gpt": gpt["cc"],
            "cc_internvl": ivl["cc"],
            "fpr_gpt": gpt["fpr"],
            "fpr_internvl": ivl["fpr"],
        })
        return merged

    return merged


def agreement_rate(y1: pd.Series, y2: pd.Series) -> float:
    mask = y1.notna() & y2.notna()
    if mask.sum() == 0:
        return np.nan
    return (y1[mask].values == y2[mask].values).mean()


def cohens_kappa(y1: pd.Series, y2: pd.Series) -> float:
    """
    二分类/离散分类通用版本
    """
    mask = y1.notna() & y2.notna()
    y1 = y1[mask]
    y2 = y2[mask]

    if len(y1) == 0:
        return np.nan

    labels = sorted(set(y1.unique()).union(set(y2.unique())))
    po = (y1.values == y2.values).mean()

    pe = 0.0
    for label in labels:
        p1 = (y1 == label).mean()
        p2 = (y2 == label).mean()
        pe += p1 * p2

    if np.isclose(1 - pe, 0):
        return 1.0 if np.isclose(po, 1.0) else np.nan

    return (po - pe) / (1 - pe)


def spearman_corr(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() < 2:
        return np.nan
    return x[mask].corr(y[mask], method="spearman")


def mae(x: pd.Series, y: pd.Series) -> float:
    mask = x.notna() & y.notna()
    if mask.sum() == 0:
        return np.nan
    return (x[mask] - y[mask]).abs().mean()


def evaluate_one_method(method_name: str, gpt_file: str, internvl_file: str):
    df_gpt = read_eval_file(gpt_file)
    df_ivl = read_eval_file(internvl_file)
    merged = align_two_results(df_gpt, df_ivl)

    # 一致性指标
    result = {
        "method": method_name,
        "n_samples": len(merged),

        "AM_AR": agreement_rate(merged["am_gpt"], merged["am_internvl"]),
        "AM_Kappa": cohens_kappa(merged["am_gpt"], merged["am_internvl"]),

        "VCR_Spearman": spearman_corr(merged["vcr_gpt"], merged["vcr_internvl"]),
        "VCR_MAE": mae(merged["vcr_gpt"], merged["vcr_internvl"]),

        "CC_Spearman": spearman_corr(merged["cc_gpt"], merged["cc_internvl"]),
        "CC_MAE": mae(merged["cc_gpt"], merged["cc_internvl"]),

        "FPR_AR": agreement_rate(merged["fpr_gpt"], merged["fpr_internvl"]),
        "FPR_Kappa": cohens_kappa(merged["fpr_gpt"], merged["fpr_internvl"]),
    }

    # 各方法在两个评估器下的均值
    mean_scores = {
        "method": method_name,
        "AM_GPT": merged["am_gpt"].mean(),
        "AM_InternVL": merged["am_internvl"].mean(),
        "VCR_GPT": merged["vcr_gpt"].mean(),
        "VCR_InternVL": merged["vcr_internvl"].mean(),
        "CC_GPT": merged["cc_gpt"].mean(),
        "CC_InternVL": merged["cc_internvl"].mean(),
        "FPR_GPT": merged["fpr_gpt"].mean(),
        "FPR_InternVL": merged["fpr_internvl"].mean(),
    }

    return merged, result, mean_scores


def add_overall_row(all_pairs_df: pd.DataFrame, agreement_df: pd.DataFrame) -> pd.DataFrame:
    overall = {
        "method": "Overall",
        "n_samples": len(all_pairs_df),

        "AM_AR": agreement_rate(all_pairs_df["am_gpt"], all_pairs_df["am_internvl"]),
        "AM_Kappa": cohens_kappa(all_pairs_df["am_gpt"], all_pairs_df["am_internvl"]),

        "VCR_Spearman": spearman_corr(all_pairs_df["vcr_gpt"], all_pairs_df["vcr_internvl"]),
        "VCR_MAE": mae(all_pairs_df["vcr_gpt"], all_pairs_df["vcr_internvl"]),

        "CC_Spearman": spearman_corr(all_pairs_df["cc_gpt"], all_pairs_df["cc_internvl"]),
        "CC_MAE": mae(all_pairs_df["cc_gpt"], all_pairs_df["cc_internvl"]),

        "FPR_AR": agreement_rate(all_pairs_df["fpr_gpt"], all_pairs_df["fpr_internvl"]),
        "FPR_Kappa": cohens_kappa(all_pairs_df["fpr_gpt"], all_pairs_df["fpr_internvl"]),
    }

    agreement_df = pd.concat([agreement_df, pd.DataFrame([overall])], ignore_index=True)
    return agreement_df


def build_ranking_table(mean_df: pd.DataFrame) -> pd.DataFrame:
    """
    同时比较 AM / VCR / CC / FPR 在 GPT 与 InternVL 下的方法排名
    输出为长表：每个 metric 一组排名结果
    """
    metric_pairs = [
        ("AM", "AM_GPT", "AM_InternVL"),
        ("VCR", "VCR_GPT", "VCR_InternVL"),
        ("CC", "CC_GPT", "CC_InternVL"),
        ("FPR", "FPR_GPT", "FPR_InternVL"),
    ]

    all_rank_rows = []

    for metric_name, col_gpt, col_ivl in metric_pairs:
        sub_df = mean_df[["method", col_gpt, col_ivl]].copy()

        sub_df["Rank_GPT"] = sub_df[col_gpt].rank(ascending=False, method="min").astype(int)
        sub_df["Rank_InternVL"] = sub_df[col_ivl].rank(ascending=False, method="min").astype(int)
        sub_df["Same_Rank"] = sub_df["Rank_GPT"] == sub_df["Rank_InternVL"]
        sub_df["metric"] = metric_name

        sub_df = sub_df.rename(columns={
            col_gpt: "Score_GPT",
            col_ivl: "Score_InternVL"
        })

        sub_df = sub_df[[
            "metric", "method",
            "Score_GPT", "Score_InternVL",
            "Rank_GPT", "Rank_InternVL", "Same_Rank"
        ]]

        sub_df = sub_df.sort_values(["metric", "Rank_GPT", "method"]).reset_index(drop=True)
        all_rank_rows.append(sub_df)

    ranking_df = pd.concat(all_rank_rows, ignore_index=True)
    return ranking_df


def main():
    all_method_agreement = []
    all_method_means = []
    all_pairs = []

    for method, paths in FILES.items():
        merged, agreement_row, mean_row = evaluate_one_method(
            method_name=method,
            gpt_file=paths["gpt"],
            internvl_file=paths["internvl"],
        )
        merged["method"] = method
        all_pairs.append(merged)
        all_method_agreement.append(agreement_row)
        all_method_means.append(mean_row)

    agreement_df = pd.DataFrame(all_method_agreement)
    mean_df = pd.DataFrame(all_method_means)
    all_pairs_df = pd.concat(all_pairs, ignore_index=True)

    agreement_df = add_overall_row(all_pairs_df, agreement_df)
    ranking_df = build_ranking_table(mean_df)

    # 统一保留 4 位小数，便于论文表格使用
    float_cols_1 = [
        "AM_AR", "AM_Kappa", "VCR_Spearman", "VCR_MAE",
        "CC_Spearman", "CC_MAE", "FPR_AR", "FPR_Kappa"
    ]
    for c in float_cols_1:
        if c in agreement_df.columns:
            agreement_df[c] = agreement_df[c].round(4)

    float_cols_2 = [
        "AM_GPT", "AM_InternVL", "VCR_GPT", "VCR_InternVL",
        "CC_GPT", "CC_InternVL", "FPR_GPT", "FPR_InternVL"
    ]
    for c in float_cols_2:
        if c in mean_df.columns:
            mean_df[c] = mean_df[c].round(4)

    for c in ["FPR_GPT", "FPR_InternVL"]:
        if c in ranking_df.columns:
            ranking_df[c] = ranking_df[c].round(4)

    # 导出结果
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        agreement_df.to_excel(writer, sheet_name="agreement_metrics", index=False)
        mean_df.to_excel(writer, sheet_name="mean_scores_by_method", index=False)
        ranking_df.to_excel(writer, sheet_name="metric_rankings", index=False)
        all_pairs_df.to_excel(writer, sheet_name="paired_raw_data", index=False)

    print(f"结果已保存到: {OUTPUT_FILE}")
    print("\n=== 一致性指标 ===")
    print(agreement_df.to_string(index=False))

    print("\n=== 方法均值 ===")
    print(mean_df.to_string(index=False))

    print("\n=== 各指标排名对比 ===")
    print(ranking_df.to_string(index=False))


if __name__ == "__main__":
    main()