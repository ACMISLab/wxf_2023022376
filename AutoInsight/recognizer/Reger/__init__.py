"""
getInsights 功能实现
"""
from .get_insights import get_insights
from .types import (
    AlgorithmType,
    InsightType,
    DataInsightOptions,
    Insight,
    DataInsightExtractContext
)

__version__ = "1.0.0"
__all__ = [
    "get_insights",
    "AlgorithmType",
    "InsightType",
    "DataInsightOptions",
    "Insight",
    "DataInsightExtractContext"
]

