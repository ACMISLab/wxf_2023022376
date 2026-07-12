"""
洞察修正逻辑
"""
from typing import List, Dict, Any, Optional, Set
from ..types import (
    Insight, InsightType, DataInsightExtractContext,
    ChartType, DataCell
)
from typing import Dict, Any
from ..utils import is_array

def filter_insight(insights: List[Insight], insight_type: InsightType) -> List[Insight]:
    """过滤特定类型的洞察"""
    return [insight for insight in insights if insight.type == insight_type]

def get_band_insight_by_outlier(
    context: DataInsightExtractContext,
    outlier_field_mapping: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """根据异常点生成异常区间"""
    band_insight_keys: List[str] = []
    abnormal_band: List[Insight] = []
    
    chart_type = context.chartType
    dimension_values = context.dimensionValues
    cell = context.cell
    
    # 只支持特定图表类型
    if chart_type not in [
        ChartType.DualAxisChart, ChartType.LineChart, ChartType.BarChart,
        ChartType.AreaChart, ChartType.WaterFallChart
    ]:
        return {'bandInsightKeys': band_insight_keys, 'abnormalBand': abnormal_band}
    
    x_field = cell.x[0] if is_array(cell.x) else cell.x
    
    for field_id, field_insights in outlier_field_mapping.items():
        # 按x值索引排序
        indexed_insights = []
        for content in field_insights:
            insight = content['insight']
            x_value = insight.data[0].dataItem.get(x_field) if insight.data else None
            if x_value is not None:
                try:
                    x_index = dimension_values.index(x_value)
                    indexed_insights.append({
                        'xIndex': x_index,
                        'content': content
                    })
                except ValueError:
                    continue
        
        indexed_insights.sort(key=lambda x: x['xIndex'])
        
        if not indexed_insights:
            continue
        
        band = [indexed_insights[0]]
        for i in range(1, len(indexed_insights) + 1):
            if i < len(indexed_insights):
                cur_index = indexed_insights[i]['xIndex']
                prev_index = band[-1]['xIndex']
                if cur_index - prev_index == 1:
                    band.append(indexed_insights[i])
                else:
                    if len(band) > 1:
                        # 创建异常区间洞察
                        abnormal_band.append(Insight(
                            type=InsightType.AbnormalBand,
                            name=InsightType.AbnormalBand,
                            data=[v['content']['insight'].data[0] for v in band],
                            seriesName=field_id,
                            value=None,
                            significant=len(band),
                            info={
                                'startValue': band[0]['content']['insight'].data[0].dataItem.get(x_field),
                                'endValue': band[-1]['content']['insight'].data[0].dataItem.get(x_field),
                                'xField': x_field
                            }
                        ))
                        band_insight_keys.extend([v['content']['key'] for v in band])
                    band = [indexed_insights[i]]
            else:
                if len(band) > 1:
                    abnormal_band.append(Insight(
                        type=InsightType.AbnormalBand,
                        name=InsightType.AbnormalBand,
                        data=[v['content']['insight'].data[0] for v in band],
                        seriesName=field_id,
                        value=None,
                        significant=len(band),
                        info={
                            'startValue': band[0]['content']['insight'].data[0].dataItem.get(x_field),
                            'endValue': band[-1]['content']['insight'].data[0].dataItem.get(x_field),
                            'xField': x_field
                        }
                    ))
                    band_insight_keys.extend([v['content']['key'] for v in band])
    
    return {'abnormalBand': abnormal_band, 'bandInsightKeys': band_insight_keys}

def merge_point_insight(
    insight_ctx: Dict[str, Any],
    insight_type: InsightType,
    context: DataInsightExtractContext
) -> Dict[str, Any]:
    """合并点洞察"""
    outlier: Dict[str, List[Insight]] = {}
    insights = insight_ctx.get('insights', [])
    outlier_field_mapping: Dict[str, List[Dict[str, Any]]] = {}
    
    filter_outlier_insight = filter_insight(insights, InsightType.Outlier)
    
    for insight in filter_outlier_insight:
        data = insight.data
        series_name = insight.seriesName
        if not data:
            continue
        
        key = f"{data[0].index}-&&&-{series_name}"
        if key not in outlier:
            outlier[key] = []
            if series_name not in outlier_field_mapping:
                outlier_field_mapping[series_name] = []
            outlier_field_mapping[series_name].append({
                'insight': insight,
                'key': key
            })
        outlier[key].append(insight)
    
    # 过滤majority value洞察
    majority_value_insight = [
        insight for insight in filter_insight(insights, InsightType.MajorityValue)
        if f"{insight.data[0].index}-&&&-{insight.seriesName}" not in outlier
    ]
    
    # 获取异常区间
    band_result = get_band_insight_by_outlier(context, outlier_field_mapping)
    abnormal_band = band_result['abnormalBand']
    band_insight_keys = band_result['bandInsightKeys']
    
    # 移除已形成区间的异常点
    for key in band_insight_keys:
        outlier.pop(key, None)
    
    # 移除转折点对应的异常点
    turn_point_insight = filter_insight(insights, InsightType.TurningPoint)
    for insight in turn_point_insight:
        if insight.data:
            key = f"{insight.data[0].index}-&&&-{insight.seriesName}"
            outlier.pop(key, None)
    
    # 合并异常点洞察
    outlier_insight = []
    for key in outlier.keys():
        first_insight = outlier[key][0]
        # 创建新洞察，合并significant值
        new_insight = Insight(
            name=first_insight.name,
            type=first_insight.type,
            data=first_insight.data,
            fieldId=first_insight.fieldId,
            seriesName=first_insight.seriesName,
            textContent=first_insight.textContent,
            value=first_insight.value,
            significant=max((ins.significant or 0 for ins in outlier[key]), default=0),
            info=first_insight.info
        )
        outlier_insight.append(new_insight)
    
    return {
        **insight_ctx,
        InsightType.Outlier: outlier_insight,
        InsightType.MajorityValue: majority_value_insight,
        InsightType.TurningPoint: turn_point_insight,
        InsightType.AbnormalBand: abnormal_band
    }

def filter_correlation_insight(insight_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """过滤相关性洞察"""
    insights = insight_ctx.get('insights', [])
    abnormal_trend = filter_insight(insights, InsightType.AbnormalTrend)
    trend_fields = {insight.seriesName for insight in abnormal_trend}
    
    correlation = [
        insight for insight in filter_insight(insights, InsightType.Correlation)
        if insight.name == 'pearson-coefficient' or
        (is_array(insight.seriesName) and
         not any(series_name in trend_fields for series_name in insight.seriesName))
    ]
    
    return {
        **insight_ctx,
        InsightType.Correlation: correlation
    }

def filter_insight_by_type(
    insight_ctx: Dict[str, Any],
    insight_type: InsightType
) -> Dict[str, Any]:
    """按类型过滤洞察"""
    return {
        **insight_ctx,
        insight_type: insight_ctx.get(insight_type) or filter_insight(insight_ctx.get('insights', []), insight_type)
    }

