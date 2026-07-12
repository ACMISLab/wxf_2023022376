"""
模板生成逻辑
"""
from typing import List, Dict, Any, Optional
from ..types import (
    Insight, DataInsightExtractContext, InsightTextContent, TextContent,
    InsightType, ChartType
)
from ..constants import DEFAULT_SERIES_NAME
from ..utils import get_field_id_in_cell, is_array

def get_field_info_by_id(field_info: List[Any], field_id: str) -> Optional[Any]:
    """根据ID获取字段信息"""
    for info in field_info:
        if info.fieldName == field_id:
            return info
    return None

def is_empty_series(series_name: Any) -> bool:
    """判断系列是否为空"""
    return not series_name or series_name == DEFAULT_SERIES_NAME

def add_plain_text(text_content: Dict[str, Any]) -> TextContent:
    """添加纯文本"""
    content = text_content.get('content', '')
    variables = text_content.get('variables', {})
    
    plain_text = content
    for key, value in variables.items():
        # 处理InsightTextContent对象或字典
        if hasattr(value, 'formatValue'):
            replace_value = value.formatValue or value.value
        elif isinstance(value, dict):
            replace_value = value.get('formatValue') or value.get('value')
        else:
            replace_value = value
        plain_text = plain_text.replace(f'${{{key}}}', str(replace_value))
    
    return TextContent(
        content=content,
        plainText=plain_text,
        variables=variables
    )

def get_min_max_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取最小/最大值模板"""
    value = insight.value
    info = insight.info or {}
    insight_type = insight.type
    field_id = insight.fieldId  # 使用insight的fieldId，支持多字段
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    
    x_field_id = get_field_id_in_cell(cell.x)
    
    is_chinese = language == 'chinese'
    placeholder_value = '最小值' if insight_type == InsightType.Min else '最大值'
    if not is_chinese:
        placeholder_value = 'minimum' if insight_type == InsightType.Min else 'maximum'
    
    # 获取字段信息
    y_field_info = get_field_info_by_id(field_info, field_id)
    field_display_name = y_field_info.alias if y_field_info and y_field_info.alias else field_id
    
    x_field_info = get_field_info_by_id(field_info, x_field_id)
    x_field_display_name = x_field_info.alias if x_field_info and x_field_info.alias else x_field_id
    
    if info.get('isAxesArea'):
        content = (
            f'${{a}}的{placeholder_value}位于${{b}}，值为${{c}}'
            if is_chinese
            else f'The {placeholder_value} value of ${{a}} at ${{b}}, with a value of ${{c}}'
        )
        variables = {
            'a': InsightTextContent(
                value=info.get('titleName') or field_display_name,
                fieldName=field_display_name
            )
        }
    else:
        # 改进：使用更自然的表达方式
        if is_chinese:
            # 中文：使用"${b}的${a}${c}，为${d}"格式，更符合中文表达习惯
            min_max_text = '最低' if insight_type == InsightType.Min else '最高'
            content = f'${{b}}的${{a}}{min_max_text}，为${{c}}'
        else:
            # 英文：保持原有格式但优化
            content = f'${{b}} has the {placeholder_value} ${{a}} of ${{c}}'
        variables = {
            'a': InsightTextContent(
                value=field_display_name,
                fieldName=field_display_name
            )
        }
    
    variables.update({
        'b': InsightTextContent(
            value=info.get('dimValue'),
            isDimValue=True,
            fieldName=x_field_display_name
        ),
        'c': InsightTextContent(
            value=value,
            isMeasure=True,
            fieldName=field_display_name
        )
    })
    
    return {'content': content, 'variables': variables}

def get_attribution_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取 Attribution 模板（占比超过50%的主导值）"""
    value = insight.value
    info = insight.info or {}
    field_id = insight.fieldId
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    
    x_field_id = get_field_id_in_cell(cell.x)
    
    is_chinese = language == 'chinese'
    
    # 获取字段信息
    y_field_info = get_field_info_by_id(field_info, field_id)
    field_display_name = y_field_info.alias if y_field_info and y_field_info.alias else field_id
    
    x_field_info = get_field_info_by_id(field_info, x_field_id)
    x_field_display_name = x_field_info.alias if x_field_info and x_field_info.alias else x_field_id
    
    dim_value = info.get('dimValue')
    ratio = info.get('ratio', 0)
    
    if is_chinese:
        # 中文：使用"${b}的${a}显著高于其他类别"格式
        content = '${b}的${a}显著高于其他类别'
    else:
        # 英文：使用"The ${b} ${a} is significantly higher in volume than others"格式
        content = 'The ${b} ${a} is significantly higher in volume than others'
    
    variables = {
        'a': InsightTextContent(
            value=field_display_name,
            fieldName=field_display_name
        ),
        'b': InsightTextContent(
            value=dim_value,
            isDimValue=True,
            fieldName=x_field_display_name
        )
    }
    
    return {'content': content, 'variables': variables}

