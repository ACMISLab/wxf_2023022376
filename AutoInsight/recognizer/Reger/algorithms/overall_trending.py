"""
整体趋势算法 - 使用Mann-Kendall Test
"""
from typing import List, Any, Optional
import numpy as np
from ..types import Insight, InsightType, DataInsightExtractContext, ChartDataItem
from .statistics import original_mk_test, longest_trend_interval, TrendType
from ..utils import is_array, is_valid_number

def find_last_index(data: List[Any], predicate) -> int:
    """找到最后一个满足条件的索引"""
    for i in range(len(data) - 1, -1, -1):
        if predicate(data[i]):
            return i
    return -1

def execute_overall_trending(
    context: DataInsightExtractContext,
    options: Any = None
) -> List[Insight]:
    """执行整体趋势检测"""
    insights: List[Insight] = []
    
    cell = context.cell
    dimension_sum_map = context.dimensionSumMap
    dimension_values = context.dimensionValues
    series_data_map = context.seriesDataMap
    
    # 检查是否可以运行（只有一个系列）
    if len(series_data_map) != 1:
        return insights
    
    alpha = options.get('alpha', 0.05) if options else 0.05
    calc_scope = options.get('calcScope', False) if options else False
    
    y_fields = cell.y if is_array(cell.y) else [cell.y]
    x_field = cell.x[0] if is_array(cell.x) else cell.x
    
    for measure_id in y_fields:
        if measure_id not in dimension_sum_map:
            continue
        
        overall_dataset = dimension_sum_map[measure_id]
        
        # 过滤有效数据
        valid_data = [v for v in overall_dataset if is_valid_number(v)]
        if len(valid_data) < 3:
            continue
        
        # 执行Mann-Kendall测试
        mk_result = original_mk_test(overall_dataset, alpha, calc_scope)
        trend = mk_result['trend']
        p_value = mk_result['pValue']
        slope = mk_result['slope']
        intercept = mk_result['intercept']
        
        if trend == TrendType.NO_TREND:
            continue
        
        # 找到最长趋势区间
        trend_interval = longest_trend_interval(overall_dataset, trend)
        length = trend_interval['length']
        start = trend_interval['start']
        end = trend_interval['end']
        
        # 找到整体数据的起始和结束索引
        overall_end_index = find_last_index(overall_dataset, lambda v: is_valid_number(v))
        overall_start_index = next((i for i, v in enumerate(overall_dataset) if is_valid_number(v)), -1)
        
        if overall_start_index < 0 or overall_end_index < 0:
            continue
        
        # 计算整体变化率
        start_value = overall_dataset[overall_start_index]
        end_value = overall_dataset[overall_end_index]
        
        if start_value == 0:
            overall_change = -end_value
        else:
            overall_change = (end_value / start_value) - 1
        
        # 验证趋势方向与变化率一致
        if (trend == TrendType.INCREASING and overall_change > 0) or \
           (trend == TrendType.DECREASING and overall_change < 0):
            
            # 计算连续趋势区间的变化率
            interval_start_value = overall_dataset[start]
            interval_end_value = overall_dataset[end]
            
            if interval_start_value == 0:
                interval_change = -interval_end_value
            else:
                interval_change = (interval_end_value / interval_start_value) - 1
            
            insights.append(Insight(
                name='overallTrending',
                type=InsightType.OverallTrend,
                data=[],
                fieldId=measure_id,
                value=trend.value,
                significant=1.0 - p_value,
                info={
                    'slope': slope,
                    'intercept': intercept,
                    'length': length,
                    'overall': {
                        'start': overall_start_index,
                        'end': overall_end_index,
                        'change': overall_change,
                        'startValue': start_value,
                        'endValue': end_value,
                        'startDimValue': dimension_values[overall_start_index] if overall_start_index < len(dimension_values) else None,
                        'endDimValue': dimension_values[overall_end_index] if overall_end_index < len(dimension_values) else None
                    },
                    'start': start,
                    'end': end,
                    'maxTrend': trend.value,
                    'change': interval_change,
                    'startDimValue': dimension_values[start] if start < len(dimension_values) else None,
                    'endDimValue': dimension_values[end] if end < len(dimension_values) else None,
                    'startValue': interval_start_value,
                    'endValue': interval_end_value
                }
            ))
    
    return insights
