# ===========================
# (1) Recommend Questions Prompts
# ===========================
def get_question_prompt(method="basic"):
    if method == "basic":
        prompt_template = GET_QUESTIONS_TEMPLATE
        system_template = GET_QUESTIONS_SYSTEM_MESSAGE
    if method == "multi":
        prompt_template = GET_QUESTIONS_TEMPLATE_MULTI
        system_template = GET_QUESTIONS_SYSTEM_MESSAGE
    if method == "follow_up":
        prompt_template = FOLLOW_UP_TEMPLATE
        system_template = FOLLOW_UP_SYSTEM_MESSAGE
    if method == "follow_up_with_type":
        prompt_template = FOLLOW_UP_TYPE_TEMPLATE
        system_template = FOLLOW_UP_SYSTEM_MESSAGE


    return prompt_template, system_template


# ===========================
# (2) CODE Prompts
# ===========================


def get_code_prompt(method="basic"):
    if method == "basic":
        code_template = GENERATE_CODE_TEMPLATE
    if method == "single":
        code_template = GENERATE_CODE_SINGLE_TEMPLATE
    elif method == "multi":
        code_template = GENERATE_CODE_TEMPLATE_MULTI

    return code_template


# ===========================
# (3) Interpret Prompt
# ===========================


def get_interpret_prompt(method):
    if method == "basic":
        prompt_template = INTERPRET_SOLUTION

    return prompt_template


# ===========================
# (4) Summarize Insights Prompt
# ===========================
def get_summarize_prompt(method="basic"):
    if method == "basic":
        prompt_template = SUMMARIZE_TEMPLATE
        system_template = SUMMARIZE_SYSTEM_MESSAGE

    return prompt_template, system_template

# ===========================
# (5) Eval Insights Prompt
# ===========================
def get_eval_prompt(method="basic"):
    if method == "basic":
        prompt_template = EVAL_TEMPLATE_BASE
    return prompt_template


EVAL_TEMPLATE_BASE="""
You are a professional data analyst responsible for evaluating the coherence and insight relevance between a question and its answer.

Evaluation Data:
Given the following goal:
<goal>{goal}</goal>
Given the following question:
<question>{question}</question>
Given the following answer:
<answer>{insight}</answer>

Scoring Instructions:
*Evaluate whether the current answer effectively addresses the given question, and assess whether the insights are relevant to the analysis goal.
*Assign a numerical score from 1 to 10, where 10 indicates that the insight perfectly answers the question.
*The score must contain only the number, with no additional explanation.
*Wrap the score in <score></score> tags.
*Strictly follow the output format shown below. Do not add any extra content.

Example response:
<score>7</score>
"""


# ===========================
# (5) Polish Insights Prompt
# ===========================
def get_polish_prompt(method="basic"):
    if method == "basic":
        prompt_template = POLISH_TEMPLATE_BASE
    return prompt_template


POLISH_TEMPLATE_BASE="""
You are a professional data analyst responsible for refining the answer.

Polish Data:
<question>{question}</question>

<answer>{insight}</answer>

Refinement Requirements:
*Refine the current answer to make it concise, clear, and fluent, without changing its original meaning.
*Ensure the refined answer directly and explicitly addresses the question as fully as possible.
*Wrap the refined answer in <insight></insight> tags.
*Strictly follow the output format shown below. Do not add any extra content.

Example Output:
<insight>The hardware incidents are significantly higher in volume than the others.</insight>
<insight>The time to resolution of incidents is uniform over time</insight>
<insight>Beth Anglin has a higher average number of incident assignments compared to other agents</insight>
<insight>The IT department has the highest Expense Rejection Rate among all departments.</insight>
"""


GET_QUESTIONS_TEMPLATE = """
### Instruction:

Given the following context:
<context>{context}</context>

Given the following goal:
<goal>{goal}</goal>

Given the following schema:
<schema>{schema}</schema>

Instructions:
* Write a list of questions to be solved by the data scientists in your team to explore my data and reach my goal.
* Explore diverse aspects of the data, and ask questions that are relevant to my goal.
* You must ask the right questions to surface anything interesting (trends, anomalies, etc.)
* Make sure these can realistically be answered based on the data schema.
* The insights that your team will extract will be used to generate a report.
* Each question should only have one part, that is a single '?' at the end which only require a single answer.
* Do not number the questions.
* You can produce at most {max_questions} questions. Stop generation after that.
* Most importantly, each question must be enclosed within <question></question> tags. Refer to the example response below:

Example response:
<question>What is the average age of the customers?</question>
<question>What is the distribution of the customers based on their age?</question>

### Response:
"""

