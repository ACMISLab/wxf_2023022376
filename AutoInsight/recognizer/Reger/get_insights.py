"""
getInsights 主入口函数
"""
from typing import Dict, Any, Optional, List
from .data_process import extract_data_from_context
from .algorithms import get_insights as algo_get_insights
from .types import DataInsightOptions, Insight, AlgorithmType, InsightType
from .llm_polish import polish_insights_with_llm

def get_insights(
    spec: Dict[str, Any],
    options: Optional[Dict[str, Any]] = None
) -> List[Insight]:
    """
    获取图表洞察的主函数
    
    Args:
        spec: VChart图表配置
        options: 洞察配置选项
            - maxNum: 最多产生的洞察数量
            - usePolish: 是否使用大模型润色（需要提供llm_client）
            - llm_client: LLM客户端（可选，如果usePolish=True则必需）
            - language: 语言类型，'chinese' 或 'english'
            - 其他选项...
        
    Returns:
        洞察结果列表
    """
    # 设置默认选项
    if options is None:
        options = {}
    
    # 构建DataInsightOptions
    insight_options = DataInsightOptions(
        maxNum=options.get('maxNum'),
        detailMaxNum=options.get('detailMaxNum'),
        algorithms=options.get('algorithms') or [
            AlgorithmType.OverallTrending,
            AlgorithmType.AbnormalTrend,
            AlgorithmType.PearsonCorrelation,
            AlgorithmType.SpearmanCorrelation,
            AlgorithmType.StatisticsAbnormal,
            AlgorithmType.LOFOutlier,
            AlgorithmType.DbscanOutlier,
            AlgorithmType.MajorityValue,
            AlgorithmType.PageHinkley,
            AlgorithmType.TurningPoint,
            AlgorithmType.StatisticsBase,
            AlgorithmType.Volatility
        ],
        algorithmOptions=options.get('algorithmOptions'),
        isLimitedbyChartType=options.get('isLimitedbyChartType', True),
        usePolish=options.get('usePolish', False),
        enableInsightAnnotation=options.get('enableInsightAnnotation', False),
        language=options.get('language', 'chinese')
    )
    
    # 从上下文提取数据
    context = extract_data_from_context(
        spec=spec,
        field_info=options.get('fieldInfo'),
        data_table=options.get('dataTable'),
        v_chart_type=options.get('vChartType')
    )
    
    if not context:
        return []
    
    # 执行算法获取洞察
    insights = algo_get_insights(context, insight_options)
    
    # 如果启用大模型润色
    if insight_options.usePolish and options.get('llm_client'):
        try:
            insights = polish_insights_with_llm(
                insights,
                options.get('llm_client'),
                insight_options.language or 'chinese'
            )
        except Exception as e:
            print(f"LLM polish failed, using original insights: {e}")
            # 如果润色失败，使用原始洞察
    
    return insights

