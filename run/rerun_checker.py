import os
import json

def get_rerun_indices(results_path, eval_path, user_mode="easy"):
    """
    Check if the results have > 20 samples.
    If user_mode == "static":
      - Return [] if > 20 samples (meaning skip entirely)
      - Return None if <= 20 samples (meaning run normally)
    If user_mode != "static":
      - If > 20 samples, check evaluation file to find samples with:
          - joint_success == False
          - result_based -> matches >= 1 (or tool_based -> matches >= 1)
      - Return a list of 0-based indices to rerun.
      - If <= 20 samples or eval file not found, return None (which means run normally).
    """
    if not os.path.exists(results_path):
        return None

    try:
        with open(results_path, 'r', encoding='utf-8') as f:
            results_data = json.load(f)
            if not isinstance(results_data, list):
                return None
            if len(results_data) <= 20:
                return None
    except Exception:
        return None

    # If > 20 samples and static point, we skip the whole scenario
    if user_mode == "static":
        return []

    if not os.path.exists(eval_path):
        return None

    try:
        with open(eval_path, 'r', encoding='utf-8') as f:
            eval_data = json.load(f)
    except Exception:
        return None
        
    detailed_results = eval_data.get("detailed_results", [])
    if not detailed_results:
        return None
        
    # Map scenario_id to its detailed result for quick lookup
    eval_map = {item.get("scenario_id"): item for item in detailed_results if "scenario_id" in item}
    
    rerun_indices = []
    
    for i, res in enumerate(results_data):
        scenario_id = res.get("scenario_id", i + 1)
        
        eval_item = eval_map.get(scenario_id)
        if eval_item:
            # Check conditions: joint_success == false
            joint_success = eval_item.get("joint_success", True)
            if not joint_success:
                matches_val = 0
                result_based = eval_item.get("result_based", {})
                tool_based = eval_item.get("tool_based", {})
                
                # check matches
                if "matches" in result_based:
                    matches = result_based.get("matches", 0)
                elif "matches" in tool_based:
                    matches = tool_based.get("matches", 0)
                else:
                    matches = 0
                    
                if isinstance(matches, list):
                    matches_val = len(matches)
                elif isinstance(matches, (int, float)):
                    matches_val = int(matches)
                    
                if matches_val >= 1:
                    rerun_indices.append(i)
                    
    return rerun_indices

def merge_rerun_results(original_results_path, new_results_list, rerun_indices,
                        scenario_total=None):
    """
    Merge the newly ran results back into the original results list.

    Each entry in ``new_results_list`` carries its own ``scenario_id`` (1-based,
    assigned during the run from a full-list scan), and is placed at the
    matching position (``scenario_id - 1``) in the on-disk list. This is robust
    to rerun task sets that are a sparse, non-contiguous subset of the scenario
    (e.g. glm-5v ran only some tasks per scenario): placements are keyed by
    scenario_id rather than by 0-based run order, and the list is *grown* (padded
    with ``None`` for not-yet-run tasks) so no reran task is ever dropped as it
    was under the old ``orig_idx < len(original_data)`` guard.

    Args:
        original_results_path: results/{model}/{scenario}{number}_{mode}.json
        new_results_list: results produced this run (list of dicts).
        rerun_indices: 0-based indices into the full scenario list that were run
            (used as a fallback position when a result lacks scenario_id).
        scenario_total: total number of tasks in the ground-truth scenario file.
            When the base file is missing/shorter than a reran task's position,
            the list is padded with ``None`` up to at least this length so every
            reran task lands at its true position. If None, padding grows only as
            far as the highest seen scenario_id.
    """
    if not new_results_list:
        return

    # Load existing base (may be absent — first run, or only part-run).
    if os.path.exists(original_results_path):
        try:
            with open(original_results_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            if not isinstance(original_data, list):
                original_data = []
        except Exception as e:
            print(f"Error reading original results to merge: {e}")
            original_data = []
    else:
        original_data = []

    # Map run-order index -> 0-based scenario index (fallback when result has no id).
    idx_fallback = {i: ri for i, ri in enumerate(rerun_indices or [])}

    max_pos = len(original_data)
    placed = 0
    for i, result in enumerate(new_results_list):
        scenario_id = result.get("scenario_id") if isinstance(result, dict) else None
        if scenario_id is None:
            scenario_id = (idx_fallback.get(i, i) + 1)
        pos = int(scenario_id) - 1  # 1-based id -> 0-based position
        if pos < 0:
            continue
        # Grow the list with None placeholders for tasks not (yet) run, so this
        # reran task always lands at its true position and is never dropped.
        while len(original_data) <= pos:
            original_data.append(None)
        original_data[pos] = result
        placed += 1
        if pos + 1 > max_pos:
            max_pos = pos + 1

    # Optionally pad up to the full scenario size so not-run tasks are explicit
    # None entries (rather than absent), making run/total counts unambiguous.
    if scenario_total is not None and isinstance(scenario_total, int):
        while len(original_data) < scenario_total:
            original_data.append(None)

    try:
        with open(original_results_path, 'w', encoding='utf-8') as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)
        run_count = sum(1 for x in original_data if x is not None)
        print(f"Successfully merged {placed} rerun results into {original_results_path} "
              f"({run_count}/{len(original_data)} tasks present)")
    except Exception as e:
        print(f"Error saving merged results: {e}")
