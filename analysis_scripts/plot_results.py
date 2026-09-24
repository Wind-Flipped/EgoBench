# -*- coding: utf-8 -*-
"""
Plot evaluation result charts
1. Joint success rate by difficulty (LaTeX table)
2. Joint success rate by scenario (model-grouped and scenario-grouped bar charts)
3. Error reason pie charts (by model and by scenario)
4. Average tokens per trajectory vs joint success rate
5. Average conversation rounds per trajectory vs joint success rate
6. Average tool calls per trajectory vs joint success rate
"""

import os
import re
import json
import math
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from adjustText import adjust_text


# =========================
# Path Configuration
# =========================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)

EVAL_RESULT_DIR = os.path.join(PROJECT_ROOT, "eval_result")
LOGO_DIR = os.path.join(CURRENT_DIR, "logo")
ERROR_ANALYSIS_DIR = os.path.join(PROJECT_ROOT, "error_analysis")
FIGURES_DIR = os.path.join(EVAL_RESULT_DIR, "figures")

os.makedirs(FIGURES_DIR, exist_ok=True)


def save_figure_pair(png_path, *, dpi=200, bbox_inches="tight"):
    """Save the current Matplotlib figure as both PNG and vector PDF."""
    stem, extension = os.path.splitext(png_path)
    if extension.lower() != ".png":
        raise ValueError(f"Expected a .png output path, got: {png_path}")
    plt.savefig(png_path, dpi=dpi, bbox_inches=bbox_inches)
    plt.savefig(f"{stem}.pdf", bbox_inches=bbox_inches)

