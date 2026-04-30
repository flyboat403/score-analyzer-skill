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

### Phase 1: Data Preparation
1.  **Extract**: `python3 scripts/extract_data.py --input <file> --output reports/data.csv`
2.  **Clean**: Remove invalid data/grades (A/B/C). **Must Run**: `python3 scripts/data_cleaner.py --input reports/data.csv --output reports/data.csv`
3.  **Tag (Recommended)**: `python3 scripts/tagger.py --input reports/data.csv --output reports/students_tags.csv` (Generates "偏科预警" etc.)
4.  **Individual Reports (Optional)**: `python3 scripts/individual_reports.py --input reports/data.csv --output reports/individual_reports`

### Phase 2: Analysis & Generation
1.  **Analyze**: Agent reads data, finds patterns, writes full Markdown report.
    - Read `references/analysis_prompt.md` for guidelines.
    - MUST include dynamic stats, fine-grained segments, and 12 chart placeholders.
2.  **Charts**: `python3 scripts/generate_charts.py --input reports/data.csv --output reports/charts/`
3.  **Assemble**: `python3 scripts/assemble_reports.py --data reports/data.csv --charts reports/charts/ --report "REPORT.md" --output reports/`
4.  **Deliver**: `reports/report.zip`

## Chart Placeholders & Template

**For the full report structure and analysis guidelines, READ:** [`references/analysis_prompt.md`](references/analysis_prompt.md)

**Mandatory Chart Placeholders** (ALL 12 maps MUST be included in the report — do NOT skip any!):
- **Overview**: `PLOT:DISTRIBUTION`, `PLOT:CDF`, `PLOT:NORMAL`
- **Comparison**: `PLOT:TREND`, `PLOT:HEATMAP`, `PLOT:BOXPLOT_SUBJ`
- **Gap/Spread**: `PLOT:SCATTER`, `PLOT:TOP_BOTTOM`, `PLOT:DEVIATION`
- **Grouped**: `PLOT:COMPARISON`, `PLOT:RADAR`, `PLOT:BOXPLOT`

**NEVER** include chart placeholders if chart generation failed — but ALWAYS ensure the markdown text includes exactly 12 placeholders if charts were generated successfully.

**NEVER** write a minimal text report. Must include dynamic passing rates, fine-grained segments, and granular actionable advice.

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