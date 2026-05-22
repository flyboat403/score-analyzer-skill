#!/usr/bin/env python3
"""
Data cleaner for student score analysis.

Reads a long-format CSV, normalizes mixed-type values to floats,
handles grade mappings and absence indicators, and outputs a cleaned CSV
ready for numeric analysis.

Usage:
    python3 scripts/data_cleaner.py --input reports/data.csv --output reports/cleaned_data.csv
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

GRADE_MAP = {
    "a+": 95.0, "a": 95.0, "a-": 90.0,
    "b+": 85.0, "b": 85.0, "b-": 80.0,
    "c+": 75.0, "c": 75.0, "c-": 70.0,
    "d": 65.0,
    "e": 50.0, "f": 50.0,
}

ABSENT_KEYWORDS = {"缺考", "病假", "休学", "退学", "转学", "缓考", "免考"}

REQUIRED_COLS = {"student_id", "student_name", "subject", "value"}
OUTPUT_COLS = ["student_id", "student_name", "subject", "value"]


def parse_value(raw) -> float | None:
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None

    s = str(raw).strip()
    if s == "":
        return None

    lower = s.lower()
    if lower in GRADE_MAP:
        return GRADE_MAP[lower]

    if s in ABSENT_KEYWORDS:
        return None

    if s.endswith("%"):
        try:
            return float(s[:-1])
        except ValueError:
            return None

    try:
        return float(s)
    except ValueError:
        return None


def clean_data(input_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    df = pd.read_csv(input_path, dtype=str)

    # Column name alias mapping for common variations
    ALIAS_MAP = {
        "id": "student_id",
        "studentno": "student_id",
        "name": "student_name",
        "subjectname": "subject",
        "subject": "subject",
        "科目": "subject",
        "score": "value",
        "total_score": "value",
        "total": "value",
        "分数": "value",
        "成绩": "value",
        "班级": "student_class",
        "年级": "student_grade",
        "学校": "student_school",
        "专业": "student_major",
    }
    # Apply aliases (case-insensitive lookup)
    col_lower_map = {c.lower().strip(): c for c in df.columns}
    rename_map = {}
    for alias, standard in ALIAS_MAP.items():
        if alias.lower() in col_lower_map and standard not in df.columns:
            rename_map[col_lower_map[alias.lower()]] = standard
    df.rename(columns=rename_map, inplace=True)

    col_map = {c.lower(): c for c in df.columns}
    missing = [c for c in REQUIRED_COLS if c not in col_map]
    if missing:
        print(f"ERROR: Missing required column(s): {missing}")
        print(f"  Found columns: {list(df.columns)}")
        sys.exit(1)

    rename_map2 = {}
    for standard in REQUIRED_COLS:
        actual = col_map.get(standard)
        if actual and actual != standard:
            rename_map2[actual] = standard
    if rename_map2:
        df.rename(columns=rename_map2, inplace=True)

    parsed = df["value"].apply(parse_value)
    mask = parsed.notna()

    kept_count = int(mask.sum())
    dropped_count = int((~mask).sum())

    # Define columns to keep. Always keep ID, Name, Subject, Value.
    # Also keep Class/Major/School if they exist.
    keep_cols = ["student_id", "student_name", "subject"]
    optional_cols = ["student_class", "student_major", "student_school", "student_grade"]
    for opt in optional_cols:
        if opt in df.columns:
            keep_cols.append(opt)

    df_clean = df.loc[mask, keep_cols].copy()
    df_clean["value"] = parsed[mask].astype(float)

    df_clean.to_csv(output_path, index=False)

    print(f"Cleaned {kept_count} records. Dropped {dropped_count} non-numeric/absent records.")
    if kept_count == 0:
        print("WARNING: No valid numeric records remain after cleaning.")

    return df_clean


def main():
    parser = argparse.ArgumentParser(
        description="Clean mixed-type student score data to numeric-only CSV."
    )
    parser.add_argument("--input", required=True, help="Path to input long-format CSV.")
    parser.add_argument("--output", required=True, help="Path to cleaned output CSV.")
    args = parser.parse_args()
    clean_data(args.input, args.output)


if __name__ == "__main__":
    main()
