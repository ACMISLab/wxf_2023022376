import numpy as np, pandas as pd, re, json, os, shutil, inspect
import contextlib
import io
import os
import re
import traceback
from autoinsight import prompts
from copy import deepcopy
from dateutil.parser import parse
from langchain.schema import HumanMessage, SystemMessage
from warnings import warn
from functools import partial
from langchain.prompts import PromptTemplate
from openai import OpenAI
from pathlib import Path
from autoinsight import tools
from recognizer.reger import reg_insight


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
JSON_MAX_TOKENS = 5000
JSON_MAX_CHARS = JSON_MAX_TOKENS * 4  # 4 chars per token (roughly)

def _parse_insight_polish(output):
    """
    A parser that makes sure that the human readable insight is produced in the correct format

    """
    try:
        insight = extract_html_tags(output, ["insight"])
        if "insight" not in insight:
            return (
                "",
                False,
                f"Error: you did not generate insight within the <insight></insight> tags",
            )
        insight = insight["insight"][0]
    except ValueError as e:
        return (
            "",
            False,
            f"The following error occured while extracting the value for the <insight> tag: {str(e)}",
        )

    return (
        insight,
        True,
        "",
    )
def polish_insight(
        base_url,
        solution,
        model_name,
        temperature,
        savedir,
        answer
):


    prompt_template = prompts.get_polish_prompt(method="basic")
    # create prompt
    prompt = PromptTemplate.from_template(prompt_template)

    # instantiate llm model
    llm = get_chat_model(base_url,model_name, temperature,savedir)

    # Get human readable answer
    out, _ = retry_on_parsing_error(
        llm,
        prompt.format(
            question=solution["question"],
            insight=answer,
        ),
        parser=_parse_insight_polish,
        n_retries=1,
    )
    return out


    return 0

def _parse_insight_rating(output):
    """
    A parser that makes sure that the human readable insight is produced in the correct format

    """
    try:
        score = extract_html_tags(output, ["score"])
        if "score" not in score:
            return (
                "",
                False,
                f"Error: you did not generate score within the <score></score> tags",
            )
        score = score["score"][0]
    except ValueError as e:
        return (
            "",
            False,
            f"The following error occured while extracting the value for the <score> tag: {str(e)}",
        )

    return (
        {"score": score},
        True,
        "",
    )
def dynamic_pruning(
        base_url,
        goal,
        question,
        model_name,
        temperature,
        savedir,
        sta_score,
        insight
):


    prompt_template = prompts.get_eval_prompt(method="basic")
    # create prompt
    prompt = PromptTemplate.from_template(prompt_template)

    # instantiate llm model
    llm = get_chat_model(base_url,model_name, temperature,savedir)

    # Get human readable answer
    out, _ = retry_on_parsing_error(
        llm,
        prompt.format(
            goal=goal,
            question=question,
            insight=insight,
        ),
        parser=_parse_insight_rating,
        n_retries=2,
    )
    if sta_score:
        insight_score = 0.5 * int(sta_score) + 0.5 * int(out["score"]) / 10
    else:
        insight_score = int(out["score"]) / 10

    return insight_score