# =========================
# Global Plot Configuration
# =========================
plt.rcParams["font.sans-serif"] = [
    "SimHei", "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 18

# =========================
# Model Configuration
# =========================
MODEL_NAMES = {
    "glm-5v-turbo": "GLM-5V-Turbo",
    "qwen3-vl-235b": "Qwen3-VL-235B",
    "qwen3.6-plus": "Qwen3.6-Plus",
    "Qwen3.5-397B-A17B": "Qwen3.5-397B-A17B",
    "gemini-3.1-pro-preview": "Gemini-3.1-Pro",
    "kimi-k2.6": "Kimi-K2.6",
    "mimo-v2.5-omni": "MiMo-V2.5-Omni",
    "doubao-seed-2-0-pro-260215": "Doubao-seed-2-0-pro"
}

LOGO_FILES = {
    "glm-5v-turbo": "chatglm-color.png",
    "qwen3-vl-235b": "qwen-color.png",
    "qwen3.6-plus": "qwen-color.png",
    "Qwen3.5-397B-A17B": "qwen-color.png",
    "gemini-3.1-pro-preview": "gemini-color.png",
    "kimi-k2.6": "kimi.png",
    "mimo-v2.5-omni": "xiaomimimo.png",
    "doubao-seed-2-0-pro-260215": "doubao-color.png"
}

MODEL_COLORS = {
    "glm-5v-turbo": "#E63946",
    "qwen3-vl-235b": "#457B9D",
    "qwen3.6-plus": "#2A9D8F",
    "Qwen3.5-397B-A17B": "#E9C46A",
    "gemini-3.1-pro-preview": "#9B59B6",
    "kimi-k2.6": "#3498DB",
    "mimo-v2.5-omni": "#FF6FA5",
    "doubao-seed-2-0-pro-260215": "#1ABC9C"
}

LIGHT_COLORS = {
    "glm-5v-turbo": "#F5A5A8",
    "qwen3-vl-235b": "#8CBFD6",
    "qwen3.6-plus": "#72D4CC",
    "Qwen3.5-397B-A17B": "#F5DFA8",
    "gemini-3.1-pro-preview": "#C9A3D4",
    "kimi-k2.6": "#8DC6E8",
    "mimo-v2.5-omni": "#F5A593",
    "doubao-seed-2-0-pro-260215": "#6ED9CB"
}

MODEL_ORDER = list(MODEL_NAMES.keys())

SCENARIOS = ["retail", "restaurant", "kitchen", "warehouse", "household"]
DIFFICULTIES = ["easy", "hard", "static"]


# =========================
# Utility Functions
# =========================
def safe_read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to read JSON: {path}, error={e}")
        return None


def list_model_dirs():
    """List model directories under eval_result that contain summary.json"""
    models = []
    if not os.path.exists(EVAL_RESULT_DIR):
        return models

    for name in os.listdir(EVAL_RESULT_DIR):
        model_dir = os.path.join(EVAL_RESULT_DIR, name)
        if os.path.isdir(model_dir) and os.path.exists(os.path.join(model_dir, "summary.json")):
            models.append(name)

    # Keep only models defined in MODEL_NAMES, sorted by predefined order, extras at the end
    models = [m for m in models if m in MODEL_NAMES]
    ordered = [m for m in MODEL_ORDER if m in models]
    extras = [m for m in models if m not in ordered]
    return ordered + sorted(extras)


def get_model_summary(model_dir):
    path = os.path.join(EVAL_RESULT_DIR, model_dir, "summary.json")
    return safe_read_json(path)


def get_model_eval_files(model_dir):
    model_path = os.path.join(EVAL_RESULT_DIR, model_dir)
    if not os.path.exists(model_path):
        return []
    files = []
    for fn in os.listdir(model_path):
        if fn.endswith("_eval.json"):
            files.append(os.path.join(model_path, fn))
    return sorted(files)


def mean_or_zero(values):
    values = [v for v in values if v is not None]
    return float(np.mean(values)) if values else 0.0


def normalize_rate(x):
    """
    Some fields may be 0~1 or already 0~100.
    Normalize to percentage values.
    """
    if x is None:
        return 0.0
    try:
        x = float(x)
    except Exception:
        return 0.0

    if x <= 1.0:
        return x * 100
    return x


def is_complete_summary_item(item):
    """Exclude partial result files from every chart-level accuracy aggregate."""
    if item.get("error"):
        return False
    if "included_in_summary" in item:
        return bool(item["included_in_summary"])
    total = item.get("total_scenarios", 0)
    valid = item.get("valid_scenarios", 0)
    return total > 0 and valid == total


def load_logo_image(model, zoom=0.12):
    logo_file = LOGO_FILES.get(model)
    if not logo_file:
        return None
    logo_path = os.path.join(LOGO_DIR, logo_file)
    if not os.path.exists(logo_path):
        return None
    try:
        img = Image.open(logo_path).convert("RGBA")
        return OffsetImage(img, zoom=zoom)
    except Exception as e:
        print(f"[WARN] Failed to load logo: model={model}, error={e}")
        return None


# =========================
# Metric Extraction
# =========================
def get_four_rates_by_difficulty(summary, model=None):
    """
    Extract four metrics by difficulty: micro_accuracy, tool_based_success_rate, result_based_success_rate, joint_success_rate
    Weighted average using valid_scenarios. Incomplete files are excluded first,
    so valid_scenarios equals the selected ground-truth task count.
    Returns: {difficulty: {"micro": x, "tool": x, "result": x, "joint": x}}

    The mode labels come directly from the evaluated result filenames; no
    model-specific reordering is applied.
    """
    result = {d: {"micro": 0.0, "tool": 0.0, "result": 0.0, "joint": 0.0} for d in DIFFICULTIES}
    if not summary:
        return result

    all_results = summary.get("all_results", [])
    # Collect (rate, weight) pairs from complete files only.
    buckets = {d: {"micro": [], "tool": [], "result": [], "joint": [], "weights": []} for d in DIFFICULTIES}

    for item in all_results:
        if not is_complete_summary_item(item):
            continue
        mode = item.get("mode")
        if mode in DIFFICULTIES:
            weight = item.get("valid_scenarios", 0)
            buckets[mode]["weights"].append(weight)
            buckets[mode]["micro"].append(normalize_rate(item.get("micro_accuracy", 0)))
            buckets[mode]["tool"].append(normalize_rate(item.get("tool_based_success_rate", 0)))
            buckets[mode]["result"].append(normalize_rate(item.get("result_based_success_rate", 0)))
            buckets[mode]["joint"].append(normalize_rate(item.get("joint_success_rate", 0)))

    for d in DIFFICULTIES:
        total_weight = sum(buckets[d]["weights"])
        if total_weight > 0:
            for key in ["micro", "tool", "result", "joint"]:
                result[d][key] = sum(r * w for r, w in zip(buckets[d][key], buckets[d]["weights"])) / total_weight
        else:
            for key in ["micro", "tool", "result", "joint"]:
                result[d][key] = mean_or_zero(buckets[d][key])

    return result


def get_joint_success_rate_by_difficulty(summary, model=None):
    result = {d: 0.0 for d in DIFFICULTIES}
    if not summary:
        return result

    rates = get_four_rates_by_difficulty(summary, model=model)
    for d in DIFFICULTIES:
        result[d] = rates[d]["joint"]
    return result


def get_joint_success_rate_by_scenario(summary):
    result = {s: 0.0 for s in SCENARIOS}
    if not summary:
        return result

    all_results = summary.get("all_results", [])
    # Collect (rate, weight) pairs from complete files only.
    bucket = defaultdict(list)

    for item in all_results:
        if not is_complete_summary_item(item):
            continue
        scenario = item.get("scenario")
        if scenario in SCENARIOS:
            rate = normalize_rate(item.get("joint_success_rate", 0))
            weight = item.get("valid_scenarios", 0)
            bucket[scenario].append((rate, weight))

    for s in SCENARIOS:
        if bucket[s]:
            total_weight = sum(w for _, w in bucket[s])
            if total_weight > 0:
                result[s] = sum(r * w for r, w in bucket[s]) / total_weight
            else:
                result[s] = mean_or_zero([r for r, _ in bucket[s]])
    return result


def get_overall_joint_success_rate(summary):
    if not summary:
        return 0.0
    complete_items = [
        item for item in summary.get("all_results", [])
        if is_complete_summary_item(item)
    ]
    total = sum(item.get("valid_scenarios", 0) for item in complete_items)
    if total <= 0:
        return 0.0
    return sum(
        normalize_rate(item.get("joint_success_rate", 0))
        * item.get("valid_scenarios", 0)
        for item in complete_items
    ) / total


def get_metrics_from_summary(summary):
    """
    Extract metrics from summary.json summary field
    Returns: avg_tokens, avg_input_tokens, avg_output_tokens, avg_rounds, avg_tool_calls
    """
    if not summary:
        return {"avg_tokens": 0.0, "avg_input_tokens": 0.0, "avg_output_tokens": 0.0, "avg_rounds": 0.0, "avg_tool_calls": 0.0}

    complete_items = [
        item for item in summary.get("all_results", [])
        if is_complete_summary_item(item)
    ]
    if summary.get("all_results"):
        total = sum(item.get("valid_scenarios", 0) for item in complete_items)
        if total <= 0:
            return {"avg_tokens": 0.0, "avg_input_tokens": 0.0, "avg_output_tokens": 0.0, "avg_rounds": 0.0, "avg_tool_calls": 0.0}

        def weighted(key):
            return sum(
                (item.get(key, 0) or 0) * item.get("valid_scenarios", 0)
                for item in complete_items
            ) / total

        avg_input_tokens = weighted("avg_input_tokens")
        avg_output_tokens = weighted("avg_output_tokens")
        return {
            "avg_tokens": float(avg_input_tokens + avg_output_tokens),
            "avg_input_tokens": float(avg_input_tokens),
            "avg_output_tokens": float(avg_output_tokens),
            "avg_rounds": float(weighted("avg_rounds_count")),
            "avg_tool_calls": float(weighted("avg_tool_calls_count")),
        }

    s = summary.get("summary", {})

    # Token consumption = input + output
    avg_input_tokens = s.get("avg_input_tokens", 0) or 0
    avg_output_tokens = s.get("avg_output_tokens", 0) or 0
    avg_tokens = avg_input_tokens + avg_output_tokens

    # Conversation rounds
    avg_rounds = s.get("avg_rounds_count", 0) or 0

    # Tool call count
    avg_tool_calls = s.get("avg_tool_calls_count", 0) or 0

    return {
        "avg_tokens": float(avg_tokens),
        "avg_input_tokens": float(avg_input_tokens),
        "avg_output_tokens": float(avg_output_tokens),
        "avg_rounds": float(avg_rounds),
        "avg_tool_calls": float(avg_tool_calls)
    }


# =========================
# Axis Model Logo Labels
# =========================
def add_model_logos_below_axis(ax, models, y_offset_axes=-0.16, zoom=0.065, fontsize=10):
    """
    Add logo + model name below x-axis
    Use coordinate transform for stable layout
    """
    xticks = ax.get_xticks()
    if len(xticks) < len(models):
        return

    for i, model in enumerate(models):
        x = xticks[i]

        # logo
        img = load_logo_image(model, zoom=zoom)
        if img is not None:
            ab = AnnotationBbox(
                img,
                (x, y_offset_axes + 0.035),
                xycoords=ax.get_xaxis_transform(),
                frameon=False,
                box_alignment=(0.5, 0.5),
                pad=0
            )
            ax.add_artist(ab)

        # text
        ax.text(
            x, y_offset_axes - 0.02,
            MODEL_NAMES.get(model, model),
            transform=ax.get_xaxis_transform(),
            ha="center", va="top",
            fontsize=fontsize, fontweight="bold"
        )

    ax.set_xticklabels([])
    plt.subplots_adjust(bottom=0.30)


# =========================
# Chart 1: LaTeX Table by Difficulty
# =========================
def _find_best_and_second(values):
    """Return (best_idx, second_idx), best is max value index, second is second-max value index"""
    if not values:
        return None, None
    sorted_indices = sorted(range(len(values)), key=lambda i: values[i], reverse=True)
    best = sorted_indices[0] if len(sorted_indices) > 0 else None
    second = sorted_indices[1] if len(sorted_indices) > 1 else None
    return best, second


def _fmt_val(val, is_best, is_second):
    s = f"{val:.2f}"
    if is_best:
        return f"\\textbf{{{s}}}"
    if is_second:
        return f"\\underline{{{s}}}"
    return s


def plot_chart1_joint_success_by_difficulty(models):
    print("Generating Table 1: Four accuracy metrics by difficulty (LaTeX)")

    # Collect four metrics per model per difficulty
    model_data = {}
    for model in models:
        summary = get_model_summary(model)
        model_data[model] = get_four_rates_by_difficulty(summary, model=model)

    metrics = ["micro", "tool", "result", "joint"]
    metric_labels = ["Micro", "Tool", "Result", "Joint"]

    # Pre-compute best / second best per column
    col_best = {}   # (difficulty, metric) -> best_model_idx
    col_second = {}
    for d in DIFFICULTIES:
        for m in metrics:
            vals = [model_data[model][d][m] for model in models]
            best, second = _find_best_and_second(vals)
            col_best[(d, m)] = best
            col_second[(d, m)] = second

    # Build LaTeX
    lines = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"% \caption{Performance by Difficulty on EgoBench.}")
    lines.append(r"\label{tab:difficulty_results}")
    lines.append(r"\large")
    lines.append(r"\setlength{\tabcolsep}{4pt}")
    lines.append(r"\begin{tabular}{clcccccccccccc}")
    lines.append(r"\toprule")
    lines.append(r" & & \multicolumn{4}{c}{\textbf{Easy}} & \multicolumn{4}{c}{\textbf{Hard}} & \multicolumn{4}{c}{\textbf{Static}} \\")
    lines.append(r"\cmidrule(lr){3-6}\cmidrule(lr){7-10}\cmidrule(lr){11-14}")
    lines.append(r" & \textbf{Model} & \textbf{Micro} & \textbf{Tool} & \textbf{Result} & \textbf{Joint} & \textbf{Micro} & \textbf{Tool} & \textbf{Result} & \textbf{Joint} & \textbf{Micro} & \textbf{Tool} & \textbf{Result} & \textbf{Joint} \\")
    lines.append(r"\midrule")

    for i, model in enumerate(models):
        logo_file = LOGO_FILES.get(model, "")
        logo_name = logo_file.replace(".png", "") if logo_file else ""
        display_name = MODEL_NAMES.get(model, model)

        row_vals = []
        for d in DIFFICULTIES:
            for j, m in enumerate(metrics):
                val = model_data[model][d][m]
                is_best = (col_best[(d, m)] == i)
                is_second = (col_second[(d, m)] == i)
                row_vals.append(_fmt_val(val, is_best, is_second))

        logo_part = f"\\includegraphics[height=0.3cm]{{logo/{logo_name}}}" if logo_name else ""
        line = f"{logo_part} & {display_name} & " + " & ".join(row_vals) + r" \\"
        lines.append(line)

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")

    latex_str = "\n".join(lines)

    save_path = os.path.join(FIGURES_DIR, "table1_difficulty_results.tex")
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(latex_str)
    print(f"LaTeX table saved to: {save_path}")


