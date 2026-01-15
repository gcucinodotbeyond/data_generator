import json
from pathlib import Path
import re
import sys

def load_json_list(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return []

def save_json_list(filepath, data):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(sorted(list(set(data))), f, indent=2, ensure_ascii=False)
    print(f"Saved {len(data)} items to {filepath.name}")

def clean_corpus():
    base_dir = Path(__file__).parent.parent / "resources" / "corpus"
    
    # Load all relevant files
    confirmations_path = base_dir / "confirmations.json"
    farewells_path = base_dir / "farewells.json"
    chitchat_path = base_dir / "chitchat.json"
    purchase_path = base_dir / "purchase_intents.json"
    
    # Start with existing data
    confirmations = load_json_list(confirmations_path)
    farewells = load_json_list(farewells_path)
    chitchat = load_json_list(chitchat_path) if chitchat_path.exists() else []
    
    # Also grab "refinements" as they might get mixed in
    refinements_path = base_dir / "refinements.json"
    refinements = load_json_list(refinements_path) if refinements_path.exists() else []

    print(f"Initial counts: Confirmations={len(confirmations)}, Farewells={len(farewells)}, ChitChat={len(chitchat)}")

    # Pool everything to re-sort
    pool = confirmations + farewells + chitchat
    pool = list(set(pool)) # Unique
    
    new_confirmations = []
    new_farewells = []
    new_chitchat = []
    new_refinements = [] # If something looks like a refinement

    # Keywords
    farewell_keywords = ["arrivederci", "a presto", "ciao", "buona serata", "buona giornata", "addio", "alla prossima", "buonanotte"]
    confirmation_keywords = ["ok", "va bene", "perfetto", "ottimo", "sì", "si ", "benissimo", "bene", "d'accordo", "capito", "chiaro", "grazie"]
    
    # Heuristics
    for text in pool:
        lower = text.lower().strip()
        words = lower.split()
        num_words = len(words)
        
        is_farewell = False
        is_confirmation = False
        
        # Check Farewell
        if any(k in lower for k in farewell_keywords):
            # Special case: "Grazie" alone is confirmation, but "Grazie e buona serata" is farewell
            is_farewell = True
            
        # Check Confirmation
        if not is_farewell:
            # Starts with confirmation keyword?
            if any(lower.startswith(k) for k in confirmation_keywords):
                is_confirmation = True
            
            # Short "Grazie" or "Grazie mille" is confirmation
            if "grazie" in lower and num_words <= 5:
                is_confirmation = True
                
        # Classify
        if is_farewell:
            new_farewells.append(text)
        elif is_confirmation:
            # If it's very long, it might be chitchat beginning with confirmation
            # "Sì, ma oggi piove tanto e sono triste..." -> ChitChat
            if num_words > 10:
                new_chitchat.append(text)
            else:
                new_confirmations.append(text)
        else:
            # Neither?
            # e.g. "Piove molto oggi" -> ChitChat
            # e.g. "Voglio un biglietto" -> Purchase (shouldn't be here ideally)
            if "biglietto" in lower or "prenotare" in lower or "acquisto" in lower:
                 # It's a purchase intent leaked here?
                 pass 
            else:
                 new_chitchat.append(text)

    # Save Back
    save_json_list(confirmations_path, new_confirmations)
    save_json_list(farewells_path, new_farewells)
    save_json_list(chitchat_path, new_chitchat)

if __name__ == "__main__":
    clean_corpus()
