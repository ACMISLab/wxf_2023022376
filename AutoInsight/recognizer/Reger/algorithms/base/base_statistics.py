"""
基础统计算法 - 最小/最大/平均值
"""
from typing import List, Any, Optional
import numpy as np
from ...types import Insight, InsightType, DataInsightExtractContext, ChartDataItem
from ...utils import is_valid_number

def execute_base_statistics(
    context: DataInsightExtractContext,
    options: Any = None
) -> List[Insight]:
    """执行基础统计算法"""
    insights: List[Insight] = []
    
    dataset = context.dataset
    field_info = context.fieldInfo
    cell = context.cell
    dimension_values = context.dimensionValues
    dimension_sum_map = context.dimensionSumMap
    
    # 获取y字段
    y_fields = cell.y if isinstance(cell.y, list) else [cell.y]
    
    for y_field in y_fields:
        if y_field not in dimension_sum_map:
            continue
        
        values = dimension_sum_map[y_field]
        valid_values = [(i, v) for i, v in enumerate(values) if is_valid_number(v)]
        
        if not valid_values:
            continue


        # 计算最小/最大/平均值
        indices, nums = zip(*valid_values)
        min_value = round(min(nums), 2)
        max_value = round(max(nums), 2)
        avg_value = round(sum(nums) / len(nums), 2)
        total_sum = sum(nums)

        min_idx = indices[nums.index(min(nums))]
        max_idx = indices[nums.index(max(nums))]

        # 检测 Attribution：如果最大值占比超过50%，则识别为 Attribution
        has_attribution = False
        if total_sum > 0:
            max_value_ratio = max(nums) / total_sum
            if max_value_ratio > 0.5:  # 占比超过50%
                has_attribution = True
                insights.append(Insight(
                    name='baseStatistics',
                    type=InsightType.Attribution,
                    data=[ChartDataItem(
                        index=max_idx,
                        dataItem=dataset[max_idx] if max_idx < len(dataset) else {}
                    )],
                    fieldId=y_field,
                    value=max(nums),
                    significant=1.0,
                    info={
                        'dimValue': dimension_values[max_idx],
                        'ratio': max_value_ratio
                    }
                ))

        # 创建最小值洞察
        if min_idx < len(dimension_values):
            insights.append(Insight(
                name='baseStatistics',
                type=InsightType.Min,
                data=[ChartDataItem(
                    index=min_idx,
                    dataItem=dataset[min_idx] if min_idx < len(dataset) else {}
                )],
                fieldId=y_field,
                value=min(nums),
                significant=1.0,
                info={'dimValue': dimension_values[min_idx]}
            ))
        
        # 创建最大值洞察（如果没有 Attribution 才输出最大值）
        if not has_attribution and max_idx < len(dimension_values):
            insights.append(Insight(
                name='baseStatistics',
                type=InsightType.Max,
                data=[ChartDataItem(
                    index=max_idx,
                    dataItem=dataset[max_idx] if max_idx < len(dataset) else {}
                )],
                fieldId=y_field,
                value=max(nums),
                significant=1.0,
                info={'dimValue': dimension_values[max_idx]}
            ))
        
        # 创建平均值洞察
        insights.append(Insight(
            name='baseStatistics',
            type=InsightType.Avg,
            data=[],
            fieldId=y_field,
            value=avg_value,
            significant=0.5
        ))
    
    return insights

