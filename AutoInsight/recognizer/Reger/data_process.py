"""
数据处理逻辑 - 从上下文提取数据
"""
from typing import List, Dict, Any, Optional, Union
from .types import (
    DataInsightExtractContext, DataTable, DataItem, FieldInfoItem,
    ChartType, Cell, DimValueDataMap, ChartDataItem, DataCell, AxesDataInfo
)
from .constants import DEFAULT_SERIES_NAME
from .utils import is_array, is_valid_number, sum_dimension_values

def get_chart_type_from_spec(spec: Dict[str, Any], v_chart_type: Optional[str] = None) -> Optional[ChartType]:
    """从spec中获取图表类型"""
    if v_chart_type:
        try:
            return ChartType(v_chart_type)
        except ValueError:
            pass
    
    chart_type = spec.get('type')
    if chart_type:
        try:
            return ChartType(chart_type)
        except ValueError:
            pass
    
    return None

def get_dataset_from_spec(spec: Dict[str, Any]) -> DataTable:
    """从spec中提取数据集"""
    data = spec.get('data', [])
    if not data:
        return []
    
    # 处理data数组
    if isinstance(data, list) and len(data) > 0:
        first_data = data[0]
        if isinstance(first_data, dict) and 'values' in first_data:
            return first_data['values']
        elif isinstance(first_data, list):
            return first_data
    
    return []

def get_cell_from_spec(spec: Dict[str, Any], chart_type: ChartType) -> Cell:
    """从spec中获取cell配置"""
    x_field = spec.get('xField', [])
    y_field = spec.get('yField', [])
    color = spec.get('seriesField') or spec.get('color')
    
    # 处理数组格式
    if is_array(x_field):
        x_field = x_field[0] if x_field else ''
    # y字段保持为数组，支持多个y字段
    if not is_array(y_field):
        y_field = [y_field] if y_field else []
    if is_array(color):
        color = color[0] if color else None
    
    return Cell(
        x=x_field or '',
        y=y_field if y_field else '',
        color=color
    )

def get_field_info_from_dataset(dataset: DataTable) -> List[FieldInfoItem]:
    """从数据集中推断字段信息"""
    if not dataset:
        return []
    
    field_info = []
    first_item = dataset[0]
    
    for key in first_item.keys():
        # 简单推断：尝试判断是维度还是度量
        sample_values = [item.get(key) for item in dataset[:10]]
        is_numeric = all(is_valid_number(v) for v in sample_values if v is not None)
        
        field_info.append(FieldInfoItem(
            fieldName=key,
            alias=key,
            fieldType='measure' if is_numeric else 'dimension'
        ))
    
    return field_info

def transfer_measure_in_table(dataset: DataTable, field_info: List[FieldInfoItem]) -> DataTable:
    """转换度量字段为数字类型"""
    # 简化实现：直接返回原数据集
    # 实际应该将度量字段转换为数字
    return dataset

def get_dimension_data_info(
    x_field: str,
    y_field: List[str],
    only_one_series: bool,
    dataset: DataTable
) -> Dict[str, Any]:
    """获取维度数据信息"""
    dimension_data_map: DimValueDataMap = {}
    dimension_values: List[DataCell] = []
    
    # 按xField分组
    for index, data_item in enumerate(dataset):
        group_by = data_item.get(x_field)
        if not group_by:
            continue
        
        if group_by not in dimension_data_map:
            dimension_data_map[group_by] = []
            dimension_values.append(group_by)
        
        dimension_data_map[group_by].append(ChartDataItem(index=index, dataItem=data_item))
    
    # 计算每个维度的总和
    dimension_stack_sum_map: Dict[str, List[float]] = {}
    dimension_sum_map: Dict[str, List[float]] = {}
    
    for measure_id in y_field:
        dimension_stack_sum_map[measure_id] = []
        dimension_sum_map[measure_id] = []
        
        for dimension in dimension_values:
            dimension_dataset = [d.dataItem for d in dimension_data_map[dimension]]
            
            # 堆叠总和
            stack_sum = sum_dimension_values(dimension_dataset, measure_id, lambda v: v)
            dimension_stack_sum_map[measure_id].append(stack_sum if stack_sum is not None else 0.0)
            
            # 普通总和
            if only_one_series:
                sum_val = sum_dimension_values(dimension_dataset, measure_id, lambda v: v)
            else:
                sum_val = sum_dimension_values(dimension_dataset, measure_id)
            dimension_sum_map[measure_id].append(sum_val if sum_val is not None else 0.0)
    
    return {
        'dimensionDataMap': dimension_data_map,
        'dimensionValues': dimension_values,
        'dimensionSumMap': dimension_sum_map,
        'dimensionStackSumMap': dimension_stack_sum_map
    }

def extract_data_from_context(
    spec: Dict[str, Any],
    field_info: Optional[List[FieldInfoItem]] = None,
    data_table: Optional[DataTable] = None,
    v_chart_type: Optional[str] = None
) -> Optional[DataInsightExtractContext]:
    """从上下文中提取数据"""
    chart_type = get_chart_type_from_spec(spec, v_chart_type)
    if not chart_type:
        print('Error: unsupported spec type')
        return None
    
    # 获取数据集
    dataset = data_table
    if not dataset or len(dataset) == 0:
        dataset = get_dataset_from_spec(spec)
    
    if not dataset:
        return None
    
    # 获取字段信息
    if not field_info or len(field_info) == 0:
        field_info = get_field_info_from_dataset(dataset)
    
    origin_dataset = dataset.copy()
    dataset = transfer_measure_in_table(dataset, field_info)
    
    # 获取cell配置
    cell = get_cell_from_spec(spec, chart_type)
    
    # 构建seriesDataMap
    series_field = cell.color[0] if is_array(cell.color) else cell.color
    series_data_map: DimValueDataMap = {}
    
    if series_field and chart_type not in [ChartType.PieChart, ChartType.RoseChart]:
        for index, data_item in enumerate(dataset):
            group_by = data_item.get(series_field)
            if not group_by or (chart_type == ChartType.WaterFallChart and group_by == 'total'):
                continue
            
            if group_by not in series_data_map:
                series_data_map[group_by] = []
            series_data_map[group_by].append(ChartDataItem(index=index, dataItem=data_item))
    else:
        series_data_map[DEFAULT_SERIES_NAME] = [
            ChartDataItem(index=index, dataItem=data_item)
            for index, data_item in enumerate(dataset)
        ]
    
    # 获取x和y字段
    x_field = cell.x[0] if is_array(cell.x) else cell.x
    y_field_list = cell.y if is_array(cell.y) else [cell.y]
    only_one_series = len(series_data_map) == 1
    
    # 获取维度数据信息
    dimension_info = get_dimension_data_info(x_field, y_field_list, only_one_series, dataset)
    
    return DataInsightExtractContext(
        dataset=dataset,
        originDataset=origin_dataset,
        fieldInfo=field_info,
        dimensionDataMap=dimension_info['dimensionDataMap'],
        dimensionSumMap=dimension_info['dimensionSumMap'],
        dimensionStackSumMap=dimension_info['dimensionStackSumMap'],
        dimensionValues=dimension_info['dimensionValues'],
        seriesDataMap=series_data_map,
        chartType=chart_type,
        cell=cell,
        spec=spec
    )

