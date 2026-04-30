#!/usr/bin/env python3
"""
Standalone data extraction script for Excel score sheets.
Extracts student score data and outputs to CSV format.
"""

import pandas as pd
import re
import sys
import argparse
import os
from typing import List, Dict, Optional

# Grade extraction patterns
GRADE_PATTERNS = [
    (r'高[一二三]', lambda m: m.group(0)),
    (r'初[一二三]', lambda m: m.group(0)),
    (r'小学[一二三五六]', lambda m: m.group(0)),
    (r'(\d+)级', lambda m: m.group(0)),
]

def extract_grade_from_text(text: str) -> str:
    """Extract grade information from text."""
    if pd.isna(text):
        return ""
    text = str(text).strip()
    for pattern, handler in GRADE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return handler(match) if callable(handler) else match.group(1)
    return ""

def find_column_by_pattern(df, patterns: List[str], default_idx: Optional[int] = None) -> Optional[int]:
    """Find column index by pattern matching."""
    for row_idx in range(min(5, len(df))):
        for col_idx, cell_value in enumerate(df.iloc[row_idx]):
            cell_str = str(cell_value).strip()
            for pattern in patterns:
                if pattern in cell_str:
                    return col_idx
    return default_idx

def parse_sheet_with_llm_like_patterns(df_raw, sheet_name: str) -> tuple:
    """
    Parse sheet using pattern matching (simulating LLM logic without API).
    Returns: (header_row, sub_header_row, column_mappings)
    """
    column_mappings = {}

    # Detect header row (first row with "学号", "姓名", "序号", or "分数")
    header_row = None
    for idx in range(min(5, len(df_raw))):
        row_str = " ".join([str(cell) for cell in df_raw.iloc[idx]])
        row_str_normalized = row_str.replace("\u3000", "").replace(" ", "")
        if any(keyword in row_str_normalized for keyword in ["学号", "姓名", "序号", "分数", "成绩"]):
            # Verify this is a real header row (has multiple meaningful columns)
            non_empty_count = sum(1 for cell in df_raw.iloc[idx] 
                                  if pd.notna(cell) and str(cell).strip() and str(cell).strip() != "nan")
            if non_empty_count >= 3:  # Header should have at least 3 columns
                header_row = idx
                break

    if header_row is None:
        header_row = 0

    # Map columns by analyzing header and sub-header rows
    header_row_data = df_raw.iloc[header_row]
    potential_sub_header = df_raw.iloc[header_row + 1] if header_row + 1 < len(df_raw) else None
    
    # Detect if potential_sub_header is actually a sub-header (mostly strings) or data (mostly numbers)
    is_actual_sub_header = False
    if potential_sub_header is not None:
        string_count = sum(1 for cell in potential_sub_header 
                          if pd.notna(cell) and isinstance(cell, str) and len(str(cell).strip()) > 0)
        numeric_count = sum(1 for cell in potential_sub_header 
                           if pd.notna(cell) and isinstance(cell, (int, float)) and not isinstance(cell, bool))
        # Sub-header should have more strings than numbers
        is_actual_sub_header = string_count > numeric_count
    
    sub_header_row_data = potential_sub_header if is_actual_sub_header else None

    for col_idx in range(df_raw.shape[1]):
        header_text = str(header_row_data.iloc[col_idx]).strip()

        # Skip empty columns
        if not header_text or header_text in ["nan", "NaN"]:
            continue

        header_text_normalized = header_text.replace("\u3000", "").replace(" ", "")
        
        # Determine column type based on header text
        col_type = "other"
        subject = "student_info"

        if any(keyword in header_text_normalized for keyword in ["学号", "考号", "身份证", "ID", "序号", "编号"]):
            col_type = "id"
        elif any(keyword in header_text_normalized for keyword in ["姓名", "Name", "名字"]):
            col_type = "name"
        elif any(keyword in header_text for keyword in ["班级", "Class"]):
            col_type = "class"
        elif any(keyword in header_text for keyword in ["年级", "Grade"]):
            col_type = "grade"
        elif any(keyword in header_text for keyword in ["学校", "School"]):
            col_type = "school"
        elif header_text_normalized == "专业" or any(keyword in header_text_normalized for keyword in ["Major"]):
            col_type = "major"
        elif any(keyword in header_text_normalized for keyword in ["总分", "汇总", "Total", "平均分"]):
            col_type = "calculated"
        elif any(keyword in header_text_normalized for keyword in ["排名", "Rank", "名次"]):
            col_type = "rank"
        elif any(keyword in header_text_normalized for keyword in ["分数", "成绩", "Score"]):
            col_type = "score"
            subject = header_text
        else:
            # Fallback: treat unknown columns as potential score columns
            col_type = "score"
            subject = header_text

        column_mappings[col_idx] = {
            "type": col_type,
            "subject": subject,
            "header_text": header_text
        }

    sub_header_row = header_row + 1 if sub_header_row_data is not None else None

    return header_row, sub_header_row, column_mappings