def recognize_insight(
    sta_json_folder: str = None,
):
    """
    Produce insights by a insight recognizer

    Parameters:
    -----------
    savedir: str
        The output of the code generation function

    Returns:
    --------
    sta_score,insights: int,str
        The path to the input solution file, which has been updated with the interpretation

    """
    import math

    for filename in os.listdir(sta_json_folder):
        if filename.endswith(".json"):
            file_path = os.path.join(sta_json_folder, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    json1 = json.load(f)
                except json.JSONDecodeError:
                    print(f"{filename} 不是有效的 JSON 文件")
                    continue

            if "value" not in json1:
                print("json1 没有 'value' 字段")
                continue

            if not json1["value"]:
                print("value 为空")
                continue

            if not isinstance(json1["value"], list) or not all(isinstance(item, dict) for item in json1["value"]):
                print(f"{filename} 数据不合规：'value' 中的元素不是字典类型")
                continue

            # ✅ ====== 关键步骤：过滤掉含 NaN 的数据 ======
            clean_values = []
            for item in json1["value"]:
                has_nan = False
                for v in item.values():
                    if isinstance(v, float) and math.isnan(v):
                        has_nan = True
                        break
                if not has_nan:
                    clean_values.append(item)

            if not clean_values:
                print(f"{filename} 清洗后数据为空")
                continue

            # 替换原数据
            json1["value"] = clean_values
            # ============================================

            first_item = json1["value"][0]
            keys = list(first_item.keys())
            if not keys:
                print(f"{filename} 数据不合规：'value' 中的字典为空")
                continue

            xField = [keys[0]]
            yField = keys[1:]

            spec = {
                "type": json1.get("plot_type"),
                "xField": xField,
                "yField": yField,
                "data": [
                    {
                        "id": "data",
                        "values": json1["value"]
                    }
                ]
            }

    try:
        sta_score, insight_text = reg_insight(spec)
        return {"text": insight_text, "score": sta_score}
    except Exception as e:
        print(f"识别出错 {e}")
        return 0

def interpret_insight(
    base_url:str,
    solution: dict,
    n_retries: int,
    model_name: str,
    prompt_method,
    schema,
    temperature: 0,
    savedir: str = None,
) -> str:
    """
    Produce insights for a task based on a solution output by a model

    Parameters:
    -----------
    solution: dict
        The output of the code generation function
    answer_template: dict
        A template for the answer that the human should provide. This template should contain a "results" tag
        that contains a list of expected results in the form of dictionaries. Each dictionary should contain
        the following keys: "name", "description", and "value". The model will be asked to fill in the values.
    model: str
        The name of the model to use (default: gpt-4)
    n_retries: int
        The number of times to retry the interpretation if it fails

    Returns:
    --------
    solution_path: str
        The path to the input solution file, which has been updated with the interpretation

    """
    prompt_template = prompts.get_interpret_prompt(method=prompt_method)
    # create prompt
    prompt = PromptTemplate.from_template(prompt_template)

    insight_prompt = _build_insight_prompt(solution)

    # instantiate llm model
    llm = get_chat_model(base_url,model_name, temperature,savedir)

    # Get human readable answer
    out, _ = retry_on_parsing_error(
        llm,
        prompt.format(
            goal=solution["goal"],
            question=solution["question"],
            message=solution["code_output"],
            insights=insight_prompt,
            schema=schema,
        ),
        parser=_parse_human_readable_insight,
        n_retries=n_retries,
    )
    solution["interpretation"] = out
    return solution


def extract_python_code_blocks(text):
    """
    Extract and merge Python code blocks from a given text string.

    The function identifies code blocks that start with ``` or ```python and end with ```.
    After extracting the code blocks, it removes the start and end delimiters (```, ```python),
    and merges the code blocks together into a single string.

    Parameters
    ----------
    text : str
        The input string from which Python code blocks need to be extracted.

    Returns
    -------
    str
        A string containing the merged Python code blocks stripped of leading and trailing whitespaces.
        Code blocks are separated by a newline character.

    """

    code_blocks = re.findall(r"```(?:python)?(.*?)```", text, re.DOTALL)
    return "\n".join(block.strip() for block in code_blocks)


class PythonREPL:
    """
    Simulates a standalone Python REPL.

    TODO add a way to pass a random seed to the REPL
    """

    def __init__(self):
        self.history = []

    def run(self, command: str, workdir: str = None) -> str:
        """Run command with own globals/locals and returns anything printed."""

        if workdir is not None:
            old_cwd = Path.cwd()
            os.chdir(workdir)

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                exec(command, locals())
                valid = True
                retry_message = ""
                self.history.append((command, workdir))
            except Exception as e:
                valid = False
                retry_message = traceback.format_exc() + "\n" + str(e)
            finally:
                if workdir is not None:
                    os.chdir(old_cwd)
        output = buffer.getvalue()

        return output, valid, retry_message

    def clone(self):
        """Clone the REPL from history.

        it is not possible to clone the REPL from the globals/locals because they
        may contain references to objects that cannot be pickled e.g. python modules.
        Instead, we clone the REPL by replaying the history.
        """
        new_repl = PythonREPL()
        # deepcopy of history
        new_repl.history = deepcopy(self.history)

        for command, workdir in self.history:
            new_repl.run(command, workdir=workdir)

        return new_repl


# =============================================================================
# Code generation
# =============================================================================
def _code_parser(code, output_folder):
    """
    A parser that is used to parse the code generated by the LLM
    and determine whether it is acceptable or not

    """
    # Clean output folder
    output_folder = Path(output_folder)
    if output_folder.exists():
        shutil.rmtree(output_folder)
    output_folder.mkdir(parents=True)

    # Extract code blocks from the input code (might contain other text)
    code_block = extract_python_code_blocks(code)
    if len(code_block) == 0:
        # No code blocks detected so input is likely already raw code
        code_block = code

    # Run code and report any errors
    output, valid, retry_message = PythonREPL().run(code_block, workdir=output_folder)
    if not valid:
        return "", valid, retry_message

    # Validate output files
    json_files = [f.name for f in output_folder.glob("*.json")]
    plot_files = [f.name for f in output_folder.glob("*.jpg")]

    try:
        # assert that there is x_axis.json, y_axis.json, and stat.json in json_files
        assert "stat.json" in json_files
        assert len(json_files) == 1

        # Check that the total length of all json files is not too long
        json_lengths = [len(open(output_folder / f).read()) for f in json_files]
        total_json_chars = sum(json_lengths)
        if total_json_chars > JSON_MAX_CHARS:
            return (
                "",
                False,
                f"Error: The total length of your json files cannot exceed {JSON_MAX_CHARS} characters. Here is the total length of each json file: {', '.join(f'{f} ({l} characters)' for f, l in zip(json_files, json_lengths))}.",
            )

        assert len(plot_files) == 1 and "plot.jpg" in plot_files

    except:
        return (
            "",
            False,
            f"Error: Your code did not generate the expected output files. Expected stat.json files.",
        )

    # All checks have passed!
    return output, True, ""


def retry_on_parsing_error(
    llm,
    initial_prompt,
    parser,
    n_retries,
    exception_on_max_retries=True,
):
    """
    Try querying a LLM until it returns a valid value with a maximum number of retries.

    Parameters:
    -----------
    llm : callable
        A langchain LLM model.
    initial_prompt : str
        The initial prompt to send to the LLM.
    parser : callable
        A function taking a message and returning a tuple (value, valid, retry_message),
        where retries will be made until valid is True.
    n_retries : int
        The maximum number of retries.
    exception_on_max_retries : bool
        If True, raise an exception if the maximum number of retries is reached.
        Otherwise, returns "".

    Returns:
    --------
    value : str
        The value returned by the LLM.
    completions : list
        The attempts made by the LLM.

    """
    retry_template = prompts.RETRY_TEMPLATE
    prompt = initial_prompt

    completions = []
    for i in range(n_retries + 1):  # Add one since the initial prompt is not a retry
        # Try to get a valid completion

        completions.append(llm(prompt))

        output, valid, retry_message = parser(completions[-1])

        # If parser execution succeeds return the output
        if valid:
            return output, completions

        # If parser execution fails, produce a new prompt that includes the previous output and the error message
        warn(
            f"Retry {i+1}/{n_retries} - Query failed with error: {retry_message}",
            RuntimeWarning,
        )

        prompt = retry_template.format(
            initial_prompt=initial_prompt,
            prev_output=completions[-1],
            error=retry_message[-200:],  # 截取后500个字符
        )

    if exception_on_max_retries:
        return f"Could not parse a valid value after {n_retries} retries.", [
            "```python\nimport pandas as pd```",
            "```python\nimport numpy as np```",
        ]
    else:
        return retry_message, completions


def _extract_top_values(values, k=3, max_str_len=100):
    """
    Extracts the top k values from a pandas series

    Parameters
    ----------
    values : pandas.Series
        Series to extract top values from
    k : int, optional
        Number of top values to extract, by default 5
    max_str_len : int, optional
        Maximum length of string values (will be truncated), by default 100

    """
    top = values.value_counts().iloc[:k].index.values.tolist()
    top = [x if not isinstance(x, str) else x[:max_str_len] for x in top]
    return top


def get_schema(df):
    """
    Extracts schema from a pandas dataframe

    Parameters
    ----------
    df : pandas.DataFrame
        Dataframe to extract schema from

    Returns
    -------
    list of dict
        Schema for each column in the dataframe

    """
    schema = []

    for col in df.columns:
        info = {
            "name": col,
            "type": df[col].dtype,
            "missing_count": df[col].isna().sum(),
            "unique_count": df[col].unique().shape[0],
            "unique_ratio": df[col].unique().shape[0] / len(df)
        }

        valid_values = df[col].dropna()
        if np.issubdtype(df[col].dtype, np.number) or _is_date(df[col].iloc[0]):
            if len(valid_values) > 0:
                info["sample_value"] = valid_values.sample(1, random_state=42).iloc[0]
            else:
                info["sample_value"] = None

        # If the column is numeric, extract some stats
        if np.issubdtype(df[col].dtype, np.number):
            info["min"] = df[col].min()
            info["max"] = df[col].max()
            info["mean"] = df[col].mean()
            info["std"] = df[col].std()
            info["quantiles"] = df[col].quantile([0.25, 0.5, 0.75]).to_dict()
        # If the column is a date, extract the min and max
        elif _is_date(df[col].iloc[0]):
            info["min"] = df[col].dropna().min()
            info["max"] = df[col].dropna().max()
        # If the column is something else, extract the top values
        else:
            info["top3_unique_values"] = _extract_top_values(df[col])

        schema.append(info)

    return schema

def get_schema_a(df):
    sample = df.sample(n=10, random_state=42)
    return sample.to_string(index=False)


def _is_date(string):
    """
    Checks if a string is a date

    Parameters
    ----------
    string : str
        String to check

    Returns
    -------
    bool
        True if the string is a date, False otherwise

    """
    try:
        parse(str(string))
        return True
    except ValueError:
        return False



def convert_messages_to_text(messages):
    """
    Convert a list of messages to a string

    Parameters
    ----------
    messages : list
        List of messages to convert

    Returns
    -------
    str
        String representation of the messages, or a fallback message on error

    """
    try:
        return "\n".join(
            [
                (
                    f"[INST]\n{m.content}\n[/INST]"
                    if m.type in ["system", "agent"]
                    else f"\n{m.content}\n"
                )
                for m in messages
            ]
        )
    except Exception as e:
        # Optional: log the error
        print(f"[convert_messages_to_text] Error while processing messages: {e}")

        # Return irrelevant text to prevent interruption
        return "\n[Unable to parse message content...]\n"



def chat_and_retry(chat, messages, n_retry, parser):
    for i in range(n_retry):
        messages = convert_messages_to_text(messages)
        answer = chat(messages)
        value, valid, retry_message = parser(answer)

        if valid:
            return value

        msg = f"Query failed. Retrying {i+1}/{n_retry}.\n[LLM]:\n{answer}\n[User]:\n{retry_message}"
        warn(msg, RuntimeWarning)
        messages += answer
        messages += retry_message

    return {
        "answer": "Error occured",
        "justification": f"Could not parse a valid value after {n_retry} retries.",
    }


def extract_html_tags(text, keys):
    """Extract the content within HTML tags for a list of keys.

    Parameters
    ----------
    text : str
        The input string containing the HTML tags.
    keys : list of str
        The HTML tags to extract the content from.

    Returns
    -------
    dict
        A dictionary mapping each key to a list of subset in `text` that match the key.

    Notes
    -----
    All text and keys will be converted to lowercase before matching.

    """
    content_dict = {}
    keys = set(keys)
    for key in keys:
        pattern = f"<{key}>(.*?)</{key}>"
        matches = re.findall(pattern, text, re.DOTALL)
        # print(matches)
        if matches:
            content_dict[key] = [match.strip() for match in matches]
    return content_dict


def _parse_human_readable_insight(output):
    """
    A parser that makes sure that the human readable insight is produced in the correct format

    """
    try:
        answer = extract_html_tags(output, ["answer"])
        if "answer" not in answer:
            return (
                "",
                False,
                f"Error: you did not generate answers within the <answer></answer> tags",
            )
        answer = answer["answer"][0]
    except ValueError as e:
        return (
            "",
            False,
            f"The following error occured while extracting the value for the <answer> tag: {str(e)}",
        )

    try:
        justification = extract_html_tags(output, ["justification"])
        if "justification" not in justification:
            return (
                "",
                False,
                f"Error: you did not generate answers within the <justification></justification> tags",
            )
        justification = justification["justification"][0]
    except ValueError as e:
        return (
            "",
            False,
            f"The following error occured while extracting the value for the <justification> tag: {str(e)}",
        )
    try:
        insight = extract_html_tags(output, ["insight"])
        if "insight" not in insight:
            return (
                "",
                False,
                f"Error: you did not generate answers within the <insight></insight> tags",
            )
        insight = insight["insight"][0]
    except ValueError as e:
        return (
            "",
            False,
            f"The following error occured while extracting the value for the <insight> tag: {str(e)}",
        )

    return (
        {"answer": answer, "justification": justification, "insight": insight},
        True,
        "",
    )


def _build_insight_prompt(solution) -> str:
    """
    Gather all plots and statistics produced by the model and format then nicely into text

    """
    insight_prompt = ""
    for i, var in enumerate(solution["vars"]):
        insight_prompt += f"<insight id='{i}'>"
        insight_prompt += f"    <stat>"
        insight_prompt += f"        <name>{var['stat'].get('name', 'n/a')}</name>"
        insight_prompt += f"        <description>{var['stat'].get('description', 'n/a')}</description>"
        stat_val = var["stat"].get("value", "n/a")
        stat_val = stat_val[:100] if isinstance(stat_val, list) else stat_val
        insight_prompt += f"        <value>{stat_val}</value>"
        insight_prompt += f"    </stat>"
        insight_prompt += f"</insight>"
    return insight_prompt


def get_questions(
    base_url,
    prompt_method,
    context,
    goal,
    messages=[],
    schema=None,
    user_schema=None,
    max_questions=10,
    model_name="gpt-4o",
    temperature=0,
    savedir=None,
):
    if prompt_method is None:
        prompt_method = "basic"
    if user_schema is not None:
        prompt_method = "multi"

    prompt, system = prompts.get_question_prompt(method=prompt_method)

    chat = get_chat_model(base_url,model_name, temperature,savedir)

    messages = [
        SystemMessage(content=system),
        HumanMessage(
            content=prompt.format(
                context=context, goal=goal, schema=schema, user_schema=user_schema, max_questions=max_questions
            )
        ),
    ]

    def _validate_tasks(out):
        questions = extract_html_tags(out, ["question"])
        if "question" not in questions:
            return (
                out,
                False,
                f"Error: you did not generate questions within the <question></question> tags",
            )
        questions = questions["question"]
        # Check that there are at most max_questions questions
        if len(questions) > max_questions:
            return (
                out,
                False,
                f"Error: you can only ask at most {max_questions} questions, but you asked {len(questions)}.",
            )

        return (questions, out), True, ""

    questions, message = chat_and_retry(
        chat, messages, n_retry=3, parser=_validate_tasks
    )

    return questions

"""
def get_dataset_description(
    prompt,
    system,
    context,
    goal,
    messages=[],
    schema=None,
    model_name="gpt-4o",
    temperature=0,
):

    chat = get_chat_model(model_name, temperature)

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=prompt.format(context=context, goal=goal, schema=schema)),
    ]

    def _validate_tasks(out):
        try:
            questions = extract_html_tags(out, ["description"])["description"]
        except Exception as e:
            return (
                out,
                False,
                f"Error: {str(e)}",
            )

        return (questions, out), True, ""

    data_description, message = chat_and_retry(
        chat, messages, n_retry=2, parser=_validate_tasks
    )

    return data_description"""


def get_follow_up_questions(
    base_url,
    context,
    goal,
    question,
    answer,
    schema=None,
    user_schema = None,
    max_questions=3,
    model_name="gpt-4o",
    prompt_method=None,
    question_type="descriptive",
    temperature=0,
    savedir=None,
):
    if prompt_method is None:
        prompt_method = "follow_up"

    prompt, system = prompts.get_question_prompt(method=prompt_method)
    chat = get_chat_model(base_url,model_name, temperature,savedir)

    if prompt_method == "follow_up_with_type":
        content = prompt.format(
            context=context,
            goal=goal,
            question=question,
            answer=answer,
            schema=schema,
            max_questions=max_questions,
            question_type=question_type,
        )

    else:
        content = prompt.format(
            context=context,
            goal=goal,
            question=question,
            answer=answer,
            schema=schema,
            max_questions=max_questions,
        )

    messages = [
        SystemMessage(content=system),
        HumanMessage(content=content),
    ]

    def _validate_tasks(out):
        try:
            questions = extract_html_tags(out, ["question"])["question"]
        except Exception:
            questions = "To analyze the data to discover valuable insights."

        # 如果 questions 是字符串，说明发生了异常，返回默认提示信息
        if isinstance(questions, str):
            return (
                (questions, out),
                True,
                "",
            )

        # 正常处理 questions 列表
        if len(questions) > max_questions:
            return (
                out,
                False,
                f"Error: you can only ask at most {max_questions} questions, but you asked {len(questions)}.",
            )

        return (questions, out), True, ""

    questions, message = chat_and_retry(
        chat, messages, n_retry=3, parser=_validate_tasks
    )

    return questions


def select_a_question(
    base_url,
    questions,
    context,
    goal,
    prev_questions,
    model_name="gpt-4o",
    prompt_template=None,
    system_template=None,
    temperature=0,
    savedir=None,
):

    chat = get_chat_model(base_url,model_name, temperature,savedir)

    followup_questions_formatted = "\n".join(
        [f"{i+1}. {q}\n" for i, q in enumerate(questions)]
    )
    if prev_questions:
        prev_questions_formatted = "\n".join(
            [f"{i+1}. {q}\n" for i, q in enumerate(prev_questions)]
        )
    else:
        prev_questions_formatted = None

    prompt = prompt_template
    messages = [
        SystemMessage(content=system_template),
        HumanMessage(
            content=prompt.format(
                context=context,
                goal=goal,
                prev_questions_formatted=prev_questions_formatted,
                followup_questions_formatted=followup_questions_formatted,
            )
        ),
    ]

    def _validate_tasks(out):
        try:
            question_id = extract_html_tags(out, ["question_id"])["question_id"][0]
        except (KeyError, IndexError, TypeError) as e:
            question_id = 100
            print(f"Failed to extract question_id: {e}")
        # Check that there are at most max_questions questions
        if int(question_id) >= len(questions):
            return (
                out,
                False,
                f"Error: selected question index should be between 0-{len(questions)-1}.",
            )
        return (int(question_id), out), True, ""

    question_id, message = chat_and_retry(
        chat, messages, n_retry=3, parser=_validate_tasks
    )
    return question_id

def generate_code(
    base_url,
    schema,
    user_schema,
    goal,
    question,
    database_path,
    user_database_path,
    output_folder,
    n_retries,
    prompt_method=None,
    model_name="gpt-4o",
    temperature=0,
    savedir=None
):
    """
    Solve a task using the naive single step approach

    See main function docstring for more details

    """
    prompt_template = prompts.get_code_prompt(method=prompt_method)

    available_functions = [
        func_name
        for func_name, obj in inspect.getmembers(tools)
        if inspect.isfunction(obj)
    ]
    function_docs = []
    for func_name in available_functions:
        function_docs.append(
            f"{func_name}{inspect.signature(getattr(tools, func_name))}:\n{inspect.getdoc(getattr(tools, func_name))}\n"
            + "=" * 20
            + "\n"
        )
    function_docs = "\n".join(function_docs)

    # instantiate llm model
    llm = get_chat_model(base_url,model_name, temperature,savedir)

    # create prompt
    if user_schema is None:
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=[
                "goal",
                "schema",
                "question",
                "database_path",
                "function_docs",
            ],
        )
    else:
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=[
                "goal",
                "schema",
                "question",
                "database_path",
                "function_docs",
                "user_schema",
                "user_database_path",
            ],
        )

    # Run the retry on error function
    if user_schema is None:
        output, completions = retry_on_parsing_error(
            llm=llm,
            initial_prompt=prompt.format(
                goal=goal,
                schema=schema,
                question=question,
                database_path=database_path,
                function_docs=function_docs,
            ),
            parser=partial(_code_parser, output_folder=output_folder),
            n_retries=n_retries,
            exception_on_max_retries=False,
        )
    else:
        output, completions = retry_on_parsing_error(
            llm=llm,
            initial_prompt=prompt.format(
                goal=goal,
                schema=schema,
                question=question,
                database_path=database_path,
                function_docs=function_docs,
                user_schema=user_schema,
                user_database_path=user_database_path,
            ),
            parser=partial(_code_parser, output_folder=output_folder),
            n_retries=n_retries,
            exception_on_max_retries=False,
        )

    # Create the output dict
    # Then, iterate over all generated plots and add them to the output dict
    output_dict = {
        "code": completions[-1],
        "prompt": str(prompt),
        "code_output": output,
        "message": output,
        "n_retries": len(completions) - 1,
        "goal": goal,
        "question": question,
        "vars": [],
    }

    # write code to a file
    with open(f"{output_folder}/code.py", "w", encoding="utf-8") as file:
        # use regex to capture the python code block
        code = completions[-1]
        try:
            code = re.findall(r"```python(.*?)```", code, re.DOTALL)[0]
            file.write(code.strip())
        except Exception as e:
            print(f"Failed to write code", e)
            file.write(code.strip())

    # Try to load the model's output files
    # TODO: We should detect errors in such files and trigger a retry
    try:
        stat = json.load(open(f"{output_folder}/stat.json", "r"))
    except Exception as e:
        print(f"Failed to load {output_folder}/stat.json", e)
        stat = {}

    # Add the plot to the final output dict
    plot_path = f"{output_folder}/plot.jpg"
    stat["type"] = "stat"
    plot_dict = {"name": plot_path, "type": "plot"}
    output_dict["vars"] += [
        {
            "stat": stat,
            "plot": plot_dict,
        }
    ]

    return output_dict
