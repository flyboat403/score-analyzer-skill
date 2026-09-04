#!/usr/bin/env python3
"""
Standalone chart generation script for student score analysis.
Generates 9 different charts based on CSV data.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
import os
import sys
import argparse
from typing import Dict, Tuple, Optional

# Chart configuration
CHART_CONFIG = {
    "dpi": 150,
    "figure_bg": "white",
    "palette": {
        "mean": "#3498db",
        "max": "#2ecc71",
        "min": "#e74c3c",
        "median": "#f39c12",
    },
}

# Font candidates
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "Noto Sans CJK SC",
]

class ScoreAnalyzerV2:
    """Standalone score analyzer without external dependencies."""

    def __init__(self, df_clean: pd.DataFrame):
        self.df = df_clean.copy()
        self.df['value'] = pd.to_numeric(self.df['value'], errors='coerce')
        self._dynamic_thresholds: Optional[Dict[str, Dict[str, float]]] = None
        self._class_performance: Optional[pd.DataFrame] = None
        self._grouping_info: Optional[Dict[str, str]] = None

    def get_available_grouping(self) -> Dict[str, str]:
        """Detect available grouping dimensions."""
        groupings = {}
        group_priority = ['student_class', 'student_major', 'student_school', 'student_grade']
        group_labels = {
            'student_class': '班级',
            'student_major': '专业',
            'student_school': '学校',
            'student_grade': '年级'
        }

        for col in group_priority:
            if col in self.df.columns:
                unique_count = self.df[col].dropna().nunique()
                if unique_count > 1:
                    non_empty_count = self.df[col].dropna().count()
                    total_count = len(self.df)
                    coverage = non_empty_count / total_count if total_count > 0 else 0

                    if coverage >= 0.5:
                        groupings[col] = {
                            'label': group_labels[col],
                            'unique_count': unique_count,
                            'coverage': coverage
                        }

        self._grouping_info = groupings
        return groupings

    def get_best_grouping(self) -> Tuple[str, str]:
        """Return the best available grouping column and its label."""
        if self._grouping_info is None:
            self.get_available_grouping()

        if not self._grouping_info:
            return ('student_class', '班级')

        best_col = list(self._grouping_info.keys())[0]
        best_label = self._grouping_info[best_col]['label']
        return (best_col, best_label)

    def calculate_dynamic_thresholds(self, ratio_g: float = 0.6, ratio_e: float = 0.15) -> Dict[str, Dict[str, float]]:
        """Calculate dynamic thresholds for each subject."""
        thresholds = {}
        for subject in self.df['subject'].unique():
            subject_scores = self.df[self.df['subject'] == subject]['value'].dropna()
            if len(subject_scores) > 0:
                d_g = subject_scores.quantile(1 - ratio_g)
                d_e = subject_scores.quantile(1 - ratio_e)
                thresholds[subject] = {
                    'd_g': round(float(d_g), 2),
                    'd_e': round(float(d_e), 2),
                    'count': len(subject_scores)
                }
        self._dynamic_thresholds = thresholds
        return thresholds

    def calculate_class_performance(self) -> pd.DataFrame:
        """Calculate performance statistics by grouping and subject."""
        if self._dynamic_thresholds is None:
            self.calculate_dynamic_thresholds()

        if self._dynamic_thresholds is None:
            return pd.DataFrame()

        group_col, group_label = self.get_best_grouping()

        if group_col not in self.df.columns:
            return pd.DataFrame()

        results = []
        for (grp, subject), group in self.df.groupby([group_col, 'subject']):
            scores = group['value'].dropna()
            n = len(scores)
            if n == 0 or subject not in self._dynamic_thresholds:
                continue
            d_g = self._dynamic_thresholds[subject]['d_g']
            d_e = self._dynamic_thresholds[subject]['d_e']
            pass_count = (scores >= 60).sum()
            excellence_count = (scores >= 85).sum()
            dg_count = (scores >= d_g).sum()
            de_count = (scores >= d_e).sum()
            results.append({
                'class': grp,
                'group_label': group_label,
                'subject': subject,
                'count': n,
                'mean': round(scores.mean(), 2),
                'std': round(scores.std(), 2),
                'pass_rate': round(pass_count / n * 100, 2),
                'excellence_rate': round(excellence_count / n * 100, 2),
                'dg_rate': round(dg_count / n * 100, 2),
                'de_rate': round(de_count / n * 100, 2),
            })
        self._class_performance = pd.DataFrame(results)
        return self._class_performance

    def analyze_by_subject(self) -> pd.DataFrame:
        """Calculate statistics per subject."""
        stats = self.df.groupby('subject')['value'].agg(['count', 'mean', 'max', 'min', 'std', 'median'])
        stats['mean'] = stats['mean'].round(2)
        stats['std'] = stats['std'].round(2)
        return stats.reset_index()

    def get_wide_format(self) -> pd.DataFrame:
        """Convert long format to wide format with Total_Score."""
        df = self.df.copy()

        if df.empty or 'value' not in df.columns:
            df['Total_Score'] = 0
            return df

        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        group_col, group_label = self.get_best_grouping()

        index_cols = ['student_id', 'student_name']
        if group_col in df.columns and df[group_col].dropna().count() > 0:
            index_cols.append(group_col)

        pivot_df = df.pivot_table(
            index=index_cols,
            columns='subject',
            values='value',
            aggfunc='first'
        ).reset_index()

        subject_cols = [col for col in pivot_df.columns if col not in index_cols]

        if subject_cols:
            pivot_df['Total_Score'] = pivot_df[subject_cols].sum(axis=1, min_count=1)
        else:
            pivot_df['Total_Score'] = 0

        return pivot_df

    def analyze_score_trend(self) -> pd.DataFrame:
        """Score segment distribution by subject."""
        results = []
        for subject in self.df['subject'].unique():
            scores = self.df[self.df['subject'] == subject]['value'].dropna()
            total = len(scores)
            results.append({
                '科目': subject,
                '60分以下': round((scores < 60).sum() / total * 100, 1) if total > 0 else 0,
                '60-69分': round(((scores >= 60) & (scores < 70)).sum() / total * 100, 1) if total > 0 else 0,
                '70-79分': round(((scores >= 70) & (scores < 80)).sum() / total * 100, 1) if total > 0 else 0,
                '80-89分': round(((scores >= 80) & (scores < 90)).sum() / total * 100, 1) if total > 0 else 0,
                '90分以上': round((scores >= 90).sum() / total * 100, 1) if total > 0 else 0,
                '总人数': total
            })
        return pd.DataFrame(results)

    def analyze_class_stability(self) -> pd.DataFrame:
        """Box plot statistics by grouping."""
        results = []
        group_col, group_label = self.get_best_grouping()

        if group_col not in self.df.columns:
            return pd.DataFrame()

        for (grp, subj), group in self.df.groupby([group_col, 'subject']):
            scores = group['value'].dropna()
            if len(scores) < 4:
                continue
            q1 = scores.quantile(0.25)
            q3 = scores.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers = ((scores < lower) | (scores > upper)).sum()
            results.append({
                '分组': grp,
                'group_label': group_label,
                '科目': subj,
                '均值': round(scores.mean(), 1),
                'Q1': round(q1, 1),
                'Q3': round(q3, 1),
                'IQR': round(iqr, 1),
                '最小值': round(scores.min(), 1),
                '最大值': round(scores.max(), 1),
                '异常值数': int(outliers)
            })
        return pd.DataFrame(results)

    def analyze_subject_correlation(self) -> pd.DataFrame:
        """Subject correlation matrix."""
        wide = self.get_wide_format()
        group_col, _ = self.get_best_grouping()
        index_cols = ['student_id', 'student_name']
        if group_col in wide.columns:
            index_cols.append(group_col)
        subject_cols = [c for c in wide.columns if c not in index_cols + ['Total_Score']]
        if len(subject_cols) < 2:
            return pd.DataFrame()
        corr_matrix = wide[subject_cols].corr()
        return corr_matrix.round(3)


class ChartGenerator:
    """Generate charts for score analysis."""

    def __init__(self, analyzer: ScoreAnalyzerV2, output_dir: str, font_path: Optional[str] = None):
        self.analyzer = analyzer
        self.output_dir = output_dir
        
        if font_path:
            self.font_path = font_path
        else:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.font_path = os.path.join(script_dir, "..", "assets", "思源黑体 CN Normal.otf")
        
        self.font_prop, font_found = self._setup_chinese_font()
        self.font_warning = not font_found
        self.max_mean = 100
        os.makedirs(self.output_dir, exist_ok=True)

    def _setup_chinese_font(self) -> Tuple:
        """Setup Chinese font for matplotlib charts."""
        font_found = False
        font_prop = None

        # Try config path
        if self.font_path and os.path.exists(self.font_path):
            try:
                font_prop = fm.FontProperties(fname=self.font_path)
                font_found = True
            except Exception:
                pass

        # Try system fonts
        if not font_found:
            for font_name in FONT_CANDIDATES:
                if font_name.startswith('/'):
                    if os.path.exists(font_name):
                        try:
                            font_prop = fm.FontProperties(fname=font_name)
                            font_found = True
                            break
                        except Exception:
                            continue
                else:
                    try:
                        font_prop = fm.FontProperties(family=font_name)
                        font_found = True
                        break
                    except Exception:
                        continue

        if font_found:
            plt.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'Noto Sans CJK JP', font_prop.get_name()]
            plt.rcParams['font.family'] = 'sans-serif'
        else:
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

        plt.rcParams['axes.unicode_minus'] = False
        return font_prop, font_found

    def plot_score_distribution(self, save=True):
        """Plot score distribution (grouped bar chart)."""
        fig, ax = plt.subplots(figsize=(14, 6))

        try:
            stats_df = self.analyzer.analyze_by_subject()

            if stats_df.empty:
                ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                        transform=ax.transAxes, fontproperties=self.font_prop)
            else:
                subjects = stats_df['subject'].tolist()
                x = np.arange(len(subjects))
                bar_width = 0.18

                means = stats_df['mean'].values
                maxes = stats_df['max'].values
                mins = stats_df['min'].values
                medians = stats_df['median'].values

                rects1 = ax.bar(x - 1.5 * bar_width, means, bar_width, label='平均分',
                               color=CHART_CONFIG["palette"]["mean"], edgecolor='black', alpha=0.8)
                rects2 = ax.bar(x - 0.5 * bar_width, maxes, bar_width, label='最高分',
                               color=CHART_CONFIG["palette"]["max"], edgecolor='black', alpha=0.8)
                rects3 = ax.bar(x + 0.5 * bar_width, mins, bar_width, label='最低分',
                               color=CHART_CONFIG["palette"]["min"], edgecolor='black', alpha=0.8)
                rects4 = ax.bar(x + 1.5 * bar_width, medians, bar_width, label='中位数',
                               color=CHART_CONFIG["palette"]["median"], edgecolor='black', alpha=0.8)

                ax.set_xlabel('科目', fontproperties=self.font_prop, fontsize=12)
                ax.set_ylabel('分数', fontproperties=self.font_prop, fontsize=12)
                ax.set_title('科目成绩对比分析 (平均/最高/最低/中位)', fontproperties=self.font_prop,
                           fontsize=14, fontweight='bold')
                ax.set_xticks(x)
                ax.set_xticklabels(subjects, fontproperties=self.font_prop, rotation=45, ha='right')
                ax.legend(prop=self.font_prop, loc='upper right', bbox_to_anchor=(1.12, 1.05))
                ax.grid(True, alpha=0.3, axis='y')
                ax.set_ylim(0, max(100, maxes.max() * 1.1) if len(maxes) > 0 else 100)

        except Exception as e:
            ax.text(0.5, 0.5, f'图表生成失败:\n{str(e)}', ha='center', va='center',
                   fontsize=12, transform=ax.transAxes, fontproperties=self.font_prop)

        path = os.path.join(self.output_dir, 'score_distribution.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_class_comparison(self, save=True):
        """Plot class comparison chart."""
        fig, ax = plt.subplots(figsize=(12, 6))
        class_perf = self.analyzer.calculate_class_performance()

        if class_perf.empty:
            ax.text(0.5, 0.5, '无分组对比数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'class_comparison.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        group_label = class_perf['group_label'].iloc[0] if 'group_label' in class_perf.columns else '班级'
        subjects = class_perf['subject'].unique()
        classes = class_perf['class'].unique()
        x = np.arange(len(classes))
        width = 0.6 / len(subjects)

        for i, subj in enumerate(subjects):
            subj_data = class_perf[class_perf['subject'] == subj]
            means = subj_data.set_index('class').reindex(classes)['mean'].fillna(0)
            ax.bar(x + i * width, means, width, label=subj)

        ax.set_xlabel(group_label, fontproperties=self.font_prop)
        ax.set_ylabel('平均分', fontproperties=self.font_prop)
        ax.set_title(f'各{group_label}学科成绩对比', fontproperties=self.font_prop)
        ax.set_xticks(x + width * (len(subjects) - 1) / 2)
        ax.set_xticklabels(classes, fontproperties=self.font_prop, rotation=45)
        ax.legend(prop=self.font_prop)
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, 'class_comparison.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_radar_chart(self, save=True):
        """Plot radar chart for multi-subject comparison."""
        class_perf = self.analyzer.calculate_class_performance()

        if class_perf.empty:
            return None

        subjects = class_perf['subject'].unique()
        classes = class_perf['class'].unique()
        group_label = class_perf['group_label'].iloc[0] if 'group_label' in class_perf.columns else '班级'

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

        angles = np.linspace(0, 2 * np.pi, len(subjects), endpoint=False).tolist()
        angles += angles[:1]

        for cls in classes:
            cls_values = []
            for subj in subjects:
                row = class_perf[(class_perf['class'] == cls) & (class_perf['subject'] == subj)]
                if not row.empty:
                    mean_value = row.iloc[0]['mean']
                    cls_values.append(mean_value if pd.notna(mean_value) else 0)
                else:
                    cls_values.append(0)
            cls_values += cls_values[:1]

            ax.plot(angles, cls_values, 'o-', linewidth=2, label=cls)
            ax.fill(angles, cls_values, alpha=0.15)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(subjects, fontsize=10, fontproperties=self.font_prop)
        ax.set_ylim(0, max(self.max_mean, max([v for v in cls_values[:-1]])) * 1.1)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels([str(x) for x in [20, 40, 60, 80, 100]], fontsize=8, fontproperties=self.font_prop)
        ax.grid(True, linestyle='--', alpha=0.6)
        ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9, prop=self.font_prop)
        ax.set_title(f'各{group_label}学科成绩雷达图', pad=20, fontsize=14, fontweight='bold', fontproperties=self.font_prop)

        plt.tight_layout()
        path = os.path.join(self.output_dir, 'radar_chart.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_score_trend(self, save=True):
        """Plot score trend line chart."""
        fig, ax = plt.subplots(figsize=(10, 5))
        trend = self.analyzer.analyze_score_trend()

        if trend.empty:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'trend_line.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        segments = ['60分以下', '60-69分', '70-79分', '80-89分', '90分以上']
        colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(segments)))

        for _, row in trend.iterrows():
            values = [row[s] for s in segments]
            ax.plot(segments, values, marker='o', label=row['科目'], linewidth=2)

        ax.set_title('各科成绩分布趋势', fontproperties=self.font_prop)
        ax.set_ylabel('人数占比 (%)', fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, 'trend_line.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_normal_distribution(self, save=True):
        """Plot normal distribution histogram."""
        try:
            from scipy import stats
        except ImportError:
            print("Warning: scipy not available, skipping normal distribution plot")
            return None

        fig, ax = plt.subplots(figsize=(10, 5))
        subjects = self.analyzer.df['subject'].unique()
        colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']

        for i, subj in enumerate(subjects[:6]):
            scores = self.analyzer.df[self.analyzer.df['subject'] == subj]['value'].dropna()
            if len(scores) < 5:
                continue
            mu, std = scores.mean(), scores.std()
            ax.hist(scores, bins=20, alpha=0.5, density=True, label=subj, color=colors[i % len(colors)])
            x = np.linspace(scores.min(), scores.max(), 100)
            ax.plot(x, stats.norm.pdf(x, mu, std), '--', color=colors[i % len(colors)], linewidth=2)

        ax.set_title('成绩正态分布拟合', fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)

        path = os.path.join(self.output_dir, 'normal_dist.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_class_boxplot(self, save=True):
        """Plot class boxplot for stability analysis."""
        fig, ax = plt.subplots(figsize=(12, 5))
        stability = self.analyzer.analyze_class_stability()

        if stability.empty:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'class_boxplot.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        group_col, group_label = self.analyzer.get_best_grouping()
        data_for_plot = []
        labels_for_plot = []

        for grp in sorted(stability['分组'].unique()):
            grp_scores = self.analyzer.df[self.analyzer.df[group_col] == grp]['value'].dropna().values
            if len(grp_scores) > 0:
                data_for_plot.append(grp_scores)
                labels_for_plot.append(grp)

        bp = ax.boxplot(data_for_plot, patch_artist=True,
                       boxprops=dict(facecolor='#3498db', alpha=0.5))
        ax.set_xticklabels(labels_for_plot, fontproperties=self.font_prop)
        ax.set_title(f'各{group_label}成绩分布稳定性 (箱线图)', fontproperties=self.font_prop)
        ax.set_ylabel('分数', fontproperties=self.font_prop)

        path = os.path.join(self.output_dir, 'class_boxplot.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_correlation_heatmap(self, save=True):
        """Plot subject correlation heatmap."""
        corr = self.analyzer.analyze_subject_correlation()

        if corr.empty:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'correlation_heatmap.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        fig, ax = plt.subplots(figsize=(8, 6))
        if HAS_SEABORN:
            sns.heatmap(corr, annot=True, cmap='RdYlGn', vmin=-1, vmax=1,
                       linewidths=0.5, ax=ax, fmt='.2f')
        else:
            im = ax.imshow(corr.values, cmap='RdYlGn', aspect='auto', vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_xticklabels(corr.columns)
            ax.set_yticks(range(len(corr.index)))
            ax.set_yticklabels(corr.index)
            for i in range(len(corr)):
                for j in range(len(corr)):
                    ax.text(j, i, f'{corr.values[i, j]:.2f}',
                           ha='center', va='center', fontsize=8)
            plt.colorbar(im, ax=ax)
        ax.set_title('科目成绩相关性热力图', fontproperties=self.font_prop)

        for label in ax.get_xticklabels():
            label.set_fontproperties(self.font_prop)
        for label in ax.get_yticklabels():
            label.set_fontproperties(self.font_prop)

        path = os.path.join(self.output_dir, 'correlation_heatmap.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_student_deviation(self, save=True):
        """Plot student deviation from mean."""
        fig, ax = plt.subplots(figsize=(10, 5))
        wide = self.analyzer.get_wide_format()
        group_col, _ = self.analyzer.get_best_grouping()
        index_cols = ['student_id', 'student_name']
        if group_col in wide.columns:
            index_cols.append(group_col)
        subject_cols = [c for c in wide.columns if c not in index_cols + ['Total_Score']]

        if not subject_cols or 'Total_Score' not in wide.columns:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'deviation_bar.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        top10 = wide.nlargest(10, 'Total_Score')
        x = np.arange(len(subject_cols))

        for i, (idx, row) in enumerate(top10.iterrows()):
            values = [row[c] - wide[c].mean() for c in subject_cols]
            alpha = 0.3 + 0.7 * (1 - i / len(top10))
            ax.bar(x + i * 0.05, values, width=0.05, alpha=alpha, label=row['student_name'])

        ax.axhline(0, color='black', linewidth=1)
        ax.set_xticks(x)
        ax.set_xticklabels(subject_cols, fontproperties=self.font_prop)
        ax.set_title('Top10学生各科偏离均值对比', fontproperties=self.font_prop)
        ax.set_ylabel('偏离均值分数', fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop, fontsize=7)

        path = os.path.join(self.output_dir, 'deviation_bar.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_top_bottom_comparison(self, save=True):
        """Plot top vs bottom quartile comparison."""
        fig, ax = plt.subplots(figsize=(10, 5))
        wide = self.analyzer.get_wide_format()

        if 'Total_Score' not in wide.columns:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'top_bottom_bar.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        group_col, _ = self.analyzer.get_best_grouping()
        index_cols = ['student_id', 'student_name']
        if group_col in wide.columns:
            index_cols.append(group_col)
        subject_cols = [c for c in wide.columns if c not in index_cols + ['Total_Score']]

        if not subject_cols:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'top_bottom_bar.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        n = len(wide)
        q1 = wide.nlargest(max(1, n // 4), 'Total_Score')
        q4 = wide.nsmallest(max(1, n // 4), 'Total_Score')
        x = np.arange(len(subject_cols))
        bar_width = 0.35

        top_means = [q1[c].mean() for c in subject_cols]
        bottom_means = [q4[c].mean() for c in subject_cols]

        ax.bar(x - bar_width/2, top_means, bar_width, label='前25%', color='#2ecc71', alpha=0.8)
        ax.bar(x + bar_width/2, bottom_means, bar_width, label='后25%', color='#e74c3c', alpha=0.8)

        ax.set_xticks(x)
        ax.set_xticklabels(subject_cols, fontproperties=self.font_prop)
        ax.set_title('尖子生 vs 普通生各科表现对比', fontproperties=self.font_prop)
        ax.set_ylabel('平均分', fontproperties=self.font_prop)
        ax.legend(prop=self.font_prop)

        path = os.path.join(self.output_dir, 'top_bottom_bar.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_scatter_with_regression(self, save=True):
        """Scatter plot with regression lines: Total_Score vs each subject."""
        fig, ax = plt.subplots(figsize=(10, 6))
        wide = self.analyzer.get_wide_format()

        if 'Total_Score' not in wide.columns:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'scatter_regression.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        group_col, _ = self.analyzer.get_best_grouping()
        index_cols = ['student_id', 'student_name']
        if group_col in wide.columns:
            index_cols.append(group_col)
        subject_cols = [c for c in wide.columns if c not in index_cols + ['Total_Score']]

        if not subject_cols:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'scatter_regression.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        palette = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']
        for i, subj in enumerate(subject_cols):
            valid = wide[['Total_Score', subj]].dropna()
            if len(valid) < 3:
                continue
            x = valid['Total_Score'].values
            y = valid[subj].values
            ax.scatter(x, y, alpha=0.3, s=10, label=subj, color=palette[i % len(palette)])

            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(x.min(), x.max(), 100)
            ax.plot(x_line, p(x_line), '--', color=palette[i % len(palette)], linewidth=1.5, alpha=0.7)

        ax.set_xlabel('总分', fontproperties=self.font_prop)
        ax.set_ylabel('学科分数', fontproperties=self.font_prop)
        ax.set_title('总分与学科相关性分析', fontproperties=self.font_prop, fontsize=14, fontweight='bold')
        ax.legend(prop=self.font_prop, fontsize=8)
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, 'scatter_regression.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_cdf_curve(self, save=True):
        """Cumulative distribution function for each subject."""
        fig, ax = plt.subplots(figsize=(10, 6))
        subjects = self.analyzer.df['subject'].unique()
        palette = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12', '#9b59b6', '#1abc9c']

        for i, subj in enumerate(subjects[:6]):
            scores = self.analyzer.df[self.analyzer.df['subject'] == subj]['value'].dropna().sort_values()
            if len(scores) < 2:
                continue
            # Compute CDF
            y = np.arange(1, len(scores) + 1) / len(scores)
            ax.plot(scores, y, marker='', linewidth=2, label=subj, color=palette[i % len(palette)])

        ax.set_xlabel('分数', fontproperties=self.font_prop)
        ax.set_ylabel('累积概率', fontproperties=self.font_prop)
        ax.set_title('成绩累积分布曲线 (CDF)', fontproperties=self.font_prop, fontsize=14, fontweight='bold')
        ax.set_ylim(0, 1.02)
        ax.legend(prop=self.font_prop)
        ax.grid(True, alpha=0.3)

        path = os.path.join(self.output_dir, 'cdf_curve.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def plot_subject_boxplot(self, save=True):
        """Box plot comparing distributions across subjects."""
        fig, ax = plt.subplots(figsize=(12, 6))
        subjects = self.analyzer.df['subject'].unique()

        data_for_plot = []
        labels_for_plot = []

        for subj in subjects:
            scores = self.analyzer.df[self.analyzer.df['subject'] == subj]['value'].dropna()
            if len(scores) >= 4:
                data_for_plot.append(scores.values)
                labels_for_plot.append(subj)

        if not data_for_plot:
            ax.text(0.5, 0.5, '无足够数据', ha='center', va='center', fontsize=14,
                   transform=ax.transAxes, fontproperties=self.font_prop)
            path = os.path.join(self.output_dir, 'subj_boxplot.png')
            if save:
                plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                           facecolor=CHART_CONFIG["figure_bg"])
            plt.close()
            return path if save else fig

        bp = ax.boxplot(data_for_plot, patch_artist=True,
                       boxprops=dict(facecolor='#3498db', alpha=0.5))
        ax.set_xticklabels(labels_for_plot, fontproperties=self.font_prop, rotation=45, ha='right')
        ax.set_title('各科成绩分布对比 (箱线图)', fontproperties=self.font_prop, fontsize=14, fontweight='bold')
        ax.set_ylabel('分数', fontproperties=self.font_prop)
        ax.grid(True, alpha=0.3, axis='y')

        path = os.path.join(self.output_dir, 'subj_boxplot.png')
        if save:
            plt.savefig(path, dpi=CHART_CONFIG["dpi"], bbox_inches='tight',
                       facecolor=CHART_CONFIG["figure_bg"])
        plt.close()
        return path if save else fig

    def generate_all(self):
        """Generate all charts."""
        paths = {}

        base_plots = [
            ('distribution', self.plot_score_distribution),
            ('comparison', self.plot_class_comparison),
            ('radar', self.plot_radar_chart),
            ('trend', self.plot_score_trend),
            ('normal', self.plot_normal_distribution),
            ('boxplot', self.plot_class_boxplot),
            ('heatmap', self.plot_correlation_heatmap),
            ('deviation', self.plot_student_deviation),
            ('top_bottom', self.plot_top_bottom_comparison),
            ('scatter', self.plot_scatter_with_regression),
            ('cdf', self.plot_cdf_curve),
            ('boxplot_subj', self.plot_subject_boxplot),
        ]

        for name, plot_fn in base_plots:
            try:
                path = plot_fn()
                if path and os.path.exists(path):
                    paths[name] = path
                    print(f"Generated: {path}")
            except Exception as e:
                print(f"Chart {name} failed: {e}")

        return paths, self.font_warning


def main():
    parser = argparse.ArgumentParser(description="Generate charts from student score CSV data")
    parser.add_argument("--input", "-i", required=True, help="Input CSV file path")
    parser.add_argument("--output", "-o", required=True, help="Output directory for charts")
    parser.add_argument("--font", "-f", default=None, help="Path to Chinese font file for chart labels. Default: assets/思源黑体 CN Normal.otf")
    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Load data
    print(f"Loading data from: {args.input}")
    df = pd.read_csv(args.input)

    if df.empty:
        print("Error: CSV file is empty", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(df)} records")

    # Initialize analyzer and generator
    analyzer = ScoreAnalyzerV2(df)
    generator = ChartGenerator(analyzer, args.output, font_path=args.font)

    if args.font:
        print(f"Using custom font: {args.font}")

    # Generate charts
    print("Generating charts...")
    paths, font_warning = generator.generate_all()

    print(f"\nGenerated {len(paths)} charts:")
    for name, path in paths.items():
        print(f"  - {name}: {path}")

    if font_warning:
        print("\nWarning: Chinese font not found. Charts may display squares for Chinese text.")

    print(f"\nCharts saved to: {args.output}")


if __name__ == "__main__":
    main()