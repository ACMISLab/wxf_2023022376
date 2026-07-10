# MAC_VG

This project is used for table question answering and visualization generation. `main.py` is for batch evaluation, and `test.py` is for testing a single case.

## 1. Install dependencies

First, install the dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## 2. Configure the model

The model interfaces are configured in the `model/` directory:

- `model/llm.py`: text model interface
- `model/mllm.py`: multimodal model interface

If you need to switch models, update the following parameters in the corresponding files:

- `base_url`
- `model`
- `api_key`

For example:

- In `model/llm.py`, update `base_url` and `model`
- In `model/mllm.py`, update `api_key`, `base_url`, and `model`

## 3. Start the project

### Batch testing

Use `main.py` for batch testing. By default, it reads `data/Text2Vis.xlsx` and writes results to `results/result.xlsx`.

```bash
python main.py
```

You can also specify the input and output files manually:

```bash
python main.py --input data/Text2Vis.xlsx --output results/result.xlsx
```

### Single-case testing

Use `test.py` to test a single case.

```bash
python test.py
```

You can edit `question` and `data` directly in `test.py` to test your own example.

## Directory structure

- `ae_agent/`: answer evaluation code
- `ana_agent/`: analysis and visualization generation code
- `vo_agent/`: visualization optimization code
- `model/`: model calling wrappers
- `data/`: test data
- `results/`: output files

## Notes

- Make sure the model service endpoint is reachable before running.
- If the output file already exists, `main.py` will try to resume from the existing results.
- `test.py` is useful for quickly verifying a single sample workflow.