# =========================
# Chart 2: Bar Chart by Scenario
# =========================
def plot_chart2_joint_success_by_scenario(models):
    print("Plotting Chart 2: Joint success rate by scenario (bar chart)")

    x = np.arange(len(models))
    width = 0.8 / len(SCENARIOS)

    scenario_data = {s: [] for s in SCENARIOS}
    for model in models:
        summary = get_model_summary(model)
        rates = get_joint_success_rate_by_scenario(summary)
        for s in SCENARIOS:
            scenario_data[s].append(rates[s])

    fig, ax = plt.subplots(figsize=(15, 8))

    colors = {
        "retail": "#2E86AB",
        "restaurant": "#E55934",
        "kitchen": "#9BC53D",
        "warehouse": "#7B61A8",
        "household": "#F2B134",
    }

    for idx, scenario in enumerate(SCENARIOS):
        ax.bar(
            x + (idx - (len(SCENARIOS) - 1) / 2) * width,
            scenario_data[scenario],
            width=width,
            label=scenario.capitalize(),
            color=colors[scenario],
            edgecolor="white",
            linewidth=1.2
        )

    ax.set_ylabel("Joint Success Rate (%)", fontsize=27)
    # No title
    ax.set_xticks(x)
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax.tick_params(axis="y", labelsize=22)
    ax.legend(fontsize=21)

    ymax = max([max(v) if v else 0 for v in scenario_data.values()] + [5])
    ax.set_ylim(0, min(100, ymax + 10))

    add_model_logos_below_axis(ax, models, y_offset_axes=-0.14, zoom=0.06, fontsize=10)

    save_path = os.path.join(FIGURES_DIR, "chart2_joint_success_by_scenario.png")
    save_figure_pair(save_path)
    plt.close()


