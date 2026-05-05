#!/usr/bin/env python3
"""
动态阈值计算脚本 (Dynamic Thresholds Calculator)

计算基于百分位数的动态及格线和优秀线，用于题目极难时的相对排名解释。

输出：
    reports/dynamic_thresholds.json - JSON格式的动态指标

概念说明：
    - 动态及格线 (D-G): P80百分位数，即排在前20%之外的门槛
    - 动态及格率: 达到D-G分数的学生比例（理论≈20%）
    - 相对优秀线 (D-E): P20百分位数，即前20%的门槛
    - 相对优秀率: 达到D-E分数的学生比例（理论≈20%）
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import numpy as np


def compute_dynamic_thresholds(df: pd.DataFrame) -> dict:
    """
    计算动态阈值指标
    
    Args:
        df: 清洗后的数据（Long Format，含 student_id, subject, value 列）
    
    Returns:
        dict: 动态阈值指标字典
    """
    scores = df["value"].dropna().values
    
    if len(scores) == 0:
        return {"error": "无有效分数数据"}
    
    d_g = np.percentile(scores, 80)  # P80 = 动态及格线
    d_e = np.percentile(scores, 20)  # P20 = 相对优秀线
    
    dynamic_pass_rate = (scores >= d_g).sum() / len(scores) * 100
    dynamic_excellent_rate = (scores >= d_e).sum() / len(scores) * 100
    
    absolute_pass_rate = float((scores >= 60).sum() / len(scores) * 100)
    absolute_excellent_rate = float((scores >= 85).sum() / len(scores) * 100)
    
    recommend_dynamic = bool(absolute_pass_rate < 20)
    
    subject_thresholds = {}
    for subject in df["subject"].unique():
        subject_scores = df[df["subject"] == subject]["value"].dropna().values
        if len(subject_scores) > 0:
            subject_thresholds[subject] = {
                "动态及格线_D-G": round(float(np.percentile(subject_scores, 80)), 2),
                "相对优秀线_D-E": round(float(np.percentile(subject_scores, 20)), 2),
                "平均分": round(float(subject_scores.mean()), 2),
                "最高分": round(float(subject_scores.max()), 2),
                "最低分": round(float(subject_scores.min()), 2),
                "绝对及格率": round(float((subject_scores >= 60).sum() / len(subject_scores) * 100), 1),
            }
    
    result = {
        "总体动态指标": {
            "动态及格线_D-G": round(d_g, 2),
            "动态及格率": round(dynamic_pass_rate, 1),
            "相对优秀线_D-E": round(d_e, 2),
            "相对优秀率": round(dynamic_excellent_rate, 1),
            "绝对及格率_>=60": round(absolute_pass_rate, 1),
            "绝对优秀率_>=85": round(absolute_excellent_rate, 1),
            "建议使用动态阈值": recommend_dynamic,
            "判断依据": "绝对及格率 < 20% 时建议使用动态阈值解释相对排名",
        },
        "各科目动态阈值": subject_thresholds,
        "分数统计": {
            "总分数个数": int(len(scores)),
            "平均分": round(float(scores.mean()), 2),
            "标准差": round(float(scores.std()), 2),
            "最高分": round(float(scores.max()), 2),
            "最低分": round(float(scores.min()), 2),
        },
        "解读建议": generate_interpretation(
            d_g, dynamic_pass_rate, absolute_pass_rate, recommend_dynamic
        ),
    }
    
    return result


def generate_interpretation(
    d_g: float, 
    dynamic_pass_rate: float, 
    absolute_pass_rate: float,
    recommend_dynamic: bool
) -> str:
    """
    生成交读建议文本
    """
    if recommend_dynamic:
        return (
            f"本次考试题目较难，绝对及格率（≥60分）仅为{absolute_pass_rate:.1f}%。"
            f"建议使用动态阈值解释相对排名：动态及格线为{d_g:.1f}分（P80），"
            f"达到该分数的学生占{dynamic_pass_rate:.1f}%，处于年级中上游位置。"
            f"报告中应说明：'虽然绝对及格率较低，但从动态阈值看，"
            f"约{dynamic_pass_rate:.0f}%的学生达到了相对及格标准。'"
        )
    else:
        return (
            f"本次考试难度适中，绝对及格率（≥60分）为{absolute_pass_rate:.1f}%。"
            f"动态阈值作为补充参考：动态及格线{d_g:.1f}分，动态及格率{dynamic_pass_rate:.1f}%。"
            f"报告中可同时展示绝对和动态两种及格率指标。"
        )


def main():
    parser = argparse.ArgumentParser(
        description="计算动态阈值指标（动态及格线、相对优秀线等）"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="输入CSV文件路径（清洗后的Long Format数据）",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出JSON文件路径",
    )
    
    args = parser.parse_args()
    
    # 读取数据
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：输入文件不存在 - {input_path}")
        sys.exit(1)
    
    df = pd.read_csv(input_path)
    
    required_cols = ["value"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"错误：缺少必要列 - {missing}")
        sys.exit(1)
    
    result = compute_dynamic_thresholds(df)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"动态阈值已计算并保存至: {output_path}")
    
    print("\n=== 动态阈值摘要 ===")
    overall = result["总体动态指标"]
    print(f"动态及格线 (D-G): {overall['动态及格线_D-G']}分")
    print(f"动态及格率: {overall['动态及格率']}%")
    print(f"相对优秀线 (D-E): {overall['相对优秀线_D-E']}分")
    print(f"绝对及格率 (>=60): {overall['绝对及格率_>=60']}%")
    print(f"建议使用动态阈值: {'是' if overall['建议使用动态阈值'] else '否'}")
    print(f"\n解读建议:\n{result['解读建议']}")


if __name__ == "__main__":
    main()