#!/usr/bin/env python3
"""Convert retail_init_new.py to retail_init.py with correct format."""

import sys
sys.path.insert(0, '.')

def parse_cart_item(item_str):
    """Parse cart item string like 'Product Name*2' into dict"""
    if isinstance(item_str, dict):
        return item_str

    item_str = str(item_str).strip()
    if '*' in item_str:
        parts = item_str.rsplit('*', 1)
        return {
            "product_name": parts[0].strip().lower(),
            "quantity": int(parts[1]) if parts[1].isdigit() else 1
        }
    else:
        return {
            "product_name": item_str.lower(),
            "quantity": 1
        }

def convert_user_carts(raw_carts):
    """Convert raw user_carts to expected format"""
    converted = []
    for cart in raw_carts:
        user_id = cart.get('user_id')
        raw_items = cart.get('items', [])

        parsed_items = []
        for item in raw_items:
            if isinstance(item, str) and '\n' in item:
                for line in item.split('\n'):
                    if line.strip():
                        parsed_items.append(parse_cart_item(line.strip()))
            else:
                parsed_items.append(parse_cart_item(item))

        converted.append({
            "user_id": user_id,
            "items": parsed_items
        })
    return converted

def convert_user_shopping_lists(raw_lists):
    """Convert raw user_shopping_lists to expected format"""
    converted = []
    for sl in raw_lists:
        user_id = sl.get('user_id')
        raw_items = sl.get('items', [])

        parsed_items = []
        for item in raw_items:
            if isinstance(item, str) and '\n' in item:
                for line in item.split('\n'):
                    if line.strip():
                        parsed_items.append(parse_cart_item(line.strip()))
            else:
                parsed_items.append(parse_cart_item(item))

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

# Get all retail_init_data variables
namespace = {}
exec(open('retail_init_new.py', 'r', encoding='utf-8').read(), namespace)

data_vars = {}
for key in namespace:
    if key.startswith('retail_init_data') and isinstance(namespace[key], dict):
        data_vars[key] = namespace[key].copy()

# Convert user_carts and user_shopping_lists for each dataset
for var_name, data in data_vars.items():
    has_carts = 'user_carts' in data
    has_lists = 'user_shopping_lists' in data
    if has_carts:
        data['user_carts'] = convert_user_carts(data['user_carts'])
    if has_lists:
        data['user_shopping_lists'] = convert_user_shopping_lists(data['user_shopping_lists'])

# Generate output
output_lines = []
for i in range(1, 11):
    var_name = f"retail_init_data{i}"
    if var_name in data_vars:
        data = data_vars[var_name]
        formatted_data = format_value(data, 0)
        output_lines.append(f"{var_name} = {formatted_data}")

# Write file
with open('retail_init.py', 'w', encoding='utf-8') as f:
    f.write("\n".join(output_lines))

print("retail_init.py has been updated successfully!")
for i in range(1, 11):
    var_name = f"retail_init_data{i}"
    if var_name in data_vars:
        data = data_vars[var_name]
        product_count = len(data.get('products', []))
        cart_count = len(data.get('user_carts', []))
        list_count = len(data.get('user_shopping_lists', []))
        print(f"  {var_name}: {product_count} products, {cart_count} carts, {list_count} shopping lists")