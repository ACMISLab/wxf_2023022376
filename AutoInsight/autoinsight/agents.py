import tempfile
import copy
import pandas as pd

from autoinsight.utils import agent_utils as au
from autoinsight import prompts
from langchain.schema import HumanMessage, SystemMessage
from PIL import Image
import os, json, logging


class Agent:

    def __init__(
        self,
        table=None,
        table_user=None,
        dataset_csv_path=None,
        user_dataset_csv_path=None,
        model_name="gpt-4o",
        goal="I want to find interesting trends in this dataset",
        max_questions=3,
        branch_depth=4,
        n_retries=2,
        savedir=None,
        temperature=0,
        base_url="http://210.40.16.12:52345"
    ):
        self.goal = goal
        self.max_questions = max_questions

        self.temperature = temperature
        self.base_url=base_url
        self.model_name = model_name
        self.n_retries = n_retries
        self.branch_depth = branch_depth

        if savedir is None:
            savedir = tempfile.mkdtemp()
        self.savedir = savedir

        self.agent_poirot = AgentPoirot(
            model_name=model_name,
            base_url=base_url,
            savedir=savedir,
            goal=goal,
            verbose=True,
            temperature=temperature,
            n_retries=n_retries,
        )
        if dataset_csv_path is not None or table is not None:
            self.agent_poirot.set_table(
                table=table,
                table_user=table_user,
                dataset_csv_path=dataset_csv_path,
                user_dataset_csv_path=user_dataset_csv_path,
            )

    def get_insights(
        self,
        dataset_csv_path=None,
        user_dataset_csv_path=None,
        table=None,
        table_user=None,
        return_summary=True,
    ) -> tuple:
        """
        run the agent to generate a sequence of questions and answers
        """
        self.agent_poirot.set_table(
            table=table,
            table_user=table_user,
            dataset_csv_path=dataset_csv_path,
            user_dataset_csv_path=user_dataset_csv_path,
        )

        # Prompt 2: Get Root Questions
        root_questions = self.agent_poirot.recommend_questions(
            prompt_method="basic", n_questions=self.max_questions
        )

        # Go through the root questions and generate insights
        for q in root_questions:
            question = q
            parent_question_id = None
            for i in range(self.branch_depth):
                if self.agent_poirot.table_user is None:
                    prompt_code_method = "single"
                else:
                    prompt_code_method = "multi"
                _, insight_dict = self.agent_poirot.answer_question(
                    question,
                    prompt_code_method=prompt_code_method,
                    prompt_interpret_method="basic",
                    parent_question_id=parent_question_id,
                )

                current_question_id = f"question_{len(self.agent_poirot.insights_history) - 1}"

                # 动态剪枝--停止当前分支，进入下一个 root_question
                print("输出当前洞察得分：")
                print(insight_dict['insight_score'])
                if insight_dict.get("insight_score", 0) < 0.75:
                    break

                next_questions = self.agent_poirot.recommend_questions(
                    n_questions=self.max_questions,
                    insights_history=[insight_dict],
                    # prompt_method="follow_up_with_type",
                    # question_type="descriptive",
                )
                question = next_questions[
                    self.agent_poirot.select_a_question(next_questions)
                ]
                parent_question_id = current_question_id

        self.agent_poirot.save_state_dict(
            os.path.join(self.savedir, "insights_history.json")
        )
        pred_insights = [o["insight"] for o in self.agent_poirot.insights_history]
        pred_questions = [o["question"] for o in self.agent_poirot.insights_history]
        if return_summary:
            pred_summary = self.summarize(self.agent_poirot.insights_history)
            return pred_questions,pred_insights, pred_summary
        return self.agent_poirot.insights_history

    def load_checkpoint(self, savedir):
        self.agent_poirot.load_state_dict(
            os.path.join(savedir, "insights_history.json")
        )

    def summarize(self, pred_insights, method="list", prompt_summarize_method="basic"):
        return self.agent_poirot.summarize(
            pred_insights, method, prompt_summarize_method
        )


