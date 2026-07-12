"""
Page-Hinkley Test 时序异常检测
"""
from typing import List, Any
import numpy as np
from ...types import Insight, InsightType, DataInsightExtractContext, ChartDataItem
from ...utils import is_valid_number

class PageHinkley:
    """Page-Hinkley算法类"""
    
    def __init__(self, delta=0.005, lambda_val=0.55, alpha=0.92, threshold=0.25, use_min=False):
        self.delta = delta
        self.lambda_val = lambda_val
        self.alpha = alpha
        self.threshold = threshold
        self.sum = 0.0
        self.min_sum = 0.0
        self.use_min = use_min
        self.x_mean = 0.0
        self.num = 0
        self.change_detected = False
    
    def _reset_params(self):
        """重置参数"""
        self.num = 0
        self.x_mean = 0.0
        self.sum = 0.0
        self.min_sum = 0.0
    
    def set_input(self, x: float) -> bool:
        """设置输入值并检测漂移"""
        self._detect_drift(x)
        return self.change_detected
    
    def _detect_drift(self, x: float):
        """检测漂移"""
        if np.isnan(x):
            return
        
        self.num += 1
        self.x_mean = (x + self.x_mean * (self.num - 1)) / self.num
        self.sum = self.sum * self.alpha + (x - self.x_mean)
        
        if self.sum > 0:
            self.sum -= self.delta
        else:
            self.sum += self.delta
        
        if self.sum < self.min_sum:
            self.min_sum = self.sum
        
        self.change_detected = (self.sum - self.min_sum if self.use_min else abs(self.sum)) > self.lambda_val
        
        if self.change_detected:
            self._reset_params()
            self.change_detected = abs(x - self.x_mean) >= self.threshold

def normalize_array(data: List[float]) -> List[float]:
    """归一化数组到0-1范围"""
    if not data:
        return []
    min_val = min(data)
    max_val = max(data)
    if max_val == min_val:
        return [0.0] * len(data)
    return [(x - min_val) / (max_val - min_val) for x in data]

def difference(data: List[float]) -> List[float]:
    """计算差分序列"""
    if len(data) < 2:
        return []
    return [data[i] - data[i-1] for i in range(1, len(data))]

def get_mean_and_std_dev(data: List[float]) -> dict:
    """计算均值和标准差"""
    valid_data = [v for v in data if is_valid_number(v) and not np.isnan(v)]
    if not valid_data:
        return {'mean': 0.0, 'stdDev': 0.0}
    mean = np.mean(valid_data)
    std_dev = np.std(valid_data)
    return {'mean': mean, 'stdDev': std_dev}

def execute_page_hinkley(
    context: DataInsightExtractContext,
    options: Any = None
) -> List[Insight]:
    """执行Page-Hinkley异常检测"""
    insights: List[Insight] = []
    
    series_data_map = context.seriesDataMap
    cell = context.cell
    spec = context.spec
    y_fields = cell.y if isinstance(cell.y, list) else [cell.y]
    
    delta = options.get('delta', 0.005) if options else 0.005
    lambda_val = options.get('lambda', 0.55) if options else 0.55
    threshold = options.get('threshold', 0.25) if options else 0.25
    
    for series_name, dataset in series_data_map.items():
        for y_field in y_fields:
            # 提取数据值
            data_list = []
            for item in dataset:
                value = item.dataItem.get(y_field)
                if value is not None:
                    try:
                        num_value = float(value)
                        if is_valid_number(num_value) and not np.isnan(num_value):
                            data_list.append(num_value)
                    except (ValueError, TypeError):
                        continue
            
            if len(data_list) < 3:
                continue
            
            # 计算均值和标准差
            stats = get_mean_and_std_dev(data_list)
            mean = stats['mean']
            std_dev = stats['stdDev']
            
            # 归一化数据（添加边界值以放大差异）
            normalized_data = normalize_array(data_list + [mean + 2 * std_dev, mean - 2 * std_dev])
            normalized_data = normalized_data[:-2]  # 移除添加的边界值
            
            # 计算差分
            diff_data = difference(normalized_data)
            
            if len(diff_data) < 1:
                continue
            
            # 使用Page-Hinkley检测
            page_hinkley = PageHinkley(delta, lambda_val, threshold=threshold)
            
            for i, diff_value in enumerate(diff_data):
                is_drift = page_hinkley.set_input(diff_value)
                if is_drift and i + 1 < len(dataset):
                    # i+1 因为差分序列比原序列少一个元素
                    data_item = dataset[i + 1]
                    insights.append(Insight(
                        name='pageHinkley',
                        type=InsightType.Outlier,
                        data=[data_item],
                        fieldId=y_field,
                        value=data_item.dataItem.get(y_field),
                        significant=1.0,
                        seriesName=series_name
                    ))
    
    return insights