def get_avg_template(insight: Insight, ctx: DataInsightExtractContext, language: str) -> Dict[str, Any]:
    """获取平均值模板"""
    value = insight.value
    info = insight.info or {}
    field_id = insight.fieldId  # 使用insight的fieldId，支持多字段
    
    field_info = ctx.fieldInfo
    
    is_chinese = language == 'chinese'
    
    # 获取字段信息
    y_field_info = get_field_info_by_id(field_info, field_id)
    field_display_name = y_field_info.alias if y_field_info and y_field_info.alias else field_id
    
    if info.get('isAxesArea'):
        content = '${a}的平均值为${b}' if is_chinese else 'The average value of ${a} is ${b}'
        variables = {
            'a': InsightTextContent(
                value=info.get('titleName') or field_display_name,
                fieldName=field_display_name
            ),
            'b': InsightTextContent(value=value, isMeasure=True, fieldName=field_display_name)
        }
    else:
        # 改进：使用更简洁自然的表达
        if is_chinese:
            # 中文：使用"${a}平均为${b}"格式，更简洁
            content = '${a}平均为${b}'
        else:
            # 英文：简化表达
            content = 'The average ${a} is ${b}'
        variables = {
            'a': InsightTextContent(
                value=field_display_name,
                fieldName=field_display_name
            ),
            'b': InsightTextContent(value=value, isMeasure=True, fieldName=field_display_name)
        }
    
    return {'content': content, 'variables': variables}