GET_QUESTIONS_TEMPLATE_MULTI = """
### Instruction:

Given the following context:
<context>{context}</context>

Given the following goal:
<goal>{goal}</goal>

Given the schema of the first dataset:\n
<schema>{schema}</schema>

Given the schema of the second dataset:\n
<schema>{user_schema}</schema>

Instructions:
* Write a list of questions to be solved by the data scientists in your team to explore my data and reach my goal.
* Explore diverse aspects of the data, and ask questions that are relevant to my goal.
* You must ask the right questions to surface anything interesting (trends, anomalies, etc.)
* Make sure these can realistically be answered based on the data schema.
* The insights that your team will extract will be used to generate a report.
* Each question should only have one part, that is a single '?' at the end which only require a single answer.
* Do not number the questions.
* You can produce at most {max_questions} questions. Stop generation after that.
* Most importantly, each question must be enclosed within <question></question> tags. Refer to the example response below:

Example response:
<question>What is the average age of the customers?</question>
<question>What is the distribution of the customers based on their age?</question>

### Response:

"""

GET_QUESTIONS_SYSTEM_MESSAGE = """
You the manager of a data science team whose goal is to help stakeholders within your company extract actionable insights from their data.
You have access to a team of highly skilled data scientists that can answer complex questions about the data.
You call the shots and they do the work.
Your ultimate deliverable is a report that summarizes the findings and makes hypothesis for any trend or anomaly that was found.
"""


INTERPRET_SOLUTION = """
### Instruction:
You are trying to answer a question based on information provided by a data scientist.

Given the context:
<context>
    You need to answer a question based on information provided by a data scientist.
</context>

Given the following dataset schema:
<schema>{schema}</schema>

Given the goal:
<goal>{goal}</goal>

Given the question:
<question>{question}</question>

Given the analysis:
<analysis>
    <message>
        {message}
    </message>
    {insights}
</analysis>

Instructions:
* Based on the analysis and other information provided above, write an answer to the question enclosed with <question></question> tags.
* The answer should be a single sentence, but it should not be too high level and should include the key details from justification.
* Write your answer in HTML-like tags, enclosing the answer between <answer></answer> tags, followed by a justification between <justification></justification> tags, followed by an insight between <insight></insight> tags.
* Refer to the following example response for the format of the answer and justification.
* The insight should be something interesting and grounded based on the question, goal, and the dataset schema, something that would be interesting. 
* The insight should be as quantiative as possible and informative and non-trivial and concise.
* The insight should be a meaningful conclusion that can be acquired from the analysis in laymans terms

Example response:
<answer>This is a sample answer</answer>
<insight>This is a sample insight</insight>
<justification>This is a sample justification</justification>

### Response:
"""

INTERPRET_SOLUTION_MAX = """
### Instruction:
You are trying to answer a question based on information provided by a data scientist.

Given the context:
<context>
    You need to answer a question based on information provided by a data scientist.
</context>

Given the goal:
<goal>{goal}</goal>

Given the question:
<question>{question}</question>

Given the analysis:
<analysis>
    <message>
        {message}
    </message>
    {insights}
</analysis>

Instructions:
* Based on the analysis and other information provided above, write an answer to the question enclosed with <question></question> tags.
* The answer should be a single sentence, but it should not be too high level and should include the key details from justification.
* Write your answer in HTML-like tags, enclosing the answer between <answer></answer> tags, followed by a justification between <justification></justification> tags, followed by an insight between <insight></insight> tags.
* Refer to the following example response for the format of the answer and justification.
* The insight should be something interesting and grounded based on the question, goal,something that would be interesting. 
* The insight should be as quantiative as possible and informative and non-trivial and concise.
* The insight should be a meaningful conclusion that can be acquired from the analysis in laymans terms

Example response:
<answer>This is a sample answer</answer>
<insight>This is a sample insight</insight>
<justification>This is a sample justification</justification>

### Response:
"""


