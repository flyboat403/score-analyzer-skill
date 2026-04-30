---
name: score-analyzer
description: >
  Analyze student score data from Excel files and generate professional analysis reports.
  Use when the user provides an Excel score sheet (.xlsx), asks to analyze student scores, test results,
  exam data, or grade data. The Agent performs all analysis directly using Python scripts (pandas, matplotlib)
  and its own intelligence for report writing—no external LLM API needed during execution.
  Supports data cleaning, statistical analysis, chart generation (score distribution, class comparison,
  radar, trends, boxplot, heatmap, deviation, top-bottom), narrative report writing, and ZIP package output.
  Triggers: "analyze scores", "score report", "exam analysis", "成绩分析", "成绩报告",
  "学生成绩", "score sheet", "upload excel for analysis", "analyze test results",
  "成绩统计", "前10名", "成绩对比", "班级成绩".
compatibility: Requires Python 3.10+, pandas, matplotlib, seaborn, openpyxl, python-docx, numpy, scipy
---

# Score Analyzer

Agent analyzes student Excel score sheets and produces professional reports. No external LLM API needed.

## Quick Start

When user provides an Excel file:

### Step 1: Extract Data (Agent uses LLM)

**Do NOT run `extract_data.py`**. Instead, use Python directly with pandas to read the Excel file:

```python
import pandas as pd
import openpyxl

# Read Excel structure to understand the layout
xl = pd.ExcelFile('input.xlsx')
for sheet in xl.sheet_names:
    df = pd.read_excel(xl, sheet_name=sheet, nrows=10)
    # Agent uses intelligence to identify:
    # - Header row location (by scanning for keywords like 学号/姓名/科目/分数)
    # - Column types (ID, name, class, subject scores)
    # - Score columns vs metadata columns
    # - Grouping dimensions (class/major/school)
```

Agent analyzes the raw data with Python, calculates statistics (mean, std, percentiles, correlations), and discovers patterns using its LLM intelligence.

### Step 2: Analyze + Write Report

Read `references/analysis_prompt.md` for detailed instructions. In short:

1. With the data loaded in Python, compute per-subject statistics and score distributions
2. **Discover patterns from the actual data**: subject strengths/weaknesses, distribution skew, correlations, top vs bottom performers
3. Write the full Markdown analysis report — cite specific numbers, explain what they mean, provide actionable improvement suggestions
4. Include chart placeholders (see template below) in the report

### Step 3: Generate Charts
```bash
python3 scripts/generate_charts.py --input reports/data.csv --output reports/charts/
```

### Step 4: Assemble Reports
```bash
python3 scripts/assemble_reports.py --data reports/data.csv --charts reports/charts/ --report "YOUR_MARKDOWN_REPORT" --output reports/
```

### Step 5: Deliver
Present `reports/report.zip` (contains .docx + .html + charts)

## Chart Placeholders & Template

**For the full report structure and analysis guidelines, READ:** [`references/analysis_prompt.md`](references/analysis_prompt.md)

**Mandatory Chart Placeholders** (use exact strings — scripts detect these via regex):
- General: `PLOT:DISTRIBUTION`, `PLOT:NORMAL`, `PLOT:TREND`, `PLOT:HEATMAP`, `PLOT:DEVIATION`, `PLOT:TOP_BOTTOM`
- Grouping-only: `PLOT:COMPARISON`, `PLOT:RADAR`, `PLOT:BOXPLOT` (Only include if `student_class`/`student_major`/`student_school` data exists!)

**NEVER** include Grouping-only placeholders if the Excel lacks grouping columns — they will fail to embed.

## 🔧 Decision Tree (Before Starting)

1. **Header Structure**:
   - Simple flat headers (Row 0 is headers) → You can optionally use `extract_data.py` backup.
   - **Complex/Merged headers** (Multi-level, Title rows) → **SKIP** `extract_data.py`. Use Agent's pandas/LLM intelligence directly to map columns.
2. **Chart Generation**:
   - Data has grouping column (class/major/school)? → Generate all **9** charts. Include ALL placeholders.
   - **NO grouping column**? → Generate **6** charts. **MUST REMOVE** `PLOT:COMPARISON`, `PLOT:RADAR`, and `PLOT:BOXPLOT` from the report.
3. **Chinese Font Check**:
   - If charts show squares (tofu): Run `fc-list :lang=zh`. If missing, install `apt install fonts-noto-cjk` → Re-generate charts.

## 🚨 Anti-Patterns (Critical Lessons)

- **NEVER pass minimal text** like `"Test Report"` to `assemble_reports.py`.
  *Why*: The script embeds EXACTLY what you pass. If the report content is short, the final docx/html will appear "empty". You MUST generate a full markdown analysis with statistics tables and narrative text.
- **NEVER include all 9 placeholders** when no grouping data exists.
  *Why*: `generate_charts.py` skips charts 7-9 if grouping is missing. Assembly will leave raw placeholder text in the document.
- **NEVER use `extract_data.py` for complex Excel files** (e.g., merged headers, sub-headers).
  *Why*: It fails on `IndexError` when detecting headers on complex layouts (we learned this the hard way!). Use pandas + Agent intelligence instead.
- **NEVER include `report.zip` in the zip archive**.
  *Why*: Recursive self-inclusion creates massive 3GB+ files. The script has been patched to skip this, but verify `create_zip_package` logic if modifying code.