def plot_chart2b_joint_success_grouped_by_scenario(models):
    """Plot five scenario groups, with one bar per model in each group."""
    print("Plotting Chart 2b: Joint success rate grouped by scenario (bar chart)")

    x = np.arange(len(SCENARIOS))
    width = 0.8 / len(models)

    model_data = {}
    for model in models:
        summary = get_model_summary(model)
        rates = get_joint_success_rate_by_scenario(summary)
        model_data[model] = [rates[scenario] for scenario in SCENARIOS]

    fig, ax = plt.subplots(figsize=(15, 8))

    for idx, model in enumerate(models):
        ax.bar(
            x + (idx - (len(models) - 1) / 2) * width,
            model_data[model],
            width=width,
            label=MODEL_NAMES.get(model, model),
            color=MODEL_COLORS.get(model),
            edgecolor="white",
            linewidth=1.2,
        )

    ax.set_ylabel("Joint Success Rate (%)", fontsize=27)
    ax.set_xticks(x)
    ax.set_xticklabels([scenario.capitalize() for scenario in SCENARIOS], fontsize=22)
    ax.grid(True, axis="y", linestyle="--", alpha=0.3)
    ax.tick_params(axis="y", labelsize=22)
    ax.legend(fontsize=15, ncol=2, loc="upper left")

    ymax = max([max(values) if values else 0 for values in model_data.values()] + [5])
    ax.set_ylim(0, min(100, ymax + 10))

    save_path = os.path.join(
        FIGURES_DIR, "chart2b_joint_success_grouped_by_scenario.png"
    )
    save_figure_pair(save_path)
    plt.close()


# =========================
# Error Analysis Data Loading
# =========================
PIE_LABELS = ["Structural Non-Compliance", "Multimodal Perceptual Misinterpretations", "Hallucination", "Logical Fallacies", "Risky Operations", "Correct"]
PIE_KEYS = ["syntax", "multimodal", "hallucination", "logic", "over_action", "correct"]

# High-contrast color scheme; Correct: green
PIE_COLORS = ["#C62828", "#E64A19", "#FFA726", "#FDD835", "#7CB342", "#2E7D32"]


def _compute_pie_proportions(counts):
    """
    Calculate proportions (percentages) from error type counts, summing to 100%.
    Memory errors are merged into Logic.

    counts: {"total": N, "syntax_error": n, ...}
    Returns: {"syntax": %, "multimodal": %, "hallucination": %, "logic": %, "over_action": %, "correct": %}
    """
    total = counts.get("total", 0)
    if total == 0:
        return {}

    syntax = counts.get("syntax_error", 0)
    multimodal = counts.get("multimodal_error", 0)
    hallucination = counts.get("hallucination_error", 0)
    logic = counts.get("logic_error", 0) + counts.get("memory_error", 0)  # memory merged into logic
    over_op = counts.get("over_operation_error", 0)
    correct = counts.get("correct", 0)

    props = {}
    props["syntax"] = syntax / total * 100
    props["multimodal"] = multimodal / total * 100
    props["hallucination"] = hallucination / total * 100
    props["logic"] = logic / total * 100
    props["over_action"] = over_op / total * 100
    props["correct"] = correct / total * 100
    return props


def load_all_error_analysis():
    """
    Read detailed results from error_analysis/all_scenarios_error_analysis_details.json,
    aggregate error counts by scenario and model, then calculate pie chart proportions.

    Returns:
    (per_scenario, overall)
      per_scenario: {scenario: {model: {"syntax": %, ...}}}
      overall:      {model: {"syntax": %, ...}}
    """
    per_scenario = {s: defaultdict(dict) for s in SCENARIOS}
    overall_counts = {}

    json_path = os.path.join(ERROR_ANALYSIS_DIR, "all_scenarios_error_analysis_details.json")
    if not os.path.exists(json_path):
        print(f"[WARN] Error analysis JSON not found: {json_path}")
        return per_scenario, {}

    details = safe_read_json(json_path)
    if not details:
        return per_scenario, {}

    # Aggregate error type counts by (scenario_type, model)
    _EMPTY = lambda: {"total": 0, "syntax_error": 0, "multimodal_error": 0,
                      "hallucination_error": 0, "logic_error": 0, "memory_error": 0,
                      "over_operation_error": 0, "correct": 0}
    counts = defaultdict(lambda: defaultdict(_EMPTY))

    for entry in details:
        if "error" in entry:
            continue
        scenario_type = entry.get("scenario_type")
        model = entry.get("model")
        if not scenario_type or not model:
            continue

        for r in entry.get("results", []):
            error_type = r.get("error_type")
            if error_type in ("missing_gt", "missing_eval"):
                continue
            counts[scenario_type][model]["total"] += 1
            if error_type in counts[scenario_type][model]:
                counts[scenario_type][model][error_type] += 1

    # Calculate pie proportions per scenario per model
    for scenario_type in SCENARIOS:
        for model, cnt in counts[scenario_type].items():
            per_scenario[scenario_type][model] = _compute_pie_proportions(cnt)

    # Calculate pie proportions per model across scenarios
    all_models = set()
    for s in SCENARIOS:
        all_models.update(counts[s].keys())

    for model in all_models:
        merged = _EMPTY()
        for s in SCENARIOS:
            if model in counts[s]:
                for k in merged:
                    merged[k] += counts[s][model][k]
        overall_counts[model] = _compute_pie_proportions(merged)

    return per_scenario, overall_counts


# =========================
# Chart 3: Error Reason Pie Charts
# =========================
def _draw_single_pie(ax, props, model, logo_zoom=0.10,
                     name_fontsize=15, pct_fontsize=11):
    """
    Draw a solid pie chart with the model logo and name below it.
    props: {"syntax": %, "multimodal": %, ...}  summing to 100%
    """
    values = [props.get(k, 0) for k in PIE_KEYS]

    # Filter out zero-value items
    filtered_labels = []
    filtered_values = []
    filtered_colors = []
    for i, v in enumerate(values):
        if v > 0:
            filtered_labels.append(PIE_LABELS[i])
            filtered_values.append(v)
            filtered_colors.append(PIE_COLORS[i])

    if filtered_values:
        _, _, autotexts = ax.pie(
            filtered_values,
            colors=filtered_colors,
            autopct=lambda pct: f"{pct:.1f}" if pct >= 4 else "",
            startangle=90,
            pctdistance=0.70,
            radius=0.78,
            center=(0, 0.22),
            wedgeprops=dict(edgecolor="white", linewidth=1.5),
            textprops=dict(fontsize=pct_fontsize, fontweight="bold"),
        )
        for text in autotexts:
            text.set_fontsize(pct_fontsize)
            text.set_color("#333333")
    else:
        ax.text(0.5, 0.58, "No Data", transform=ax.transAxes,
                ha="center", va="center", fontsize=name_fontsize)

    # Keep the logo and model name outside the pie so the center remains solid.
    img = load_logo_image(model, zoom=logo_zoom)
    if img is not None:
        ab = AnnotationBbox(
            img, (0.5, 0.085), xycoords=ax.transAxes,
            frameon=False, box_alignment=(0.5, 0.5), pad=0,
        )
        ax.add_artist(ab)

    ax.text(0.5, -0.025, MODEL_NAMES.get(model, model),
            transform=ax.transAxes, ha="center", va="top",
            fontsize=name_fontsize, fontweight="bold", clip_on=False)
    # Remove the generous default margins added by ``Axes.pie``.  Keeping a
    # little extra room at the bottom leaves space for the logo and name.
    ax.set_xlim(-0.92, 0.92)
    ax.set_ylim(-1.00, 1.15)
    ax.set_aspect("equal")
    ax.axis("off")


