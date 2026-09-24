"""Print the four simulated-user averages saved by the main evaluator."""

import argparse
import json
import os


USER_PERFORMANCE_KEYS = (
    "role_consistency",
    "instruction_following",
    "resilience",
    "contextual_robustness",
)


def main():
    parser = argparse.ArgumentParser(
        description="Print simulated-user metric averages from evaluation summaries"
    )
    parser.add_argument(
        "--eval_root",
        default=os.path.join(os.path.dirname(__file__), "..", "eval_result"),
        help="Directory containing per-model evaluation summaries",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.eval_root):
        print(f"Evaluation directory not found: {args.eval_root}")
        return

    found = False
    for model_name in sorted(os.listdir(args.eval_root)):
        summary_path = os.path.join(args.eval_root, model_name, "summary.json")
        if not os.path.isfile(summary_path):
            continue

        with open(summary_path, "r", encoding="utf-8") as stream:
            summary = json.load(stream).get("summary", {})

        averages = summary.get("avg_user_performance")
        if not isinstance(averages, dict):
            continue

        counts = summary.get("user_performance_sample_counts", {})
        found = True
        print(f"\n{model_name}")
        print(f"{'Metric':<28} {'Average':>10} {'Samples':>10}")
        print("-" * 50)
        for key in USER_PERFORMANCE_KEYS:
            print(
                f"{key:<28} {averages.get(key, 0.0):>10.4f} "
                f"{counts.get(key, 0):>10}"
            )

    if not found:
        print("No evaluation summary containing simulated-user metrics was found.")


if __name__ == "__main__":
    main()
