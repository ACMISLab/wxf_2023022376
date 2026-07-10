# Text2Vis

Text2Vis is a benchmark dataset for evaluating large language models on generating multimodal visualizations from text. It covers answer correctness, chart quality, and structured-data reasoning, making it useful for both model development and evaluation.

## Dataset Access

You can download the dataset from:

- [Hugging Face Dataset](https://huggingface.co/datasets/mizanurr/Text2Vis)
- [Google Drive Download](https://drive.google.com/drive/folders/1sA4ynL26i1ex8C-spcIVSlBpSZXcGjO6?usp=sharing)

## Paper

- [ArXiv Version](https://arxiv.org/abs/2507.19969)

## Quick Start

This repository includes evaluation scripts for two different model backends:

- `InternVL`
- `GPT-4o`

Both scripts follow the same general workflow:

1. Read the input Excel file
2. Generate charts from the `Generated Code` column
3. Evaluate the generated answer and chart quality
4. Save the scored results to an output Excel file

## Using InternVL for Evaluation

To evaluate with InternVL, first configure the required model information in `eval_predictions_intrenvl.py`.

After that, set the input and output paths, then run the script to start evaluation.

Example:

```bash
python eval_predictions_intrenvl.py --input your_input.xlsx --output your_output.xlsx --chart_dir your_chart_dir
```

### What you need to prepare

- An input Excel file containing the required fields, such as `ID`, `Question`, `Answer`, `Generated Answer`, `Generated Code`, and `Table Data`
- A writable folder for chart outputs
- Valid InternVL access information in `eval_predictions_intrenvl.py`

## Using GPT-4o for Evaluation

To evaluate with GPT-4o, first configure the required model information in `eval_predictions_gpt_4o.py`.

After that, set the input and output paths, then run the script to start evaluation.

Example:

```bash
python eval_predictions_gpt_4o.py --input your_input.xlsx --output your_output.xlsx --chart_dir your_chart_dir
```

### What you need to prepare

- An input Excel file containing the required fields, such as `ID`, `Question`, `Answer`, `Generated Answer`, `Generated Code`, and `Table Data`
- A writable folder for chart outputs
- Valid GPT-4o access information in `eval_predictions_gpt_4o.py`

## Output

The evaluation script will save an Excel file with scoring columns such as:

- `Answer Match`
- `Readability and Quality Score`
- `Chart Correctness Score`
- `Final Score`

It will also store generated chart images in the specified chart directory.

## Notes

- If chart execution fails, the corresponding sample will be marked as failed.
- Make sure your API configuration and network access are correct before running the scripts.
- The output Excel file is updated during evaluation so you can track progress.

## Contact

If you have any questions about this project, please contact the authors of Text2Vis.

## Citation

If you use Text2Vis in your research, please cite:

```bibtex
@misc{rahman2025text2vischallengingdiversebenchmark,
      title={Text2Vis: A Challenging and Diverse Benchmark for Generating Multimodal Visualizations from Text},
      author={Mizanur Rahman and Md Tahmid Rahman Laskar and Shafiq Joty and Enamul Hoque},
      year={2025},
      eprint={2507.19969},
      archivePrefix={arXiv},
      primaryClass={cs.CL},
      url={https://arxiv.org/abs/2507.19969},
}
```