def parse_no_header_sheet(df_raw, sheet_name: str) -> List[Dict]:
    """
    Heuristic parsing for tables without explicit headers.
    Col0 = ID, Col1 = Name, Col2+ = Scores
    """
    if df_raw.shape[0] < 3 or df_raw.shape[1] < 3:
        return []

    # Detect data start row
    data_start = 0
    for idx, row in df_raw.iterrows():
        numeric_count = sum(1 for val in row if pd.notna(val) and isinstance(val, (int, float)) and val > 0)
        if numeric_count >= 3:
            data_start = idx
            break

    if data_start == 0:
        return []

    df_data = df_raw.iloc[data_start:]
    rows = []
    grade = extract_grade_from_text(sheet_name)

    for idx, row in df_data.iterrows():
        # Validate first column as ID
        first_val = row.iloc[0]
        if pd.isna(first_val):
            continue
        try:
            int(first_val)
        except (ValueError, TypeError):
            continue

        # Validate second column as name
        name_val = row.iloc[1]
        if pd.isna(name_val) or str(name_val).strip() == "":
            continue

        student_name = str(name_val).strip()
        student_id = str(first_val)

        # Extract score columns
        num_cols = df_data.shape[1]
        score_cols = range(2, num_cols - 2) if num_cols > 4 else range(2, num_cols)

        for col_idx in score_cols:
            score_val = row.iloc[col_idx]
            if pd.isna(score_val):
                continue
            try:
                score = float(score_val)
                if score < 0 or score > 150:
                    continue
            except (ValueError, TypeError):
                continue

            subject_name = f"科目{col_idx - 1}"

            rows.append({
                "sheet_source": sheet_name,
                "student_id": student_id,
                "student_name": student_name,
                "student_class": "",
                "student_grade": grade,
                "student_school": "",
                "student_major": "",
                "subject": subject_name,
                "metric_type": "score",
                "value": score
            })

    return rows

def extract_rows(df_data, column_mappings, cols, sheet_name: str) -> List[Dict]:
    """Extract data rows based on column mappings."""
    rows = []
    student_id_col = cols.get('student_id_col')
    student_name_col = cols.get('student_name_col')
    student_class_col = cols.get('student_class_col')
    student_grade_col = cols.get('student_grade_col')
    student_school_col = cols.get('student_school_col')
    student_major_col = cols.get('student_major_col')

    for r_idx, row in df_data.iterrows():
        # Skip header rows
        first_val = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ""
        if any(keyword in first_val for keyword in ["姓名", "分数", "排名"]):
            continue

        # Extract student info
        student_id = row.iloc[student_id_col] if student_id_col is not None else f"Unknown-{sheet_name}-{r_idx}"
        student_name = row.iloc[student_name_col] if student_name_col is not None else "Unknown"
        student_class = row.iloc[student_class_col] if student_class_col is not None else ""
        student_school = row.iloc[student_school_col] if student_school_col is not None else ""
        student_major = row.iloc[student_major_col] if student_major_col is not None else ""

        # Clean string values
        if pd.isna(student_class):
            student_class = ""
        else:
            student_class = str(student_class).strip()

        if pd.isna(student_school):
            student_school = ""
        else:
            student_school = str(student_school).strip()

        if pd.isna(student_major):
            student_major = ""
        else:
            student_major = str(student_major).strip()

        # Extract grade
        if student_grade_col is not None and pd.notna(row.iloc[student_grade_col]):
            student_grade = str(row.iloc[student_grade_col]).strip()
        else:
            student_grade = extract_grade_from_text(student_class)
            if not student_grade:
                student_grade = extract_grade_from_text(sheet_name)

        # Skip invalid names
        if pd.isna(student_name) or str(student_name).strip() in ["", "--"]:
            continue

        # Extract scores
        for col_idx, mapping in column_mappings.items():
            col_type = mapping.get('type')
            subject = mapping.get('subject')

            if col_type == 'score':
                subj_str = str(subject)
                if any(keyword in subj_str for keyword in ["总分", "排名", "Total"]):
                    continue

                val = row.iloc[col_idx]
                if pd.isna(val) or str(val).strip() == "":
                    continue
                try:
                    float(val)
                except (ValueError, TypeError):
                    continue

                rows.append({
                    "sheet_source": sheet_name,
                    "student_id": student_id,
                    "student_name": student_name,
                    "student_class": student_class,
                    "student_grade": student_grade,
                    "student_school": student_school,
                    "student_major": student_major,
                    "subject": subject,
                    "metric_type": "score",
                    "value": val
                })

    return rows

