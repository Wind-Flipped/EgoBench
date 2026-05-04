#!/usr/bin/env python3
"""Convert restaurant_init_new.py to restaurant_init.py with correct format."""

def parse_order_item(item_str):
    """Parse order item string like 'Dish*1\nTiramisu*1' into list of dicts"""
    if isinstance(item_str, dict):
        return [item_str]

    result = []
    item_str = str(item_str).strip()
    # Split by newline to get individual items
    for line in item_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '*' in line:
            parts = line.rsplit('*', 1)
            result.append({
                "dish_name": parts[0].strip().lower(),
                "quantity": int(parts[1]) if parts[1].isdigit() else 1
            })
        else:
            result.append({
                "dish_name": line.lower(),
                "quantity": 1
            })
    return result

def convert_included_dishes(dishes_str):
    """Convert included_dishes string to list of dicts"""
    if isinstance(dishes_str, list):
        return dishes_str  # Already in correct format
    return parse_order_item(dishes_str)

def convert_user_orders(raw_orders):
    """Convert raw user_orders to expected format"""
    converted = []
    for order in raw_orders:
        user_id = order.get('user_id')
        raw_items = order.get('items', [])

        parsed_items = []
        for item in raw_items:
            if isinstance(item, str) and '\n' in item:
                # Item string contains multiple dishes separated by \n
                parsed_items.extend(parse_order_item(item))
            else:
                parsed_items.extend(parse_order_item(item))

        converted.append({
            "user_id": user_id,
            "items": parsed_items
        })
    return converted

def escape_string(s):
    if not isinstance(s, str):
        return s
    s = s.replace('\\', '\\\\')
    s = s.replace('\n', '\\n')
    s = s.replace('\r', '\\r')
    s = s.replace('\t', '\\t')
    s = s.replace('"', '\\"')
    return s

def format_value(value, indent_level=1):
    indent = "  " * indent_level
    next_indent = "  " * (indent_level + 1)

    if isinstance(value, dict):
        if not value:
            return "{}"
        items = []
        for k, v in value.items():
            formatted_v = format_value(v, indent_level + 1)
            items.append(f'{next_indent}"{k}": {formatted_v}')
        return "{\n" + ",\n".join(items) + f"\n{indent}}}"
    elif isinstance(value, list):
        if not value:
            return "[]"
        items = []
        for item in value:
            formatted_item = format_value(item, indent_level + 1)
            items.append(f'{next_indent}{formatted_item}')
        return "[\n" + ",\n".join(items) + f"\n{indent}]"
    elif isinstance(value, str):
        escaped = escape_string(value)
        return f'"{escaped}"'
    elif isinstance(value, bool):
        return "True" if value else "False"
    elif isinstance(value, (int, float)):
        return str(value)
    elif value is None:
        return "None"
    else:
        return repr(value)

# Get all restaurant_init_data variables
namespace = {}
exec(open('restaurant_init_new.py', 'r', encoding='utf-8').read(), namespace)

data_vars = {}
for key in namespace:
    if key.startswith('restaurant_init_data') and isinstance(namespace[key], dict):
        data_vars[key] = namespace[key].copy()

# Convert included_dishes in set_meals and user_orders for each dataset
for var_name, data in data_vars.items():
    if 'set_meals' in data:
        for set_meal in data['set_meals']:
            if 'included_dishes' in set_meal:
                set_meal['included_dishes'] = convert_included_dishes(set_meal['included_dishes'])
    if 'user_orders' in data:
        data['user_orders'] = convert_user_orders(data['user_orders'])

# Generate output
output_lines = []
for var_name in ['restaurant_init_data', 'restaurant_init_data5']:
    if var_name in data_vars:
        data = data_vars[var_name]
        formatted_data = format_value(data, 0)
        output_lines.append(f"{var_name} = {formatted_data}")

# Write file
with open('restaurant_init.py', 'w', encoding='utf-8') as f:
    f.write("\n".join(output_lines))

print("restaurant_init.py has been updated successfully!")
for var_name in ['restaurant_init_data', 'restaurant_init_data5']:
    if var_name in data_vars:
        data = data_vars[var_name]
        dish_count = len(data.get('dishes', []))
        set_meal_count = len(data.get('set_meals', []))
        order_count = len(data.get('user_orders', []))
        print(f"  {var_name}: {dish_count} dishes, {set_meal_count} set meals, {order_count} orders")