def get_outlier_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取异常点模板"""
    series_name = insight.seriesName
    data = insight.data
    value = insight.value
    field_id = insight.fieldId
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    chart_type = ctx.chartType
    
    x_field_id = get_field_id_in_cell(cell.x)
    series_field = get_field_id_in_cell(cell.color)
    
    is_chinese = language == 'chinese'
    
    if chart_type == ChartType.ScatterPlot:
        content = (
            '(${b}, ${c})上显著异常'
            if is_empty_series(series_name)
            else '${a}在(${b}, ${c})上显著异常'
        ) if is_chinese else (
            'Significant anomaly at (${b}, ${c})'
            if is_empty_series(series_name)
            else '${a} shows a significant anomaly at (${b}, ${c})'
        )
        
        variables = {}
        if not is_empty_series(series_name):
            series_field_info = get_field_info_by_id(field_info, series_field)
            variables['a'] = InsightTextContent(
                value=series_name,
                fieldName=series_field_info.alias if series_field_info else series_field
            )
        
        if data and field_id:
            field_id_list = field_id if is_array(field_id) else [field_id]
            field_info_0 = get_field_info_by_id(field_info, field_id_list[0])
            field_info_1 = get_field_info_by_id(field_info, field_id_list[1]) if len(field_id_list) > 1 else None
            
            variables['b'] = InsightTextContent(
                value=data[0].dataItem.get(field_id_list[0]),
                isDimValue=True,
                fieldName=field_info_0.alias if field_info_0 else field_id_list[0]
            )
            variables['c'] = InsightTextContent(
                value=data[0].dataItem.get(field_id_list[1]) if len(field_id_list) > 1 else None,
                isDimValue=True,
                fieldName=field_info_1.alias if field_info_1 else (field_id_list[1] if len(field_id_list) > 1 else '')
            )
    else:
        # 获取字段显示名称
        field_id_str = field_id[0] if is_array(field_id) else field_id
        field_info_by_field_id = get_field_info_by_id(field_info, field_id_str)
        field_display_name = field_info_by_field_id.alias if field_info_by_field_id and field_info_by_field_id.alias else field_id_str
        
        x_field_info = get_field_info_by_id(field_info, x_field_id)
        x_field_display_name = x_field_info.alias if x_field_info and x_field_info.alias else x_field_id
        
        # 改进：包含字段名称，让描述更自然
        if is_empty_series(series_name):
            content = (
                f'${{a}}在${{b}}出现异常，值为${{c}}'
                if is_chinese
                else f'${{a}} shows an anomaly at ${{b}} with a value of ${{c}}'
            )
            variables = {
                'a': InsightTextContent(
                    value=field_display_name,
                    fieldName=field_display_name
                )
            }
        else:
            content = (
                f'${{a}}在${{b}}出现异常，值为${{c}}'
                if is_chinese
                else f'${{a}} shows an anomaly at ${{b}} with a value of ${{c}}'
            )
            series_field_info = get_field_info_by_id(field_info, series_field)
            variables = {
                'a': InsightTextContent(
                    value=f"{series_name}的{field_display_name}" if is_chinese else f"{series_name} {field_display_name}",
                    fieldName=field_display_name
                )
            }
        
        variables['b'] = InsightTextContent(
            value=data[0].dataItem.get(x_field_id) if data else None,
            isDimValue=True,
            fieldName=x_field_display_name
        )
        variables['c'] = InsightTextContent(
            value=value,
            isMeasure=True,
            fieldName=field_display_name
        )
    
    return {'content': content, 'variables': variables}

def get_turn_point_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取转折点模板"""
    res = get_outlier_template(insight, ctx, language)
    content = res['content']
    
    if language == 'chinese':
        content = content.replace('上显著异常', '是个拐点')
    else:
        content = content.replace('Significant anomaly', 'Turning point')
        content = content.replace('significant anomaly', 'turning point')
    
    return {'content': content, 'variables': res['variables']}

def get_extreme_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取极值模板"""
    res = get_outlier_template(insight, ctx, language)
    content = res['content']
    
    if language == 'chinese':
        content = content.replace('上显著异常', '是极值')
    else:
        content = content.replace('Significant anomaly', 'Extreme value')
        content = content.replace('significant anomaly', 'extreme value')
    
    return {'content': content, 'variables': res['variables']}

def get_majority_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取占比贡献巨大值模板"""
    series_name = insight.seriesName
    field_id = insight.fieldId
    info = insight.info or {}
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    
    ratio = info.get('ratio', 0)
    dimension_name = info.get('dimensionName', '')
    x_field_id = get_field_id_in_cell(cell.x)
    series_field = get_field_id_in_cell(cell.color)
    
    content = (
        '${a}在${b}的占比贡献度显著，占比高达${c}'
        if language == 'chinese'
        else '${a} significantly contributes to ${b}, at ${c}'
    )
    
    series_field_info = get_field_info_by_id(field_info, series_field)
    x_field_info = get_field_info_by_id(field_info, x_field_id)
    field_id_str = field_id[0] if is_array(field_id) else field_id
    field_info_by_field_id = get_field_info_by_id(field_info, field_id_str)
    
    variables = {
        'a': InsightTextContent(
            value=series_name,
            fieldName=series_field_info.alias if series_field_info else series_field
        ),
        'b': InsightTextContent(
            value=dimension_name,
            isDimValue=True,
            fieldName=x_field_info.alias if x_field_info else x_field_id
        ),
        'c': InsightTextContent(
            value=ratio,
            formatValue=f'{ratio * 100:.1f}%',
            fieldName=field_info_by_field_id.alias if field_info_by_field_id else field_id_str,
            icon='ratio'
        )
    }
    
    return {'content': content, 'variables': variables}

