# 成绩分析技能（Score Analyzer Skill）

OpenCode 技能包，用于分析学生成绩 Excel 文件并生成专业分析报告。

## 功能特性

- **数据提取**：解析各种表头结构的 Excel 文件（简单/复杂/合并表头）
- **数据清洗**：处理 A/B/C 等级、"缺考"标记及无效数据
- **智能标签**：生成学生分类标签，如"偏科预警"、"临界踩线"等
- **个人报告**：为每位学生生成"体检单"式 HTML 报告
- **12种图表**：分布图、CDF、正态分布、趋势图、热力图、箱线图、散点图、偏差图、尖子生对比、班级对比、雷达图
- **专业输出**：Word (.docx) 和 HTML 报告，图表嵌入式打包为 ZIP
- **本地处理**：无需外部 LLM API，所有分析由 Agent 智能完成

## 环境要求

- Python 3.10+
- 依赖包：`pandas`, `matplotlib`, `seaborn`, `openpyxl`, `python-docx`, `numpy`, `scipy`
- 图表中文字体：`fonts-noto-cjk` 或 `SimHei`/`Microsoft YaHei`

```bash
pip install pandas matplotlib seaborn openpyxl python-docx numpy scipy
apt install fonts-noto-cjk  # 安装中文字体
```

## 快速开始

### 1. 提取数据

```bash
# 简单表头
python3 scripts/extract_data.py --input 成绩表.xlsx --output reports/data.csv

# 复杂表头（合并单元格、多级标题）- Agent 直接用 pandas 处理
```

### 2. 清洗数据

```bash
python3 scripts/data_cleaner.py --input reports/data.csv --output reports/data.csv
```

### 3. 生成标签（推荐）

```bash
python3 scripts/tagger.py --input reports/data.csv --output reports/students_tags.csv
```

### 4. 生成个人报告

```bash
python3 scripts/individual_reports.py --input reports/data.csv --output reports/individual_reports
```

### 5. 生成图表

```bash
python3 scripts/generate_charts.py --input reports/data.csv --output reports/charts/
```

### 6. 组装最终报告

```bash
python3 scripts/assemble_reports.py --data reports/data.csv --charts reports/charts/ --report "reports/report_content.md" --output reports/
```

### 7. 交付

最终输出：`reports/report.zip`

## 工作流程概览

| 阶段 | 步骤 | 脚本 | 输出 |
|------|------|------|------|
| 1 | 提取 | `extract_data.py` | `data.csv` |
| 1 | 清洗 | `data_cleaner.py` | `cleaned_data.csv` |
| 1 | 标签 | `tagger.py` | `students_tags.csv` |
| 1 | 个人报告 | `individual_reports.py` | `individual_reports/*.html` |
| 2 | 分析 | Agent 智能 | `report_content.md` |
| 2 | 图表 | `generate_charts.py` | `charts/*.png` |
| 2 | 组装 | `assemble_reports.py` | `report.docx`, `report.html` |
| 2 | 打包 | ZIP | `report.zip` |

## 图表占位符

撰写 Markdown 报告时，需嵌入以下占位符：

| 类别 | 占位符 | 图表说明 |
|------|--------|----------|
| 总体概览 | `PLOT:DISTRIBUTION` | 分数分布直方图 |
| | `PLOT:CDF` | 累积分布函数图 |
| | `PLOT:NORMAL` | 正态分布 Q-Q 图 |
| 横向对比 | `PLOT:TREND` | 各科目平均分趋势 |
| | `PLOT:HEATMAP` | 班级/科目成绩热力图 |
| | `PLOT:BOXPLOT_SUBJ` | 各科目箱线图 |
| 差距离散 | `PLOT:SCATTER` | 总分与各科散点图 |
| | `PLOT:TOP_BOTTOM` | 前N名与后N名对比 |
| | `PLOT:DEVIATION` | 成绩偏差分析图 |
| 分组分析* | `PLOT:COMPARISON` | 班际/组间对比 |
| | `PLOT:RADAR` | 班级雷达图 |
| | `PLOT:BOXPLOT` | 班级总分箱线图 |

*分组分析图表需要数据中包含分组列（班级/专业/学校）。

## 输出文件结构

```
reports/
├── data.csv              # 标准化长格式数据
├── students_tags.csv     # 学生分类标签
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
│   ├── class_comparison.png    # （如有分组）
│   ├── radar_chart.png         # （如有分组）
│   └── class_boxplot.png       # （如有分组）
├── individual_reports/
│   ├── student_001.html
│   ├── student_002.html
│   └── ...
├── report.docx           # Word 文档（图表嵌入式）
├── report.html           # 独立 HTML（base64 图表）
└── report.zip            # 最终交付包
```

## 验证检查项

### Phase 1 验证（数据质量）

- ✓ 清洗后数据文件存在
- ✓ 数据行数合理（> 0 且 ≤ 原始数据行数）
- ✓ 成绩列无空值/NaN
- ✓ 标签文件已生成
- ✓ 标签数与学生数匹配

### Phase 2 验证（输出质量）

- ✓ 报告包含动态及格率/优秀率计算（非固定60分阈值）
- ✓ 动态及格线基于百分位数（P80），题目极难时替代绝对及格率
- ✓ 报告包含精细分数段统计
- ✓ 图表数量与占位符匹配（12张或9张）
- ✓ 个人报告数量与学生数匹配
- ✓ HTML 报告包含嵌入式图表
- ✓ Word 报告文件大小 > 100KB
- ✓ 报告中提及的学生数/科目数与数据一致

## 文档说明

- `SKILL.md` - 技能触发和工作流程定义
- `references/analysis_prompt.md` - 报告撰写指南
- `scripts/` - Python 处理脚本

## 许可证

MIT License

## 作者

成绩分析技能 - OpenCode Agent 技能包