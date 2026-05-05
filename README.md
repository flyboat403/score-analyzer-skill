# Score Analyzer Skill

OpenCode skill for analyzing student Excel score sheets and generating professional analysis reports.

## Features

- **Data Extraction**: Parse Excel files with various header structures (simple/complex/merged)
- **Data Cleaning**: Handle A/B/C grades, absence marks ("缺考"), and invalid data
- **Smart Tagging**: Generate student tags like "偏科预警" (imbalanced subjects), "临界踩线" (borderline), etc.
- **Individual Reports**: Per-student "health check" HTML reports with personalized analysis
- **12 Chart Types**: Distribution, CDF, normal distribution, trend, heatmap, boxplot, scatter, deviation, top-bottom, comparison, radar
- **Professional Output**: Word (.docx) and HTML reports with embedded charts, packaged in ZIP
- **Local Processing**: No external LLM API needed - all analysis done by Agent intelligence

## Requirements

- Python 3.10+
- Dependencies: `pandas`, `matplotlib`, `seaborn`, `openpyxl`, `python-docx`, `numpy`, `scipy`
- Chinese fonts for charts: `fonts-noto-cjk` or `SimHei`/`Microsoft YaHei`

```bash
pip install pandas matplotlib seaborn openpyxl python-docx numpy scipy
apt install fonts-noto-cjk  # For Chinese chart labels
```

## Quick Start

### 1. Extract Data

```bash
# Simple headers
python3 scripts/extract_data.py --input test.xlsx --output reports/data.csv

# Complex headers (merged cells, multi-level) - use pandas directly
# Agent will handle column mapping automatically
```

### 2. Clean Data

```bash
python3 scripts/data_cleaner.py --input reports/data.csv --output reports/data.csv
```

### 3. Generate Tags (Recommended)

```bash
python3 scripts/tagger.py --input reports/data.csv --output reports/students_tags.csv
```

### 4. Generate Individual Reports

```bash
python3 scripts/individual_reports.py --input reports/data.csv --output reports/individual_reports
```

### 5. Generate Charts

```bash
python3 scripts/generate_charts.py --input reports/data.csv --output reports/charts/
```

### 6. Assemble Final Report

```bash
python3 scripts/assemble_reports.py --data reports/data.csv --charts reports/charts/ --report "reports/report_content.md" --output reports/
```

### 7. Deliver

Final output: `reports/report.zip`

## Workflow Overview

| Phase | Step | Script | Output |
|-------|------|--------|--------|
| 1 | Extract | `extract_data.py` | `data.csv` |
| 1 | Clean | `data_cleaner.py` | `cleaned_data.csv` |
| 1 | Tag | `tagger.py` | `students_tags.csv` |
| 1 | Individual | `individual_reports.py` | `individual_reports/*.html` |
| 2 | Analyze | Agent intelligence | `report_content.md` |
| 2 | Charts | `generate_charts.py` | `charts/*.png` |
| 2 | Assemble | `assemble_reports.py` | `report.docx`, `report.html` |
| 2 | Package | ZIP | `report.zip` |

## Chart Placeholders

When writing the Markdown report, include these placeholders:

| Category | Placeholder | Chart |
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

## Output Files

```
reports/
├── data.csv              # Normalized long-format data
├── students_tags.csv     # Student classification tags
├── charts/
│   ├── score_distribution.png
│   ├── cdf_curve.png
│   ├── normal_dist.png
│   ├── trend_line.png
│   ├── correlation_heatmap.png
│   ├── subj_boxplot.png
│   ├── scatter_regression.png
│   ├── top_bottom_bar.png
│   ├── deviation_bar.png
│   ├── class_comparison.png    # (if grouping exists)
│   ├── radar_chart.png         # (if grouping exists)
│   └── class_boxplot.png       # (if grouping exists)
├── individual_reports/
│   ├── student_001.html
│   ├── student_002.html
│   └── ...
├── report.docx           # Word document with embedded charts
├── report.html           # Standalone HTML with base64 charts
└── report.zip            # Final deliverable package
```

## Verification Checks

### Phase 1 Verification (Data Quality)

- ✓ Cleaned data file exists
- ✓ Data rows count reasonable (> 0, ≤ original)
- ✓ No empty/NaN values in score column
- ✓ Tag file generated
- ✓ Tags count matches student count

### Phase 2 Verification (Output Quality)

- ✓ Report contains "及格率" / "优秀率" keywords
- ✓ Report contains fine-grained score segments
- ✓ Chart count matches placeholders (12 or 9)
- ✓ Individual report count matches students
- ✓ HTML report contains embedded charts
- ✓ Word report size > 100KB
- ✓ Student/subject counts match between report and data

## Test Data

Sample Excel file available in `test/` directory:
- `test/2019高考成绩统计表（韩旭东).xlsx` - 31 students, 4 subjects

## Documentation

- `SKILL.md` - Skill trigger and workflow definition
- `AGENTS.md` - Technical implementation guide
- `references/analysis_prompt.md` - Report writing guidelines

## License

MIT License

## Author

Score Analyzer Skill - OpenCode Agent Skill Package