def get_openai_response(url,model_name,messages,savedir):


    client = OpenAI(
        base_url='https://api.openai-proxy.org/v1',
        api_key='api_key',
    )

    response = client.chat.completions.create(
        messages=messages,
        model=model_name,
    )

    content = response.choices[0].message.content
    usages = {
        "completion_tokens": response.usage.completion_tokens,
        "prompt_tokens": response.usage.prompt_tokens,
        "total_tokens": response.usage.total_tokens
    }

    usage_file = os.path.join(savedir, "usages.json")

    if not os.path.exists(usage_file):
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump([usages], f, indent=2)
    else:
        with open(usage_file, 'r+', encoding='utf-8') as f:
            try:
                existing_usages = json.load(f)
                if not isinstance(existing_usages, list):
                    existing_usages = []
            except json.JSONDecodeError:
                existing_usages = []

            existing_usages.append(usages)
            f.seek(0)
            json.dump(existing_usages, f, indent=2)
            f.truncate()

    return content
def swift_deploy_responce(base_url,model_name,messages,savedir):

    from openai import OpenAI
    # 初始化客户端
    client = OpenAI(
        base_url=base_url,
        api_key="xxxxxx"
    )

    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature = 0
    )

    content=response.choices[0].message.content
    usages = {
        "completion_tokens": response.usage.completion_tokens,
        "prompt_tokens": response.usage.prompt_tokens,
        "total_tokens": response.usage.total_tokens,
    }

    usage_file = os.path.join(savedir, "usages.json")

    if not os.path.exists(usage_file):
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump([usages], f, indent=2)
    else:
        with open(usage_file, 'r+', encoding='utf-8') as f:
            try:
                existing_usages = json.load(f)
                if not isinstance(existing_usages, list):
                    existing_usages = []
            except json.JSONDecodeError:
                existing_usages = []

            existing_usages.append(usages)
            f.seek(0)
            json.dump(existing_usages, f, indent=2)
            f.truncate()

    return content
