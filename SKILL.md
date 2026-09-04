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
    - **Complex/Merged headers** (Multi-level, Title rows) → **SKIP** `extract_data.py`. Agent must manually process and output `reports/data.csv` in **strict Long Format**:
      ```
      student_id,student_name,student_class,subject,value
      001,张三,一班,语文分数,85.0
      001,张三,一班,数学分数,92.0
      002,李四,一班,语文分数,88.0
      ```
      - Column names **MUST** be: `student_id`, `student_name`, `subject`, `value`
      - Format **MUST** be Long Format (one row per subject per student)
      - `value` **MUST** be numeric float
      - Python pattern to use:
        ```python
        df = pd.read_excel(file, header=n)  # n = header row index (try 0, 1, 2)
        df.rename(columns={'学号': 'student_id', '姓名': 'student_name'}, inplace=True)
        id_cols = ['student_id', 'student_name']
        if 'student_class' in df.columns:
            id_cols.append('student_class')
        df_long = df.melt(id_vars=id_cols, var_name='subject', value_name='value')
        df_long = df_long.dropna(subset=['value'])
        df_long['value'] = pd.to_numeric(df_long['value'], errors='coerce')
        df_long.to_csv('reports/data.csv', index=False)
        ```
      - **DO**: Output Long Format, use standard column names, handle merged cells
      - **DON'T**: Keep Wide Format (one column per subject), pass raw columns to data_cleaner
2.  **Clean**: Remove invalid data/grades (A/B/C). **Must Run**: `python3 scripts/data_cleaner.py --input reports/data.csv --output reports/data.csv`
3.  **Tag (Recommended)**: `python3 scripts/tagger.py --input reports/data.csv --output reports/students_tags.csv` (Generates "偏科预警" etc.)
4.  **Individual Reports (Optional)**: `python3 scripts/individual_reports.py --input reports/data.csv --output reports/individual_reports`
5.  **Dynamic Thresholds (MANDATORY)**: Calculate percentile-based passing/excellent thresholds.
    - `python3 scripts/dynamic_thresholds.py --input reports/data.csv --output reports/dynamic_thresholds.json`
    - Output JSON contains: D-G (P20 passing line), D-E (P80 excellent line), pass rates.
    - Read this file when writing the report — provides dynamic metrics to interpret difficult exams.
6.  **Verify Phase 1 (MANDATORY)**: Before proceeding to analysis, validate data quality:
    - **Cleaned data exists**: `reports/data.csv` (or `cleaned_data.csv`) file present?
    - **Data rows reasonable**: Count > 0 and ≤ original Excel rows?
    - **No empty values**: Check `value` column has no NaN/null entries?
    - **Tag file exists**: `students_tags.csv` generated?
    - **Tags match students**: Tag file rows = unique student count in data?
    - **Dynamic thresholds file**: `reports/dynamic_thresholds.json` generated?
    - If ANY check fails → fix data issues before continuing.

### Phase 2: Analysis & Generation

Before writing, ask yourself:
- **读者是谁**（校长/教研组长/班主任）？决定详略与措辞。
- **读者最关心的 3 个指标**（通常含及格率、优秀率、班级差异）— 必须显眼呈现。
- **数据中最反常的发现**（极端分数/异常缺考/班级断层）— 这是报告的"钩子"。

1.  **Analyze**: Agent reads data, finds patterns, writes full Markdown report.
    - **MANDATORY**: Read `reports/dynamic_thresholds.json` for percentile-based metrics.
    - **MANDATORY - READ ENTIRE FILE**: Read `references/analysis_prompt.md` (~430 lines) completely from start to finish before writing the report. NEVER set range limits when reading this file.
    - MUST include dynamic stats (D-G, D-E from JSON), fine-grained segments, and 12 chart placeholders.
    - ⚠️ CRITICAL: Chart placeholders MUST use inline format `![描述](PLOT:KEY)`. **NEVER use tables or appendix formats.** The assemble script only recognizes inline placeholders.
2.  **Charts**: `python3 scripts/generate_charts.py --input reports/data.csv --output reports/charts/`
3.  **Assemble**: `python3 scripts/assemble_reports.py --data reports/data.csv --charts reports/charts/ --report "REPORT.md" --output reports/`
4.  **Verify (MANDATORY)**: Before delivering, check ALL outputs:
    - **Dynamic passing/excellent rates** (NOT optional — MUST calculate):
        - Report contains "动态及格线" / "动态及格率" / "相对优秀线" keywords?
        - Passing line is percentile-based (P20, surpassing bottom 20%), NOT fixed 60-point threshold.
        - Excellent line is percentile-based (P80, entering top 20%).
    - **Fine-grained score segments**: Report.md contains segment stats (e.g., "90-100分", "80-89分")?
    - **Chart files**: `ls reports/charts/*.png | wc -l` equals 12 (or 11 if no grouping — radar skipped)?
    - **Chart file sizes**: Each PNG > 10KB (not empty/blank)? `ls -la reports/charts/*.png | awk '$5 < 10000 {print "TOO SMALL: "$0}'`
    - **HTML embedded images**: `reports/report.html` contains valid base64 charts?
        - Count: `grep -c 'data:image/png;base64' reports/report.html` equals PNG count (12, or 11 if no grouping)?
    - **Word embedded images**: Are charts actually embedded in `report.docx`?
        - Count: `python3 -c "from docx import Document; print(len(Document('reports/report.docx').element.xpath('.//a:blip')))"` equals PNG count (12, or 11 if no grouping)?
    - **Placeholder replacement complete**: No raw `PLOT:XXX` remains?
        - HTML: `grep -c 'PLOT:' reports/report.html` = 0?
    - ⚠️ Pre-assembly format check: Run `grep -c '!\[.*\](PLOT:' reports/report_content.md` → must equal the generated PNG count (12, or 11 if no grouping) before running assemble_reports.py. If result is 0, the report has placeholders in wrong format (e.g. table).
    - **Individual reports**: `ls reports/individual_reports/*.html | wc -l` equals student count?
    - **Word report**: Size > 100KB?
    - **Data consistency (Cross-Phase)**:
        - Student count in report matches data file row count?
        - Subject count in report matches unique subjects in data?
    - If ANY check fails → report issue to user before continuing.
