"""
大模型润色功能实现
"""
from typing import List, Dict, Any, Optional
from .types import Insight, TextContent
import json

def get_polish_prompt(language: str = 'chinese') -> str:
    """
    获取大模型润色的系统提示词
    
    Args:
        language: 语言类型，'chinese' 或 'english'
        
    Returns:
        系统提示词
    """
    is_chinese = language == 'chinese'
    
    task_desc = (
        "你是一个数据可视化和数据分析专家，拥有出色的语言润色能力。"
        "用户从图表中提取了一些洞察。你的任务是将用户提取的结构化洞察润色成"
        "高度可读的文本内容，供数据消费者查看。"
        if is_chinese
        else "You are a visualization and data analysis expert, and you possess excellent "
        "language polishing skills. The user extracted some insights from a chart. "
        "Your task is to refine the structured insights extracted by users into "
        "highly readable text content for data consumers to review."
    )
    
    return f"""# Task
{task_desc}

# User Input
用户会提供一个JSON格式的洞察列表，每个洞察包含：
- type: 洞察类型（如outlier、overall_trend等）
- content: 文本模板，包含占位符如${{a}}、${{b}}等
- variables: 占位符的字段信息（不包含具体数值）

# Requirements
1. 严格使用JSON格式返回
2. 返回结果的顺序与输入一一对应
3. **必须保持占位符不变**（如${{a}}、${{b}}等）
4. 使用{language}语言回答
5. 让文本更加自然、流畅、易读

# Return Format
{{"results": ["润色后的文本1", "润色后的文本2", ...]}}

# Example
## Input
{{"insights": [{{"type": "outlier", "content": "${{a}}在${{b}}出现异常，值为${{c}}", "variables": {{"a": {{"fieldName": "销售额"}}, "b": {{"fieldName": "年份"}}, "c": {{"fieldName": "销售额"}}}}}}]}}

## Response
{{"results": ["${{a}}在${{b}}年出现显著异常，其数值为${{c}}，值得重点关注。"]}}
"""

def build_llm_messages(insights: List[Insight], language: str = 'chinese') -> List[Dict[str, str]]:
    """
    构建发送给LLM的消息
    
    Args:
        insights: 洞察列表
        language: 语言类型
        
    Returns:
        LLM消息列表
    """
    # 构建用户输入，注意：不传递具体数值
    user_content = {
        "insights": [
            {
                "type": insight.type.value,
                "content": insight.textContent.content if insight.textContent else "",
                "variables": {
                    key: {
                        "fieldName": var.fieldName or "",
                        # ⚠️ 关键：不传递具体数值，保护数据隐私
                        "value": None,
                        "formatValue": None
                    }
                    for key, var in (insight.textContent.variables or {}).items()
                }
            }
            for insight in insights
        ]
    }
    
    return [
        {
            "role": "system",
            "content": get_polish_prompt(language)
        },
        {
            "role": "user",
            "content": json.dumps(user_content, ensure_ascii=False)
        }
    ]

def parse_llm_response(
    llm_response: Dict[str, Any],
    insights: List[Insight]
) -> List[Insight]:
    """
    解析LLM返回的结果并更新洞察文本
    
    Args:
        llm_response: LLM返回的JSON响应
        insights: 原始洞察列表
        
    Returns:
        更新后的洞察列表
    """
    results = llm_response.get("results", [])
    
    if not results:
        # 如果LLM返回错误，使用原始文本
        return insights
    
    from .algorithms.template import add_plain_text
    
    new_insights = []
    for i, insight in enumerate(insights):
        # 使用LLM润色后的文本，保留原始变量信息
        polished_content = results[i] if i < len(results) else (
            insight.textContent.content if insight.textContent else ""
        )
        
        new_insights.append(Insight(
            **insight.__dict__,
            textContent=add_plain_text({
                "content": polished_content,
                "variables": insight.textContent.variables if insight.textContent else None
            })
        ))
    
    return new_insights

def polish_insights_with_llm(
    insights: List[Insight],
    llm_client: Any,  # LLM客户端，需要实现run方法
    language: str = 'chinese'
) -> List[Insight]:
    """
    使用LLM润色洞察文本
    
    Args:
        insights: 原始洞察列表
        llm_client: LLM客户端（需要实现run方法）
        language: 语言类型
        
    Returns:
        润色后的洞察列表
    """
    if not insights:
        return insights
    
    try:
        # 1. 构建消息
        messages = build_llm_messages(insights, language)
        
        # 2. 调用LLM
        response = llm_client.run(messages)
        
        # 3. 解析响应
        if isinstance(response, str):
            response = json.loads(response)
        
        # 4. 更新洞察文本
        return parse_llm_response(response, insights)
    
    except Exception as e:
        # 如果LLM调用失败，返回原始洞察
        print(f"LLM polish failed: {e}")
        return insights

