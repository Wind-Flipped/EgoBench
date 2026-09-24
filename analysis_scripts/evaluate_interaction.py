import json
import hashlib
from typing import Any, Dict, List
from collections import Counter
import argparse
import inspect
import re
from dataclasses import asdict

# 1. Import database classes
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.retail.retail_db import RetailDB
from tools.retail.retail_init import retail_init_data1, retail_init_data2, retail_init_data3, retail_init_data4, retail_init_data5, retail_init_data6, retail_init_data7, retail_init_data8, retail_init_data9, retail_init_data10
from tools.kitchen.kitchen_db import KitchenDB
from tools.kitchen.kitchen_init import kitchen_init_data
from tools.restaurant.restaurant_db import RestaurantDB
from tools.restaurant.restaurant_init import restaurant_init_data, restaurant_init_data5
from tools.restaurant.restaurant6_db import Restaurant6DB
from tools.restaurant.restaurant6_init import restaurant6_init_data
from tools.warehouse.warehouse_db import WarehouseDB
from tools.warehouse import warehouse_init
from tools.household.household_db import HouseholdDB
from tools.household import household_init


SUPPORTED_SCENARIOS = ("retail", "kitchen", "restaurant", "warehouse", "household")
SCENARIO_NUMBER_RANGES = {
    "retail": (1, 10),
    "kitchen": (1, 4),
    "restaurant": (1, 6),
    "warehouse": (1, 25),
    "household": (1, 18),
}
RESULT_FILE_PATTERN = re.compile(r'^([a-z]+)(\d+)_(easy|hard|static)\.json$')
USER_PERFORMANCE_KEYS = (
    "role_consistency",
    "instruction_following",
    "resilience",
    "contextual_robustness",
)


def parse_result_filename(filename):
    """Return ``(scenario, variant, mode)`` for a supported result filename.

    The numeric suffix is always the variant number, so ``restaurant6`` is
    classified as scenario ``restaurant`` with variant ``6``.
    """
    match = RESULT_FILE_PATTERN.fullmatch(filename)
    if not match:
        return None

    scenario = match.group(1)
    scenario_number = int(match.group(2))
    mode = match.group(3)
    if scenario not in SUPPORTED_SCENARIOS:
        return None

    min_number, max_number = SCENARIO_NUMBER_RANGES[scenario]
    if not min_number <= scenario_number <= max_number:
        return None
    return scenario, scenario_number, mode

# ===================== Core Configuration: Fuzzy Match Fields & Scenario Mapping =====================
FUZZY_KEYS = {
    "retail": ["product_name"],
    "kitchen": ["ingredient_name", "recipe_name", "recipes"],
    "restaurant": ["dish_name", "set_meal_name", "restaurant_name"],
    "warehouse": ["equipment"],
    "household": ["item_name", "name"],
}

# Database match method mapping
DB_MATCH_METHOD = {
    "retail": "_find_matching_products",
    "kitchen": None,  # Kitchen uses exact matching, not fuzzy matching
    "restaurant": "_find_matching_dishes",
    "warehouse": None,
    "household": None,
}

# Set meal match method mapping (dish_name may be a set meal name, need to match both dishes and set meals)
DB_SET_MEAL_MATCH_METHOD = {
    "retail": None,
    "kitchen": None,
    "restaurant": "_find_matching_set_meals",
    "warehouse": None,
    "household": None,
}

# Scenario fuzzy match field config (for fuzzy matching within evaluate_interaction.py)
SCENARIO_FUZZY_FIELDS = {
    "retail": ["product_name"],
    "kitchen": ["ingredient_name", "recipe_name"],
    "restaurant": ["dish_name", "set_meal_name", "restaurant_name"],
    "warehouse": ["equipment"],
    "household": ["item_name", "name"],
}

# ===================== Merge Similar Items Configuration =====================
MERGE_NAME_KEYS = [
    "product_name",
    "ingredient_name",
    "equipment",
    "item_name",
    "dish_name",
    "set_meal_name",
    "restaurant_name",
    "recipe_name",
    "name",
]

MERGE_SUM_KEYS = {
    "quantity",
}


