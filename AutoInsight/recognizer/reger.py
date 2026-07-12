from recognizer.Reger import get_insights, AlgorithmType
import re


def reg_insight(spec):
    if spec["type"]=="line":
        options = {
            "maxNum": 10,  # 增加洞察数量以发现更多异常
            "language": "english",
            "usePolish": False,  # 不使用大模型润色
            "isLimitedbyChartType": True,  # 根据图表类型限制算法
            "algorithms": [
                AlgorithmType.StatisticsBase,  # 基础统计（最小/最大/平均）
                AlgorithmType.StatisticsAbnormal,  # 统计异常检测（z-score, IQR）
                AlgorithmType.OverallTrending,  # 整体趋势检测
                AlgorithmType.AbnormalTrend,  # 异常趋势检测
                AlgorithmType.PageHinkley,  # 时序异常检测
                AlgorithmType.TurningPoint,  # 转折点检测
                AlgorithmType.Volatility,  # 周期性检测
                AlgorithmType.ExtremeValue,  # 极值检测
            ],
            "algorithmOptions": {
                AlgorithmType.StatisticsAbnormal: {
                    "threshold": 2.5  # z-score阈值
                }
            }
        }
    else:
        options = {
            "maxNum": 15,  # 增加洞察数量以发现更多异常
            "language": "english",
            "usePolish": False,  # 不使用大模型润色
            "isLimitedbyChartType": True,  # 根据图表类型限制算法
            "algorithms": [
                AlgorithmType.StatisticsBase,  # 基础统计（最小/最大/平均）
            ],
            "algorithmOptions": {
                AlgorithmType.StatisticsAbnormal: {
                    "threshold": 2.5  # z-score阈值
                }
            }
        }
    # 1 获取洞察
    insights = get_insights(spec, options)

    # 2 定义变量
    sta_score = None  # 所有洞察得分的最大值
    insight_text = ""  # 所有洞察描述拼接文本

    # 3 统计洞察得分最大值 & 拼接洞察描述
    # 检查是否有 Attribution，如果有则跳过最大值
    has_attribution = any(insight.type.value == "attribution" for insight in insights)
    
    for insight in insights:
        insight_type = insight.type.value

        # 如果识别到 Attribution，跳过最大值（因为 Attribution 已经代表了最大值）
        if has_attribution and insight_type == "max":
            continue

        # min / max / avg 是基础统计事实；Attribution 参与评分
        if insight_type not in ("min", "max", "avg","attribution"):
            if insight.significant is not None:
                if sta_score is None or insight.significant > sta_score:
                    sta_score = insight.significant

        # 拼接洞察描述
        if insight.textContent:
            text = insight.textContent.plainText or insight.textContent.content
            if text:
                def format_number(match):
                    num = float(match.group())
                    # 数值是整数 → 输出整数
                    if num.is_integer():
                        return str(int(num))
                    # 否则保留两位小数
                    return f"{num:.2f}"

                # 匹配整数或小数
                text = re.sub(r'\d+(?:\.\d+)?', format_number, text)

                # ⭐ 关键：拼接时加逗号
                if insight_text:
                    insight_text += ";"
                insight_text += text

    if sta_score is None:
        sta_score = 0.0

    return sta_score, insight_text

# 复杂示例数据 - 包含多个异常点、趋势变化、周期性波动
"""spec = {
    "type": "line",
    "xField": ["年份"],
    "yField": ["高考录取率"],
    "data": [{
        "id": "data",
        "values": [
            # 正常增长期
          {"年份": 1977, "高考录取率": 0.05},
          {"年份": 1978, "高考录取率": 0.07},
          {"年份": 1979, "高考录取率": 0.06},
          {"年份": 1980, "高考录取率": 0.08},
          {"年份": 1981, "高考录取率": 0.11},
          {"年份": 1982, "高考录取率": 0.17},
          {"年份": 1983, "高考录取率": 0.23},
          {"年份": 1984, "高考录取率": 0.29},
          {"年份": 1985, "高考录取率": 0.96},
          {"年份": 1986, "高考录取率": 0.3},
          {"年份": 1987, "高考录取率": 0.27},
          {"年份": 1988, "高考录取率": 0.25},
          {"年份": 1989, "高考录取率": 0.23},
          {"年份": 1990, "高考录取率": 0.22},
          {"年份": 1991, "高考录取率": 0.21},
          {"年份": 1992, "高考录取率": 0.25},
          {"年份": 1993, "高考录取率": 0.34},
          {"年份": 1994, "高考录取率": 0.36},
          {"年份": 1995, "高考录取率": 0.37},
          {"年份": 1996, "高考录取率": 0.4},
          {"年份": 1997, "高考录取率": 0.36},
          {"年份": 1998, "高考录取率": 0.34},
          {"年份": 1999, "高考录取率": 0.56},
          {"年份": 2000, "高考录取率": 0.59},
          {"年份": 2001, "高考录取率": 0.59},
          {"年份": 2002, "高考录取率": 0.63},
          {"年份": 2003, "高考录取率": 0.62},
          {"年份": 2004, "高考录取率": 0.61},
          {"年份": 2005, "高考录取率": 0.57},
          {"年份": 2006, "高考录取率": 0.57},
          {"年份": 2007, "高考录取率": 0.56},
          {"年份": 2008, "高考录取率": 0.57},
          {"年份": 2009, "高考录取率": 0.62},
          {"年份": 2010, "高考录取率": 0.69},
          {"年份": 2011, "高考录取率": 0.72},
          {"年份": 2012, "高考录取率": 0.75},
          {"年份": 2013, "高考录取率": 0.75},
          {"年份": 2014, "高考录取率": 0.74},
          {"年份": 2015, "高考录取率": 0.74},
          {"年份": 2016, "高考录取率": 0.75},
          {"年份": 2017, "高考录取率": 0.74},
          {"年份": 2018, "高考录取率": 0.81},
          {"年份": 2019, "高考录取率": 0.8},
          {"年份": 2020, "高考录取率": 0.8},
          {"年份": 2021, "高考录取率": 0.93},
          {"年份": 2022, "高考录取率": 0.96}
        ]
    }]
}
# 配置选项 - 启用更多算法来检测复杂模式

s,insights = reg_insight(spec)
print(insights)
print(s)"""
