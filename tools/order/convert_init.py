#!/usr/bin/env python3
"""Convert order_init_new.py to order_init.py with correct format."""

def parse_order_item(item_str):
    """Parse order item string like 'Dish*1\nPasta*2' into list of dicts"""
    if isinstance(item_str, dict):
        return [item_str]

    result = []
    item_str = str(item_str).strip()
    for line in item_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '*' in line:
            parts = line.rsplit('*', 1)
            result.append({
                'dish_name': parts[0].strip().lower(),
                'quantity': int(parts[1]) if parts[1].isdigit() else 1
            })
        else:
            result.append({
                'dish_name': line.lower(),
                'quantity': 1
            })
    return result

def convert_user_orders(raw_orders):
    converted = []
    for order in raw_orders:
        user_id = order.get('user_id')
        for key, value in order.items():
            if key.endswith('_items') and key != 'items':
                restaurant_name = key[:-6]
                parsed_items = parse_order_item(value)
                converted.append({
                    'user_id': user_id,
                    'items': parsed_items,
                    'restaurant_name': restaurant_name
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
    indent = '  ' * indent_level
    next_indent = '  ' * (indent_level + 1)

    if isinstance(value, dict):
        if not value:
            return '{}'
        items = []
        for k, v in value.items():
            formatted_v = format_value(v, indent_level + 1)
            items.append(f'{next_indent}"{k}": {formatted_v}')
        return '{\n' + ',\n'.join(items) + f'\n{indent}}}'
    elif isinstance(value, list):
        if not value:
            return '[]'
        items = []
        for item in value:
            formatted_item = format_value(item, indent_level + 1)
            items.append(f'{next_indent}{formatted_item}')
        return '[\n' + ',\n'.join(items) + f'\n{indent}]'
    elif isinstance(value, str):
        escaped = escape_string(value)
        return f'"{escaped}"'
    elif isinstance(value, bool):
        return 'True' if value else 'False'
    elif isinstance(value, (int, float)):
        return str(value)
    elif value is None:
        return 'None'
    else:
        return repr(value)

namespace = {}
exec(open('order_init_new.py', 'r', encoding='utf-8').read(), namespace)

data_vars = {}
for key in namespace:
    if key.startswith('order_init_data') and isinstance(namespace[key], dict):
        data_vars[key] = namespace[key].copy()

for var_name, data in data_vars.items():
    if 'set_meals' in 
        for set_meal in data['set_meals']:
            if 'included_dishes' in set_meal:
                set_meal['included_dishes'] = parse_order_item(set_meal['included_dishes'])
    if 'user_orders' in 
        data['user_orders'] = convert_user_orders(data['user_orders'])

output_lines = []
for var_name in ['order_init_data']:
    if var_name in data_vars:
        data = data_vars[var_name]
        formatted_data = format_value(data, 0)
        output_lines.append(f'{var_name} = {formatted_data}')

with open('order_init.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output_lines))

print('order_init.py has been updated successfully!')
for var_name in ['order_init_data']:
    if var_name in data_vars:
        data = data_vars[var_name]
        dish_count = len(data.get('dishes', []))
        set_meal_count = len(data.get('set_meals', []))
        order_count = len(data.get('user_orders', []))
        print(f'  {var_name}: {dish_count} dishes, {set_meal_count} set meals, {order_count} orders')
