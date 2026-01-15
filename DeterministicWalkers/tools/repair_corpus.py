import json
from pathlib import Path
import sys

def repair_greetings(corpus_dir: Path):
    filepath = corpus_dir / "greetings.json"
    print(f"Repairing {filepath.name}...")
    
    greetings = [
        "Ciao", "Buongiorno", "Buonasera", "Salve", "Hey", 
        "Vorrei informazioni", "Senta scusi", "Buondì", 
        "Ciao, come va?", "Buonasera, mi serve un aiuto",
        "Salve, vorrei prenotare", "Ehilà", "Buon pomeriggio"
    ]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(greetings, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Populated with {len(greetings)} greetings.")

def repair_rude_phrases(corpus_dir: Path):
    filepath = corpus_dir / "rude_phrases.json"
    print(f"Repairing {filepath.name}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return

    # Filter out likely responses
    bad_prefixes = ["Sì", "Si", "No", "Ok", "Va bene", "Grazie", "Perfetto", "Bene", "Ah", "Comunque", "Ma poi"]
    clean_data = []
    
    for phrase in data:
        is_bad = False
        phrase_clean = phrase.strip()
        for prefix in bad_prefixes:
            if phrase_clean.startswith(prefix + " ") or phrase_clean.startswith(prefix + ",") or phrase_clean.startswith(prefix + "."):
                is_bad = True
                break
        
        if not is_bad:
            clean_data.append(phrase)
            
    # Remove duplicates
    clean_data = sorted(list(set(clean_data)))
    
    if len(clean_data) < 5:
        print(f"  ⚠️ Warning: filtering left very few items ({len(clean_data)}). Keeping original for now.")
        return

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Filtered down to {len(clean_data)} items (was {len(data)}).")

def repair_search_queries(corpus_dir: Path):
    filepath = corpus_dir / "search_queries.json"
    print(f"Repairing {filepath.name}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ❌ Error reading file: {e}")
        return

    bad_prefixes = ["Ah ", "Allora ", "Ok ", "Comunque ", "Sì ", "Si ", "No ", "E ", "Scusa ", "Grazie ", "Perfetto ", "Bene ", "Adesso ", "Ora ", "Capito", "Affascinante", "Interessante", "Giusto", "Eh ", "Mah ", "Beh ", "Mmm", "Mamma mia", "Oddio", "Madonna"]
    bad_substrings = ["capito", "capisco", "torniamo"]

    clean_data = []
    
    for query in data:
        is_bad = False
        q_clean = query.strip()
        
        # Check prefixes
        for bp in bad_prefixes:
             if q_clean.startswith(bp):
                 is_bad = True
                 # But verify if it's valid urgency "Madonna, che prezzi!" -> might be valid if it initiates.
                 # Actually, "Madonna, pure 89 euro!" is a reaction to a price, so it's a follow-up.
                 break
        
        # Check substrings
        if not is_bad:
            for bs in bad_substrings:
                if bs in q_clean.lower():
                    is_bad = True
                    break
        
        if not is_bad:
             # Additional check: must contain at least one entity placeholder or be generic
             if "{" in q_clean or "treno" in q_clean.lower() or "biglietto" in q_clean.lower():
                 clean_data.append(query)
                 
    # Remove duplicates
    clean_data = sorted(list(set(clean_data)))

    if len(clean_data) < 50:
         print(f"  ⚠️ Warning: filtering aggressively left only {len(clean_data)} items. Aborting save.")
         return

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(clean_data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Filtered down to {len(clean_data)} items (was {len(data)}).")

def main():
    corpus_dir = Path(__file__).parent.parent / "resources" / "corpus"
    if not corpus_dir.exists():
        print("Corpus directory not found.")
        sys.exit(1)
        
    repair_greetings(corpus_dir)
    repair_rude_phrases(corpus_dir)
    repair_search_queries(corpus_dir)

if __name__ == "__main__":
    main()
