import os
import json
import time
import asyncio

from autogen_agentchat.agents import AssistantAgent, CodeExecutorAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


async def autogen_pipeline(
    instruction: str,   # ← 现在只输入一个指令（包含数据+问题）
    savedir: str,
    model_config: dict,
):
    """
    最简数据分析智能体团队：
    输入：一条完整指令（包含数据路径 + 分析问题）
    输出：分析答案 + 可视化代码
    """

    start_time = time.time()

    messages_json_path = os.path.join(savedir, 'messages.json')
    usages_json_path = os.path.join(savedir, 'usage.json')

    # 初始化模型
    client = OpenAIChatCompletionClient(
        model=model_config['model'],
        api_key=model_config['api_key'],
        base_url=model_config['base_url'],
        model_info={
            "vision": False,
            "function_calling": False,
            "json_output": False,
            "structured_output": False,
            "family": "unknown",
            "parameters": model_config.get("parameters", {}),
        }
    )

    # =============================
    # 1️⃣ Planner Agent（任务解析）
    # =============================
    planner_agent = AssistantAgent(
        name="PlannerAgent",
        description="Parses the user instruction and identifies analysis plan.",
        model_client=client,
        system_message="""
You are a data analysis planner.

Given a user instruction (including dataset path and question),
1. Clarify the analysis objective.
2. Produce a short structured plan.

Keep it concise.
"""
    )

    # =============================
    # 2️⃣ Code Agent（生成分析+可视化代码）
    # =============================
    code_agent = AssistantAgent(
        name="CodeAgent",
        description="Generate Python analysis and visualization code.",
        model_client=client,
        system_message="""
You are a professional data scientist.

Generate complete Python code to:
1. Load the dataset
2. Perform required analysis
3. Generate code using matplotlib
4. Print clear results

Return ONLY executable Python code.
"""
    )

    # =============================
    # 3️⃣ 代码执行器
    # =============================
    code_executor = CodeExecutorAgent(
        name="CodeExecutor",
        description="Executes Python code.",
        code_executor=LocalCommandLineCodeExecutor(
            work_dir=r"C:\Users\wxf\Desktop\coding"
        ),
    )

    # =============================
    # 4️⃣ Insight Agent（总结答案）
    # =============================
    insight_agent = AssistantAgent(
        name="InsightAgent",
        description="Summarizes analysis results.",
        model_client=client,
        system_message="""
You are a senior data analyst.

Based on the code and execution output,Provide a clear  answer to the question.
Return your response strictly in the following JSON format **without any extra explanation**:
{
  "answer": "<short answer>",
  "code": "<matplotlib code for visualization>"
}
"""
    )
    # =============================
    # 构建最简单团队
    # =============================
    team = RoundRobinGroupChat(
        [planner_agent, code_agent, code_executor, insight_agent],
        termination_condition=MaxMessageTermination(max_messages=6),
    )

    # =============================
    # 运行
    # =============================
    result = await team.run(task=instruction)

    end_time = time.time()

    output = {
        #"time": end_time - start_time,
        "messages": [m.content for m in result.messages]
    }

    with open(messages_json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return result.messages










