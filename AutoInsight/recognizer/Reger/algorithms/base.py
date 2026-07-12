"""
算法基类
"""
from typing import List, Optional, Callable, Any
from ..types import InsightAlgorithm, DataInsightExtractContext, Insight, ChartType, InsightType

class BaseAlgorithm:
    """算法基类"""
    
    def __init__(
        self,
        name: str,
        insight_type: InsightType,
        priority: int = 0,
        chart_type: Optional[List[ChartType]] = None,
        force_chart_type: Optional[List[ChartType]] = None,
        support_stack: Optional[bool] = None,
        support_percent: Optional[bool] = None,
        can_run: Optional[Callable[[DataInsightExtractContext], bool]] = None
    ):
        self.name = name
        self.insight_type = insight_type
        self.priority = priority
        self.chart_type = chart_type
        self.force_chart_type = force_chart_type
        self.support_stack = support_stack
        self.support_percent = support_percent
        self.can_run = can_run
    
    def execute(self, context: DataInsightExtractContext, options: Any = None) -> List[Insight]:
        """执行算法"""
        raise NotImplementedError("Subclass must implement execute method")
    
    def to_algorithm_info(self) -> InsightAlgorithm:
        """转换为算法信息"""
        return InsightAlgorithm(
            name=self.name,
            chartType=self.chart_type,
            forceChartType=self.force_chart_type,
            supportStack=self.support_stack,
            supportPercent=self.support_percent,
            insightType=self.insight_type,
            canRun=self.can_run,
            algorithmFunction=self.execute,
            priority=self.priority
        )