def local_deploy_responce(base_url,model_name,messages,savedir):
    import requests
    base_url = base_url
    data = {
        "model": model_name,
        "messages": messages,
        "temperature": 0,
    }

    response = requests.post(f"{base_url}/v1/chat/completions", json=data, stream=False).json()
    content = response['choices'][0]['message']['content']


    usages = {
        "completion_tokens": response['usage']['completion_tokens'],
        "prompt_tokens": response['usage']['prompt_tokens'],
        "total_tokens": response['usage']['total_tokens']
    }

    usage_file = os.path.join(savedir, "usages.json")

    if not os.path.exists(usage_file):
        with open(usage_file, 'w', encoding='utf-8') as f:
            json.dump([usages], f, indent=2)
    else:
        with open(usage_file, 'r+', encoding='utf-8') as f:
            try:
                existing_usages = json.load(f)
                if not isinstance(existing_usages, list):
                    existing_usages = []
            except json.JSONDecodeError:
                existing_usages = []

            existing_usages.append(usages)
            f.seek(0)
            json.dump(existing_usages, f, indent=2)
            f.truncate()

    return content

def get_chat_model(base_url,model_name, temperature=0,savedir=None):
    if "swift" in model_name:
        llm = lambda content: swift_deploy_responce(base_url, model_name, [{"role": "user", "content": content}], savedir)
    elif "gpt" in model_name:
        llm = lambda content: get_openai_response(base_url,model_name, [{"role": "user", "content": content}], savedir)
    elif "QwQ" in model_name or "Qwen" in model_name or "Llama" in model_name:
        llm = lambda content: local_deploy_responce(base_url,model_name, [{"role": "user", "content": content}], savedir)
    else:
        raise ValueError("Unsupported model. Please set the model name correctly.")

    return llm

