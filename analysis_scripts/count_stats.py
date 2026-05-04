import json
import re
import os

# 1. Count tool numbers
print('=== Tool Count ===')
for scene in ['retail', 'kitchen', 'restaurant', 'order']:
    with open(f'../tools/{scene}/{scene}_tools.json', 'r') as f:
        tools = json.load(f)
        print(f'{scene}: {len(tools)}')

# 2. Count item numbers
print('\n=== Item Count ===')

# Retail
with open('../tools/retail/retail_init.py', 'r') as f:
    content = f.read()
    products = re.findall(r'"name":\s*"([^"]+)"', content)
    print(f'retail: {len(set(products))} products')

# Kitchen
with open('../tools/kitchen/kitchen_init.py', 'r') as f:
    content = f.read()
    if '"recipes"' in content:
        parts = content.split('"recipes"')
        ingredients = len(re.findall(r'"name":\s*"([^"]+)"', parts[0]))
        recipes = len(re.findall(r'"name":\s*"([^"]+)"', parts[1][:10000]))
        print(f'kitchen: {ingredients} ingredients + {recipes} recipes')
    else:
        ingredients = len(re.findall(r'"name":\s*"([^"]+)"', content))
        print(f'kitchen: {ingredients} ingredients')

# Restaurant
with open('../tools/restaurant/restaurant_init.py', 'r') as f:
    content = f.read()
    if '"set_meals"' in content:
        parts = content.split('"set_meals"')
        dishes = len(re.findall(r'"name":\s*"([^"]+)"', parts[0]))
        print(f'restaurant: {dishes} dishes')
    else:
        dishes = len(re.findall(r'"name":\s*"([^"]+)"', content))
        print(f'restaurant: {dishes} dishes')

# Order
with open('../tools/order/order_init.py', 'r') as f:
    content = f.read()
    if '"set_meals"' in content:
        parts = content.split('"set_meals"')
        dishes = len(re.findall(r'"name":\s*"([^"]+)"', parts[0]))
        print(f'order: {dishes} dishes')
    else:
        dishes = len(re.findall(r'"name":\s*"([^"]+)"', content))
        print(f'order: {dishes} dishes')

# 3. Count scenario files
print('\n=== Scenario File Statistics ===')
scenarios_dir = '../scenarios/final'

# Group by scenario
scene_stats = {}
for filename in sorted(os.listdir(scenarios_dir)):
    if filename.endswith('.json'):
        # Extract scenario name (remove numeric suffix)
        scene_name = re.match(r'([a-z]+)', filename).group(1)

        if scene_name not in scene_stats:
            scene_stats[scene_name] = {'videos': set(), 'tasks': 0, 'files': 0}

        filepath = os.path.join(scenarios_dir, filename)
        with open(filepath, 'r') as f:
            data = json.load(f)
            scene_stats[scene_name]['tasks'] += len(data)
            scene_stats[scene_name]['files'] += 1
            for item in data:
                if 'image_path' in item and item['image_path']:
                    scene_stats[scene_name]['videos'].add(item['image_path'])

for scene, stats in sorted(scene_stats.items()):
    print(f"{scene}: videos={len(stats['videos'])}, tasks={stats['tasks']}, scenarios={stats['files']}")