RETRY_TEMPLATE = """You failed.

Instructions:
-------------
{initial_prompt}
-------------

Completion:
-------------
{prev_output}
-------------

Above, the Completion did not satisfy the constraints given in the Instructions.
Error:
-------------
{error}
-------------

Please try again. Do not apologize. Please only respond with an answer that satisfies the constraints laid out in the Instructions:

"""


GET_INSIGHTS_TEMPLATE = """
Hi, I require the services of your team to help me reach my goal.

<context>{context}</context>

<goal>{goal}</goal>

<schema>{schema}</schema>

Instructions:
* Produce a list of possible insights that we should look into to explore my data and reach my goal.
* Explore diverse aspects of the data, and present possible interesting insights (with explanation) that are relevant to my goal.
* Make sure these can realistically be based on the data schema.
* The insights that your team will extract will be used to insight a report.
* Each question that you produce must be enclosed in <insight></question> tags.
* Do not number the questions.
* You can produce at most {max_questions} insight.

"""

GET_INSIGHTS_SYSTEM_MESSAGE = """
You the manager of a data science team whose goal is to help stakeholders within your company extract actionable insights from their data.
You have access to a team of highly skilled data scientists that can answer complex questions about the data.
You call the shots and they do the work.
Your ultimate deliverable is a report that summarizes the findings and makes hypothesis for any trend or anomaly that was found.
"""



FOLLOW_UP_TEMPLATE = """
Hi, I require the services of your team to help me reach my goal.

<context>{context}</context>

<goal>{goal}</goal>

<schema>{schema}</schema>

<question>{question}</question>

<answer>{answer}</answer>

Instructions:
* Produce a list of follow up questions explore my data and reach my goal.
* Note that we have already answered <question> and have the answer at <answer>, do not include a question similar to the one above. 
* Explore diverse aspects of the data, and ask questions that are relevant to my goal.
* You must ask the right questions to surface anything interesting (trends, anomalies, etc.)
* Make sure these can realistically be answered based on the data schema.
* The insights that your team will extract will be used to generate a report.
* Each question that you produce must be enclosed in <question>content</question> tags.
* Each question should only have one part, that is a single '?' at the end which only require a single answer.
* Do not number the questions.
* You can produce at most {max_questions} questions.

"""

FOLLOW_UP_TYPE_TEMPLATE = """
Hi, I require the services of your team to help me reach my goal.

<context>{context}</context>

<goal>{goal}</goal>

<schema>{schema}</schema>

<question_type>{question_type}</question_type>

<question>{question}</question>

<answer>{answer}</answer>

Instructions:
* Produce a list of follow up questions explore my data and reach my goal.
* Note that we have already answered <question> and have the answer at <answer>, do not include a question similar to the one above. 
* Explore diverse aspects of the data, and ask questions that are relevant to my goal.
* You must ask the right questions to surface anything interesting (trends, anomalies, etc.)
* Make sure these can realistically be answered based on the data schema.
* The insights that your team will extract will be used to generate a report.
* The question has to adhere to the type of question that is provided in the <question_type> tag
* The type of question is either descriptive, diagnostic, prescriptive, or predictive.
* Each question that you produce must be enclosed in <question>content</question> tags.
* Each question should only have one part, that is a single '?' at the end which only require a single answer.
* Do not number the questions.
* You can produce at most {max_questions} questions.

"""


FOLLOW_UP_SYSTEM_MESSAGE = """
You the manager of a data science team whose goal is to help stakeholders within your company extract actionable insights from their data.
You have access to a team of highly skilled data scientists that can answer complex questions about the data.
You call the shots and they do the work.
Your ultimate deliverable is a report that summarizes the findings and makes hypothesis for any trend or anomaly that was found.
"""

SELECT_A_QUESTION_TEMPLATE = """
Hi, I require the services of your team to help me reach my goal.

<context>{context}</context>

<goal>{goal}</goal>

<prev_questions>{prev_questions_formatted}</prev_questions>

<followup_questions>{followup_questions_formatted}</followup_questions>

Instructions:
* Given a context and a goal, select one follow up question from the above list to explore after prev_question that will help me reach my goal.
* Do not select a question similar to the prev_questions above. 
* Output only the index of the question in your response inside <question_id></question_id> tag.
* The output questions id must be 0-indexed.
"""

