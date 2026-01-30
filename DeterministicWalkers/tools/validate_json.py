import json

files = ['data/predataset/dialogue_dataset.jsonl', 'data/hydrated-dataset/dialogue_dataset.jsonl']
for f in files:
    print(f'=== {f} ===')
    lines = [l for l in open(f, 'r', encoding='utf-8') if l.strip()]
    print(f'  Lines: {len(lines)}')
    for i, line in enumerate(lines):
        try:
            json.loads(line)
        except json.JSONDecodeError as e:
            print(f'  ERROR line {i}: {e}')
            break
    else:
        print('  Syntax: OK')
