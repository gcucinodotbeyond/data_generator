import json
import os
import re

path = r'c:\Users\gcucino\Desktop\data_generator\DeterministicWalkers\data\predataset\dialogue_dataset.jsonl'
if not os.path.exists(path):
    print("File not found")
    exit()

followup_prefixes = ["Ah", "Senti", "Senta", "Invece", "A proposito", "Ma allora", "Allora", "E invece", "Capisco", "Capito", "D'accordo", "Ok", "Okay", "Bene", "Perfetto", "Grazie", "Certo", "Sì", "Si"]
followup_pattern = re.compile(r'^(' + '|'.join(followup_prefixes) + r')\b', re.IGNORECASE)

with open(path, 'r', encoding='utf-8') as f:
    for line_idx, line in enumerate(f):
        data = json.loads(line)
        msgs = data['messages']
        
        # Check first user message (skip system)
        first_user = None
        for m in msgs:
            if m['role'] == 'user':
                first_user = m['content']
                break
        
        # Check if first user is OOD
        is_ood_start = False
        if first_user:
            # Simple check: the assistant response to the first user is an ood_redirect
            # (In dialogue.py, if OOD start, assistant redirects immediately)
            for i, m in enumerate(msgs):
                if m['role'] == 'user' and m['content'] == first_user:
                    if i + 1 < len(msgs) and msgs[i+1]['role'] == 'assistant' and \
                       ("Mi dispiace" in (msgs[i+1].get('content') or "") or "Non posso" in (msgs[i+1].get('content') or "") or "Mi spiace" in (msgs[i+1].get('content') or "")):
                        is_ood_start = True
                        break
        
        if is_ood_start:
            is_followup = followup_pattern.match(first_user)
            print(f"Line {line_idx} - OOD START: {first_user[:50]}... -> Followup Prefix: {bool(is_followup)}")

        # Check for OOD interruptions
        for i in range(1, len(msgs)):
            m = msgs[i]
            if m['role'] == 'user':
                # Check if it's an interruption redirected by assistant
                if i + 1 < len(msgs) and msgs[i+1]['role'] == 'assistant' and \
                   ("Mi dispiace" in (msgs[i+1].get('content') or "") or "Non posso" in (msgs[i+1].get('content') or "") or "Mi spiace" in (msgs[i+1].get('content') or "")):
                    # If this is NOT the first user message, it's an interruption
                    if m['content'] != first_user:
                        is_followup = followup_pattern.match(m['content'])
                        print(f"Line {line_idx} - OOD INTERRUPT: {m['content'][:50]}... -> Followup Prefix: {bool(is_followup)}")
