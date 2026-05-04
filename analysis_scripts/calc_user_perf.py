import json
import os
import re
from collections import defaultdict

# Define 8 metrics
metrics = [
    'original_role_consistency_avg',
    'original_instruction_following_avg',
    'original_resilience_avg',
    'original_contextual_robustness_avg',
    'final_role_consistency_avg',
    'final_instruction_following_avg',
    'final_resilience_avg',
    'final_contextual_robustness_avg'
]

# Store all data
all_metrics = defaultdict(list)
scene_metrics = defaultdict(lambda: defaultdict(list))
mode_metrics = defaultdict(lambda: defaultdict(list))

# Iterate over all model directories under results
results_dir = '../results'
for model_dir in os.listdir(results_dir):
    model_path = os.path.join(results_dir, model_dir)
    if not os.path.isdir(model_path):
        continue

    # Iterate over all JSON files in the model directory
    for filename in os.listdir(model_path):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(model_path, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            if not isinstance(data, list):
                continue

            # Extract scenario name and mode
            # Filename format: retail1_easy.json
            parts = filename.replace('.json', '').rsplit('_', 1)
            if len(parts) == 2:
                scene_name = parts[0]  # retail1
                mode = parts[1]  # easy/hard/static

                # Extract base scenario name (retail)
                base_scene = re.match(r'([a-z]+)', scene_name).group(1) if scene_name else 'unknown'
            else:
                base_scene = 'unknown'
                mode = 'unknown'

            # Collect metrics per scenario
            for item in data:
                if 'user_performance' not in item:
                    continue
                up = item['user_performance']

                for metric in metrics:
                    if metric in up and up[metric] is not None:
                        value = up[metric]
                        all_metrics[metric].append(value)
                        scene_metrics[base_scene][metric].append(value)
                        mode_metrics[mode][metric].append(value)

        except Exception as e:
            print(f"Error processing {filepath}: {e}")

# Calculate and output results
print("=" * 80)
print("Average user_performance metrics across all scenarios")
print("=" * 80)
print(f"{'Metric':<45} {'Average':>10} {'Samples':>10}")
print("-" * 80)
for metric in metrics:
    values = all_metrics[metric]
    if values:
        avg = sum(values) / len(values)
        print(f"{metric:<45} {avg:>10.4f} {len(values):>10}")
    else:
        print(f"{metric:<45} {'N/A':>10} {0:>10}")

print("\n" + "=" * 80)
print("Average metrics grouped by base scenario")
print("=" * 80)
for scene in sorted(scene_metrics.keys()):
    print(f"\n--- {scene.upper()} ---")
    print(f"{'Metric':<45} {'Average':>10} {'Samples':>10}")
    print("-" * 65)
    for metric in metrics:
        values = scene_metrics[scene][metric]
        if values:
            avg = sum(values) / len(values)
            print(f"{metric:<45} {avg:>10.4f} {len(values):>10}")

print("\n" + "=" * 80)
print("Average metrics grouped by mode")
print("=" * 80)
for mode in sorted(mode_metrics.keys()):
    print(f"\n--- {mode.upper()} ---")
    print(f"{'Metric':<45} {'Average':>10} {'Samples':>10}")
    print("-" * 65)
    for metric in metrics:
        values = mode_metrics[mode][metric]
        if values:
            avg = sum(values) / len(values)
            print(f"{metric:<45} {avg:>10.4f} {len(values):>10}")