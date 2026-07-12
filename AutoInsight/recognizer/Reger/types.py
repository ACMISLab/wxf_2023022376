"""
类型定义
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field

# 图表类型（简化版）
class ChartType(str, Enum):
    LineChart = 'line'
    BarChart = 'bar'
    ScatterPlot = 'scatter'
    AreaChart = 'area'
    PieChart = 'pie'
    RoseChart = 'rose'
    WaterFallChart = 'waterfall'
    DualAxisChart = 'dual-axis'

# 算法类型
class AlgorithmType(str, Enum):
    OverallTrending = 'overallTrend'
    AbnormalTrend = 'abnormalTrend'
    PearsonCorrelation = 'pearsonCorrelation'
    SpearmanCorrelation = 'spearmanCorrelation'
    ExtremeValue = 'extremeValue'
    MajorityValue = 'majorityValue'
    StatisticsAbnormal = 'statisticsAbnormal'
    StatisticsBase = 'statisticsBase'
    DbscanOutlier = 'dbscanOutlier'
    LOFOutlier = 'lofOutlier'
    TurningPoint = 'turningPoint'
    PageHinkley = 'pageHinkley'
    DifferenceOutlier = 'differenceOutlier'
    Volatility = 'volatility'

# 洞察类型
class InsightType(str, Enum):
    Min = 'min'
    Max = 'max'
    Avg = 'avg'
    Attribution = 'attribution'
    Outlier = 'outlier'
    PairOutlier = 'pair_outlier'
    ExtremeValue = 'extreme_value'
    MajorityValue = 'majority_value'
    TurningPoint = 'turning_point'
    OverallTrend = 'overall_trend'
    AbnormalTrend = 'abnormal_trend'
    AbnormalBand = 'abnormal_band'
    Correlation = 'correlation'
    Volatility = 'volatility'

# 数据类型
DataCell = Union[str, int, float]
DataItem = Dict[str, Any]
DataTable = List[DataItem]

@dataclass
class FieldInfoItem:
    """字段信息"""
    fieldName: str
    alias: Optional[str] = None
    fieldType: Optional[str] = None  # 'dimension' | 'measure'

@dataclass
class ChartDataItem:
    """图表数据项"""
    index: int
    dataItem: DataItem

DimValueDataMap = Dict[Union[str, int], List[ChartDataItem]]

@dataclass
class Cell:
    """单元格配置"""
    x: Union[str, List[str]]
    y: Union[str, List[str]]
    color: Optional[Union[str, List[str]]] = None

@dataclass
class InsightTextContent:
    """洞察文本内容变量"""
    value: DataCell
    formatValue: Optional[str] = None
    fieldName: Optional[str] = None
    isMeasure: Optional[bool] = None
    isDimValue: Optional[bool] = None
    color: Optional[str] = None
    valueType: Optional[str] = None  # 'ascendTrend' | 'descendTrend'
    icon: Optional[str] = None  # 'ratio' | 'ascendTrend' | 'descendTrend'

@dataclass
class TextContent:
    """文本内容"""
    content: str
    plainText: Optional[str] = None
    variables: Optional[Dict[str, InsightTextContent]] = None

@dataclass
class Insight:
    """洞察结果"""
    name: str
    type: InsightType
    data: List[ChartDataItem]
    fieldId: Optional[Union[str, List[str]]] = None
    seriesName: Optional[Union[DataCell, List[DataCell]]] = None
    textContent: Optional[TextContent] = None
    value: Optional[Union[float, str]] = None
    significant: float = 0.0
    info: Optional[Dict[str, Any]] = None

@dataclass
class AxesDataInfo:
    """坐标轴数据信息"""
    dataset: DataTable
    seriesNames: List[str]
    series: List[Any]
    seriesIndex: Optional[int] = None
    seriesId: Optional[str] = None
    dimensionDataMap: DimValueDataMap = field(default_factory=dict)
    dimensionValues: List[DataCell] = field(default_factory=list)
    dimensionSumMap: Dict[str, List[float]] = field(default_factory=dict)
    dimensionStackSumMap: Dict[str, List[float]] = field(default_factory=dict)
    axisTitle: Optional[Union[str, List[str]]] = None
    yField: Optional[Union[str, List[str]]] = None

@dataclass
class DataInsightExtractContext:
    """数据洞察提取上下文"""
    dataset: DataTable
    originDataset: DataTable
    fieldInfo: List[FieldInfoItem]
    dimensionDataMap: DimValueDataMap
    dimensionSumMap: Dict[str, List[float]]
    dimensionStackSumMap: Dict[str, List[float]]
    dimensionValues: List[DataCell]
    seriesDataMap: DimValueDataMap
    chartType: ChartType
    cell: Cell
    spec: Dict[str, Any]
    insights: Optional[List[Insight]] = None
    leftAxesDataList: Optional[AxesDataInfo] = None
    rightAxesDataList: Optional[AxesDataInfo] = None

@dataclass
class DataInsightOptions:
    """数据洞察选项"""
    maxNum: Optional[int] = None
    detailMaxNum: Optional[List[Dict[str, Any]]] = None
    algorithms: Optional[List[AlgorithmType]] = None
    algorithmOptions: Optional[Dict[str, Any]] = None
    isLimitedbyChartType: Optional[bool] = True
    usePolish: Optional[bool] = False
    enableInsightAnnotation: Optional[bool] = False
    language: Optional[str] = 'chinese'  # 'chinese' | 'english'

@dataclass
class InsightAlgorithm:
    """洞察算法定义"""
    name: str
    chartType: Optional[List[ChartType]] = None
    forceChartType: Optional[List[ChartType]] = None
    supportStack: Optional[bool] = None
    supportPercent: Optional[bool] = None
    insightType: InsightType = InsightType.Outlier
    canRun: Optional[Callable[[DataInsightExtractContext], bool]] = None
    algorithmFunction: Callable[[DataInsightExtractContext, Any], List[Insight]] = None
    priority: int = 0