def get_overall_trend_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取整体趋势模板"""
    value = insight.value
    info = insight.info or {}
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    
    start_dim_value = info.get('startDimValue')
    end_dim_value = info.get('endDimValue')
    change = info.get('change', 0)
    overall = info.get('overall', {})
    
    x_field_id = get_field_id_in_cell(cell.x)
    is_chinese = language == 'chinese'
    
    trend_text = '上升' if value == 'increasing' else '下降'
    if not is_chinese:
        trend_text = 'increasing' if value == 'increasing' else 'decreasing'
    
    change_text = '增长了' if value == 'increasing' else '下降了'
    if not is_chinese:
        change_text = 'increase ' if value == 'increasing' else 'decrease '
    
    content = (
        f'数据整体呈${{a}}趋势，整体{change_text}${{d}}。其中在${{b}}至${{c}}间连续${{a}}。'
        if is_chinese
        else f'The overall data shows a ${{a}} trend, with an overall {change_text}of ${{d}}. Notably, from ${{b}} to ${{c}}, there was a continuous ${{a}} trend.'
    )
    
    x_field_info = get_field_info_by_id(field_info, x_field_id)
    
    variables = {
        'a': InsightTextContent(
            value=trend_text,
            icon='ascendTrend' if value == 'increasing' else 'descendTrend'
        ),
        'b': InsightTextContent(
            value=start_dim_value,
            isDimValue=True,
            fieldName=x_field_info.alias if x_field_info else x_field_id
        ),
        'c': InsightTextContent(
            value=end_dim_value,
            isDimValue=True,
            fieldName=x_field_info.alias if x_field_info else x_field_id
        ),
        'd': InsightTextContent(
            value=overall.get('change', change),
            formatValue=f'{abs(overall.get("change", change)) * 100:.1f}%',
            valueType='ascendTrend' if value == 'increasing' else 'descendTrend'
        )
    }
    
    return {'content': content, 'variables': variables}

def get_abnormal_trend_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取异常趋势模板"""
    series_name = insight.seriesName
    value = insight.value
    info = insight.info or {}
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    series_field = get_field_id_in_cell(cell.color)
    
    is_chinese = language == 'chinese'
    
    trend_text = '上升' if value == 'increasing' else '下降'
    if not is_chinese:
        trend_text = 'increase' if value == 'increasing' else 'decrease'
    
    content = (
        '${a}趋势异常，呈${b}趋势，整体${b}了${c}'
        if is_chinese
        else 'The ${a} trend is abnormal, showing a ${b} trend, with an overall ${b} of ${c}.'
    )
    
    series_field_info = get_field_info_by_id(field_info, series_field)
    change = info.get('change', 0)
    
    variables = {
        'a': InsightTextContent(
            value=series_name,
            fieldName=series_field_info.alias if series_field_info else series_field
        ),
        'b': InsightTextContent(
            value=trend_text,
            icon='ascendTrend' if value == 'increasing' else 'descendTrend'
        ),
        'c': InsightTextContent(
            value=f'{abs(change) * 100:.1f}%',
            valueType='ascendTrend' if value == 'increasing' else 'descendTrend'
        )
    }
    
    return {'content': content, 'variables': variables}

