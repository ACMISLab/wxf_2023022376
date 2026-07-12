"""
Pearson相关性算法
"""
from typing import List, Any, Optional, Tuple
import numpy as np
from scipy.stats import pearsonr
from ...types import Insight, InsightType, DataInsightExtractContext
from ...utils import is_valid_number, is_array


def _extract_numeric_pairs(dataset, x_field, y_field) -> List[Tuple[float, float]]:
    values: List[Tuple[float, float]] = []
    for item in dataset:
        x_value = item.dataItem.get(x_field)
        y_value = item.dataItem.get(y_field)
        if x_value is None or y_value is None:
            continue
        try:
            x_num = float(x_value)
            y_num = float(y_value)
        except (TypeError, ValueError):
            continue
        if is_valid_number(x_num) and is_valid_number(y_num) and not np.isnan(x_num) and not np.isnan(y_num):
            values.append((x_num, y_num))
    return values


def execute_pearson_correlation(
    context: DataInsightExtractContext,
    options: Any = None
) -> List[Insight]:
    """执行Pearson相关性检测"""
    insights: List[Insight] = []

    series_data_map = context.seriesDataMap
    cell = context.cell
    y_fields = cell.y if is_array(cell.y) else [cell.y]

    for series_name, dataset in series_data_map.items():
        for i in range(len(y_fields)):
            for j in range(i + 1, len(y_fields)):
                field_a = y_fields[i]
                field_b = y_fields[j]
                pairs = _extract_numeric_pairs(dataset, field_a, field_b)
                if len(pairs) < 3:
                    continue

                x_values = [p[0] for p in pairs]
                y_values = [p[1] for p in pairs]
                try:
                    coefficient, p_value = pearsonr(x_values, y_values)
                except Exception:
                    continue

                if np.isnan(coefficient):
                    continue

                correlation_type = 'positive' if coefficient >= 0 else 'negative'
                insights.append(Insight(
                    name='pearson-coefficient',
                    type=InsightType.Correlation,
                    data=[],
                    fieldId=[field_a, field_b],
                    seriesName=[field_a, field_b],
                    value=float(coefficient),
                    significant=float(abs(coefficient)),
                    info={
                        'correlationType': correlation_type,
                        'coefficient': float(coefficient),
                        'pValue': float(p_value),
                        'seriesName': series_name,
                        'fieldA': field_a,
                        'fieldB': field_b,
                        'sampleSize': len(pairs)
                    }
                ))
    return insights
