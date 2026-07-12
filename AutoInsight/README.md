# AutoInsight

AutoInsight 用于读取数据集配置并调用大语言模型，自动生成数据洞察与汇总结果。

## 1. 安装依赖

建议使用 Python 3.9 及以上版本，并在虚拟环境中安装依赖。

```bash
python -m venv .venv
```

激活虚拟环境：

Windows：

```bash
.venv\Scripts\activate
```

Linux / macOS：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 2. 配置模型参数与输出路径

可在 `main.py` 的程序入口中配置以下参数：

- `savedir_base`：结果输出根目录，默认为 `results`。
- `datadir`：数据集配置目录，默认为 `data/notebooks`。
- `openai_api_key`：模型服务 API Key。
- `model_name`：模型名称，默认为 `Qwen2.5-72B-Instruct`。
- `base_url`：OpenAI 兼容模型服务地址。
- `max_questions`：最大问题数量，在 `exp_dict` 中配置。
- `branch_depth`：分析分支深度，在 `exp_dict` 中配置。
- `reset`：是否在运行前删除已有实验结果；`1` 表示重置，`0` 表示保留。

也可以通过命令行参数覆盖默认配置：

```bash
python main.py --model_name Qwen2.5-72B-Instruct --base_url http://127.0.0.1:8000/v1 --openai_api_key your-api-key --datadir data/notebooks --savedir_base results --reset 0
```

结果将保存到：

```text
<savedir_base>/<model_name>/
```

使用默认配置时，输出目录为 `results/Qwen2.5-72B-Instruct/`。

## 3. 启动

确认模型服务已启动、模型参数和数据路径配置正确后，执行：

```bash
python main.py
```

程序会处理 `datadir` 下的 JSON 数据集配置，并在输出目录中保存：

- `exp_dict.json`：本次实验配置。
- `summary.json`：各数据集的洞察摘要及运行耗时。
- 数据集同名子目录：对应数据集的详细分析结果。

运行完成后，终端将输出 `Experiment Done!`。

## 4. 消融说明

进行消融实验前，建议备份相关文件或使用独立的 Git 分支。以下行号基于当前版本代码；如果代码发生改动，请以对应代码逻辑为准。每组实验完成后，应恢复代码再进行下一组实验，第三组实验除外，因为它需要在第二组实验的基础上继续修改。

### 4.1 摘要模块消融

在 `autoinsight/utils/agent_utils.py` 中，将原有的 `get_scheam` 函数替换为 `get_schaem_a` 函数，然后按照正常方式启动程序：

```bash
python main.py
```

该实验用于评估摘要模块对整体效果的影响。

### 4.2 剪枝模块消融

在 `autoinsight/agents.py` 中进行以下修改：

1. 注释第 103 行代码。
2. 注释第 435—444 行代码。
3. 保存修改后启动程序。

```bash
python main.py
```

该实验用于评估剪枝模块对整体效果的影响。

### 4.3 洞察识别管道消融

本实验需要在“剪枝模块消融”的代码基础上继续修改 `autoinsight/agents.py`：

1. 保留第二组实验中对第 103 行和第 435—444 行代码的注释。
2. 继续注释第 376—388 行代码。
3. 将对应逻辑中的 `sta_score` 设置为 `0`，即 `sta_score = 0`。
4. 保存修改后启动程序。

```bash
python main.py
```

该实验用于评估洞察识别管道对整体效果的影响。

> 注意：不同消融实验应使用不同的输出目录，或在启动时设置 `--reset 1`，避免已有结果影响实验结果。建议在每次实验时通过 `--savedir_base` 指定独立目录，例如 `results/ablation_summary`、`results/ablation_pruning` 和 `results/ablation_insight_pipeline`。