def get_correlation_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取相关性模板"""
    series_name = insight.seriesName
    name = insight.name
    info = insight.info or {}
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    series_field = get_field_id_in_cell(cell.color)
    
    is_chinese = language == 'chinese'
    correlation_type = info.get('correlationType', 'positive')
    
    if name == 'spearman':
        content = (
            '${a}和${b}呈${c}相关'
            if is_chinese
            else '${a} and ${b} show a ${c} correlation'
        )
        
        series_name_list = series_name if is_array(series_name) else [series_name]
        series_field_info = get_field_info_by_id(field_info, series_field)
        
        correlation_text = '正' if correlation_type == 'positive' else '负'
        if not is_chinese:
            correlation_text = 'positive' if correlation_type == 'positive' else 'negative'
        
        variables = {
            'a': InsightTextContent(
                value=series_name_list[0] if series_name_list else '',
                fieldName=series_field_info.alias if series_field_info else series_field
            ),
            'b': InsightTextContent(
                value=series_name_list[1] if len(series_name_list) > 1 else '',
                fieldName=series_field_info.alias if series_field_info else series_field
            ),
            'c': InsightTextContent(value=correlation_text)
        }
    else:
        content = (
            '图表在xy上呈线性相关'
            if is_empty_series(series_name)
            else '${a}在xy上呈线性相关'
        ) if is_chinese else (
            'The chart shows a linear correlation on the xy plane'
            if is_empty_series(series_name)
            else '${a} shows a linear correlation on the xy plane'
        )
        
        variables = {}
        if not is_empty_series(series_name):
            series_field_info = get_field_info_by_id(field_info, series_field)
            variables['a'] = InsightTextContent(
                value=series_name,
                fieldName=series_field_info.alias if series_field_info else series_field
            )
    
    return {'content': content, 'variables': variables}

def get_volatility_template(
    insight: Insight,
    ctx: DataInsightExtractContext,
    language: str
) -> Dict[str, Any]:
    """获取周期性模板"""
    series_name = insight.seriesName
    
    field_info = ctx.fieldInfo
    cell = ctx.cell
    series_field = get_field_id_in_cell(cell.color)
    
    content = (
        '数据呈周期性波动'
        if is_empty_series(series_name)
        else '${a}呈周期性波动'
    ) if language == 'chinese' else (
        'The data shows cyclical fluctuations.'
        if is_empty_series(series_name)
        else '${a} shows cyclical fluctuations'
    )
    
    variables = {}
    if not is_empty_series(series_name):
        series_field_info = get_field_info_by_id(field_info, series_field)
        variables['a'] = InsightTextContent(
            value=series_name,
            fieldName=series_field_info.alias if series_field_info else series_field
        )
    
    return {'content': content, 'variables': variables}

def generate_insight_template(
    insights: List[Insight],
    ctx: DataInsightExtractContext,
    language: str
) -> List[Insight]:
    """生成洞察模板"""
    for insight in insights:
        insight_type = insight.type
        text_content = None
        
        if insight_type == InsightType.Outlier:
            text_content = get_outlier_template(insight, ctx, language)
        elif insight_type == InsightType.TurningPoint:
            text_content = get_turn_point_template(insight, ctx, language)
        elif insight_type == InsightType.MajorityValue:
            text_content = get_majority_template(insight, ctx, language)
        elif insight_type == InsightType.AbnormalBand:
            # 简化实现
            text_content = {'content': f'异常区间', 'variables': {}}
        elif insight_type == InsightType.OverallTrend:
            text_content = get_overall_trend_template(insight, ctx, language)
        elif insight_type == InsightType.AbnormalTrend:
            text_content = get_abnormal_trend_template(insight, ctx, language)
        elif insight_type == InsightType.Correlation:
            text_content = get_correlation_template(insight, ctx, language)
        elif insight_type == InsightType.Volatility:
            text_content = get_volatility_template(insight, ctx, language)
        elif insight_type == InsightType.ExtremeValue:
            text_content = get_extreme_template(insight, ctx, language)
        elif insight_type == InsightType.Attribution:
            text_content = get_attribution_template(insight, ctx, language)
        elif insight_type in [InsightType.Min, InsightType.Max]:
            text_content = get_min_max_template(insight, ctx, language)
        elif insight_type == InsightType.Avg:
            text_content = get_avg_template(insight, ctx, language)
        else:
            text_content = {
                'content': f'数据含有{insight_type}的见解' if language == 'chinese' else f'Data has {insight_type} insight',
                'variables': {}
            }
        
        insight.textContent = add_plain_text(text_content)
    
    return insights

