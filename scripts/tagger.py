#!/usr/bin/env python3
"""
Generate 重点关注名单 (Students to Watch List) from long-format score CSV.

Usage:
    python3 scripts/tagger.py --input reports/cleaned_data.csv --output reports/students_tag.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Tag thresholds (magic numbers — do not change without pedagogical review)
TOTAL_STRONG_PCT = 75
TOTAL_WEAK_PCT = 15
SUBJECT_WEAK_PCT = 25
SUBJECT_STRENGTH_PCT = 95
BORDERLINE_LOW = 55
BORDERLINE_HIGH = 65


def _safe_percentile_rank(series: pd.Series) -> pd.Series:
    if series.nunique() <= 1:
        return pd.Series(50.0, index=series.index)
    return series.rank(pct=True) * 100


def load_data(input_path: str | Path) -> pd.DataFrame:
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    df = pd.read_csv(input_path, dtype=str)
    col_map = {c.lower().strip(): c for c in df.columns}
    df.rename(columns={col_map[c.lower()]: c.lower() for c in df.columns}, inplace=True)

    required = {"student_id", "student_name", "subject", "value"}
    missing = required - set(df.columns)
    if missing:
        print(f"ERROR: Missing required columns: {missing}")
        print(f"  Found: {list(df.columns)}")
        sys.exit(1)

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"]).copy()

    if df.empty:
        print("WARNING: No valid numeric records after loading.")
        sys.exit(0)

    return df


def compute_percentiles(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    has_class = "student_class" in df.columns and df["student_class"].notna().any()

    if has_class:
        df["subject_pct"] = df.groupby(["student_class", "subject"])["value"].transform(
            _safe_percentile_rank
        )
    else:
        df["subject_pct"] = df.groupby("subject")["value"].transform(_safe_percentile_rank)

    pivot_cols = ["student_id", "student_name"]
    if has_class:
        pivot_cols.append("student_class")

    pivot = df.pivot_table(
        index=pivot_cols, columns="subject", values="value", fill_value=0, aggfunc="first"
    )

    total = pivot.sum(axis=1).to_frame("total_score").reset_index()
    df = df.merge(total, on=pivot_cols, how="left")

    if has_class:
        df["total_pct"] = df.groupby("student_class")["total_score"].transform(_safe_percentile_rank)
    else:
        df["total_pct"] = _safe_percentile_rank(df["total_score"])

    if has_class:
        subject_stats = df.groupby(["subject", "student_class"])["value"].agg(["mean", "std"])
    else:
        subject_stats = df.groupby("subject")["value"].agg(["mean", "std"])

    return df, subject_stats


def apply_tags(df: pd.DataFrame) -> pd.DataFrame:
    tags = pd.Series("", index=df.index)

    mask_imbalance = (df["total_pct"] > TOTAL_STRONG_PCT) & (df["subject_pct"] < SUBJECT_WEAK_PCT)
    tags[mask_imbalance] += "偏科预警;"

    mask_borderline = df["value"].between(BORDERLINE_LOW, BORDERLINE_HIGH)
    tags[mask_borderline] += "临界踩线;"

    mask_strength = df["subject_pct"] > SUBJECT_STRENGTH_PCT
    tags[mask_strength] += "优势明显;"

    mask_weak = df["total_pct"] < TOTAL_WEAK_PCT
    tags[mask_weak] += "全科预警;"

    tags = tags.str.rstrip(";")
    tags = tags.replace("", "无")

    df = df.copy()
    df["tags"] = tags
    return df


def print_summary(df: pd.DataFrame) -> None:
    all_tags = []
    for t in df["tags"]:
        if t and t != "无":
            all_tags.extend(t.split(";"))

    if not all_tags:
        print("\n── 标签统计 ──\n无学生被标记任何预警标签。")
        return

    tag_counts = pd.Series(all_tags).value_counts().sort_values(ascending=False)
    print("\n── 标签统计 ──")
    for tag, count in tag_counts.items():
        print(f"  {tag}: {count} 条记录")
    print(f"\n总计: {len(df[df['tags'] != '无'])} 条记录被标记 / {len(df)} 总记录数")

    print("\n── 涉及学生数 ──")
    for tag in tag_counts.index:
        students = df[df["tags"].str.contains(tag, na=False)]["student_id"].nunique()
        print(f"  {tag}: {students} 名学生")


def main():
    parser = argparse.ArgumentParser(
        description="Generate 重点关注名单 (Students to Watch List) from long-format score CSV."
    )
    parser.add_argument("--input", "-i", required=True, help="Path to input long-format CSV.")
    parser.add_argument("--output", "-o", required=True, help="Path to tagged output CSV.")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = load_data(args.input)
    print(f"Loaded {len(df)} records from {args.input}")

    df, _ = compute_percentiles(df)
    print("Percentiles computed.")

    df = apply_tags(df)
    print_summary(df)

    save_cols = ["student_id", "student_name", "subject", "value", "tags"]
    if "student_class" in df.columns:
        save_cols.insert(2, "student_class")

    df[save_cols].to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nTagged list saved to: {output_path}")


if __name__ == "__main__":
    main()