class AgentPoirot:
    def __init__(
        self,
        savedir=None,
        context="This is a dataset that could potentially consist of interesting insights",
        base_url="base_url",
        model_name="gpt-3.5-turbo-0613",
        goal="I want to find interesting trends in this dataset",
        verbose=False,
        temperature=0,
        n_retries=2
    ):
        self.goal = goal
        if savedir is None:
            savedir = tempfile.mkdtemp()
        self.base_url=base_url
        self.savedir = savedir
        self.context = context

        self.model_name = model_name
        self.temperature = temperature

        self.insights_history = []
        self.verbose = verbose
        self.n_retries = n_retries

    def set_table(
        self,
        table=None,
        table_user=None,
        dataset_csv_path=None,
        user_dataset_csv_path=None,
    ):
        self.table = table
        self.table_user = table_user
        self.dataset_csv_path = dataset_csv_path
        self.user_dataset_csv_path = user_dataset_csv_path

        if table is not None:
            self.table = table
        if table_user is not None:
            self.table_user = table_user
        if dataset_csv_path is not None:
            self.dataset_csv_path = dataset_csv_path
            self.table = pd.read_csv(dataset_csv_path)
        if user_dataset_csv_path is not None:
            self.user_dataset_csv_path = user_dataset_csv_path
            self.table_user = pd.read_csv(user_dataset_csv_path)

        # schema
        self.schema = au.get_schema(self.table)
        if self.table_user is not None:
            self.user_schema = au.get_schema(self.table_user)
        else:
            self.user_schema = None

    def summarize(self, pred_insights, method="list", prompt_summarize_method="basic"):
        if method == "list":
            chat = au.get_chat_model(self.base_url,self.model_name, self.temperature,self.savedir)

            # Function to format the data
            def format_data(data):
                result = ""
                for i, item in enumerate(data):
                    question_tag = f"<question_{i}>{item['question']}</question_{i}>\n"
                    answer_tag = f"<answer_{i}>{item['answer']}</answer_{i}>\n\n"
                    result += f"{question_tag} {answer_tag}\n"
                return result

            # Format the data and print
            formatted_history = format_data(pred_insights)

            # summary = agent.summarize_insights(method="list")
            content_prompt, system_prompt = prompts.get_summarize_prompt(
                method=prompt_summarize_method
            )
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=content_prompt.format(
                        context=self.context,
                        goal=self.goal,
                        history=formatted_history,
                    )
                ),
            ]

            def _validate_tasks(out):
                isights = au.extract_html_tags(out, ["insight"])

                # Check that there are insights generated
                if "insight" not in isights:
                    return (
                        out,
                        False,
                        f"Error: you did not generate insights within the <insight></insight> tags.",
                    )
                isights = isights["insight"]
                return (isights, out), True, ""

            insight_list, message = au.chat_and_retry(
                chat, messages, n_retry=3, parser=_validate_tasks
            )

            insights = "\n".join(insight_list)

        return insights

    def select_a_question(self, questions):
        """
        Select a question from the list of questions
        """
        return au.select_a_question(
            base_url=self.base_url,
            questions=questions,
            context=self.context,
            goal=self.goal,
            prev_questions=[o["question"] for o in self.insights_history],
            model_name=self.model_name,
            prompt_template=prompts.SELECT_A_QUESTION_TEMPLATE,
            system_template=prompts.SELECT_A_QUESTION_SYSTEM_MESSAGE,
            temperature=self.temperature,
            savedir=self.savedir
        )

    """def generate_notebook():
        pass

    def generate_report():
        pass"""
    def recommend_questions(
        self,
        n_questions=3,
        insights_history=None,
        prompt_method=None,
        question_type=None,
    ):
        """
        Suggest Next Best Questions
        """
        if self.verbose:
            print(f"Generating {n_questions} Questions using {self.model_name}...")

        if insights_history is None:

            # Generate Root Questions
            questions = au.get_questions(
                base_url=self.base_url,
                prompt_method=prompt_method,
                context=self.context,
                goal=self.goal,
                messages=[],
                schema=self.schema,
                user_schema=self.user_schema,
                max_questions=n_questions,
                model_name=self.model_name,
                temperature=self.temperature,
                savedir=self.savedir
            )
        else:
            # Generate Follow Up Questions
            last_insight = insights_history[-1]
            questions = au.get_follow_up_questions(
                base_url=self.base_url,
                context=self.context,
                goal=self.goal,
                question=last_insight["question"],
                answer=last_insight["answer"],
                schema=self.schema,
                user_schema=self.user_schema,
                max_questions=n_questions,
                model_name=self.model_name,
                prompt_method=prompt_method,
                question_type=question_type,
                temperature=self.temperature,
                savedir=self.savedir

            )
            if self.verbose:
                print(
                    "\nFollowing up on the last insight:\n---------------------------------"
                )
                print(f"Question: {last_insight['question']}\n")
                print(f"Answer: {last_insight['answer']}\n")

        if self.verbose:
            print("\nNext Best Questions:\n-------------------")
            for idx, question in enumerate(questions):
                print(f"{idx+1}. {question}")
            print()

        return questions

    def answer_question(
        self,
        question,
        n_retries=2,
        return_insight_dict=True,
        prompt_code_method="single",
        prompt_interpret_method="interpret",
        parent_question_id=None,
    ):
        n_retries = self.n_retries
        if self.verbose:
            print(f"Generating Code...")
        # Prompt 3: Generate Code
        code_output_folder = os.path.join(
            self.savedir, f"question_{str(len(self.insights_history))}"
        )

        #获取数据存放路径
        sta_output_folder =code_output_folder

        if self.verbose:
            print(f"Interpreting Solution...")
            print(f"Results saved at: {self.savedir}")

        # with au.SuppressOutput():
        solution = au.generate_code(
            base_url=self.base_url,
            schema=self.schema,
            user_schema=self.user_schema,
            goal=self.goal,
            question=question,
            database_path=os.path.abspath(self.dataset_csv_path),
            user_database_path=(
                os.path.abspath(self.user_dataset_csv_path)
                if self.user_dataset_csv_path is not None
                else None
            ),
            output_folder=code_output_folder,
            model_name=self.model_name,
            n_retries=n_retries,
            prompt_method=prompt_code_method,
            temperature=self.temperature,
            savedir=self.savedir
        )

        #prompt 3.5: Reger Insight recognize
        reconization_dict = au.recognize_insight(
            sta_json_folder=sta_output_folder
        )
        print("au.recognize_insight")
        try:
            answer = reconization_dict["text"]
            sta_score = int(reconization_dict["score"])
            print(f"Success to reconize insght")
        except Exception as e:
            print(f"Failed to reconize insght: {e}")
            answer = "Unable to recognize the insight"
            sta_score = 0


        # 3.8 识别出洞察
        if sta_score:
            if self.verbose:
                print("\nSolution\n---------")
                print(f"Question: {question}\n")
                print(f"Answer: {answer}\n")
                # 3.9 润色
                insight = au.polish_insight(
                    base_url=self.base_url,
                    solution=solution,
                    model_name=self.model_name,
                    temperature=self.temperature,
                    savedir=self.savedir,
                    answer=answer
                )
            # 未识别出洞察
        else:
            # Prompt 4: LLM Interpret Insight
            interpretation_dict = au.interpret_insight(
                base_url=self.base_url,
                solution=solution,
                model_name=self.model_name,
                schema=self.schema,
                n_retries=n_retries,
                prompt_method=prompt_interpret_method,
                temperature=self.temperature,
                savedir=self.savedir
            )

            print("au.interpret_insight")
            try:
                insight= interpretation_dict["interpretation"]["insight"]

            except Exception as e:
                insight='Unable to retrieve the insight'

            try:
                answer = interpretation_dict["interpretation"]["answer"]
            except Exception as e:
                print(f"Failed to retrieve answer: {e}")
                answer = "Unable to retrieve the answer"

        insight_score=0
        # 4.2 计算洞察得分
        insight_score = au.dynamic_pruning(
            base_url=self.base_url,
            goal=self.goal,
            question=solution["question"],
            model_name=self.model_name,
            temperature=self.temperature,
            sta_score=sta_score,
            savedir=self.savedir,
            insight=insight
        )
        print("au.dynamic_pruning")


        #4.5 Save into the savedir
        question_id = f"question_{len(self.insights_history)}"
        try:
            insight_dict = {
                "question_id": question_id,
                "parent_question_id": parent_question_id,
                "question": question,
                "answer": answer,
                "insight": insight,
                "insight_score": insight_score,
                "output_folder": code_output_folder,
            }
        except Exception as e:
            print(f"Unable to store the insight_dict: {e}")
            insight_dict = {
                "question_id": question_id,
                "parent_question_id": parent_question_id,
                "question": question,
                "answer": answer,
                "insight": 'Unable to retrieve the insight',
                "insight_score": insight_score,
                "output_folder": code_output_folder,
            }


        # Save into the savedir
        with open(os.path.join(code_output_folder, "insight.json"), "w") as json_file:
            json.dump(insight_dict, json_file, indent=4, sort_keys=True)

        # add to insights
        self.insights_history += [insight_dict]
        self.save_tree_state_dict(os.path.join(self.savedir, "insights_tree.json"))

        insight_dict = copy.deepcopy(insight_dict)
        insight_dict.update(self.get_insight_objects(insight_dict))

        if return_insight_dict:
            return answer, insight_dict

        return answer["answer"]

    import os, json, logging
    from PIL import Image

    def get_insight_objects(self, insight_dict):
        folder = insight_dict["output_folder"]

        # plot.jpg
        try:
            path = os.path.join(folder, "plot.jpg")
            if os.path.exists(path):
                plot = Image.open(path)
            else:
                plot = None
        except Exception as e:
            logging.exception(f"加载 plot.jpg 失败: {e}")
            plot = None

        # stat.json
        try:
            path = os.path.join(folder, "stat.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    stat = json.load(f)
            else:
                stat = None
        except Exception as e:
            logging.exception(f"加载 stat.json 失败: {e}")
            stat = None

        # code.py
        try:
            path = os.path.join(folder, "code.py")
            if os.path.exists(path):
                with open(path, "r") as f:
                    code = f.read()
            else:
                code = None
        except Exception as e:
            logging.exception(f"加载 code.py 失败: {e}")
            code = None

        return {
            "plot": plot,
            "stat": stat,
            "code": code,
        }

    def get_insight_objects_old(self, insight_dict):
        """
        Get Insight Objects
        """
        if os.path.exists(os.path.join(insight_dict["output_folder"], "plot.jpg")):
            # get plot.jpg
            plot = Image.open(os.path.join(insight_dict["output_folder"], "plot.jpg"))
        else:
            plot = None

        if os.path.exists(os.path.join(insight_dict["output_folder"], "stat.json")):
            try:
                # get stat.json
                stat = json.load(
                    open(os.path.join(insight_dict["output_folder"], "stat.json"), "r")
                )
            except:
                stat = None
        else:
            stat = None

        # get code.py
        if os.path.exists(os.path.join(insight_dict["output_folder"], "code.py")):
            code = open(
                os.path.join(insight_dict["output_folder"], "code.py"), "r"
            ).read()
        else:
            code = None

        insight_object = {
            "plot": plot,
            "stat": stat,
            "code": code,
        }
        return insight_object

    def _build_tree_node(self, question_id, children_map):
        node = {"question_id": question_id}
        children = children_map.get(question_id, [])
        if children:
            node["children"] = [self._build_tree_node(child, children_map) for child in children]
        return node

    def save_tree_state_dict(self, fname):
        children_map = {}
        roots = []
        for item in self.insights_history:
            question_id = item.get("question_id")
            parent_question_id = item.get("parent_question_id")
            if question_id is None:
                continue
            if parent_question_id is None:
                roots.append(question_id)
            else:
                children_map.setdefault(parent_question_id, []).append(question_id)
        tree = [self._build_tree_node(root, children_map) for root in roots]
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=4)

    def save_state_dict(self, fname):
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(self.insights_history, f, ensure_ascii=False, indent=4)

    def load_state_dict(self, fname):
        with open(fname, "r", encoding="utf-8") as f:
            self.insights_history = json.load(f)
