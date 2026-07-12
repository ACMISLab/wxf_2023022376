"""
工具函数
"""
from typing import List, Dict, Any, Optional, Union
from .types import ChartType, Cell, DataItem, DataTable

def is_array(value: Any) -> bool:
    """判断是否为数组"""
    return isinstance(value, list)

def is_number(value: Any) -> bool:
    """判断是否为数字"""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def is_valid_number(value: Any) -> bool:
    """判断是否为有效数字"""
    if value == '' or value is None:
        return False
    try:
        num = float(value)
        return not (num != num)  # not NaN
    except (ValueError, TypeError):
        return False

def is_stack_chart(spec: Dict[str, Any], chart_type: ChartType, cell: Cell) -> bool:
    """判断是否为堆叠图表"""
    series_field = spec.get('seriesField')
    chart_spec_type = spec.get('type')
    series = spec.get('series', [])
    stack = spec.get('stack')
    
    if chart_spec_type == 'common' and chart_type in [ChartType.BarChart, ChartType.AreaChart, ChartType.LineChart]:
        return all(
            ((s.get('stack') is not False and s.get('type') == 'bar') or bool(s.get('stack'))) 
            and not (is_array(cell.x) and len(cell.x) > 1)
            for s in series
        )
    
    return (
        ((stack is not False and (chart_type == ChartType.BarChart or chart_spec_type == 'bar')) or bool(stack))
        and series_field
        and not (is_array(cell.x) and series_field in cell.x)
    )

def is_percent_chart(spec: Dict[str, Any], chart_type: ChartType, cell: Cell) -> bool:
    """判断是否为百分比图表"""
    chart_spec_type = spec.get('type')
    series = spec.get('series', [])
    series_field = spec.get('seriesField')
    
    if chart_spec_type == 'common' and chart_type in [ChartType.BarChart, ChartType.AreaChart, ChartType.LineChart]:
        return all(bool(s.get('percent')) for s in series)
    
    return bool(spec.get('percent')) and not (series_field and is_array(cell.x) and series_field in cell.x)

def sum_dimension_values(
    dataset: DataTable,
    measure_id: Union[str, int],
    get_value: Optional[callable] = None
) -> Optional[float]:
    """计算维度值的总和"""
    if get_value is None:
        get_value = lambda v: abs(v)
    
    valid_count = 0
    total = 0.0
    
    for item in dataset:
        num_value = None
        try:
            num_value = float(item.get(measure_id, 0))
        except (ValueError, TypeError):
            pass
        
        is_valid = is_number(num_value) and not (num_value != num_value) and item.get(measure_id) != ''
        value = get_value(num_value) if is_valid and num_value is not None else 0
        
        if is_valid:
            valid_count += 1
        
        total += value
    
    return total if valid_count > 0 else None

def get_field_id_in_cell(cell_field: Union[str, List[str]]) -> str:
    """从cell中获取字段ID"""
    if is_array(cell_field):
        return cell_field[0] if cell_field else ''
    return cell_field if cell_field else ''

