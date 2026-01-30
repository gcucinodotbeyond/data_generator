import json

with open('data/hydrated-dataset/dialogue_dataset.jsonl', 'r', encoding='utf-8') as f:
    d = json.loads(f.readline())

found_issues = []
for i, m in enumerate(d['messages']):
    content = m.get('content', '')
    if content and ('generation failed' in content.lower() if content else False):
        found_issues.append((i, m['role'], content[:80]))

print("=== Checking for generation failures ===")
if found_issues:
    for issue in found_issues:
        print(f"  Line {issue[0]}: [{issue[1]}] {issue[2]}")
else:
    print("  No generation failures found!")

print("\n=== First 15 messages ===")
for i, m in enumerate(d['messages'][1:16]):
    role = m['role']
    content = m.get('content')
    if content:
        print(f"  {i+1}. [{role}] {content[:50]}")
    else:
        tc = m.get('tool_calls', [])
        if tc:
            print(f"  {i+1}. [{role}] TOOL: {tc[0]['function']['name']}")
        else:
            print(f"  {i+1}. [{role}] (empty)")

print("\n=== Metadata passengers ===")
for ctx in d['_meta']['contexts'][:3]:
    print(f"  passengers: {ctx['params'].get('passengers')}")