def process_excel_file(file_path: str) -> pd.DataFrame:
    """Process entire Excel file and extract all data."""
    all_rows = []

    try:
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names
    except Exception as e:
        print(f"Error: Cannot read Excel file: {e}", file=sys.stderr)
        sys.exit(1)

    MAX_SHEETS = 20
    if len(sheet_names) > MAX_SHEETS:
        print(f"Warning: File has {len(sheet_names)} sheets. Only processing first {MAX_SHEETS}.")
        sheet_names = sheet_names[:MAX_SHEETS]

    MAX_COLUMNS = 30

    for sheet_name in sheet_names:
        try:
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=5)
        except Exception:
            continue

        if df_raw.shape[1] > MAX_COLUMNS:
            continue

        # Skip empty sheets (no rows)
        if df_raw.shape[0] == 0:
            continue

        # Parse sheet structure
        header_row, sub_header_row, column_mappings = parse_sheet_with_llm_like_patterns(df_raw, sheet_name)

        if not column_mappings:
            # Fallback: no-header parsing
            fallback_data = parse_no_header_sheet(df_raw, sheet_name)
            if fallback_data:
                all_rows.extend(fallback_data)
            continue

        # Identify special columns
        student_id_col = None
        student_name_col = None
        student_class_col = None
        student_grade_col = None
        student_school_col = None
        student_major_col = None

        for col_idx, mapping in column_mappings.items():
            col_type = mapping.get('type')
            if col_type == 'id':
                student_id_col = col_idx
            elif col_type == 'name':
                student_name_col = col_idx
            elif col_type == 'class':
                student_class_col = col_idx
            elif col_type == 'grade':
                student_grade_col = col_idx
            elif col_type == 'school':
                student_school_col = col_idx
            elif col_type == 'major':
                student_major_col = col_idx

        cols = {
            'student_id_col': student_id_col,
            'student_name_col': student_name_col,
            'student_class_col': student_class_col,
            'student_grade_col': student_grade_col,
            'student_school_col': student_school_col,
            'student_major_col': student_major_col
        }

        # Read data rows
        data_start_row = (sub_header_row if sub_header_row is not None else header_row) + 1
        df_data = pd.read_excel(file_path, sheet_name=sheet_name, header=None, skiprows=data_start_row)

        # Extract rows
        sheet_data = extract_rows(df_data, column_mappings, cols, sheet_name)
        all_rows.extend(sheet_data)

    return pd.DataFrame(all_rows)

def main():
    parser = argparse.ArgumentParser(description="Extract student score data from Excel file")
    parser.add_argument("--input", "-i", required=True, help="Input Excel file path (.xlsx)")
    parser.add_argument("--output", "-o", required=True, help="Output CSV file path")
    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    # Process file
    print(f"Processing: {args.input}")
    df = process_excel_file(args.input)

    if df.empty:
        print("Warning: No data extracted from file", file=sys.stderr)
    else:
        print(f"Extracted {len(df)} records")
        print(f"Columns: {df.columns.tolist()}")

    # Save to CSV
    df.to_csv(args.output, index=False, encoding='utf-8-sig')
    print(f"Saved to: {args.output}")

if __name__ == "__main__":
    main()