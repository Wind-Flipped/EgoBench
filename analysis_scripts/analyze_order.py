#!/usr/bin/env python3
"""Analyze whether each model selected the correct restaurant in order scenarios.

For order1, the correct restaurant is "Annie Italian Restaurant".
For order2, the correct restaurant is "Mediterranean Greek Restaurant".
Checks the last tool call's restaurant_name parameter in each sample.
"""

import json
import os
import glob

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

CORRECT_RESTAURANT = {
    "order1": "Annie Italian Restaurant",
    "order2": "Mediterranean Greek Restaurant",
}

MODES = ["easy", "hard", "static"]


def get_last_restaurant_name(tool_calls):
    """Extract the restaurant_name from the last tool call."""
    if not tool_calls:
        return None
    last_entry = tool_calls[-1]
    for call in last_entry.get("calls", []):
        params = call.get("parameters", {})
        if "restaurant_name" in params:
            return params["restaurant_name"]
    for result in last_entry.get("results", []):
        params = result.get("parameters", {})
        if "restaurant_name" in params:
            return params["restaurant_name"]
    return None


def analyze_model(model_dir):
    """Analyze a single model's order results."""
    model_name = os.path.basename(model_dir)
    results = {}

    for scenario in ["order1", "order2"]:
        correct_name = CORRECT_RESTAURANT[scenario]
        scenario_results = {}

        for mode in MODES:
            filepath = os.path.join(model_dir, f"{scenario}_{mode}.json")
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            total = 0
            correct = 0
            no_tool_calls = 0
            no_restaurant_name = 0

            for sample in data:
                tool_calls = sample.get("tool_calls", [])
                if not tool_calls:
                    no_tool_calls += 1
                    total += 1
                    continue

                restaurant = get_last_restaurant_name(tool_calls)
                total += 1

                if restaurant is None:
                    no_restaurant_name += 1
                elif restaurant == correct_name:
                    correct += 1

            scenario_results[mode] = {
                "total": total,
                "correct": correct,
                "no_tool_calls": no_tool_calls,
                "no_restaurant_name": no_restaurant_name,
                "accuracy": correct / total if total > 0 else 0,
            }

        if scenario_results:
            results[scenario] = scenario_results

    return model_name, results


def main():
    model_dirs = []
    for entry in sorted(os.listdir(RESULTS_DIR)):
        path = os.path.join(RESULTS_DIR, entry)
        if not os.path.isdir(path):
            continue
        if glob.glob(os.path.join(path, "order*_*.json")):
            model_dirs.append(path)

    if not model_dirs:
        print("No order result files found.")
        return

    header = "{:<30} {:<10} {:<8} {:<10} {:<8} {:<10} {:<14} {:<12}".format(
        "Model", "Scenario", "Mode", "Correct", "Total", "Accuracy", "No ToolCalls", "No RestName"
    )
    print("=" * 100)
    print(header)
    print("=" * 100)

    for model_dir in model_dirs:
        model_name, results = analyze_model(model_dir)
        for scenario in ["order1", "order2"]:
            if scenario not in results:
                continue
            for mode in MODES:
                if mode not in results[scenario]:
                    continue
                r = results[scenario][mode]
                acc_str = "{:.1%}".format(r["accuracy"])
                row = "{:<30} {:<10} {:<8} {:<10} {:<8} {:<10} {:<14} {:<12}".format(
                    model_name, scenario, mode, r["correct"], r["total"],
                    acc_str, r["no_tool_calls"], r["no_restaurant_name"]
                )
                print(row)
        print("-" * 100)

    # Summary: overall accuracy per model across all order scenarios
    print()
    print("=" * 70)
    summary_header = "{:<30} {:<10} {:<8} {:<18}".format(
        "Model", "Correct", "Total", "Overall Accuracy"
    )
    print(summary_header)
    print("=" * 70)

    for model_dir in model_dirs:
        model_name, results = analyze_model(model_dir)
        total_correct = 0
        total_samples = 0
        for scenario in results.values():
            for mode_data in scenario.values():
                total_correct += mode_data["correct"]
                total_samples += mode_data["total"]
        overall = total_correct / total_samples if total_samples > 0 else 0
        row = "{:<30} {:<10} {:<8} {:.1%}".format(model_name, total_correct, total_samples, overall)
        print(row)

    print("=" * 70)


if __name__ == "__main__":
    main()