def plot_chart3a_pie_by_model(models):
    """Chart 3a: Overall error reason pies, with up to eight models per row."""
    print(f"Plotting Chart 3a: Overall error reason pies for {len(models)} models")

    _, overall_data = load_all_error_analysis()

    ncols = min(8, max(1, len(models)))
    nrows = math.ceil(len(models) / ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(ncols * 1.85, nrows * 2.8),
        gridspec_kw={"wspace": 0.0, "hspace": 0.06},
    )
    axes = np.asarray(axes, dtype=object).reshape(nrows, ncols)

    for idx, model in enumerate(models):
        r, c = divmod(idx, ncols)
        if r >= nrows:
            break
        ax = axes[r][c]
        props = overall_data.get(model, {})
        _draw_single_pie(
            ax, props, model,
            logo_zoom=0.055, name_fontsize=11, pct_fontsize=10,
        )

    # Hide extra subplots
    for idx in range(len(models), nrows * ncols):
        r, c = divmod(idx, ncols)
        axes[r][c].axis("off")

    # Legend
    legend_elements = [plt.matplotlib.patches.Patch(
        facecolor=PIE_COLORS[i], edgecolor="white", label=PIE_LABELS[i]
    ) for i in range(len(PIE_LABELS))]
    fig.legend(handles=legend_elements, loc="lower center", ncol=len(PIE_LABELS),
               fontsize=11, frameon=True, bbox_to_anchor=(0.5, -0.02))

    plt.subplots_adjust(left=0.005, right=0.995, top=0.995, bottom=0.20,
                        wspace=0.0, hspace=0.06)

    save_path = os.path.join(FIGURES_DIR, "chart3a_error_pie_by_model.png")
    save_figure_pair(save_path)
    plt.close()
    print(f"Saved: {save_path}")


def plot_chart3b_pie_by_model_scenario(models):
    """Chart 3b: Error reason pies by scenario and model."""
    per_scenario, _ = load_all_error_analysis()
    plotted_scenarios = [
        scenario for scenario in SCENARIOS
        if any(per_scenario[scenario].get(model) for model in models)
    ] or SCENARIOS
    print(f"Plotting Chart 3b: Error reason pies for "
          f"{len(plotted_scenarios)} scenarios")

    scenario_labels = {
        "retail": "Retail", "restaurant": "Restaurant",
        "kitchen": "Kitchen", "warehouse": "Warehouse",
        "household": "Household",
    }

    nrows = len(plotted_scenarios)
    ncols = len(models)
    fig, axes = plt.subplots(nrows, ncols,
                             figsize=(ncols * 1.9, nrows * 2.5))

    for row, scenario in enumerate(plotted_scenarios):
        for col, model in enumerate(models):
            ax = axes[row][col] if nrows > 1 else axes[col]
            props = per_scenario[scenario].get(model, {})
            _draw_single_pie(ax, props, model,
                             logo_zoom=0.045, name_fontsize=8,
                             pct_fontsize=10)
            # Add scenario label to first column
            if col == 0:
                ax.text(-0.25, 0.5, scenario_labels.get(scenario, scenario),
                        transform=ax.transAxes, ha="center", va="center",
                        fontsize=21, fontweight="bold", rotation=90)

    # Legend
    legend_elements = [plt.matplotlib.patches.Patch(
        facecolor=PIE_COLORS[i], edgecolor="white", label=PIE_LABELS[i]
    ) for i in range(len(PIE_LABELS))]
    fig.legend(handles=legend_elements, loc="lower center", ncol=len(PIE_LABELS),
               fontsize=12, frameon=True, bbox_to_anchor=(0.5, -0.01))

    plt.subplots_adjust(left=0.045, right=0.995, top=0.995, bottom=0.10,
                        wspace=0.0, hspace=0.04)

    save_path = os.path.join(FIGURES_DIR, "chart3b_error_pie_by_model_scenario.png")
    save_figure_pair(save_path)
    plt.close()
    print(f"Saved: {save_path}")


def plot_chart3_error_pie(models):
    """Plot all error reason pie charts."""
    plot_chart3a_pie_by_model(models)
    plot_chart3b_pie_by_model_scenario(models)


# =========================
# Scatter Plot Utility Functions
# =========================
def annotate_scatter_with_logo(ax, x, y, model, text_offset=(0, -12), zoom=0.11, fontsize=10):
    img = load_logo_image(model, zoom=zoom)
    if img is not None:
        ab = AnnotationBbox(
            img, (x, y),
            frameon=False,
            box_alignment=(0.5, 0.5),
            pad=0
        )
        ax.add_artist(ab)

    ax.annotate(
        MODEL_NAMES.get(model, model),
        (x, y),
        textcoords="offset points",
        xytext=text_offset,
        ha="center",
        va="top",
        fontsize=fontsize,
        fontweight="bold"
    )