5.  **Deliver**: `reports/report.zip`

## Chart Placeholders & Template

**For the full report structure and analysis guidelines, READ (MANDATORY — ENTIRE FILE):** [`references/analysis_prompt.md`](references/analysis_prompt.md) (~430 lines). Read completely from start to finish — NEVER set range limits or skim. **Do NOT load** `README.md`, `AGENTS.md`, or `test/` contents — development docs, not needed for execution.

**Chart Key Reference** (⚠️ 下表仅为 KEY 速查 — 裸键 `PLOT:XXX` 不能直接写入报告！必须使用完整行内格式 `![描述](PLOT:KEY)`。12 个 KEY 的完整行内格式以 `references/analysis_prompt.md`「图表-章节映射关系」表为唯一权威来源):

| Category | Key | Chart |
|----------|-------------|-------|
| Overview | `PLOT:DISTRIBUTION` | Score distribution histogram |
| | `PLOT:CDF` | Cumulative distribution function |
| | `PLOT:NORMAL` | Normal distribution Q-Q plot |
| Comparison | `PLOT:TREND` | Subject mean trends |
| | `PLOT:HEATMAP` | Class/subject heatmap |
| | `PLOT:BOXPLOT_SUBJ` | Subject box plots |
| Gap/Spread | `PLOT:SCATTER` | Total vs subject scatter |
| | `PLOT:TOP_BOTTOM` | Top vs bottom N comparison |
| | `PLOT:DEVIATION` | Score deviation analysis |
| Grouped* | `PLOT:COMPARISON` | Inter-class comparison |
| | `PLOT:RADAR` | Class radar chart |
| | `PLOT:BOXPLOT` | Class total box plot |

*Grouped placeholders require a grouping column (class/major/school) in the data.

**NEVER** leave a placeholder whose PNG was not generated — replace it with a one-line note (e.g. "因无分组数据，雷达图未生成"). Otherwise the raw `PLOT:XXX` text leaks into report.html and fails verification. Keep ALL other placeholders.

## 🔧 Decision Tree (Before Starting)

1. **Header Structure**: Follow Phase 1 Step 1 — flat headers may use `extract_data.py`; complex/merged headers MUST skip it (Agent processes manually, strict Long Format output).
2. **Chart Generation**:
   - Data has grouping column (class/major/school)? → All **12** charts generate. Include ALL 12 placeholders.
   - **NO grouping column**? → **11** PNGs: `PLOT:COMPARISON`/`PLOT:BOXPLOT` render "无分组数据" notice images (keep their placeholders); `PLOT:RADAR` gets NO PNG → remove its placeholder, note "因无分组数据，雷达图未生成" in place.
3. **Chinese Font Check**:
   - If charts show squares (tofu): Run `fc-list :lang=zh`. If missing, install `apt install fonts-noto-cjk` → Re-generate charts.

## 🚨 Anti-Patterns (Critical Lessons)

- **NEVER pass minimal text** like `"Test Report"` to `assemble_reports.py`.
  *Why*: The script embeds EXACTLY what you pass. If the report content is short, the final docx/html will appear "empty". You MUST generate a full markdown analysis with statistics tables and narrative text.
- **NEVER leave a placeholder whose PNG does not exist.** With no grouping column: `PLOT:COMPARISON`/`PLOT:BOXPLOT` render "无分组数据" notice images (PNGs exist — keep placeholders); `PLOT:RADAR` gets NO PNG — remove its placeholder and note "因无分组数据，雷达图未生成" in place.
  *Why*: Assembly silently drops missing-PNG placeholders in Word but leaks raw `PLOT:XXX` text into report.html, failing verification. (Aligned with Decision Tree #2 and analysis_prompt.md 通用规则.)
- **NEVER use `extract_data.py` for complex Excel files** (e.g., merged headers, sub-headers).
  *Why*: It fails on `IndexError` when detecting headers on complex layouts (we learned this the hard way!). Use pandas + Agent intelligence instead.
- **NEVER include `report.zip` in the zip archive**.
  *Why*: Recursive self-inclusion creates massive 3GB+ files. The script has been patched to skip this, but verify `create_zip_package` logic if modifying code.