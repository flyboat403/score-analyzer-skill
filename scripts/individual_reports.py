#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import sys
import argparse
import io
import base64
from typing import Optional, Dict, Tuple, List

FONT_CANDIDATES = [
    "SimHei",
    "Microsoft YaHei",
    "WenQuanYi Micro Hei",
    "Noto Sans CJK SC",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/root/studyScoreExtract/方正仿宋_GB2312.ttf",
]


def setup_chinese_font() -> Optional[fm.FontProperties]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    assets_font = os.path.join(script_dir, "..", "assets", "思源黑体 CN Normal.otf")
    assets_font = os.path.abspath(assets_font)
    
    if os.path.exists(assets_font):
        try:
            return fm.FontProperties(fname=assets_font)
        except Exception:
            pass
    
    for font_name in FONT_CANDIDATES:
        if font_name.startswith('/'):
            if os.path.exists(font_name):
                try:
                    return fm.FontProperties(fname=font_name)
                except Exception:
                    continue
        else:
            try:
                return fm.FontProperties(family=font_name)
            except Exception:
                continue

    plt.rcParams['axes.unicode_minus'] = False
    return None


def fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return f"data:image/png;base64,{img_base64}"


def generate_radar_chart(
    student_scores: Dict[str, float],
    class_avgs: Dict[str, float],
    font_prop,
) -> str:
    subjects = sorted(student_scores.keys())
    values = [student_scores.get(s, 0) for s in subjects]
    avgs = [class_avgs.get(s, 0) for s in subjects]

    angles = np.linspace(0, 2 * np.pi, len(subjects), endpoint=False).tolist()
    angles += angles[:1]
    values += values[:1]
    avgs += avgs[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'),
                           facecolor='white')

    ax.plot(angles, values, 'o-', linewidth=2.5, color='#e74c3c', label='学生成绩',
            markersize=7, markerfacecolor='white', markeredgewidth=2)
    ax.fill(angles, values, alpha=0.2, color='#e74c3c')

    ax.plot(angles, avgs, 's--', linewidth=1.5, color='#95a5a6', label='班级平均',
            markersize=5)
    ax.fill(angles, avgs, alpha=0.1, color='#95a5a6')

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(subjects, fontproperties=font_prop, fontsize=10)

    max_val = max(values) * 1.15 if values else 120
    ax.set_ylim(0, max_val)
    ax.set_yticks(np.arange(0, max_val, max_val / 5))
    ax.set_yticklabels(
        [f'{int(v)}分' for v in np.arange(0, max_val, max_val / 5)],
        fontsize=8, fontproperties=font_prop
    )

    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(prop=font_prop, loc='upper left', fontsize=9)
    ax.set_title('学科能力雷达图', fontproperties=font_prop, fontsize=14,
                 fontweight='bold', pad=20)

    fig.tight_layout()
    return fig_to_base64(fig)


