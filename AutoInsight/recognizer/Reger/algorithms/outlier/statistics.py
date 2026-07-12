"""
统计异常点检测算法 (zScore, IQR)
"""
from typing import List, Any, Tuple
import numpy as np
from ...types import Insight, InsightType, DataInsightExtractContext, ChartDataItem
from ...utils import is_valid_number

def calculate_quantile(sorted_data: List[float], quantile: float) -> float:
    """计算分位数"""
    if not sorted_data:
        return 0.0
    pos = (len(sorted_data) - 1) * quantile
    base = int(pos)
    rest = pos - base
    
    if base + 1 < len(sorted_data):
        return sorted_data[base] + rest * (sorted_data[base + 1] - sorted_data[base])
    return sorted_data[base]

def get_abnormal_by_zscore(data_points: List[Tuple[int, float]], threshold: float = 3.0) -> List[int]:
    """使用z-score检测异常点"""
    if len(data_points) < 3:
        return []
    
    values = [v for _, v in data_points]
    mean = np.mean(values)
    std = np.std(values)
    
    if std == 0:
        return []
    
    outliers = []
    for index, value in data_points:
        z_score = abs((value - mean) / std)
        if z_score >= threshold:
            outliers.append(index)
    
    return outliers

def get_abnormal_by_iqr(data_points: List[Tuple[int, float]]) -> List[int]:
    """使用IQR（四分位距）检测异常点"""
    if len(data_points) < 3:
        return []
    
    # 按值排序
    sorted_data = sorted(data_points, key=lambda x: x[1])
    values = [v for _, v in sorted_data]
    
    # 计算四分位数
    q1 = calculate_quantile(values, 0.25)
    q3 = calculate_quantile(values, 0.75)
    iqr = q3 - q1
    
    if iqr == 0:
        return []
    
    # 计算异常值边界
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    # 找出异常点
    outliers = []
    for index, value in data_points:
        if value < lower_bound or value > upper_bound:
            outliers.append(index)
    
    return outliers

def get_intersection(list1: List[int], list2: List[int]) -> List[int]:
    """获取两个列表的交集"""
    set1 = set(list1)
    set2 = set(list2)
    return list(set1 & set2)

def execute_statistics_abnormal(
    context: DataInsightExtractContext,
    options: Any = None
) -> List[Insight]:
    """执行统计异常点检测 - 使用z-score和IQR方法"""
    insights: List[Insight] = []
    
    series_data_map = context.seriesDataMap
    cell = context.cell
    spec = context.spec
    y_fields = cell.y if isinstance(cell.y, list) else [cell.y]
    
    threshold = options.get('threshold', 3.0) if options else 3.0
    
    for series_name, dataset in series_data_map.items():
        for y_field in y_fields:
            # 构建数据点列表
            data_points = []
            for item in dataset:
                value = item.dataItem.get(y_field)
                if value is not None:
                    try:
                        num_value = float(value)
                        if is_valid_number(num_value) and not np.isnan(num_value):
                            data_points.append((item.index, num_value))
                    except (ValueError, TypeError):
                        continue
            
            if len(data_points) < 3:
                continue
            
            # 根据数据量选择检测方法
            z_score_result = None
            iqr_result = None
            
            # 数据量>=30时使用z-score
            if len(data_points) >= 30:
                z_score_result = get_abnormal_by_zscore(data_points, threshold)
            
            # 数据量>=10时使用IQR
            if len(data_points) >= 10:
                iqr_result = get_abnormal_by_iqr(data_points)
            
            # 确定最终结果：如果有z-score结果，取交集；否则只用IQR
            if z_score_result is not None and iqr_result is not None:
                final_result = get_intersection(z_score_result, iqr_result)
            elif z_score_result is not None:
                final_result = z_score_result
            elif iqr_result is not None:
                final_result = iqr_result
            else:
                final_result = []
            
            # 创建洞察
            for index in final_result:
                # 找到对应的数据项
                data_item = next((item for item in dataset if item.index == index), None)
                if data_item:
                    insights.append(Insight(
                        name='statisticsAbnormal',
                        type=InsightType.Outlier,
                        data=[data_item],
                        fieldId=y_field,
                        value=data_item.dataItem.get(y_field),
                        significant=1.0,
                        seriesName=series_name
                    ))
    
    return insights

