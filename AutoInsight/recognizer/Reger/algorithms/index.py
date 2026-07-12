"""
核心getInsights函数和算法映射
"""
from typing import List, Dict, Any, Optional
from ..types import (
    DataInsightExtractContext, DataInsightOptions, Insight, InsightType,
    AlgorithmType, ChartType
)
from typing import Dict as TypingDict
from ..utils import is_stack_chart, is_percent_chart
from .revised import (
    merge_point_insight, filter_insight_by_type, filter_correlation_insight
)
from .template import generate_insight_template

# 导入所有算法
from .base.base_statistics import execute_base_statistics
from .correlation.pearson import execute_pearson_correlation
from .correlation.spearman import execute_spearman_correlation
from .outlier.statistics import execute_statistics_abnormal
from .outlier.lof import execute_lof_outlier
from .outlier.dbscan import execute_dbscan_outlier
from .outlier.difference import execute_difference_outlier
from .overall_trending import execute_overall_trending
from .abnormal_trend import execute_abnormal_trend
from .extreme_value import execute_extreme_value
from .majority_value import execute_majority_value
from .turning_point import execute_turning_point
from .volatility import execute_volatility
from .drift.page_hinkley import execute_page_hinkley
from ..types import ChartType

# 算法映射
algorithm_mapping: Dict[AlgorithmType, Dict[str, Any]] = {
    AlgorithmType.OverallTrending: {
        'info': {
            'name': 'overallTrending',
            'chartType': [ChartType.LineChart, ChartType.AreaChart, ChartType.BarChart],
            'algorithmFunction': execute_overall_trending,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 1
    },
    AlgorithmType.AbnormalTrend: {
        'info': {
            'name': 'abnormalTrend',
            'chartType': [ChartType.LineChart, ChartType.AreaChart],
            'algorithmFunction': execute_abnormal_trend,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 2
    },
    AlgorithmType.PearsonCorrelation: {
        'info': {
            'name': 'pearsonCorrelation',
            'chartType': [ChartType.ScatterPlot],
            'algorithmFunction': execute_pearson_correlation,
            'forceChartType': [ChartType.ScatterPlot],
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 3
    },
    AlgorithmType.SpearmanCorrelation: {
        'info': {
            'name': 'spearmanCorrelation',
            'chartType': [ChartType.LineChart],
            'algorithmFunction': execute_spearman_correlation,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 4
    },
    AlgorithmType.ExtremeValue: {
        'info': {
            'name': 'extremeValue',
            'chartType': None,
            'algorithmFunction': execute_extreme_value,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 5
    },
    AlgorithmType.MajorityValue: {
        'info': {
            'name': 'majorityValue',
            'chartType': [ChartType.LineChart, ChartType.BarChart, ChartType.AreaChart],
            'algorithmFunction': execute_majority_value,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 6
    },
    AlgorithmType.StatisticsAbnormal: {
        'info': {
            'name': 'statisticsAbnormal',
            'chartType': None,
            'algorithmFunction': execute_statistics_abnormal,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 7
    },
    AlgorithmType.LOFOutlier: {
        'info': {
            'name': 'lofOutlier',
            'chartType': [ChartType.ScatterPlot],
            'algorithmFunction': execute_lof_outlier,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 8
    },
    AlgorithmType.DifferenceOutlier: {
        'info': {
            'name': 'differenceOutlier',
            'chartType': None,
            'algorithmFunction': execute_difference_outlier,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 9
    },
    AlgorithmType.TurningPoint: {
        'info': {
            'name': 'turningPoint',
            'chartType': [ChartType.LineChart, ChartType.AreaChart],
            'algorithmFunction': execute_turning_point,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 10
    },
    AlgorithmType.PageHinkley: {
        'info': {
            'name': 'pageHinkley',
            'chartType': [ChartType.LineChart, ChartType.AreaChart],
            'algorithmFunction': execute_page_hinkley,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 10
    },
    AlgorithmType.DbscanOutlier: {
        'info': {
            'name': 'dbscanOutlier',
            'chartType': [ChartType.ScatterPlot],
            'algorithmFunction': execute_dbscan_outlier,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 11
    },
    AlgorithmType.Volatility: {
        'info': {
            'name': 'volatility',
            'chartType': [ChartType.LineChart, ChartType.AreaChart],
            'algorithmFunction': execute_volatility,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 12
    },
    AlgorithmType.StatisticsBase: {
        'info': {
            'name': 'baseStatistics',
            'chartType': None,
            'algorithmFunction': execute_base_statistics,
            'forceChartType': None,
            'canRun': None,
            'supportPercent': None,
            'supportStack': None
        },
        'priority': 13
    }
}

# 洞察排序映射
INSIGHT_SORT_MAPPING = {
    InsightType.Min: 0,
    InsightType.Max: 0,
    InsightType.Avg: 0,
    InsightType.Attribution: 0,
    InsightType.Outlier: 1,
    InsightType.PairOutlier: 2,
    InsightType.AbnormalBand: 10,
    InsightType.ExtremeValue: 1,
    InsightType.TurningPoint: 1,
    InsightType.MajorityValue: 1,
    InsightType.AbnormalTrend: 2,
    InsightType.OverallTrend: 2,
    InsightType.Correlation: 2,
    InsightType.Volatility: 2
}

# 洞察修正映射
REVISED_INSIGHT_BY_TYPE_MAPPING: Dict[InsightType, Optional[callable]] = {
    InsightType.Outlier: merge_point_insight,
    InsightType.PairOutlier: None,
    InsightType.AbnormalBand: None,
    InsightType.ExtremeValue: filter_insight_by_type,
    InsightType.TurningPoint: None,
    InsightType.MajorityValue: filter_insight_by_type,
    InsightType.AbnormalTrend: filter_insight_by_type,
    InsightType.OverallTrend: filter_insight_by_type,
    InsightType.Correlation: filter_correlation_insight,
    InsightType.Volatility: filter_insight_by_type,
    InsightType.Min: filter_insight_by_type,
    InsightType.Max: filter_insight_by_type,
    InsightType.Avg: filter_insight_by_type,
    InsightType.Attribution: filter_insight_by_type
}

def get_insights(context: DataInsightExtractContext, options: DataInsightOptions) -> List[Insight]:
    """
    核心getInsights函数 - 一比一复现TypeScript版本
    """
    algorithms = options.algorithms or []
    max_num = options.maxNum
    is_limited_by_chart_type = options.isLimitedbyChartType
    detail_max_num = options.detailMaxNum or []
    language = options.language or 'chinese'
    
    chart_type = context.chartType
    cell = context.cell
    spec = context.spec
    origin_dataset = context.originDataset
    
    insights: List[Insight] = []
    # 创建算法上下文，添加insights字段
    context_dict = context.__dict__.copy()
    context_dict['insights'] = insights
    insight_algorithm_context = DataInsightExtractContext(**context_dict)
    
    is_stack = is_stack_chart(spec, chart_type, cell)
    is_percent = is_percent_chart(spec, chart_type, cell)
    
    # 按优先级排序算法
    algorithms_sorted = sorted(
        algorithms,
        key=lambda a: algorithm_mapping.get(a, {}).get('priority', 999)
    )
    
    # 执行每个算法
    for algo_key in algorithms_sorted:
        algo_info = algorithm_mapping.get(algo_key)
        if not algo_info:
            continue
        
        algo_config = algo_info.get('info', {})
        algo_chart_type = algo_config.get('chartType')
        algorithm_function = algo_config.get('algorithmFunction')
        force_chart_type = algo_config.get('forceChartType')
        name = algo_config.get('name', str(algo_key))
        can_run = algo_config.get('canRun')
        support_percent = algo_config.get('supportPercent')
        support_stack = algo_config.get('supportStack')
        
        # 检查算法是否应该运行
        should_run = (
            (not force_chart_type or chart_type in force_chart_type) and
            (not is_limited_by_chart_type or not algo_chart_type or chart_type in algo_chart_type) and
            (not can_run or can_run(insight_algorithm_context)) and
            ((is_stack and support_stack is not False) or not is_stack) and
            (not is_percent or (is_percent and support_percent is not False))
        )
        
        if should_run and algorithm_function:
            # 执行算法
            algo_options = options.algorithmOptions.get(algo_key) if options.algorithmOptions else None
            res = algorithm_function(insight_algorithm_context, algo_options)
            
            # 处理结果，映射回原始数据集
            for insight in res:
                # 转换数据索引到原始数据集
                if insight.info and insight.info.get('isAxesArea'):
                    mapped_data = insight.data
                else:
                    from ..types import ChartDataItem
                    mapped_data = [
                        ChartDataItem(
                            index=item.index,
                            dataItem=origin_dataset[item.index] if item.index < len(origin_dataset) else item.dataItem
                        )
                        for item in insight.data
                    ] if insight.data else []
                
                insights.append(Insight(
                    name=name,
                    type=insight.type,
                    data=mapped_data,
                    fieldId=insight.fieldId,
                    seriesName=insight.seriesName,
                    textContent=insight.textContent,
                    value=insight.value,
                    significant=insight.significant,
                    info=insight.info
                ))
    
    # 洞察修正
    res: TypingDict[str, Any] = {'insights': insights}
    
    for insight_type in REVISED_INSIGHT_BY_TYPE_MAPPING.keys():
        revised_func = REVISED_INSIGHT_BY_TYPE_MAPPING[insight_type]
        if revised_func:
            # 根据函数签名调用
            import inspect
            sig = inspect.signature(revised_func)
            if len(sig.parameters) == 3:
                res = revised_func(res, insight_type, context)
            elif len(sig.parameters) == 2:
                res = revised_func(res, insight_type)
            else:
                res = revised_func(res)
    
    # 收集修正后的洞察
    revised_insights: List[Insight] = []
    for insight_type in REVISED_INSIGHT_BY_TYPE_MAPPING.keys():
        if insight_type in res and isinstance(res[insight_type], list):
            revised_insights.extend(res[insight_type])
    
    # 按重要性排序
    revised_insights.sort(key=lambda a: (
        INSIGHT_SORT_MAPPING.get(a.type, 999),
        -(a.significant if a.significant is not None else -1)
    ))
    
    # 应用数量限制
    after_limits_insights = revised_insights.copy()
    
    for item in detail_max_num:
        types = item.get('types', [])
        max_num_for_type = item.get('maxNum', 0)
        type_insights = [
            insight for insight in revised_insights
            if insight.type in types
        ]
        if len(type_insights) > max_num_for_type:
            filtered_insights = type_insights[max_num_for_type:]
            after_limits_insights = [
                insight for insight in after_limits_insights
                if insight not in filtered_insights
            ]
    
    # 应用总体数量限制
    if max_num:
        after_limits_insights = after_limits_insights[:max_num]
    
    # 生成模板
    final_insights = generate_insight_template(
        after_limits_insights,
        context,
        language
    )
    
    return final_insights

