import os, argparse,json
import pandas as pd
from autoinsight import agents
from autoinsight.utils import exp_utils as eu
from autoinsight.utils.exp_utils import hash_dict, save_json
import time


def get_benchmark(dataset_type, datadir):
    json_files = []
    for root, _, files in os.walk(datadir):
        for file in files:
            if file.endswith(".json"):
                relative_path = os.path.relpath(os.path.join(root, file), datadir)
                json_files.append(relative_path)
    return [f"{datadir}/{flag}" for flag in json_files]


def load_dataset_dict(dataset_json_path):
    # load json
    with open(dataset_json_path, "r",encoding="utf-8") as f:
        return json.load(f)


def main(exp_dict, savedir, args):
    import json
    # Hyperparameters:
    # ----------------

    # Print Exp dict as hyperparamters and savedir
    print("\nExperiment Dict:")
    eu.print(exp_dict)
    print(f"\nSavedir: {savedir}\n")

    # Reset savedir if reset flag is set
    if args.reset and os.path.exists(savedir):
        assert os.path.exists(os.path.join(savedir, "exp_dict.json"))
        os.system(f"rm -rf {savedir}")

    # Save experiment config at root
    #os.makedirs(savedir, exist_ok=True)
    save_json(os.path.join(savedir, "exp_dict.json"), exp_dict)

    # time_summary_list.json 的路径
    summary_file = os.path.join(savedir, "summary.json")

    # 如果文件已存在，则加载已有列表；否则初始化为空列表
    if os.path.exists(summary_file):
        with open(summary_file, 'r', encoding='utf-8') as f:
            data_list = json.load(f)
    else:
        data_list = []

    # Get Benchmark:
    dataset_list = get_benchmark(
        exp_dict["benchmark_type"], datadir=args.datadir
    )

    for dataset_json_path in dataset_list:

        start_time = time.time()

        # Create a subdirectory for this dataset
        ds_name = os.path.splitext(os.path.basename(dataset_json_path))[0]
        ds_savedir = os.path.join(savedir, ds_name)
        os.makedirs(ds_savedir, exist_ok=True)

        # Load Dataset
        dataset_dict = load_dataset_dict(dataset_json_path=dataset_json_path)

        # load agent
        agent = agents.Agent(
            model_name=exp_dict["model_name"],
            max_questions=exp_dict["max_questions"],
            branch_depth=exp_dict["branch_depth"],
            n_retries=3,
            savedir=ds_savedir,
            base_url=exp_dict['base_url'],
            goal = dataset_dict['metadata']['goal']
        )

        # Predict Insights
        pred_questions, pred_insights, pred_summary = agent.get_insights(
            dataset_csv_path=dataset_dict["dataset_csv_path"],
        )

        elapsed_time = time.time() - start_time

        data_list.append(
            {
                "data_path": dataset_json_path,
                "summary": pred_summary,
                "times": elapsed_time
            }
        )

        print(pd.DataFrame(data_list).tail())
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, ensure_ascii=False, indent=2)
        # save score_list

    print("Experiment Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-sb", "--savedir_base", type=str, default="results")

    #reset 参数的作用是 在实验开始前重置（删除）对应的保存目录 (savedir)，确保实验从头开始运行，而不会受到已有结果的影响
    parser.add_argument("-r", "--reset", type=int, default=0)
    parser.add_argument("-d", "--datadir", type=str, default="data/notebooks")
    parser.add_argument("-o", "--openai_api_key", type=str, default="api-key")
    parser.add_argument("-m", "--model_name", type=str, default="Qwen2.5-72B-Instruct") #本地部署
    parser.add_argument("-b", "--base_url", type=str, default='model_name')
    args, unknown = parser.parse_known_args()

    # exp_list
    exp_list = []
    exp_list.append(
        {
            "benchmark_type": "ours",
            "model_name": args.model_name,
            "max_questions": 3,
            "branch_depth": 3,
            "base_url": args.base_url
        }
    )
    print(args.model_name)
    # set open ai env
    for exp_dict in exp_list:
        hash_id = hash_dict(exp_dict)
        savedir = os.path.join(args.savedir_base, args.model_name)  # 确保 number 转为字符串
        main(exp_dict, savedir, args)