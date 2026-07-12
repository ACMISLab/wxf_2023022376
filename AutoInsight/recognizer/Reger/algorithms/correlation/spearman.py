"""
Spearman相关性算法
"""
from typing import List, Any, Tuple
import numpy as np
from scipy.stats import spearmanr
from ...types import Insight, InsightType, DataInsightExtractContext
from ...utils import is_valid_number, is_array


def _extract_numeric_pairs(dataset, field_a, field_b) -> List[Tuple[float, float]]:
    values: List[Tuple[float, float]] = []
    for item in dataset:
        a_value = item.dataItem.get(field_a)
        b_value = item.dataItem.get(field_b)
        if a_value is None or b_value is None:
            continue
        try:
            a_num = float(a_value)
            b_num = float(b_value)
        except (TypeError, ValueError):
            continue
        if is_valid_number(a_num) and is_valid_number(b_num) and not np.isnan(a_num) and not np.isnan(b_num):
            values.append((a_num, b_num))
    return values


def execute_spearman_correlation(
    context: DataInsightExtractContext,
    options: Any = None
) -> List[Insight]:
    """执行Spearman相关性检测"""
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
                    coefficient, p_value = spearmanr(x_values, y_values)
                except Exception:
                    continue

                if np.isnan(coefficient):
                    continue

                correlation_type = 'positive' if coefficient >= 0 else 'negative'
                insights.append(Insight(
                    name='spearman',
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