def annotate_scatter_points(ax, models, xs, ys, fontsize=16, top_only=True,
                            top_strict=False, color_overrides=None):
    """Deterministically place each model's label ABOVE its point with no overlaps.

    color_overrides: optional {model: hex_color} to override the label text color
    for specific models (e.g. render a single model's label in pink).
    top_strict=True tightens top_only mode so the label sits DIRECTLY above its own
    point and is never allowed to drift below any other point; crowded points trade
    horizontal offset rather than dropping below.

    Labels must sit above their own point (model name over the scatter dot) and not
    cover any other point or label. Because several charts cluster points tightly
    (e.g. conversation rounds all land near 4.5), apply a deterministic screen-space
    placement instead of a force-directed packer:

    - Isolated points keep their label close; crowded points push farther out.
    - Candidate anchors are tried at increasing screen radii around each point along a
      ring of angles; the nearest legal anchor that avoids point- and label-overlap is
      chosen, with the search ordered so sparser points grab the near slots first.
    - top_only=True restricts the candidate ring to the upper semicircle so every label
      sits strictly above its own point (still nudged left/right to dodge overlaps).
    - A final objective-driven local search rejects any label that ends up closer to
      another point than that point's own label, and clears residual point/label hits.
    - Thin leader lines tie each label back to its point; a white text halo keeps the
      colored name readable over the grid.
    """
    import matplotlib.patheffects as pe

    fig = ax.figure
    renderer = fig.canvas.get_renderer()

    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    n = len(xs)
    names = [MODEL_NAMES.get(m, m) for m in models]
    colors = [MODEL_COLORS.get(m, "#000000") for m in models]
    if color_overrides:
        for i, m in enumerate(models):
            if m in color_overrides:
                colors[i] = color_overrides[m]

    # Point centers in pixels.
    def _to_pixels(xy):
        return ax.transData.transform(np.asarray(xy, dtype=float))
    pt_px = _to_pixels(list(zip(xs, ys)))

    # Measure each label's size in pixels with a hidden text artist.
    def _text_extent(txt):
        bb = txt.get_window_extent(renderer=renderer)
        return ((bb.x0 + bb.x1) / 2.0, (bb.y0 + bb.y1) / 2.0,
                bb.x1 - bb.x0, bb.y1 - bb.y0)

    label_sizes = []
    tmp = ax.text(0, 0, "", fontsize=fontsize, fontweight="bold")
    for nm in names:
        tmp.set_text(nm)
        _, _, w, h = _text_extent(tmp)
        label_sizes.append((w, h))
    tmp.remove()

    # Axes size in pixels, for scaling candidate radii.
    xlim = ax.get_xlim(); ylim = ax.get_ylim()
    x0, y0 = _to_pixels([(xlim[0], ylim[0])])[0]
    x1, y1 = _to_pixels([(xlim[1], ylim[1])])[0]
    axes_w, axes_h = abs(x1 - x0), abs(y1 - y0)
    axes_min = min(axes_w, axes_h)

    pt_marker_r = 11.0  # half-extent of an s=150 marker on a 14x9in fig at 200 dpi

    # Angles to try around each point. top_only keeps every candidate in the upper
    # semicircle (screen-up), straight up first then fanning into the upper diagonals.
    if top_only:
        a = np.pi / 2
        angles = [a,
                  a - np.pi / 8, a + np.pi / 8,
                  a - np.pi / 4, a + np.pi / 4,
                  a - 3 * np.pi / 8, a + 3 * np.pi / 8,
                  a - (np.pi / 2 - 0.18), a + (np.pi / 2 - 0.18)]
    else:
        angles = [0.0, np.pi, np.pi / 2, -np.pi / 2,
                  np.pi / 4, -np.pi / 4, 3 * np.pi / 4, -3 * np.pi / 4]

    # Nearest-neighbor isolation in pixels (bigger = more isolated).
    nn_dist = np.full(n, np.inf)
    for i in range(n):
        for j in range(n):
            if i != j:
                nn_dist[i] = min(nn_dist[i], np.hypot(pt_px[i, 0] - pt_px[j, 0],
                                                      pt_px[i, 1] - pt_px[j, 1]))

    cand_radii = [axes_min * r for r in (0.05, 0.08, 0.11, 0.15, 0.20, 0.26, 0.33, 0.42, 0.52)]

    # Axes pixel bounds (allow labels inside the axes rectangle, with small margin).
    margin = 6.0
    ax_bb = ax.get_window_extent(renderer=renderer)
    ax_left = ax_bb.x0 + margin; ax_right = ax_bb.x1 - margin
    ax_bottom = ax_bb.y0 + margin; ax_top = ax_bb.y1 - margin

    placed = [None] * n  # (cx, cy, w, h)

    def overlaps_rect(cx, cy, w, h, other):
        ox, oy, ow, oh = other
        pad = 5.0
        return (abs(cx - ox) < (w + ow) / 2 + pad and abs(cy - oy) < (h + oh) / 2 + pad)

    def overlaps_any_point(cx, cy, w, h):
        pad = 6.0
        for j in range(n):
            if (abs(cx - pt_px[j, 0]) < w / 2 + pt_marker_r + pad and
                    abs(cy - pt_px[j, 1]) < h / 2 + pt_marker_r + pad):
                return True
        return False

    def out_of_bounds(cx, cy, w, h):
        return (cx - w / 2 < ax_left or cx + w / 2 > ax_right or
                cy - h / 2 < ax_bottom or cy + h / 2 > ax_top)

    def label_label_ok(cx, cy, w, h, skip=None):
        for k in range(n):
            if k == skip or placed[k] is None:
                continue
            if overlaps_rect(cx, cy, w, h, placed[k]):
                return False
        return True

    # Isolated points first so they claim the near slots; crowded points take the
    # farther rings their neighbors haven't used.
    order = sorted(range(n), key=lambda i: -nn_dist[i])

    for i in order:
        w, h = label_sizes[i]
        chosen = None
        fallback = None  # in-bounds-but-overlapping last resort
        for r in cand_radii:
            for ang in angles:
                cx = pt_px[i, 0] + r * np.cos(ang)
                cy = pt_px[i, 1] + r * np.sin(ang)
                ob = out_of_bounds(cx, cy, w, h)
                if overlaps_any_point(cx, cy, w, h):
                    continue
                lo = label_label_ok(cx, cy, w, h, skip=i)
                if ob:
                    if lo and fallback is None:
                        fallback = (cx, cy, w, h)
                    continue
                if not lo:
                    continue
                chosen = (cx, cy, w, h)
                break
            if chosen is not None:
                break
        if chosen is None:
            if fallback is not None:
                chosen = fallback
            else:
                r = cand_radii[-1]
                # last resort: directly above the point
                chosen = (pt_px[i, 0], pt_px[i, 1] + r, w, h)
        placed[i] = chosen

    # Objective-driven local search: minimize (nearest-violations, point-overlaps,
    # label-overlaps, out-of-bounds) so a label never lands closer to a neighbor's
    # point than that neighbor's own label.
    fine_angles = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    if top_only:
        fine_angles = fine_angles[np.sin(fine_angles) > 0.25]

    def score(layout):
        s_viol = 0
        for j in range(n):
            cx, cy, w, h = layout[j]
            dj = np.hypot(cx - pt_px[j, 0], cy - pt_px[j, 1])
            best_other = min(
                np.hypot(layout[i][0] - pt_px[j, 0], layout[i][1] - pt_px[j, 1])
                for i in range(n) if i != j)
            if best_other + 14 < dj:
                s_viol += 1
        s_pt = sum(1 for i in range(n) if overlaps_any_point(*layout[i]))
        s_ll = sum(1 for i in range(n) for k in range(n)
                   if k < i and overlaps_rect(*layout[i], layout[k]))
        s_oob = sum(1 for i in range(n) if out_of_bounds(*layout[i]))
        return (s_viol, s_pt, s_ll, s_oob)

    cur = list(placed)
    cur_score = score(cur)
    improved = True
    for _ in range(40):
        if not improved or cur_score[:3] == (0, 0, 0):
            break
        improved = False
        for i in range(n):
            w, h = label_sizes[i]
            best = cur[i]; best_s = cur_score
            for r in cand_radii:
                for ang in fine_angles:
                    nx = pt_px[i, 0] + r * np.cos(ang)
                    ny = pt_px[i, 1] + r * np.sin(ang)
                    cand = (nx, ny, w, h)
                    trial = list(cur); trial[i] = cand
                    s = score(trial)
                    if s < best_s or (s == best_s and
                                      np.hypot(nx - pt_px[i, 0], ny - pt_px[i, 1]) <
                                      np.hypot(best[0] - pt_px[i, 0], best[1] - pt_px[i, 1])):
                        best = cand; best_s = s
            if best is not cur[i]:
                cur[i] = best; cur_score = best_s; improved = True
    placed = cur

    # Pixel centers back to data coords; draw labels + leader lines.
    inv = ax.transData.inverted()
    for i in range(n):
        cx, cy, w, h = placed[i]
        dx, dy = inv.transform((cx, cy))
        text = ax.text(
            dx, dy, names[i],
            fontsize=fontsize, fontweight="bold", color=colors[i],
            ha="center", va="center", zorder=12,
            path_effects=[pe.withStroke(linewidth=3.5, foreground="white")],
        )
        ax.plot([xs[i], dx], [ys[i], dy],
                color="gray", lw=0.6, alpha=0.5, zorder=6,
                solid_capstyle="round")


