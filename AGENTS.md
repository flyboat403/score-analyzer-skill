# Score Analyzer Skill

OpenCode skill for analyzing student Excel score sheets and generating professional analysis reports.

## What This Is

A skill package—not a library or application. The SKILL.md defines triggers and workflow. Agent uses Python scripts for data processing and its own intelligence for report writing (no external LLM API).

## Workflow (Strict Order)

1. **Extract Data**: Agent reads the xlsx file directly with Python (pandas/openpyxl) or use `extract_data.py`. Save as `reports/data.csv` (Long Format: `student_id`, `student_name`, `subject`, `value`).
2. **Clean Data**: `python3 scripts/data_cleaner.py --input reports/data.csv --output reports/cleaned_data.csv`. (Handles "A/B/C", "缺考" cases). Use `cleaned_data.csv` for further steps.
3. **Tag Students (Optional but Recommended)**: `python3 scripts/tagger.py --input reports/cleaned_data.csv --output reports/students_tags.csv`. Produces "偏科预警", "临界踩线", etc.
4. **Generate Individual Reports**: `python3 scripts/individual_reports.py --input reports/cleaned_data.csv --output reports/individual_reports`. Produces HTML "体检单" per student.
5. **Analyze + Write Report**: Read `cleaned_data.csv` and `students_tags.csv` → find patterns → write Markdown with statistics and chart placeholders.
6. **Generate Charts**: `python3 scripts/generate_charts.py --input reports/cleaned_data.csv --output reports/charts/`.
7. **Assemble Reports**: `python3 scripts/assemble_reports.py --data reports/cleaned_data.csv --charts reports/charts/ --report "MARKDOWN" --output reports/`.
8. **Deliver**: `reports/report.zip` (contains .docx + .html + charts + individual reports CSV if added).

## Chart Placeholders

Use these exact placeholders in Markdown report:
- `![分数分布图](PLOT:DISTRIBUTION)` — subject score comparison (mean/max/min/median)
- `![分组对比图](PLOT:COMPARISON)` — class/group comparison (requires grouping data)
- `![雷达图](PLOT:RADAR)` — multi-subject radar (requires grouping data)
- `![成绩趋势图](PLOT:TREND)` — score segment distribution
- `![正态分布图](PLOT:NORMAL)` — normal distribution fit
- `![分组稳定性图](PLOT:BOXPLOT)` — class stability boxplot (requires grouping data)
- `![科目相关性图](PLOT:HEATMAP)` — subject correlation heatmap
- `![学生偏离度图](PLOT:DEVIATION)` — top10 deviation from mean
- `![尖子生对比图](PLOT:TOP_BOTTOM)` — top vs bottom quartile

**Note**: Radar/Comparison/Boxplot charts require grouping data (student_class/student_major/student_school). If no grouping available, these charts are skipped — resulting in 6-8 charts instead of 9.

## Environment

- Python 3.10+ required
- Dependencies: `pip install pandas matplotlib seaborn openpyxl python-docx numpy scipy`
- Setup script: `scripts/setup_env.sh` — validates environment
- Chinese fonts needed for charts: `fonts-noto-cjk` or `SimHei`/`Microsoft YaHei`
- If no Chinese font, charts display squares — warn user

## Data Extraction Edge Cases

- No `student_class` column → uses `student_major` or `student_school` as grouping
- No headers → heuristic parsing (Col0=ID, Col1=Name, Col2+=Scores)
- Empty sheets → silently skipped
- >20 sheets → only first 20 processed
- >30 columns → sheet skipped
- File names with spaces → auto-sanitized

## Output Files

- `reports/data.csv` — normalized long-format data
- `reports/charts/*.png` — 9 chart images
- `reports/report.docx` — Word document with embedded charts
- `reports/report.html` — standalone HTML with base64-embedded images
- `reports/report.zip` — final deliverable

## Assembly Script Usage (CRITICAL)

The `--report` flag accepts either inline markdown OR a file path:
- **File path**: `--report "reports/report_content.md"` (recommended for long reports)
- **Inline**: `--report "# 标题\n\n正文..."`

**CRITICAL**: You MUST write a FULL analysis report with statistics tables, narrative analysis, and chart placeholders. Passing minimal text (like "Test Report") results in empty docx/html with no analysis content. The `assemble_reports.py` embeds EXACTLY what you pass—it does NOT generate analysis.

## Key Constraints

- Agent writes analysis narrative—scripts only handle data/charts
- Never modify scripts unless fixing bugs
- `reports/` directory created automatically
- All scripts accept `--input` and `--output` CLI args