
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
CORPUS_DIR = BASE_DIR / "resources" / "corpus"
REFINEMENTS_PATH = CORPUS_DIR / "refinements.json"
SEARCH_PATH = CORPUS_DIR / "search_queries.json"

# List of words/phrases that strongly indicate an opening message
OPENING_INDICATORS = [
    "ciao", "salve", "buongiorno", "buonasera", "ehi", "hey",
    "devo andare", "vorrei andare", "mi serve", "cerco", 
    "voglio", "acquista", "biglietto", "treno per", "treni per",
    "per {destination}", "scusa", "senti", "ascolta", "capito", "bene", "ottimo",
    "ah ", "allora ", "perfetto", "fantastico", "bah", "basta", "benissimo", "interessante",
    "ok", "grazie", "top", "giusto", "certo", "esatto"
]

# Words that, if present anywhere, suggest it's a full NEW search, not a refinement
INTENT_BLACKLIST = [
    "devo andare", "vorrei andare", "voglio andare", "mi serve", "ho bisogno",
    "cerchiamo", "vediamo", "cercami", "trovami", "ci sono treni", "che treni ci sono"
]

# List of words/phrases typical for refinements (change of plan, modification)
# or short phrases
REFINEMENT_INDICATORS = [
    "no", "invece", "anzi", "solo", "meglio", "preferisco", 
    "dopo", "prima", "tardi", "presto", "mattina", "sera", "pomeriggio",
    "cambio", "classe", "posto", "senza", "con", "vers" # verso
]

def load_json(path):
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def is_opening(text):
    text_lower = text.lower().strip()
    
    # Check strict openers
    for ind in OPENING_INDICATORS:
        if text_lower.startswith(ind):
            # Exception: "No, ..." might be a refinement starting with "No, grazie"
            if ind == "no" or text_lower.startswith("no,"):
                continue
            return True
            
    # Check for full intent phrases inside the text (Refinements shouldn't restate "I need to go to X")
    # Unless it's a correction "No, devo andare a Milano" (handled by "No" check maybe?)
    # But "Allora devo andare a..." is a restart.
    
    for phrase in INTENT_BLACKLIST:
        if phrase in text_lower:
             # If it has a strong refinement indicator, maybe keep it?
             # E.g. "No, invece devo andare a Roma" -> keep.
             # "Allora devo andare a Roma" -> discard.
             
             is_refinement = False
             for ref in REFINEMENT_INDICATORS:
                 if text_lower.startswith(ref):
                     is_refinement = True
                     break
             
             if not is_refinement:
                 return True
                 
    return False

def sanitize():
    print("Sanitizing corpus...")
    
    refinements = load_json(REFINEMENTS_PATH)
    search_queries = load_json(SEARCH_PATH)
    
    print(f"Original Refinements: {len(refinements)}")
    print(f"Original Search Queries: {len(search_queries)}")
    
    clean_refinements = []
    
    # Filter Refinements
    ignored_count = 0
    for item in refinements:
        if is_opening(item):
            # It's an opening message, remove from refinements
            ignored_count += 1
        else:
            # Keep if it doesn't look like an opening
            clean_refinements.append(item)
    
    print(f"Removed {ignored_count} opening-like messages from refinements.")
    
    # If refinements is too empty, add some defaults
    if len(clean_refinements) < 10:
        print("Refinements list is too short. Adding defaults.")
        defaults = [
            "No, preferisco partire la mattina",
            "C'è qualcosa dopo le {time_request}?",
            "Meglio nel pomeriggio",
            "Anzi, facciamo domani",
            "Solo andata",
            "In prima classe",
            "No, cambio destinazione: vado a {destination}",
            "Verso le {time_request}",
            "Più tardi",
            "Prima delle {time_request}",
            "No, troppo caro",
            "Cerca solo Frecce"
        ]
        clean_refinements.extend(defaults)
        
    # Deduplicate
    clean_refinements = sorted(list(set(clean_refinements)))
    
    # Search Queries Safety Check
    # Ensure they ARE openings. If not? 
    # For now, we trust search queries are mostly ok, but if we found "pure refinements" we might want to flag them.
    # But user asked to separate openings.
    # Let's just ensure clean_refinements are saved.
    
    save_json(REFINEMENTS_PATH, clean_refinements)
    print(f"Saved {len(clean_refinements)} refined refinements.")

if __name__ == "__main__":
    sanitize()