def generate_comparison_bar(
    student_scores: Dict[str, float],
    class_avgs: Dict[str, float],
    student_name: str,
    font_prop,
) -> str:
    subjects = sorted(student_scores.keys())
    student_vals = [student_scores.get(s, 0) for s in subjects]
    avg_vals = [class_avgs.get(s, 0) for s in subjects]

    fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')

    x = np.arange(len(subjects))
    bar_width = 0.3

    bars1 = ax.bar(x - bar_width / 2, student_vals, bar_width, label='学生成绩',
                   color='#3498db', edgecolor='#2980b9')
    bars2 = ax.bar(x + bar_width / 2, avg_vals, bar_width, label='班级平均',
                   color='#bdc3c7', edgecolor='#95a5a6')

    for bar in bars1:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., height + 1,
                    f'{height:.0f}', ha='center', va='bottom',
                    fontsize=9, fontweight='bold', color='#2980b9')

    for bar in bars2:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., height + 1,
                    f'{height:.1f}', ha='center', va='bottom',
                    fontsize=8, color='#7f8c8d')

    ax.set_ylabel('分数', fontproperties=font_prop, fontsize=11)
    ax.set_title(f'{student_name} - 学科成绩对比', fontproperties=font_prop,
                 fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(subjects, fontproperties=font_prop, rotation=20, ha='right')
    ax.legend(prop=font_prop, loc='upper right')
    ax.axhline(y=60, color='#e74c3c', linestyle='--', alpha=0.4, label='及格线')
    ax.grid(True, alpha=0.2, axis='y')

    fig.tight_layout()
    return fig_to_base64(fig)


def compute_overall_rating(total_score: float, all_totals: pd.Series) -> Tuple[str, str, str]:
    if total_score in all_totals.values:
        percentile = (all_totals < total_score).sum() / len(all_totals) * 100
    else:
        percentile = 0

    if percentile >= 90:
        return ("优秀", "🏆", "#2ecc71", "Top 10%")
    elif percentile >= 70:
        return ("良好", "👍", "#3498db", "Top 30%")
    elif percentile >= 50:
        return ("中等", "📊", "#f39c12", "Top 50%")
    else:
        return ("需努力", "💪", "#e74c3c", "Top 50% 之后")


def generate_subject_row(
    subject: str, score: float, class_avg: float
) -> Dict:
    deviation = round(score - class_avg, 1)
    if deviation > 10:
        status = "优秀"
        status_color = "#2ecc71"
    elif deviation > 0:
        status = "高于平均"
        status_color = "#3498db"
    elif deviation > -10:
        status = "接近平均"
        status_color = "#f39c12"
    else:
        status = "落后"
        status_color = "#e74c3c"

    return {
        "subject": subject,
        "score": round(score, 1),
        "class_avg": round(class_avg, 1),
        "deviation": f"+{deviation}" if deviation > 0 else str(deviation),
        "status": status,
        "status_color": status_color,
    }


def generate_commentary(
    student_scores: Dict[str, float],
    class_avgs: Dict[str, float],
    total_score: float,
    max_total: float,
) -> str:
    comments = []
    weak_subjects = []
    strong_subjects = []

    for subj, score in sorted(student_scores.items()):
        avg = class_avgs.get(subj, 0)
        diff = score - avg
        if diff > 10:
            strong_subjects.append((subj, diff))
            comments.append(
                f"<li><b>{subj}</b>：{score:.0f}分，高于班级平均{diff:.0f}分。表现优异，继续保持。</li>"
            )
        elif diff < -10:
            weak_subjects.append((subj, diff))
            comments.append(
                f"<li><b>{subj}</b>：{score:.0f}分，低于班级平均{abs(diff):.0f}分。"
                f"明显落后，建议寻找原因，加强基础。</li>"
            )
        elif diff < 0:
            comments.append(
                f"<li><b>{subj}</b>：{score:.0f}分，略低于班级平均{abs(diff):.0f}分。"
                f"有提升空间，继续努力。</li>"
            )
        else:
            comments.append(
                f"<li><b>{subj}</b>：{score:.0f}分，与班级平均持平或略高。"
                f"发挥稳定。</li>"
            )

    if strong_subjects and weak_subjects:
        strong_names = ', '.join([s for s, _ in strong_subjects])
        weak_names = ', '.join([s for s, _ in weak_subjects])
        comments.insert(0, (
            f'<div class="warning-box">⚠️ <b>偏科提醒：</b>'
            f'该生在 <span class="highlight-green">{strong_names}</span> 表现突出，'
            f'但在 <span class="highlight-red">{weak_names}</span> 明显落后。'
            f'建议合理分配学习时间，弥补短板。</div>'
        ))

    pct = (total_score / max_total * 100) if max_total > 0 else 0
    if pct >= 85:
        comments.insert(0, (
            '<div class="info-box">🌟 <b>综合评价：</b>'
            f'该生总分为{total_score:.0f}分（满分{max_total:.0f}分），'
            f'得分率{pct:.1f}%。整体表现优秀，是同学们的榜样。</div>'
        ))
    elif pct >= 70:
        comments.insert(0, (
            '<div class="info-box">📋 <b>综合评价：</b>'
            f'该生总分为{total_score:.0f}分（满分{max_total:.0f}分），'
            f'得分率{pct:.1f}%。整体表现良好，部分科目仍有提升空间。</div>'
        ))
    elif pct >= 50:
        comments.insert(0, (
            '<div class="info-box">📝 <b>综合评价：</b>'
            f'该生总分为{total_score:.0f}分（满分{max_total:.0f}分），'
            f'得分率{pct:.1f}%。基础尚可，建议查漏补缺，加强薄弱科目。</div>'
        ))
    else:
        comments.insert(0, (
            '<div class="info-box">⚠️ <b>综合评价：</b>'
            f'该生总分为{total_score:.0f}分（满分{max_total:.0f}分），'
            f'得分率{pct:.1f}%。学习需要更多关注和方法调整，建议制定详细学习计划。</div>'
        ))

    return '\n'.join(comments)


def build_html(
    student_id: str,
    student_name: str,
    student_class: str,
    student_major: str,
    total_score: float,
    max_total: float,
    rating: Tuple,
    radar_img: str,
    comparison_img: str,
    subject_rows: List[Dict],
    commentary: str,
    font_warning: bool,
) -> str:
    rating_label, rating_emoji, rating_color, rank_info = rating

    subject_rows_html = ""
    for row in subject_rows:
        dev_class = "dev-positive" if float(row["deviation"].replace("+", "")) > 0 else "dev-negative"
        subject_rows_html += f"""
        <tr>
            <td>{row['subject']}</td>
            <td class="score-cell">{row['score']}</td>
            <td>{row['class_avg']}</td>
            <td class="{dev_class}">{row['deviation']}</td>
            <td><span class="badge" style="background:{row['status_color']}">{row['status']}</span></td>
        </tr>"""

    font_warning_html = ""
    if font_warning:
        font_warning_html = '<div class="warning-box">⚠ 系统中文字体不可用，部分汉字可能显示为方块。</div>'

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{student_name} - 成绩体检单</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: "Noto Sans CJK SC", "Microsoft YaHei", "SimHei", sans-serif;
            background: #f0f2f5;
            color: #2c3e50;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{ font-size: 32px; margin-bottom: 8px; }}
        .header .subtitle {{ font-size: 14px; opacity: 0.85; }}
        .header .meta {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            font-size: 15px;
        }}
        .header .meta span {{ opacity: 0.9; }}
        .section {{ padding: 30px 40px; border-bottom: 1px solid #eee; }}
        .section:last-child {{ border-bottom: none; }}
        .section-title {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
        }}
        .summary-card {{
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .summary-card .label {{ font-size: 13px; color: #7f8c8d; margin-bottom: 8px; }}
        .summary-card .value {{ font-size: 28px; font-weight: bold; }}
        .summary-card .value {{ color: {rating_color}; }}
        .rating-badge {{
            display: inline-block;
            padding: 6px 16px;
            background: {rating_color};
            color: white;
            border-radius: 20px;
            font-size: 14px;
            margin-top: 4px;
        }}
        .chart-container {{
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            justify-content: center;
        }}
        .chart-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }}
        th {{ background: #f8f9fa; font-weight: 600; color: #34495e; }}
        tr:hover {{ background: #fafafa; }}
        .score-cell {{ font-weight: bold; font-size: 16px; }}
        .dev-positive {{ color: #27ae60; font-weight: bold; }}
        .dev-negative {{ color: #e74c3c; font-weight: bold; }}
        .badge {{
            padding: 4px 10px;
            border-radius: 12px;
            color: white;
            font-size: 12px;
        }}
        .info-box {{
            background: #e8f6f3;
            border-left: 4px solid #1abc9c;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 12px;
        }}
        .warning-box {{
            background: #fef5e7;
            border-left: 4px solid #f39c12;
            padding: 16px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 12px;
        }}
        .highlight-green {{ color: #27ae60; font-weight: bold; }}
        .highlight-red {{ color: #e74c3c; font-weight: bold; }}
        .commentary li {{ margin-bottom: 8px; }}
        .commentary ul {{ list-style: none; padding: 0; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #95a5a6;
            font-size: 12px;
            background: #f8f9fa;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .container {{ box-shadow: none; }}
            .section {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📋 学生成绩体检单</h1>
        <div class="subtitle">Student Score Health Check Report</div>
        <div class="meta">
            <span>👤 姓名：<b>{student_name}</b></span>
            <span>🆔 学号：<b>{student_id}</b></span>
            <span>🏫 {'班级：' + student_class if student_class else '专业：' + student_major}</span>
        </div>
    </div>

    <!-- Summary -->
    <div class="section">
        <div class="section-title">📊 成绩概览</div>
        <div class="summary-grid">
            <div class="summary-card">
                <div class="label">总分</div>
                <div class="value">{total_score:.0f}</div>
            </div>
            <div class="summary-card">
                <div class="label">满分</div>
                <div class="value" style="color:#95a5a6">{max_total:.0f}</div>
            </div>
            <div class="summary-card">
                <div class="label">综合评价</div>
                <div class="rating-badge">{rating_emoji} {rating_label} ({rank_info})</div>
            </div>
        </div>
    </div>

    {font_warning_html}

    <!-- Charts -->
    <div class="section">
        <div class="section-title">📈 可视化分析</div>
        <div class="chart-container">
            <div>
                <p style="text-align:center;font-weight:bold;color:#7f8c8d;margin-bottom:8px;">学科能力雷达图</p>
                <img src="{radar_img}" alt="雷达图" style="max-width:480px;">
            </div>
            <div>
                <p style="text-align:center;font-weight:bold;color:#7f8c8d;margin-bottom:8px;">学科对比（含班级均分）</p>
                <img src="{comparison_img}" alt="对比图" style="max-width:520px;">
            </div>
        </div>
    </div>

    <!-- Subject Analysis Table -->
    <div class="section">
        <div class="section-title">📝 学科详细分析</div>
        <table>
            <thead>
                <tr>
                    <th>科目</th>
                    <th>得分</th>
                    <th>班级均分</th>
                    <th>偏离</th>
                    <th>评价</th>
                </tr>
            </thead>
            <tbody>{subject_rows_html}
            </tbody>
        </table>
    </div>

    <!-- Commentary -->
    <div class="section">
        <div class="section-title">💬 智能评语</div>
        <div class="commentary">
            {commentary}
        </div>
    </div>
</div>

<div class="footer">
    本报告由系统自动生成，仅供参考 | Generated by Score Analyzer
</div>
</body>
</html>"""
    return html


def generate_individual_reports(csv_path: str, output_dir: str):
    df = pd.read_csv(csv_path)
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    font_prop = setup_chinese_font()
    font_warning = font_prop is None
    if font_warning:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    os.makedirs(output_dir, exist_ok=True)

    class_avgs = df.groupby('subject')['value'].mean().to_dict()

    student_totals = df.groupby(['student_id', 'student_name'])['value'].sum().reset_index()
    student_totals.columns = ['student_id', 'student_name', 'total']
    all_totals = student_totals['total']

    max_total = df.groupby(['student_id', 'student_name'])['value'].sum().max()

    count = 0
    for (sid, sname), student_df in df.groupby(['student_id', 'student_name']):
        s_class = ''
        s_major = ''
        first_row = student_df.iloc[0]
        if 'student_class' in first_row and pd.notna(first_row.get('student_class', None)):
            s_class = str(first_row['student_class']).strip()
        if 'student_major' in first_row and pd.notna(first_row.get('student_major', None)):
            s_major = str(first_row['student_major']).strip()

        group_display = s_class if s_class else s_major

        student_scores = {}
        for _, row in student_df.iterrows():
            subj = row['subject']
            val = row['value']
            if pd.notna(val):
                student_scores[subj] = float(val)

        total_score = sum(student_scores.values())

        rating = compute_overall_rating(total_score, all_totals)

        radar_img = generate_radar_chart(student_scores, class_avgs, font_prop)
        comparison_img = generate_comparison_bar(
            student_scores, class_avgs, sname, font_prop
        )

        subject_rows = []
        for subj in sorted(student_scores.keys()):
            score = student_scores[subj]
            avg = class_avgs.get(subj, 0)
            subject_rows.append(generate_subject_row(subj, score, avg))

        commentary = generate_commentary(student_scores, class_avgs, total_score, max_total)

        html = build_html(
            student_id=str(sid),
            student_name=str(sname),
            student_class=group_display,
            student_major=s_major,
            total_score=total_score,
            max_total=max_total,
            rating=rating,
            radar_img=radar_img,
            comparison_img=comparison_img,
            subject_rows=subject_rows,
            commentary=commentary,
            font_warning=font_warning,
        )

        safe_name = str(sname).replace('/', '_').replace('\\', '_')
        filename = f"{sid}_{safe_name}.html"
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        count += 1
        print(f"  [{count}] {filepath}")

    print(f"\nGenerated {count} individual reports in: {output_dir}")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Generate individual student health check reports (HTML)"
    )
    parser.add_argument("--input", "-i", required=True, help="Input CSV file path")
    parser.add_argument("--output", "-o", default="reports/individual_reports",
                        help="Output directory (default: reports/individual_reports)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading data from: {args.input}")
    df = pd.read_csv(args.input)
    print(f"Loaded {len(df)} records, {df['student_id'].nunique()} students")

    print(f"\nGenerating individual reports...")
    n = generate_individual_reports(args.input, args.output)

    if n == 0:
        print("Warning: No reports generated.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
