import json
import os
import re

def extract_content():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    followups_path = os.path.join(base_dir, 'resources', 'ood_followups.json')
    starters_path = os.path.join(base_dir, 'resources', 'ood_starters.json')
    
    # Check if files exist
    if not os.path.exists(followups_path):
        print(f"Error: {followups_path} not found.")
        return

    with open(followups_path, 'r', encoding='utf-8') as f:
        followups = json.load(f)
        
    core_questions = []
    nuances = {
        "acknowledgement": [], 
        "connector": [], 
        "frustration": [], 
        "polite_request": [] 
    }

    fillers = [
        # Interjections
        "ah", "oh", "beh", "bhè", "mah", "mmm", "mmh", "mhm", "ok", "okay", "vabbè", "vabbeh", 
        "d'accordo", "capito", "capisco", "ottimo", "perfetto", "fantastico", "bene", "grazie",
        "ciao", "buongiorno", "salve", "davvero", "insomma", "uffa", "dai", "arrendo", "basta",
        
        # Connectors
        "allora", "comunque", "invece", "tra l'altro", "a proposito", "quindi", "cioè", 
        "piuttosto", "magari", "forse", "almeno", "così",
        
        # Conjunctions/Particles
        "ma", "e", "però", "no", "sì", "non", "già",
        
        # Verbs (Imperative/Request wrappers)
        "dimmi", "spiegami", "raccontami", "parlami", "consigliami", "aiutami", "diresti",
        "sai", "sapresti", "puoi", "potresti", "riesci a", "vuoi", "vorrei", "volevo",
        "scusa", "scusi", "senti", "senta", "guarda", "ascolta", "vedi",
        "pensavo", "stavo pensando", "ho sentito", "ho letto", "detto", "chidevo",
        
        # Common phrases
        "per caso", "mi sai dire", "mi puoi dire", "ti prego", "per favore", "gentilmente",
        "potete", "può", "dirmi", "mi può dire", "mi sa dire", "mi sapresti dire"
    ]
    
    sorted_fillers = sorted(fillers, key=len, reverse=True)
    
    for item in followups:
        text = item.strip()
        original_text = text
        
        # 1. Split by ellipsis
        parts = text.split("...")
        if len(parts) > 1:
             last_part = parts[-1].strip()
             if len(last_part) > 5:
                 text = last_part
        
        # 2. Iterative Stripping
        changed = True
        while changed:
            changed = False
            
            # Clean non-alphanum start
            text_cleaned = re.sub(r"^[\W_]+", "", text).strip()
            if text_cleaned != text:
                text = text_cleaned
                changed = True
                if not text: break
            
            text_lower = text.lower()
            
            for filler in sorted_fillers:
                pattern = r"^" + re.escape(filler) + r"(\b|[\s\.\?!,])"
                match = re.match(pattern, text_lower)
                if match:
                    remove_len = match.end()
                    text = text[remove_len:].strip()
                    changed = True
                    break 
        
        # Final cleanup
        text = re.sub(r"^[\W_]+", "", text).strip()
        if text:
             text = text[0].upper() + text[1:]
        
        if len(text) < 3:
            text = original_text 

        # Capture Nuance
        if text and text in original_text:
            idx = original_text.find(text)
            if idx > 0:
                prefix = original_text[:idx].strip()
                # Categorize roughly
                p_lower = prefix.lower()
                category = "connector"
                if any(x in p_lower for x in ["ah ok", "capisco", "ottimo", "perfetto", "grazie"]):
                    category = "acknowledgement"
                elif any(x in p_lower for x in ["ma insomma", "ma dai", "non sai niente"]):
                    category = "frustration"
                elif any(x in p_lower for x in ["scusi", "potresti", "gentilmente"]):
                    category = "polite_request"
                
                if prefix and prefix not in nuances[category]:
                    nuances[category].append(prefix)
        
        core_questions.append(text)

    # Dedup
    core_questions = sorted(list(set(core_questions)))

    # Verification Step
    issues = 0
    for q in core_questions:
        if q.startswith("Allora") or q.startswith("Ah ") or q.startswith("Senti ") or q.startswith("Ma "):
            # print(f"WARNING: Leftover prefix in '{q}'")
            issues += 1
    
    if issues > 0:
        print(f"WARNING: {issues} questions still have common prefixes (Allora/Ah/Senti/Ma).")
    
    # Save files
    out_q_path = os.path.join(base_dir, 'resources', 'ood_core_questions.json')
    out_n_path = os.path.join(base_dir, 'resources', 'user_nuances.json')

    with open(out_q_path, 'w', encoding='utf-8') as f:
        json.dump(core_questions, f, indent=2, ensure_ascii=False)
        
    with open(out_n_path, 'w', encoding='utf-8') as f:
        json.dump(nuances, f, indent=2, ensure_ascii=False)
        
    print(f"Extracted {len(core_questions)} clean core questions to {out_q_path}")
    print(f"Extracted usage nuances to {out_n_path}")

if __name__ == "__main__":
    extract_content()
