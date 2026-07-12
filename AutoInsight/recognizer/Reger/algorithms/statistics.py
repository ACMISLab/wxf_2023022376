"""
统计工具函数 - Mann-Kendall测试等
"""
from typing import List, Tuple, Optional
import numpy as np
from enum import Enum

class TrendType(str, Enum):
    """趋势类型"""
    INCREASING = 'increasing'
    DECREASING = 'decreasing'
    NO_TREND = 'no_trend'

def original_mk_test(data: List[float], alpha: float = 0.05, calc_scope: bool = False) -> dict:
    """
    Mann-Kendall趋势测试
    
    Args:
        data: 数据序列
        alpha: 显著性水平
        calc_scope: 是否计算范围
        
    Returns:
        包含trend, pValue, zScore, slope, intercept的字典
    """
    n = len(data)
    if n < 3:
        return {
            'trend': TrendType.NO_TREND,
            'pValue': 1.0,
            'zScore': 0.0,
            'slope': 0.0,
            'intercept': 0.0
        }
    
    # 计算S统计量
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            if data[j] > data[i]:
                s += 1
            elif data[j] < data[i]:
                s -= 1
    
    # 计算方差
    var_s = n * (n - 1) * (2 * n + 5) / 18.0
    
    # 处理相同值
    ties = {}
    for value in data:
        ties[value] = ties.get(value, 0) + 1
    
    tie_correction = 0
    for count in ties.values():
        if count > 1:
            tie_correction += count * (count - 1) * (2 * count + 5)
    
    if tie_correction > 0:
        var_s -= tie_correction / 18.0
    
    # 计算Z分数
    if s > 0:
        z_score = (s - 1) / np.sqrt(var_s) if var_s > 0 else 0
    elif s < 0:
        z_score = (s + 1) / np.sqrt(var_s) if var_s > 0 else 0
    else:
        z_score = 0
    
    # 计算p值（使用正态分布近似）
    from scipy.stats import norm
    p_value = 2 * (1 - norm.cdf(abs(z_score)))
    
    # 判断趋势
    if p_value < alpha:
        trend = TrendType.INCREASING if z_score > 0 else TrendType.DECREASING
    else:
        trend = TrendType.NO_TREND
    
    # 计算斜率（Sen's slope）
    slopes = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            if j != i:
                slope = (data[j] - data[i]) / (j - i)
                slopes.append(slope)
    
    slope = np.median(slopes) if slopes else 0.0
    
    # 计算截距（使用中位数）
    intercept = np.median([data[i] - slope * i for i in range(n)]) if n > 0 else 0.0
    
    return {
        'trend': trend,
        'pValue': p_value,
        'zScore': z_score,
        'slope': slope,
        'intercept': intercept
    }

def longest_trend_interval(data: List[float], trend: TrendType) -> dict:
    """
    找到最长的趋势区间
    
    Args:
        data: 数据序列
        trend: 趋势类型
        
    Returns:
        包含length, start, end, maxTrend的字典
    """
    n = len(data)
    if n < 2:
        return {'length': 0, 'start': 0, 'end': 0, 'maxTrend': trend}
    
    max_length = 0
    max_start = 0
    max_end = 0
    
    i = 0
    while i < n - 1:
        start = i
        # 找到连续趋势的结束点
        while i < n - 1:
            if trend == TrendType.INCREASING:
                if data[i + 1] >= data[i]:
                    i += 1
                else:
                    break
            elif trend == TrendType.DECREASING:
                if data[i + 1] <= data[i]:
                    i += 1
                else:
                    break
            else:
                break
        
        length = i - start + 1
        if length > max_length:
            max_length = length
            max_start = start
            max_end = i
        
        i += 1
    
    return {
        'length': max_length,
        'start': max_start,
        'end': max_end,
        'maxTrend': trend
    }

