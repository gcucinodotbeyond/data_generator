import json

# Load line 9
lines = open('data/predataset/dialogue_dataset.jsonl', 'r', encoding='utf-8').readlines()
d = json.loads(lines[9])
m = d['messages'][24]

print(f"Role: {m['role']}")
print(f"Content type: {type(m['content'])}")
print(f"Content: {m['content']}")

# Also show context - messages around it
print("\n--- Context ---")
for i in range(22, 27):
    if i < len(d['messages']):
        msg = d['messages'][i]
        role = msg['role']
        content = msg.get('content')
        if content:
            print(f"M{i} [{role}] {str(content)[:70]}")
        else:
            tc = msg.get('tool_calls')
            if tc:
                print(f"M{i} [{role}] TOOL: {tc[0]['function']['name']}")
