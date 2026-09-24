# Analysis Scripts

This directory contains all Python scripts used for analyzing evaluation results.

## Script List

### Core Evaluation Scripts

1. **evaluate_interaction.py** - Interaction success rate evaluation script
   - Evaluates model tool calls and result correctness for retail, kitchen,
     restaurant (including `restaurant6`), warehouse, and household scenarios
   - `restaurant6` is variant 6 of the `restaurant` scenario; it is aggregated
     together with `restaurant1` through `restaurant5`
   - Household evaluation supports `household1` through `household18`
   - Per-file details are still emitted for partial runs, but incomplete result
     files are excluded from aggregate accuracy and downstream charts
   - Use `--include_partial` to aggregate every valid trajectory that actually
     exists in `results/`, while retaining per-file completeness and overall
     trajectory coverage metadata in `summary.json`
   - Reports only overall performance metrics; it no longer computes separate
     metrics for successful/failed samples or a filtered "normal user" subset
   - Keeps the averages of the four raw simulated-user metrics: role consistency,
     instruction following, resilience, and contextual robustness
   - Usage: `python evaluate_interaction.py --model_name <model_name>`
   - Example: `python evaluate_interaction.py --model_name kimi-k2.6`

2. **print_eval.py** - Evaluation result printing script
   - Prints detailed evaluation results and statistics

### Analysis Scripts

3. **analyze_error_reasons.py** - Error analysis script
   - Analyzes error types and distributions across models
   - Counts tool call errors, execution errors, etc.

4. **analyze_restaurant6.py** - Restaurant 6 selection analysis
   - Analyzes whether each model selected the correct restaurant in the multi-restaurant variant

5. **calc_user_perf.py** - User performance metrics calculation script
   - Prints the four simulated-user averages already saved in each model's
     evaluation summary, without recomputing original/final variants

6. **count_stats.py** - Statistics script
   - Counts tool numbers, item numbers, scenario files, etc.

### Visualization Scripts

7. **plot_results.py** - Result visualization script
   - Generates academic-style statistical charts
   - Outputs bar charts, donut charts, scatter plots, LaTeX tables, etc.

## Path Configuration

All scripts are configured to run from the `analysis_scripts` directory, with relative paths set to:
- `../results` - Evaluation result directory
- `../eval_result` - Evaluation output directory
- `../scenarios` - Scenario file directory
- `../tools` - Tool directory

## Usage

Run scripts from the `analysis_scripts` directory or the project root:

```bash
# From project root
cd /ossfs/workspace/process_data
python analysis_scripts/evaluate_interaction.py --model_name glm-4.5v

# Or from the analysis_scripts directory
cd /ossfs/workspace/process_data/analysis_scripts
python evaluate_interaction.py --model_name glm-4.5v
```

## Dependencies

Ensure the following dependencies are installed:
- pandas
- numpy
- matplotlib
- Pillow
- adjustText
- argparse (Python standard library)

Ground-truth files and result files use the same naming convention:
`{scenario}{number}.json` under `scenarios/final/` and
`{scenario}{number}_{easy|hard|static}.json` under `results/{model}/`.
For example, `warehouse1.json`, `household1.json`, and `restaurant6.json`.
