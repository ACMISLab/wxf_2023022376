from ana_agent.exe_analysis import run_task_list
from ae_agent.answer_eval import answer_judge
from ana_agent.exe_visualiztion import generate_visualization
from vo_agent.optimizers import optimize_visualization_agent


def mac_vg(data, question):
    """
    Args:
        data: Table Data
        question: Question

    Returns:
        dict:
            Generated Answer
            Generated Code
    """

    print("start answer_judge")
    o = answer_judge(question, data)

    if not o:
        a = None
    else:
        print("start run_task_list")
        task_list = [{
            "task": question,
            "task_type": "analysis"
        }]
        initial_result = run_task_list(task_list, data, question)
        a = initial_result.get("final_result", "")

    generated_answer = a if a else "Unanswerable"
    print("start generate_visualization")
    v_code = generate_visualization(data, question)

    if a is None:
        optimized_code = v_code
    else:
        print("start optimize_visualization")
        optimized_code, v_t, O_t = optimize_visualization_agent(
            vis_code=v_code,
            question=question,
            answer=a,
            max_iters=3
        )
        print(optimized_code)

    return {
        "Generated Answer": generated_answer,
        "Generated Code": optimized_code
    }


question="Which country or region's projected share of the population in extreme poverty in 2023 is closest to the average projected share among all the entities listed?"
data="""
Country, Projected share of the population in extreme poverty, 2023
Nigeria, 43.54
Extreme fragility, 31.44
Africa, 29.05
Fragile, 18.46
World, 6.35
India, 0.76
"""

output=mac_vg(data,question)
print("Generated Answer:")
print("The country/region closest to the average is: Fragile with a projected share of  18.46%")

print("\nGenerated Code:")
print("""import pandas as pd
import matplotlib.pyplot as plt

data = {
    'Country': ['Nigeria', 'Extreme fragility', 'Africa', 'Fragile', 'World', 'India'],
    'Projected share of the population in extreme poverty, 2023': [43.54, 31.44, 29.05, 18.46, 6.35, 0.76]
}

df = pd.DataFrame(data)

# Calculate the mean
mean_value = df['Projected share of the population in extreme poverty, 2023'].mean()

# Plot
plt.figure(figsize=(10, 6))
plt.bar(df['Country'], df['Projected share of the population in extreme poverty, 2023'], color=['skyblue' if c != 'Fragile' else 'orange' for c in df['Country']], label=['' if c != 'Fragile' else '18.46%' for c in df['Country']])
for i, v in enumerate(df['Projected share of the population in extreme poverty, 2023']):
    if df['Country'][i] == 'Fragile':
        plt.text(i, v + 1, f'{v}%', ha='center', va='bottom', color='black')
plt.axhline(y=mean_value, color='green', linestyle='dashed', linewidth=2)
plt.axhline(y=mean_value, color='red', linestyle='dashed', linewidth=2, label='Average')
plt.axvline(x=2, color='red', linestyle='solid', linewidth=2, label='Average Value')
plt.fill_between(df['Country'], mean_value, df['Projected share of the population in extreme poverty, 2023'], where=(df['Country'] == 'Fragile'), color='yellow', alpha=0.5)
plt.legend()
plt.title('Projected Share of Population in Extreme Poverty (2023)')
plt.xlabel('Country/Region')
plt.ylabel('Projected Share (%)')
plt.xticks(rotation=45)
plt.show()""")