def get_axis_padding(vals, ratio=0.08):
    vals = [v for v in vals if v is not None]
    if not vals:
        return 0, 1
    vmin = min(vals)
    vmax = max(vals)
    if math.isclose(vmin, vmax):
        pad = vmax * ratio if vmax != 0 else 1
    else:
        pad = (vmax - vmin) * ratio
    return vmin - pad, vmax + pad


# =========================
# Chart 4: Tokens vs Success
# =========================
def plot_chart4_tokens_vs_success(models):
    print("Plotting Chart 4: Avg token consumption vs joint success rate")

    xs, ys = [], []

    for model in models:
        summary = get_model_summary(model)
        metrics = get_metrics_from_summary(summary)
        xs.append(metrics["avg_tokens"])
        ys.append(get_overall_joint_success_rate(summary))

    fig, ax = plt.subplots(figsize=(14, 9))

    # MiMo (mimo-v2.5-omni) is highlighted in pink per request.
    MIMO_PINK = "#FF6FA5"

    # Draw with large points
    for model, x, y in zip(models, xs, ys):
        color = MODEL_COLORS.get(model, "#000000")
        if model == "mimo-v2.5-omni":
            color = MIMO_PINK
        ax.scatter(x, y, c=color, s=150, edgecolors="white", linewidths=1.5, zorder=5)

    ax.set_xlabel("Average Tokens per Trajectory (Input + Output)", fontsize=28)
    ax.set_ylabel("Joint Success Rate (%)", fontsize=28)
    ax.tick_params(labelsize=22)
    ax.grid(True, linestyle="--", alpha=0.3)

    # Set x-axis to k units
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(round(x/1000))}k"))

    xmin, xmax = get_axis_padding(xs)
    ymin, ymax = get_axis_padding(ys)
    ax.set_xlim(max(0, xmin), xmax)
    # Extra headroom on top so labels placed strictly above their points never clip.
    ax.set_ylim(max(0, ymin - 2), min(100, ymax + 12))

    annotate_scatter_points(
        ax, models, xs, ys, fontsize=16,
        top_strict=True,
        color_overrides={"mimo-v2.5-omni": MIMO_PINK},
    )

    save_path = os.path.join(FIGURES_DIR, "chart4_tokens_vs_success.png")
    save_figure_pair(save_path)
    plt.close()


# =========================
# Chart 4a: Input Tokens vs Success
# =========================
def plot_chart4a_input_tokens_vs_success(models):
    print("Plotting Chart 4a: Avg input token consumption vs joint success rate")

    xs, ys = [], []

    for model in models:
        summary = get_model_summary(model)
        metrics = get_metrics_from_summary(summary)
        xs.append(metrics["avg_input_tokens"])
        ys.append(get_overall_joint_success_rate(summary))

    fig, ax = plt.subplots(figsize=(14, 9))

    # Draw with large points
    for model, x, y in zip(models, xs, ys):
        color = MODEL_COLORS.get(model, "#000000")
        ax.scatter(x, y, c=color, s=150, edgecolors="white", linewidths=1.5, zorder=5)

    ax.set_xlabel("Average Input Tokens per Trajectory", fontsize=28)
    ax.set_ylabel("Joint Success Rate (%)", fontsize=28)
    ax.tick_params(labelsize=22)
    ax.grid(True, linestyle="--", alpha=0.3)

    # Set x-axis to k units
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(round(x/1000))}k"))

    xmin, xmax = get_axis_padding(xs)
    ymin, ymax = get_axis_padding(ys)
    ax.set_xlim(max(0, xmin), xmax)
    ax.set_ylim(max(0, ymin - 2), min(100, ymax + 9))

    annotate_scatter_points(ax, models, xs, ys, fontsize=16)

    save_path = os.path.join(FIGURES_DIR, "chart4a_input_tokens_vs_success.png")
    save_figure_pair(save_path)
    plt.close()