SELECT_A_QUESTION_SYSTEM_MESSAGE = """
You the manager of a data science team whose goal is to help stakeholders within your company extract actionable insights from their data.
You have access to a team of highly skilled data scientists that can answer complex questions about the data.
You call the shots and they do the work.
Your ultimate deliverable is a report that summarizes the findings and makes hypothesis for any trend or anomaly that was found.
"""


GENERATE_CODE_TEMPLATE = """

Given the goal:\n
{goal}

Given the schema:\n
{schema}

Given the data path:\n
{database_path}

Given the list of predefined functions in autoinsight.tools module and their example usage:\n\n
{function_docs}

Give me the python code required to answer this question "{question}" and put a comment on top of each variable.\n\n

Make a single code block for starting with ```python
Do not produce code blocks for languages other than Python.
Make simple plots and save them as jpg files.
Import autoinsight.tools, pandas as pd, and numpy as np at the beginning and use the predefined functions above to make plots.
If you need to make multiple line/histogram plots, plot with the same x-axis data should be plotted together.
For every plot, save a stats json file that stores the data of the plot.
There can be at most 100 datapoints in the plot.
Round floating datapoints values to the 100th decimal place if necessary.
Each json file must have a "name", "description", and "value" field that describes the data.
If the content of the json file is getting too long, truncate the unnecessary parts.
Call the fix_fnames function in autoinsight.tools at the end of your code.
End your code with ```.

Output code:\n
"""

GENERATE_CODE_TEMPLATE_MULTI = """

Given the goal:\n
{goal}

Given the schema of the first dataset:\n
{schema}

Given the data path of the first dataset:\n
{database_path}

Given the schema of the second dataset:\n
{user_schema}

Given the data path of the second dataset:\n
{user_database_path}

Given the list of predefined functions in autoinsight.tools module and their example usage:\n\n
{function_docs}

Give me the python code required to answer this question "{question}" and put a comment on top of each variable.\n\n

Make a single code block for starting with ```python
Do not produce code blocks for languages other than Python.
Import autoinsight.tools at the beginning. 
You must only use the predefined functions mentioned above to make the plot.
You must generate one single simple plot and save it as a jpg file.
For the plot, save a stats json file that stores the data of the plot.
Save each json file using the autoinsight.save_json function
For the json file must have a "name", "description", and "value" field that describes the data.
If the content of the json file is getting too long, truncate the unnecessary parts until the number of characters is less than 10000

Call the fix_fnames function in autoinsight.tools at the end of your code.
End your code with ```.

Output code:\n
"""

GENERATE_CODE_SINGLE_TEMPLATE = """

Given the goal:\n
{goal}

Given the schema:\n
{schema}

Given the data path:\n
{database_path}

Given the list of predefined functions in autoinsight.tools module and their example usage:\n\n
{function_docs}

Give me the python code required to answer this question "{question}" and put a comment on top of each variable.\n\n

Make a single code block for starting with ```python
Do not produce code blocks for languages other than Python.
Import autoinsight.tools at the beginning. 
You must only use the predefined functions mentioned above to make the plot.
You must generate one single simple plot and save it as a jpg file.
For the plot, save a stats json file that stores the data of the plot.
Save stats json file using the autoinsight.save_json function.
If to_dict() is called on a pandas DataFrame, orient='records' must be specified.
Do not use orient='records' when calling to_dict() on a Series.
For the json file must have a "plot type" and "value" field that describes the data.
Call the fix_fnames function in autoinsight.tools at the end of your code.
End your code with ```.

Output code:\n
"""


SUMMARIZE_TEMPLATE = """
Hi, I require the services of your team to help me reach my goal.

<context>{context}</context>

<goal>{goal}</goal>

<history>{history}</history>

Instructions:
* Given a context and a goal, and all the history of <question_i><answer_i> pairs from the above list generate the 3 top actionable insights.
* Make sure they don't offer actions and the summary should be more about highlights of the findings
* Output each insight within this tag <insight></insight>.
* Each insight should be a meaningful conclusion that can be acquired from the analysis in laymans terms and should be as quantiative as possible and should aggregate the findings.
"""

SUMMARIZE_SYSTEM_MESSAGE = """
You the manager of a data science team whose goal is to help stakeholders within your company extract actionable insights from their data.
You have access to a team of highly skilled data scientists that can answer complex questions about the data.
You call the shots and they do the work.
Your ultimate deliverable is a report that summarizes the findings and makes hypothesis for any trend or anomaly that was found.
"""


