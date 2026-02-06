import json

print('=== DATASET HEALTH CHECK ===')

# Predataset
with open('data/predataset/dialogue_dataset.jsonl', 'r', encoding='utf-8') as f:
    lines = [l for l in f if l.strip()]
print(f'Predataset dialogues: {len(lines)}')

issues = []
for idx, line in enumerate(lines):
    d = json.loads(line)
    msgs = d.get('messages', [])
    for i, m in enumerate(msgs):
        content = m.get('content', '') or ''
        if isinstance(content, dict):
            issues.append((idx, i, 'DICT_CONTENT'))
        elif isinstance(content, str):
            if 'failed' in content.lower():
                issues.append((idx, i, 'GENERATION_FAILED'))
            if '{{' in content:
                issues.append((idx, i, 'TEMPLATE_SYNTAX'))

print(f'Issues: {len(issues)}')
if issues:
    for x in issues[:5]:
        print(f'  D{x[0]} M{x[1]}: {x[2]}')
else:
    print('  ✓ No issues found!')

# Hydrated check
with open('data/hydrated-dataset/dialogue_dataset.jsonl', 'r', encoding='utf-8') as f:
    hlines = [l for l in f if l.strip()]
print(f'Hydrated dialogues: {len(hlines)}')

# Sample first dialogue
d0 = json.loads(hlines[0])
meta = d0.get('_meta', {})
print(f'Generator Version: {meta.get("generator_version", "N/A")}')
print(f'Scenario: {meta.get("scenario", "N/A")}') 

inter = meta.get('interaction')
if inter:
    print(f'Origin: {inter.get("origin")}')
    print(f'Destination: {inter.get("destination")}')
    print(f'Passengers: {inter.get("passengers")}')
else:
    print("No interaction metadata found.")