# =========================
# Chart 4b: Output Tokens vs Success
# =========================
def plot_chart4b_output_tokens_vs_success(models):
    print("Plotting Chart 4b: Avg output token consumption vs joint success rate")

    xs, ys = [], []

    for model in models:
        summary = get_model_summary(model)
        metrics = get_metrics_from_summary(summary)
        xs.append(metrics["avg_output_tokens"])
        ys.append(get_overall_joint_success_rate(summary))

    fig, ax = plt.subplots(figsize=(14, 9))

    # Draw with large points
    for model, x, y in zip(models, xs, ys):
        color = MODEL_COLORS.get(model, "#000000")
        ax.scatter(x, y, c=color, s=150, edgecolors="white", linewidths=1.5, zorder=5)

    ax.set_xlabel("Average Output Tokens per Trajectory", fontsize=28)
    ax.set_ylabel("Joint Success Rate (%)", fontsize=28)
    ax.tick_params(labelsize=22)
    ax.grid(True, linestyle="--", alpha=0.3)

    # Set x-axis to k units
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(round(x/1000))}k"))

    xmin, xmax = get_axis_padding(xs)
    ymin, ymax = get_axis_padding(ys)
    ax.set_xlim(max(0, xmin), xmax)
    ax.set_ylim(max(0, ymin - 2), min(100, ymax + 9))

    annotate_scatter_points(ax, models, xs, ys, fontsize=16)

    save_path = os.path.join(FIGURES_DIR, "chart4b_output_tokens_vs_success.png")
    save_figure_pair(save_path)
    plt.close()


# =========================
# Chart 5: Rounds vs Success
# =========================
def plot_chart5_rounds_vs_success(models):
    print("Plotting Chart 5: Avg conversation rounds vs joint success rate")

    xs, ys = [], []

    for model in models:
        summary = get_model_summary(model)
        metrics = get_metrics_from_summary(summary)
        xs.append(metrics["avg_rounds"])
        ys.append(get_overall_joint_success_rate(summary))

    fig, ax = plt.subplots(figsize=(14, 9))

    # Draw with large points
    for model, x, y in zip(models, xs, ys):
        color = MODEL_COLORS.get(model, "#000000")
        ax.scatter(x, y, c=color, s=150, edgecolors="white", linewidths=1.5, zorder=5)

    ax.set_xlabel("Average User-Agent Conversation Rounds per Trajectory", fontsize=28)
    ax.set_ylabel("Joint Success Rate (%)", fontsize=28)
    ax.tick_params(labelsize=22)
    ax.grid(True, linestyle="--", alpha=0.3)

    xmin, xmax = get_axis_padding(xs)
    ymin, ymax = get_axis_padding(ys)
    ax.set_xlim(max(0, xmin), xmax)
    ax.set_ylim(max(0, ymin - 2), min(100, ymax + 9))

    annotate_scatter_points(ax, models, xs, ys, fontsize=16)

    save_path = os.path.join(FIGURES_DIR, "chart5_rounds_vs_success.png")
    save_figure_pair(save_path)
    plt.close()


# =========================
# Chart 6: Tool Calls vs Success
# =========================
def plot_chart6_tool_calls_vs_success(models):
    print("Plotting Chart 6: Avg tool calls vs joint success rate")

    xs, ys = [], []

    for model in models:
        summary = get_model_summary(model)
        metrics = get_metrics_from_summary(summary)
        xs.append(metrics["avg_tool_calls"])
        ys.append(get_overall_joint_success_rate(summary))

    fig, ax = plt.subplots(figsize=(14, 9))

    # Draw with large points
    for model, x, y in zip(models, xs, ys):
        color = MODEL_COLORS.get(model, "#000000")
        ax.scatter(x, y, c=color, s=150, edgecolors="white", linewidths=1.5, zorder=5)

    ax.set_xlabel("Average Tool Calls per Trajectory", fontsize=28)
    ax.set_ylabel("Joint Success Rate (%)", fontsize=28)
    ax.tick_params(labelsize=22)
    ax.grid(True, linestyle="--", alpha=0.3)

    xmin, xmax = get_axis_padding(xs)
    ymin, ymax = get_axis_padding(ys)
    ax.set_xlim(max(0, xmin), xmax)
    ax.set_ylim(max(0, ymin - 2), min(100, ymax + 9))

    annotate_scatter_points(ax, models, xs, ys, fontsize=16)

    save_path = os.path.join(FIGURES_DIR, "chart6_tool_calls_vs_success.png")
    save_figure_pair(save_path)
    plt.close()


# =========================
# Main Function
# =========================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Plot evaluation result charts")
    parser.add_argument("--eval_root", type=str, default=None,
                        help="Root dir of per-model eval output (default: eval_result). "
                             "Set to GPT_user_eval_result to plot the GPT-user run; figures "
                             "are written under <eval_root>/figures.")
    parser.add_argument("--error_analysis_root", type=str, default=None,
                        help="Root dir of error-analysis details JSON (default: error_analysis). "
                             "Must match the --output_root used by analyze_error_reasons.py.")
    args = parser.parse_args()

    global EVAL_RESULT_DIR, ERROR_ANALYSIS_DIR, FIGURES_DIR
    if args.eval_root is not None:
        EVAL_RESULT_DIR = os.path.join(PROJECT_ROOT, args.eval_root)
        FIGURES_DIR = os.path.join(EVAL_RESULT_DIR, "figures")
    if args.error_analysis_root is not None:
        ERROR_ANALYSIS_DIR = os.path.join(PROJECT_ROOT, args.error_analysis_root)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print("=" * 60)
    print("Starting evaluation result chart generation")
    print(f"EVAL_RESULT_DIR   : {EVAL_RESULT_DIR}")
    print(f"LOGO_DIR          : {LOGO_DIR}")
    print(f"ERROR_ANALYSIS_DIR: {ERROR_ANALYSIS_DIR}")
    print(f"FIGURES_DIR       : {FIGURES_DIR}")
    print("=" * 60)

    models = list_model_dirs()
    if not models:
        print("[ERROR] No valid model directories found under eval_result (containing summary.json)")
        return

    print("Detected models:")
    for m in models:
        print(f" - {m}")

    plot_chart1_joint_success_by_difficulty(models)
    plot_chart2_joint_success_by_scenario(models)
    plot_chart2b_joint_success_grouped_by_scenario(models)
    plot_chart3_error_pie(models)
    plot_chart4_tokens_vs_success(models)
    plot_chart4a_input_tokens_vs_success(models)
    plot_chart4b_output_tokens_vs_success(models)
    plot_chart5_rounds_vs_success(models)
    plot_chart6_tool_calls_vs_success(models)

    print("=" * 60)
    print("All charts generated.")
    print(f"Output directory: {FIGURES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