# ===================== Numeric Normalization for Hashing =====================
def normalize_for_hash(value):
    """Normalize numeric values so that integer-valued floats (e.g. 12.0) hash identically to ints (12)."""
    if isinstance(value, dict):
        return {k: normalize_for_hash(v) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize_for_hash(v) for v in value]
    if isinstance(value, tuple):
        return [normalize_for_hash(v) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    return value


# ===================== Generic Helpers =====================
def try_parse_number(value):
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            v = value.strip()
            if v == "":
                return None
            return float(v)
    except Exception:
        return None
    return None


def canonical_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


# ===================== Fuzzy Match Function =====================
def fuzzy_match_str(query: str, target: str) -> bool:
    """Generic string fuzzy matching: lowercase containment check"""
    if not query or not target:
        return False
    return query.lower() in target.lower() or target.lower() in query.lower()


# ===================== Scenario-based Fuzzy Matching Core Function =====================
def fuzzy_match_field(gt_name: str, inter_name: str, db_instance: Any, scenario: str) -> bool:
    """
    Perform fuzzy matching based on scenario; dish_name matches both dishes and set meals, either match counts as correct
    """
    # No database instance: fallback to string fuzzy matching
    if not db_instance:
        return fuzzy_match_str(inter_name, gt_name)

    if scenario == "kitchen":
        # Kitchen scenario: use exact matching (KitchenDB has no fuzzy match method)
        return gt_name.lower().strip() == inter_name.lower().strip()

    match_method = DB_MATCH_METHOD.get(scenario)
    set_meal_method = DB_SET_MEAL_MATCH_METHOD.get(scenario)

    def _collect_matching_names(name: str) -> set:
        """Collect all matching names for dishes and set meals"""
        all_names = set()

        # Dish matching
        if match_method and hasattr(db_instance, match_method):
            try:
                match_func = getattr(db_instance, match_method)
                if isinstance(db_instance, Restaurant6DB):
                    # Restaurant6DB needs to iterate over all restaurants.
                    for r_name in db_instance.restaurants:
                        matches = match_func(r_name, name)
                        all_names.update(m.name for m in matches)
                else:
                    matches = match_func(name)
                    all_names.update(m.name for m in matches)
            except Exception:
                pass

        # Set meal matching
        if set_meal_method and hasattr(db_instance, set_meal_method):
            try:
                sm_func = getattr(db_instance, set_meal_method)
                if isinstance(db_instance, Restaurant6DB):
                    for r_name in db_instance.restaurants:
                        matches = sm_func(r_name, name)
                        all_names.update(m.name for m in matches)
                else:
                    matches = sm_func(name)
                    all_names.update(m.name for m in matches)
            except Exception:
                pass

        return all_names

    gt_names = _collect_matching_names(gt_name)
    inter_names = _collect_matching_names(inter_name)

    # Match succeeds if dishes or set meals have intersection
    if len(gt_names) > 0 and len(inter_names) > 0:
        return len(gt_names & inter_names) > 0

    # Database methods all returned empty lists, fallback to string fuzzy matching
    return fuzzy_match_str(inter_name, gt_name)


# ===================== Merge Similar Items Before Matching =====================
def get_merge_identity_key(item: dict):
    """
    Return the first available name-like key for grouping similar dict items.
    """
    for key in MERGE_NAME_KEYS:
        if key in item and item[key] is not None:
            return key
    return None


def merge_two_dict_items(base: dict, incoming: dict) -> dict:
    """
    Merge two similar dict items:
    - sum numeric quantity-like fields in MERGE_SUM_KEYS
    - for other fields, keep existing non-empty value; otherwise fill from incoming
    """
    merged = dict(base)

    for k, v in incoming.items():
        if k in MERGE_SUM_KEYS:
            a = try_parse_number(merged.get(k))
            b = try_parse_number(v)
            if a is not None and b is not None:
                summed = a + b
                merged[k] = int(summed) if summed.is_integer() else summed
            elif merged.get(k) is None:
                merged[k] = v
        else:
            existing = merged.get(k)
            if existing is None or (isinstance(existing, str) and existing.strip() == ""):
                merged[k] = v

    return merged


def merge_similar_items_in_list(items, db_instance=None, scenario="retail", current_key=None):
    """
    Merge similar dict items in a list before matching.
    Typical use case:
    [
        {"dish_name": "apple", "quantity": 1},
        {"dish_name": "apple", "quantity": 2}
    ]
    =>
    [
        {"dish_name": "apple", "quantity": 3}
    ]

    注意：
    为保证 list 参数评估时是"无序精准匹配"，这里的"similar"也只按严格相等合并，
    不再对 name 类字段使用模糊匹配合并。
    """
    if not isinstance(items, list):
        return items

    normalized_items = [
        merge_similar_items_in_value(item, db_instance=db_instance, scenario=scenario, current_key=current_key)
        for item in items
    ]

    if not normalized_items:
        return normalized_items

    if not all(isinstance(x, dict) for x in normalized_items):
        return normalized_items

    merged_groups = []

    for item in normalized_items:
        name_key = get_merge_identity_key(item)
        if not name_key:
            merged_groups.append(item)
            continue

        current_name = item.get(name_key)
        merged = False

        for idx, existing in enumerate(merged_groups):
            if not isinstance(existing, dict):
                continue
            existing_name_key = get_merge_identity_key(existing)
            if existing_name_key != name_key:
                continue

            existing_name = existing.get(existing_name_key)
            if isinstance(current_name, str) and isinstance(existing_name, str):
                same = canonical_string(existing_name) == canonical_string(current_name)

                if same:
                    merged_groups[idx] = merge_two_dict_items(existing, item)
                    merged = True
                    break
            else:
                if current_name == existing_name:
                    merged_groups[idx] = merge_two_dict_items(existing, item)
                    merged = True
                    break

        if not merged:
            merged_groups.append(item)

    def sort_key(x):
        if isinstance(x, dict):
            name_key = get_merge_identity_key(x)
            if name_key:
                return canonical_string(x.get(name_key))
        return json.dumps(normalize_for_hash(x), ensure_ascii=False, sort_keys=True, default=str)

    return sorted(merged_groups, key=sort_key)


def merge_similar_items_in_value(value, db_instance=None, scenario="retail", current_key=None):
    """
    Recursively merge similar items in complex parameter values.
    """
    if isinstance(value, dict):
        return {
            k: merge_similar_items_in_value(v, db_instance=db_instance, scenario=scenario, current_key=k)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return merge_similar_items_in_list(value, db_instance=db_instance, scenario=scenario, current_key=current_key)
    if isinstance(value, tuple):
        return [
            merge_similar_items_in_value(v, db_instance=db_instance, scenario=scenario, current_key=current_key)
            for v in value
        ]
    return value


def normalize_call_parameters_before_match(params, db_instance=None, scenario="retail"):
    """
    Normalize parameters before comparison:
    1. recursively process nested values
    2. merge similar items in lists
    """
    if not isinstance(params, dict):
        return params
    return merge_similar_items_in_value(params, db_instance=db_instance, scenario=scenario)


# ===================== Strict / Exact Comparison Helpers =====================
def compare_parameters_recursive_exact(
    gt_val: Any,
    inter_val: Any,
    db_instance: Any = None,
    scenario: str = "retail",
    current_key: str = None
) -> bool:
    """
    Exact recursive comparison.
    For list:
    - unordered exact matching only
    For fuzzy keys:
    - exact means normalized string equality, NOT fuzzy db matching
    """
    if type(gt_val) != type(inter_val):
        try:
            if isinstance(gt_val, (str, int, float)) and isinstance(inter_val, (str, int, float)):
                return float(gt_val) == float(inter_val)
        except (ValueError, TypeError):
            pass
        return False

    if isinstance(gt_val, list):
        gt_val = merge_similar_items_in_list(gt_val, db_instance, scenario, current_key)
        inter_val = merge_similar_items_in_list(inter_val, db_instance, scenario, current_key)

        if len(gt_val) != len(inter_val):
            return False

        inter_used = [False] * len(inter_val)
        for gt_item in gt_val:
            found = False
            for j, inter_item in enumerate(inter_val):
                if inter_used[j]:
                    continue
                if compare_parameters_recursive_exact(gt_item, inter_item, db_instance, scenario, current_key):
                    inter_used[j] = True
                    found = True
                    break
            if not found:
                return False
        return True

    if isinstance(gt_val, dict):
        gt_val = merge_similar_items_in_value(gt_val, db_instance, scenario, current_key)
        inter_val = merge_similar_items_in_value(inter_val, db_instance, scenario, current_key)

        if set(gt_val.keys()) != set(inter_val.keys()):
            return False

        for key, g_val in gt_val.items():
            i_val = inter_val[key]
            if not compare_parameters_recursive_exact(g_val, i_val, db_instance, scenario, key):
                return False
        return True

    if isinstance(gt_val, str):
        if current_key in FUZZY_KEYS.get(scenario, []):
            return canonical_string(gt_val) == canonical_string(inter_val)
        return gt_val == inter_val

    return gt_val == inter_val


# ===================== Recursive Parameter Comparison =====================
def compare_parameters_recursive(
    gt_val: Any,
    inter_val: Any,
    db_instance: Any = None,
    scenario: str = "retail",
    current_key: str = None
) -> bool:
    """
    Recursively compare two parameter values, supporting:
    1. Array/list: unordered comparison, ignoring order
    2. Dict/object: recursive field-by-field comparison
    3. Specified fields: scenario-based fuzzy matching
    4. Basic types: exact comparison

    关键修改：
    当参数是 list 时，严格按照"无序精准匹配"进行评估，
    不再使用任何模糊匹配。
    """
    # When types differ, try numeric-compatible comparison (str/int/float mix, e.g. "2" vs 2.0)
    if type(gt_val) != type(inter_val):
        try:
            if isinstance(gt_val, (str, int, float)) and isinstance(inter_val, (str, int, float)):
                return float(gt_val) == float(inter_val)
        except (ValueError, TypeError):
            pass
        return False

    # 1. Handle array/list type: unordered exact matching
    if isinstance(gt_val, list):
        return compare_parameters_recursive_exact(gt_val, inter_val, db_instance, scenario, current_key)

    # 2. Handle dict/object type
    if isinstance(gt_val, dict):
        gt_val = merge_similar_items_in_value(gt_val, db_instance, scenario, current_key)
        inter_val = merge_similar_items_in_value(inter_val, db_instance, scenario, current_key)

        if set(gt_val.keys()) != set(inter_val.keys()):
            return False

        for key, g_val in gt_val.items():
            i_val = inter_val[key]
            # Check if current field needs fuzzy matching
            if key in FUZZY_KEYS.get(scenario, []):
                # If value is string, use fuzzy matching directly
                if isinstance(g_val, str):
                    if not fuzzy_match_field(g_val, i_val, db_instance, scenario):
                        return False
                else:
                    # If value is list or other type, continue recursive comparison (keep current key for subsequent string comparison)
                    if not compare_parameters_recursive(g_val, i_val, db_instance, scenario, key):
                        return False
            else:
                if not compare_parameters_recursive(g_val, i_val, db_instance, scenario, key):
                    return False
        return True

    # 3. Basic types: special string handling
    if isinstance(gt_val, str):
        # If current field is in FUZZY_KEYS, use case-insensitive comparison
        if current_key in FUZZY_KEYS.get(scenario, []):
            return gt_val.lower().strip() == inter_val.lower().strip()
        return gt_val == inter_val

    # 4. Other basic types: exact comparison directly
    return gt_val == inter_val


# ===================== Parameter Comparison Wrapper =====================
def compare_parameters_with_fuzzy_match(
    gt_params: Dict[str, Any],
    interaction_params: Dict[str, Any],
    db_instance: Any = None,
    scenario: str = "retail"
) -> bool:
    """Upper-level wrapper: compatible with original function parameters, added scenario parameter"""
    gt_params = normalize_call_parameters_before_match(gt_params, db_instance, scenario)
    interaction_params = normalize_call_parameters_before_match(interaction_params, db_instance, scenario)
    return compare_parameters_recursive(gt_params, interaction_params, db_instance, scenario)


# ===================== Database Hash Calculation =====================
def calculate_db_hash(db_instance):
    """Calculate database state hash, supporting all scenario databases"""
    db_data = {}
    if isinstance(db_instance, KitchenDB):
        db_data = {
            'ingredients': {k: {'name': v.name, 'quantity': v.quantity, 'category': v.category,
                               'storage_location': v.storage_location, 'expiry_date': v.expiry_date,
                               'nutrition': vars(v.nutrition) if v.nutrition else None}
                         for k, v in db_instance.ingredients.items()},
            'recipes': {k: {'name': v.name, 'ingredients': [{'ingredient_name': i.ingredient_name, 'quantity': i.quantity} for i in v.ingredients],
                           'allergens': v.allergens, 'taste': v.taste, 'nutritional_characteristics': v.nutritional_characteristics}
                       for k, v in db_instance.recipes.items()},
            'user_menus': db_instance.user_menus,
            'user_shopping_lists': {k: sorted([{'ingredient_name': item.ingredient_name, 'quantity': item.quantity} for item in v.values()],
                                              key=lambda x: x['ingredient_name'])
                                   for k, v in db_instance.user_shopping_lists.items()}
        }
    elif isinstance(db_instance, RetailDB):
        db_data = {
            'catalog': {k: {'name': v.name, 'category': v.category, 'price': v.price, 'tax_rate': v.tax_rate,
                           'discount': v.discount, 'nutritional_characteristics': v.nutritional_characteristics,
                           'taste': v.taste, 'country_of_origin': v.country_of_origin,
                           'nutrition': vars(v.nutrition) if v.nutrition else None}
                     for k, v in db_instance.catalog.items()},
            'user_carts': {k: sorted([{'product_name': item.product_name, 'quantity': item.quantity,
                                       'category': item.category, 'price': item.price, 'tax_rate': item.tax_rate,
                                       'discount': item.discount} for item in v.values()],
                                      key=lambda x: x['product_name'])
                          for k, v in db_instance.user_carts.items()},
            'user_shopping_lists': db_instance.user_shopping_lists
        }
    elif isinstance(db_instance, RestaurantDB):
        db_data = {
            'catalog': {k: {'name': v.name, 'category': v.category, 'price': v.price, 'tax_rate': v.tax_rate,
                           'discount': v.discount, 'nutritional_characteristics': v.nutritional_characteristics,
                           'taste': v.taste, 'allergens': v.allergens,
                           'nutrition': vars(v.nutrition) if v.nutrition else None}
                     for k, v in db_instance.catalog.items()},
            'set_meals': {k: {'name': v.name, 'included_dishes': v.included_dishes,
                             'set_meal_price': v.set_meal_price, 'set_meal_discount': v.set_meal_discount}
                         for k, v in db_instance.set_meals.items()},
            'user_orders': {k: sorted([{'dish_name': item.dish_name, 'quantity': item.quantity} for item in v.values()],
                                       key=lambda x: x['dish_name'])
                           for k, v in db_instance.user_orders.items()}
        }
    elif isinstance(db_instance, Restaurant6DB):
        db_data = {
            'restaurants': {}
        }
        for r_name, store in db_instance.restaurants.items():
            db_data['restaurants'][r_name] = {
                'catalog': {k: {'name': v.name, 'category': v.category, 'price': v.price, 'tax_rate': v.tax_rate,
                               'discount': v.discount, 'nutritional_characteristics': v.nutritional_characteristics,
                               'taste': v.taste, 'allergens': v.allergens,
                               'nutrition': vars(v.nutrition) if v.nutrition else None}
                         for k, v in store['catalog'].items()},
                'set_meals': {k: {'name': v.name, 'included_dishes': v.included_dishes,
                                 'set_meal_price': v.set_meal_price, 'set_meal_discount': v.set_meal_discount}
                             for k, v in store['set_meals'].items()},
                'user_orders': {k: sorted([{'dish_name': item.dish_name, 'quantity': item.quantity} for item in v.values()],
                                           key=lambda x: x['dish_name'])
                               for k, v in store['user_orders'].items()}
            }
    elif isinstance(db_instance, WarehouseDB):
        db_data = {
            'equipment': {name: asdict(item) for name, item in db_instance.equipment.items()},
            'user_action_lists': {
                user_id: sorted(
                    (asdict(action) for action in actions),
                    key=lambda action: (
                        action['equipment'], action['required_action'], action['due_date']
                    ),
                )
                for user_id, actions in db_instance.user_action_lists.items()
            },
        }
    elif isinstance(db_instance, HouseholdDB):
        db_data = {
            'items': {name: asdict(item) for name, item in db_instance.items.items()},
            'user_action_lists': {
                user_id: sorted(
                    (asdict(action) for action in actions),
                    key=lambda action: (
                        action['name'], action['required_action'], action['due_date']
                    ),
                )
                for user_id, actions in db_instance.user_action_lists.items()
            },
        }
    elif hasattr(db_instance, 'get_all_data'):
        db_data = db_instance.get_all_data()
    else:
        # Generic extraction
        for attr in dir(db_instance):
            if not attr.startswith('_') and not callable(getattr(db_instance, attr)):
                attr_value = getattr(db_instance, attr)
                try:
                    json.dumps(attr_value, sort_keys=True, default=str)
                    db_data[attr] = attr_value
                except Exception:
                    continue

    json_str = json.dumps(normalize_for_hash(db_data), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


# ===================== Ground Truth Tool Call Simplification =====================
def simplify_tool_calls(db_instance, tool_calls, scenario="retail"):
    """
    Simplify ground truth tool calls, keeping only parameters needed by database methods.
    Also normalize parameters by merging similar items before matching/execution.
    """
    simplified_calls = []
    for tool_call in tool_calls:
        try:
            method_name = tool_call.get("tool_name") or tool_call.get("name")
            params = tool_call.get("parameters", {})

            if hasattr(db_instance, method_name):
                method = getattr(db_instance, method_name)
                sig = inspect.signature(method)

                # Keep only parameters accepted by the method signature
                valid_params = {
                    k: v for k, v in params.items()
                    if k in sig.parameters
                }
                valid_params = normalize_call_parameters_before_match(valid_params, db_instance, scenario)

                simplified_calls.append({
                    "tool_name": method_name,
                    "parameters": valid_params
                })
            else:
                # If method does not exist, keep original call (for subsequent error statistics)
                tool_call_copy = dict(tool_call)
                if "parameters" in tool_call_copy:
                    tool_call_copy["parameters"] = normalize_call_parameters_before_match(
                        tool_call_copy.get("parameters", {}), db_instance, scenario
                    )
                simplified_calls.append(tool_call_copy)
        except Exception:
            # Keep original call on error
            simplified_calls.append(tool_call)

    return simplified_calls


# ===================== Tool Execution Function =====================
def execute_tool_chain(db_instance, tool_calls, scenario="retail"):
    """Execute tool call chain (generic adapter) - with parameter filtering and pre-merge normalization."""
    results = []
    for tool_call in tool_calls:
        try:
            method_name = tool_call.get("tool_name") or tool_call.get("name")
            params = tool_call.get("parameters", {})

            if hasattr(db_instance, method_name):
                method = getattr(db_instance, method_name)

                # Filter parameters, keeping only those in the method signature
                sig = inspect.signature(method)
                valid_params = {
                    k: v for k, v in params.items()
                    if k in sig.parameters
                }
                valid_params = normalize_call_parameters_before_match(valid_params, db_instance, scenario)

                result = method(**valid_params)
                results.append({
                    "tool_name": method_name,
                    "parameters": valid_params,
                    "result": result,
                    "status": "success"
                })
            else:
                results.append({
                    "tool_name": method_name,
                    "parameters": params,
                    "result": f"Tool '{method_name}' not found",
                    "status": "error"
                })
        except Exception as e:
            results.append({
                "tool_name": tool_call.get("tool_name") or tool_call.get("name"),
                "parameters": tool_call.get("parameters", {}),
                "result": str(e),
                "status": "error"
            })
    return results


# ===================== Tool Call Comparison =====================
def compare_tool_calls(ground_truth_calls, interaction_calls, db_instance=None, scenario="retail"):
    """
    Compare tool calls:
    1. Tool name exact match
    2. Parameters: unordered arrays + scenario-based fuzzy matching
    3. Overall call sequence unordered comparison
    4. Parameter filtering: only compare parameters needed by database methods
    """
    def extract_call_info(call):
        if isinstance(call, dict):
            return {
                "tool_name": call.get("tool_name") or call.get("name"),  # Support both field names
                "parameters": call.get("parameters", {})
            }
        return call

    def filter_params_by_method(tool_name, params, db):
        """Filter parameters based on database method signature"""
        if db and hasattr(db, tool_name):
            try:
                method = getattr(db, tool_name)
                sig = inspect.signature(method)
                params = {k: v for k, v in params.items() if k in sig.parameters}
            except Exception:
                pass
        return normalize_call_parameters_before_match(params, db, scenario)

    try:
        # Ground truth calls: normalize parameters
        gt_calls = [extract_call_info(call) for call in ground_truth_calls]
        for call in gt_calls:
            call["parameters"] = normalize_call_parameters_before_match(
                call.get("parameters", {}), db_instance, scenario
            )

        # Extract model calls and filter parameters
        # New format: {"turn": 0, "calls": [...], "results": [...]}
        # Old format: {"turn": 0, "call": {...}, "result": "..."}
        interaction_only_calls = []
        for entry in interaction_calls:
            if isinstance(entry, dict):
                # New format: use "calls" list
                if "calls" in entry and isinstance(entry["calls"], list):
                    for call in entry["calls"]:
                        call_info = extract_call_info(call)
                        call_info["parameters"] = filter_params_by_method(
                            call_info["tool_name"],
                            call_info["parameters"],
                            db_instance
                        )
                        interaction_only_calls.append(call_info)
                # Old format: use "call" single object (backward compatible)
                elif "call" in entry:
                    call_info = extract_call_info(entry["call"])
                    call_info["parameters"] = filter_params_by_method(
                        call_info["tool_name"],
                        call_info["parameters"],
                        db_instance
                    )
                    interaction_only_calls.append(call_info)

        matches = 0
        matched_interaction_indices = set()

        for gt_call in gt_calls:
            for idx, interaction_call in enumerate(interaction_only_calls):
                if idx in matched_interaction_indices:
                    continue

                if gt_call.get("tool_name") == interaction_call.get("tool_name"):
                    if compare_parameters_with_fuzzy_match(
                        gt_call.get("parameters", {}),
                        interaction_call.get("parameters", {}),
                        db_instance,
                        scenario
                    ):
                        matches += 1
                        matched_interaction_indices.add(idx)
                        break

        return matches, len(gt_calls), len(interaction_only_calls)
    except Exception:
        return 0, 0, 0


# ===================== Database Initialization =====================
def get_init_db(scenario, scenario_number):
    import io
    import sys

    # Temporarily redirect print output to avoid database initialization messages
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    try:
        db = None
        if scenario == "retail":
            db = RetailDB()
            init_data = [
                retail_init_data1, retail_init_data2, retail_init_data3, retail_init_data4,
                retail_init_data5, retail_init_data6, retail_init_data7, retail_init_data8,
                retail_init_data9, retail_init_data10
            ]
            if 1 <= scenario_number <= 10:
                db.init_from_json(init_data[scenario_number-1])
        elif scenario == "kitchen":
            db = KitchenDB()
            db.init_from_json(kitchen_init_data)
        elif scenario == "restaurant":
            if scenario_number == 6:
                db = Restaurant6DB()
                db.init_from_json(restaurant6_init_data)
            else:
                db = RestaurantDB()
            if 1 <= scenario_number <= 4:
                db.init_from_json(restaurant_init_data)
            elif scenario_number == 5:
                db.init_from_json(restaurant_init_data5)
        elif scenario == "warehouse":
            db = WarehouseDB()
            init_data = getattr(warehouse_init, f"warehouse_init_data{scenario_number}", None)
            if init_data is None:
                raise ValueError(f"warehouse initialization data {scenario_number} not found")
            db.init_from_json(init_data)
        elif scenario == "household":
            db = HouseholdDB()
            init_data = getattr(household_init, f"household_init_data{scenario_number}", None)
            if init_data is None:
                raise ValueError(f"household initialization data {scenario_number} not found")
            db.init_from_json(init_data)
        else:
            raise ValueError(f"unsupported scenario: {scenario}")
        return db
    finally:
        sys.stdout = old_stdout


# ===================== Main Evaluation Function =====================
def evaluate_interaction_success(ground_truth_file, interaction_log_file, scenario="kitchen", args=None, silent=False, num_samples=0):
    """
    Evaluate interaction success rate

    Args:
        ground_truth_file: Ground truth file path
        interaction_log_file: Interaction log file path
        scenario: Scenario type (kitchen, retail, restaurant, warehouse, household)
        args: Argument object containing scenario_number
        silent: Whether to run in silent mode
        num_samples: Number of samples per scenario to test, 0 means test all samples
    """
    with open(ground_truth_file, 'r', encoding='utf-8') as f:
        ground_truth_data = json.load(f)
    with open(interaction_log_file, 'r', encoding='utf-8') as f:
        interaction_data = json.load(f)

    # Limit sample count based on num_samples
    if num_samples > 0:
        ground_truth_data = ground_truth_data[:num_samples]
        interaction_data = interaction_data[:num_samples]

    results = {
        "total_scenarios": len(ground_truth_data),
        "valid_scenarios": 0,
        "invalid_scenarios": [],
        "tool_based": {"success_count": 0, "partial_matches": [], "success_rate": 0.0},
        "result_based": {"success_count": 0, "success_rate": 0.0},
        "joint_success": {"success_count": 0, "success_rate": 0.0},  # Joint success rate
        "detailed_results": [],
        "micro_tool_stats": {
            "total_correct_calls": 0, "total_ground_truth_calls": 0,
            "total_interaction_calls": 0, "micro_accuracy": 0.0,
            "task_count": 0  # Actual number of evaluated tasks (denominator)
        },
        "performance_metrics": {
            "avg_user_response_time": 0.0,
            "avg_agent_response_time": 0.0,
            "avg_tokens_consumed": 0.0,
            "avg_rounds_count": 0.0,
            "avg_input_tokens": 0.0,
            "avg_output_tokens": 0.0,
            "avg_tool_calls_count": 0.0,
            "avg_user_performance": {key: 0.0 for key in USER_PERFORMANCE_KEYS},
            "user_performance_sample_counts": {key: 0 for key in USER_PERFORMANCE_KEYS},
        },
    }

    total_correct_calls = total_gt_calls = total_interaction_calls = 0
    total_user_response_time = 0.0
    total_agent_response_time = 0.0
    total_tokens_consumed = 0
    total_rounds_count = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_tool_calls_count = 0
    total_user_performance = {key: 0.0 for key in USER_PERFORMANCE_KEYS}
    user_performance_counts = {key: 0 for key in USER_PERFORMANCE_KEYS}
    valid_interaction_count = 0

    # Match interaction results to ground truth by scenario_id (not by sequential
    # index). Reruns write back only the tasks they executed, so the interaction
    # file may contain a non-contiguous, sparse subset of scenario_ids (e.g. only
    # the reran tasks), which index-aligned matching would mis-pair. Falling back
    # to positional scenario_id when an entry lacks the field keeps behavior
    # identical for fully-run files (where ids are 1..N and position-stable).
    interaction_by_id = {}
    for _i, _entry in enumerate(interaction_data):
        if isinstance(_entry, dict):
            _sid = _entry.get("scenario_id", _i + 1)
        else:
            _sid = _i + 1
        interaction_by_id[_sid] = _entry

    for _gt_idx, gt_scenario in enumerate(ground_truth_data):
        scenario_id = gt_scenario.get("scenario_id", _gt_idx + 1) if isinstance(gt_scenario, dict) else _gt_idx + 1
        interaction_scenario = interaction_by_id.get(scenario_id)
        if interaction_scenario is None:
            # This ground-truth task was not (re)run, so no interaction result exists.
            if not silent:
                print(f"Warning: interaction log missing scenario {scenario_id} data, skipped")
            results["invalid_scenarios"].append({
                "scenario_id": scenario_id,
                "reason": "Missing interaction data"
            })
            continue

        # Data format validation
        gt_tool_calls_raw = gt_scenario.get("ground_truth", [])
        interaction_tool_calls = interaction_scenario.get("tool_calls", [])
        if not isinstance(gt_tool_calls_raw, list) or not isinstance(interaction_tool_calls, list):
            results["invalid_scenarios"].append({
                "scenario_id": scenario_id,
                "reason": "Data format error (not a list)"
            })
            continue

        # Validation passed: include in valid evaluation
        valid_interaction_count += 1
        results["valid_scenarios"] += 1

        # Performance metrics statistics
        total_tokens_consumed += interaction_scenario.get("tokens_consumed", 0)
        total_user_response_time += interaction_scenario.get("user_response_time_seconds", 0.0)
        total_agent_response_time += interaction_scenario.get("agent_response_time_seconds", 0.0)
        total_rounds_count += interaction_scenario.get("rounds_count", 0)
        total_input_tokens += interaction_scenario.get("input_tokens", 0)
        total_output_tokens += interaction_scenario.get("output_tokens", 0)
        total_tool_calls_count += interaction_scenario.get("tool_calls_count", 0)

        user_perf = interaction_scenario.get("user_performance", {})
        if user_perf:
            for key in USER_PERFORMANCE_KEYS:
                value = user_perf.get(f"original_{key}_avg")
                if value is None:
                    value = user_perf.get(key)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    total_user_performance[key] += float(value)
                    user_performance_counts[key] += 1

        detailed_result = {
            "scenario_id": scenario_id,
            "tool_based": {"success": False, "matches": 0, "total_gt_calls": 0, "total_interaction_calls": 0},
            "result_based": {"success": False, "gt_hash": None, "interaction_hash": None},
            "joint_success": False  # Joint success flag
        }

        # Get database instance for ground truth simplification and comparison
        db_instance_for_matching = get_init_db(scenario, args.scenario_number)

        # Simplify ground truth tool calls: keep only parameters needed by database methods
        gt_tool_calls = simplify_tool_calls(db_instance_for_matching, gt_tool_calls_raw, scenario=scenario)

        # Tool call evaluation (using simplified ground truth)
        matches, total_gt, total_interactions = compare_tool_calls(
            gt_tool_calls, interaction_tool_calls, db_instance_for_matching, scenario
        )
        detailed_result["tool_based"].update({"matches": matches, "total_gt_calls": total_gt, "total_interaction_calls": total_interactions})

        total_correct_calls += matches
        total_gt_calls += total_gt
        total_interaction_calls += total_interactions

        tool_success = False
        if matches == total_gt and total_gt > 0:
            results["tool_based"]["success_count"] += 1
            detailed_result["tool_based"]["success"] = True
            tool_success = True
        elif matches > 0:
            results["tool_based"]["partial_matches"].append({"scenario_id": scenario_id, "matches": matches, "total": total_gt})

        # Final result evaluation
        result_success = False
        try:
            gt_db = get_init_db(scenario, args.scenario_number)
            gt_tool_calls = execute_tool_chain(gt_db, gt_tool_calls, scenario=scenario)
            gt_hash = calculate_db_hash(gt_db)

            interaction_db = get_init_db(scenario, args.scenario_number)
            # New format: {"turn": 0, "calls": [...], "results": [...]}
            # Old format: {"turn": 0, "call": {...}, "result": "..."}
            interaction_only_calls = []
            for entry in interaction_tool_calls:
                if isinstance(entry, dict):
                    if "calls" in entry and isinstance(entry["calls"], list):
                        # New format: expand all calls
                        interaction_only_calls.extend(entry["calls"])
                    elif "call" in entry:
                        # Old format: backward compatible
                        interaction_only_calls.append(entry["call"])
            interaction_only_calls = execute_tool_chain(interaction_db, interaction_only_calls, scenario=scenario)
            interaction_hash = calculate_db_hash(interaction_db)

            detailed_result["result_based"].update({"gt_hash": gt_hash, "interaction_hash": interaction_hash})
            if gt_hash == interaction_hash:
                results["result_based"]["success_count"] += 1
                detailed_result["result_based"]["success"] = True
                result_success = True
        except Exception as e:
            if not silent:
                print(f"Scenario {scenario_id} database operation failed, skipped result evaluation: {e}")

        # Joint success: only when both process-based and result-based evaluations succeed
        if tool_success and result_success:
            results["joint_success"]["success_count"] += 1
            detailed_result["joint_success"] = True

        results["detailed_results"].append(detailed_result)

    # Calculate rates
    if results["valid_scenarios"] > 0:
        results["tool_based"]["success_rate"] = results["tool_based"]["success_count"] / results["valid_scenarios"]
        results["result_based"]["success_rate"] = results["result_based"]["success_count"] / results["valid_scenarios"]
        results["joint_success"]["success_rate"] = results["joint_success"]["success_count"] / results["valid_scenarios"]

    # Micro tool call success rate: use actual evaluated task count as denominator
    task_count = len(results["detailed_results"])  # Actual number of evaluated tasks
    results["micro_tool_stats"].update({
        "total_correct_calls": total_correct_calls,
        "total_ground_truth_calls": total_gt_calls,
        "total_interaction_calls": total_interaction_calls,
        "task_count": task_count,  # Actual number of evaluated tasks
        "micro_accuracy": total_correct_calls / total_gt_calls if total_gt_calls > 0 else 0.0,
        # Per-task tool call accuracy (average)
        "avg_task_accuracy": sum(d["tool_based"]["matches"] / d["tool_based"]["total_gt_calls"]
                                  for d in results["detailed_results"]
                                  if d["tool_based"]["total_gt_calls"] > 0) / task_count if task_count > 0 else 0.0
    })

    if valid_interaction_count > 0:
        results["performance_metrics"]["avg_user_response_time"] = total_user_response_time / valid_interaction_count
        results["performance_metrics"]["avg_agent_response_time"] = total_agent_response_time / valid_interaction_count
        results["performance_metrics"]["avg_tokens_consumed"] = total_tokens_consumed / valid_interaction_count
        results["performance_metrics"]["avg_rounds_count"] = total_rounds_count / valid_interaction_count
        results["performance_metrics"]["avg_input_tokens"] = total_input_tokens / valid_interaction_count
        results["performance_metrics"]["avg_output_tokens"] = total_output_tokens / valid_interaction_count
        results["performance_metrics"]["avg_tool_calls_count"] = total_tool_calls_count / valid_interaction_count
    for key in USER_PERFORMANCE_KEYS:
        count = user_performance_counts[key]
        results["performance_metrics"]["user_performance_sample_counts"][key] = count
        if count > 0:
            results["performance_metrics"]["avg_user_performance"][key] = (
                total_user_performance[key] / count
            )

    # A result file is complete only when every selected ground-truth task has a
    # valid interaction entry. Aggregate accuracy must not include partial files.
    results["is_complete"] = (
        results["total_scenarios"] > 0
        and results["valid_scenarios"] == results["total_scenarios"]
        and not results["invalid_scenarios"]
    )

    return results


# ===================== Report Printing =====================
def print_evaluation_report(results):
    print("=" * 60)
    print("Interaction Success Rate Evaluation Report")
    print("=" * 60)
    print(f"Total scenarios: {results['total_scenarios']}")
    print(f"Valid evaluation scenarios: {results['valid_scenarios']}")
    print(f"Invalid skipped scenarios: {len(results['invalid_scenarios'])}")
    if results["invalid_scenarios"]:
        print("Skipped invalid samples:")
        for item in results["invalid_scenarios"]:
            print(f"  - Scenario {item['scenario_id']}: {item['reason']}")
    print()

    print("1. Tool-based evaluation:")
    print(f"   Successful scenarios: {results['tool_based']['success_count']}")
    print(f"   Success rate: {results['tool_based']['success_rate']:.2%}")
    if results['tool_based']['partial_matches']:
        print("   Partially matched scenarios:")
        for m in results['tool_based']['partial_matches']:
            print(f"     Scenario {m['scenario_id']}: {m['matches']}/{m['total']}")
    print()

    print("2. Result-based evaluation:")
    print(f"   Successful scenarios: {results['result_based']['success_count']}")
    print(f"   Success rate: {results['result_based']['success_rate']:.2%}\n")

    print("3. Joint success rate (process + result dual evaluation):")
    print(f"   Successful scenarios: {results['joint_success']['success_count']}")
    print(f"   Success rate: {results['joint_success']['success_rate']:.2%}\n")

    print("4. Per-task tool call detailed statistics:")
    for d in results['detailed_results']:
        print(f"   Scenario {d['scenario_id']}: correct {d['tool_based']['matches']}/{d['tool_based']['total_gt_calls']}")

    print("\n5. Micro tool call success rate:")
    print(f"   Evaluated tasks: {results['micro_tool_stats']['task_count']}")
    print(f"   Total correct calls: {results['micro_tool_stats']['total_correct_calls']}")
    print(f"   Total ground truth calls: {results['micro_tool_stats']['total_ground_truth_calls']}")
    print(f"   Overall accuracy: {results['micro_tool_stats']['micro_accuracy']:.2%}")
    print(f"   Average task accuracy: {results['micro_tool_stats']['avg_task_accuracy']:.2%}")

    print("\n6. Overall performance metrics:")
    perf = results.get('performance_metrics', {})
    print(f"   Avg user response time: {perf.get('avg_user_response_time', 0):.2f} seconds")
    print(f"   Avg agent response time: {perf.get('avg_agent_response_time', 0):.2f} seconds")
    print(f"   Avg tokens consumed: {perf.get('avg_tokens_consumed', 0):.0f}")
    print(f"   Avg conversation rounds: {perf.get('avg_rounds_count', 0):.2f}")
    print(f"   Avg input tokens: {perf.get('avg_input_tokens', 0):.0f}")
    print(f"   Avg output tokens: {perf.get('avg_output_tokens', 0):.0f}")
    print(f"   Avg tool calls: {perf.get('avg_tool_calls_count', 0):.2f}")
    print("   Simulated-user metric averages:")
    user_perf_avg = perf.get("avg_user_performance", {})
    user_perf_counts = perf.get("user_performance_sample_counts", {})
    for key in USER_PERFORMANCE_KEYS:
        print(
            f"     {key}: {user_perf_avg.get(key, 0):.2f} "
            f"(n={user_perf_counts.get(key, 0)})"
        )


# ===================== Main Function =====================
def main():
    import os

    parser = argparse.ArgumentParser(description="evaluation script")
    parser.add_argument("--model_name", type=str, default="gemini-3.1-pro-preview", help="Model name (subdirectory under results folder)")
    parser.add_argument("--num_samples", type=int, default=0, help="Number of samples per scenario to test, 0 means test all samples")
    parser.add_argument(
        "--include_partial",
        action="store_true",
        help=(
            "Include every valid trajectory from incomplete result files in "
            "aggregate metrics. Per-file completeness is still reported."
        ),
    )
    # Configurable I/O roots. Defaults preserve the original behaviour
    # (reading ../results/{model} and writing ../eval_result/{model}).
    # Pass --results_root ../GPT_user_results --output_root ../GPT_user_eval_result
    # to evaluate the GPT-user run instead.
    parser.add_argument("--results_root", type=str, default="../results",
                        help="Root directory holding per-model result subdirs (default: ../results)")
    parser.add_argument("--output_root", type=str, default="../eval_result",
                        help="Root directory for per-model eval output (default: ../eval_result)")
    args = parser.parse_args()

    model_name = args.model_name
    num_samples = args.num_samples
    results_dir = os.path.join(args.results_root, model_name)

    if not os.path.exists(results_dir):
        print(f"Error: result directory '{results_dir}' does not exist")
        return

    # Ensure output directory exists
    output_dir = os.path.join(args.output_root, model_name)
    os.makedirs(output_dir, exist_ok=True)

    # Get all JSON files
    json_files = [f for f in os.listdir(results_dir) if f.endswith('.json')]

    if not json_files:
        print(f"Error: no JSON files found in directory '{results_dir}'")
        return

    supported_result_files = {
        filename for filename in json_files
        if parse_result_filename(filename) is not None
    }
    unsupported_result_files = sorted(set(json_files) - supported_result_files)
    expected_result_files = {
        f"{scenario}{number}_{mode}.json"
        for scenario, (minimum, maximum) in SCENARIO_NUMBER_RANGES.items()
        for number in range(minimum, maximum + 1)
        for mode in ("easy", "hard", "static")
    }
    missing_result_files = sorted(expected_result_files - supported_result_files)
    benchmark_total_tasks = 0
    for scenario, (minimum, maximum) in SCENARIO_NUMBER_RANGES.items():
        for number in range(minimum, maximum + 1):
            ground_truth_path = os.path.join(
                os.path.dirname(__file__), '..', 'scenarios', 'final',
                f'{scenario}{number}.json'
            )
            with open(ground_truth_path, 'r', encoding='utf-8') as stream:
                benchmark_total_tasks += len(json.load(stream)) * 3

    print(f"Found {len(json_files)} result files, starting evaluation...\n")

    # Aggregate all results
    all_results = []

    for json_file in sorted(json_files):
        parsed_filename = parse_result_filename(json_file)
        if parsed_filename is None:
            print(f"Skipping unsupported result filename: {json_file}")
            continue
        scenario_prefix, scenario_number, user_mode = parsed_filename

        ground_truth_file = os.path.join(
            os.path.dirname(__file__), '..', 'scenarios', 'final',
            f'{scenario_prefix}{scenario_number}.json'
        )
        interaction_log_file = f"{results_dir}/{json_file}"

        # Check if ground truth file exists
        if not os.path.exists(ground_truth_file):
            print(f"Skipped: ground truth file not found '{ground_truth_file}'")
            continue

        print(f"Evaluating: {json_file}...", end=" ")

        try:
            results = evaluate_interaction_success(
                ground_truth_file,
                interaction_log_file,
                scenario=scenario_prefix,
                args=argparse.Namespace(scenario_number=scenario_number),
                silent=True,
                num_samples=num_samples
            )

            # Save per-file evaluation results
            output_file = f"{output_dir}/{json_file.replace('.json', '_eval.json')}"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

            print(f"Evaluation results saved to {output_file}")

            # Print brief report (success rates only)
            print(f"Valid samples: {results['valid_scenarios']}/{results['total_scenarios']}, "
                  f"Tool success rate: {results['tool_based']['success_rate']:.2%}, "
                  f"Result success rate: {results['result_based']['success_rate']:.2%}, "
                  f"Joint success rate: {results['joint_success']['success_rate']:.2%}")
            included_in_summary = results["is_complete"] or (
                args.include_partial and results["valid_scenarios"] > 0
            )
            if not included_in_summary:
                print("Excluded from aggregate accuracy: result file is incomplete")
            elif not results["is_complete"]:
                print("Included available trajectories from incomplete result file")

            performance = results["performance_metrics"]

            all_results.append({
                "file": json_file,
                "scenario": scenario_prefix,
                "scenario_number": scenario_number,
                "mode": user_mode,
                "total_scenarios": results["total_scenarios"],
                "valid_scenarios": results["valid_scenarios"],
                "is_complete": results["is_complete"],
                "included_in_summary": included_in_summary,
                "tool_based_success_rate": results["tool_based"]["success_rate"],
                "result_based_success_rate": results["result_based"]["success_rate"],
                "joint_success_rate": results["joint_success"]["success_rate"],
                "micro_accuracy": results["micro_tool_stats"]["micro_accuracy"],
                "avg_task_accuracy": results["micro_tool_stats"]["avg_task_accuracy"],
                "avg_user_response_time": performance["avg_user_response_time"],
                "avg_agent_response_time": performance["avg_agent_response_time"],
                "avg_tokens_consumed": performance["avg_tokens_consumed"],
                "avg_rounds_count": performance["avg_rounds_count"],
                "avg_input_tokens": performance["avg_input_tokens"],
                "avg_output_tokens": performance["avg_output_tokens"],
                "avg_tool_calls_count": performance["avg_tool_calls_count"],
                "avg_user_performance": performance["avg_user_performance"],
                "user_performance_sample_counts": performance["user_performance_sample_counts"],
            })

        except Exception as e:
            print(f"Evaluation failed {json_file}: {e}")
            all_results.append({
                "file": json_file,
                "error": str(e)
            })

    # Print summary report
    print("\n" + "="*120)
    print("Evaluation Summary Report")
    print("="*120)
    if num_samples > 0:
        print(f"Sample limit: first {num_samples} samples per scenario")
    else:
        print("Sample limit: test all samples")
    print(f"{'File':<40} {'Scenario':<12} {'Num':<6} {'Mode':<8} {'Valid':<10} {'Tool Rate':<10} {'Result Rate':<10} {'Joint Rate':<10}")
    print("-"*120)

    for r in all_results:
        if "error" in r:
            print(f"{r['file']:<40} Error: {r['error']}")
        else:
            valid_str = f"{r.get('valid_scenarios', '?')}/{r.get('total_scenarios', '?')}"
            print(f"{r['file']:<40} {r['scenario']:<12} {r['scenario_number']:<6} {r['mode']:<8} "
                  f"{valid_str:<10} "
                  f"{r['tool_based_success_rate']:>8.2%}   {r['result_based_success_rate']:>8.2%}   "
                  f"{r['joint_success_rate']:>8.2%}")

    # Calculate average success rates
    valid_results = [
        r for r in all_results
        if "error" not in r and r.get("included_in_summary", False)
    ]
    incomplete_results = [
        r for r in all_results
        if "error" not in r and not r.get("is_complete", False)
    ]
    excluded_incomplete_results = [
        r for r in incomplete_results
        if not r.get("included_in_summary", False)
    ]
    included_partial_results = [
        r for r in incomplete_results
        if r.get("included_in_summary", False)
    ]
    if excluded_incomplete_results:
        print(
            "Excluded incomplete files from aggregate accuracy: "
            + ", ".join(r["file"] for r in excluded_incomplete_results)
        )
    if included_partial_results:
        print(
            "Included valid trajectories from incomplete files: "
            + ", ".join(r["file"] for r in included_partial_results)
        )
    if valid_results:
        total_valid = sum(r["valid_scenarios"] for r in valid_results)
        total_tasks = sum(r["total_scenarios"] for r in valid_results)

        def task_weighted_average(field):
            return sum(
                r[field] * r["valid_scenarios"] for r in valid_results
            ) / total_valid

        avg_tool_success = task_weighted_average("tool_based_success_rate")
        avg_result_success = task_weighted_average("result_based_success_rate")
        avg_joint_success = task_weighted_average("joint_success_rate")
        avg_micro_accuracy = task_weighted_average("micro_accuracy")
        avg_task_accuracy = task_weighted_average("avg_task_accuracy")
        avg_user_response_time = task_weighted_average("avg_user_response_time")
        avg_agent_response_time = task_weighted_average("avg_agent_response_time")
        avg_tokens_consumed = task_weighted_average("avg_tokens_consumed")
        avg_rounds_count = task_weighted_average("avg_rounds_count")
        avg_input_tokens = task_weighted_average("avg_input_tokens")
        avg_output_tokens = task_weighted_average("avg_output_tokens")
        avg_tool_calls_count = task_weighted_average("avg_tool_calls_count")

        avg_user_performance = {}
        user_performance_sample_counts = {}
        for key in USER_PERFORMANCE_KEYS:
            count = sum(
                r["user_performance_sample_counts"].get(key, 0)
                for r in valid_results
            )
            user_performance_sample_counts[key] = count
            avg_user_performance[key] = (
                sum(
                    r["avg_user_performance"].get(key, 0.0)
                    * r["user_performance_sample_counts"].get(key, 0)
                    for r in valid_results
                ) / count
                if count > 0 else 0.0
            )

        print("-"*120)
        print(f"Average success rates: tool-based={avg_tool_success:.2%}, result-based={avg_result_success:.2%}, joint={avg_joint_success:.2%}")
        print(f"Micro tool calls: overall accuracy={avg_micro_accuracy:.2%}, avg task accuracy={avg_task_accuracy:.2%}")
        weighting = (
            "all available valid trajectories"
            if args.include_partial else "complete files only"
        )
        print(f"   [weighting] {weighting}: tasks={total_valid}/{total_tasks}")
        print(
            f"   [benchmark coverage] tasks={total_valid}/{benchmark_total_tasks} "
            f"({total_valid / benchmark_total_tasks:.2%})"
        )
        print()
        print("Overall performance averages:")
        print(f"   Avg user response time: {avg_user_response_time:.2f}s")
        print(f"   Avg agent response time: {avg_agent_response_time:.2f}s")
        print(f"   Avg tokens consumed: {avg_tokens_consumed:.0f}")
        print(f"   Avg conversation rounds: {avg_rounds_count:.2f}")
        print(f"   Avg input tokens: {avg_input_tokens:.0f}")
        print(f"   Avg output tokens: {avg_output_tokens:.0f}")
        print(f"   Avg tool calls: {avg_tool_calls_count:.2f}")
        print()
        print("Simulated-user metric averages:")
        for key in USER_PERFORMANCE_KEYS:
            print(
                f"   {key}: {avg_user_performance[key]:.4f} "
                f"(n={user_performance_sample_counts[key]})"
            )

    # Save summary results
    summary_file = f"{output_dir}/summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({"all_results": all_results, "summary": {
            "total_files": len(all_results),
            "valid_files": len(valid_results),
            "incomplete_files": len(incomplete_results),
            "included_partial_files": [r["file"] for r in included_partial_results],
            "excluded_incomplete_files": [r["file"] for r in excluded_incomplete_results],
            "num_samples": num_samples,
            "include_partial": args.include_partial,
            "overall_weighting": (
                "all_available_valid_trajectories_task_weighted"
                if args.include_partial else "complete_files_only_task_weighted"
            ),
            "total_valid_scenarios": total_valid if valid_results else 0,
            "total_original_tasks": total_tasks if valid_results else 0,
            "trajectory_coverage_rate": (
                total_valid / total_tasks
                if valid_results and total_tasks > 0 else 0
            ),
            "benchmark_total_tasks": benchmark_total_tasks,
            "benchmark_coverage_rate": (
                total_valid / benchmark_total_tasks
                if valid_results and benchmark_total_tasks > 0 else 0
            ),
            "missing_result_files": missing_result_files,
            "unsupported_result_files": unsupported_result_files,
            "avg_tool_based_success_rate": avg_tool_success if valid_results else 0,
            "avg_result_based_success_rate": avg_result_success if valid_results else 0,
            "avg_joint_success_rate": avg_joint_success if valid_results else 0,
            "micro_accuracy": avg_micro_accuracy if valid_results else 0,
            "avg_task_accuracy": avg_task_accuracy if valid_results else 0,
            "avg_user_response_time": avg_user_response_time if valid_results else 0,
            "avg_agent_response_time": avg_agent_response_time if valid_results else 0,
            "avg_tokens_consumed": avg_tokens_consumed if valid_results else 0,
            "avg_rounds_count": avg_rounds_count if valid_results else 0,
            "avg_input_tokens": avg_input_tokens if valid_results else 0,
            "avg_output_tokens": avg_output_tokens if valid_results else 0,
            "avg_tool_calls_count": avg_tool_calls_count if valid_results else 0,
            "avg_user_performance": avg_user_performance if valid_results else {
                key: 0.0 for key in USER_PERFORMANCE_KEYS
            },
            "user_performance_sample_counts": user_performance_sample_counts if valid_results else {
                key: 0 for key in USER_PERFORMANCE_KEYS
            },
        }}, f, ensure_ascii=False, indent=2)
    print(f"\nSummary results saved to {summary_file}")


if __name__ == "__main__":
    main()
