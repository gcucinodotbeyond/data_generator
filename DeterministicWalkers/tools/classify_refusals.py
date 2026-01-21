import json
import re
import os

def classify():
    refusal_path = r'c:\Users\gcucino\Desktop\data_generator\DeterministicWalkers\resources\refusal.json'
    starters_path = r'c:\Users\gcucino\Desktop\data_generator\DeterministicWalkers\resources\refusal_starters.json'
    followups_path = r'c:\Users\gcucino\Desktop\data_generator\DeterministicWalkers\resources\refusal_followups.json'

    if not os.path.exists(refusal_path):
        print(f"Error: {refusal_path} not found")
        return

    with open(refusal_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Load stations for filtering
    stations_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'stations.json')
    with open(stations_path, 'r', encoding='utf-8') as f:
        stations_data = json.load(f)
    
    all_stations = []
    for category in stations_data.values():
        all_stations.extend(category)
    
    # Sort by length descending to match longer station names first
    all_stations.sort(key=len, reverse=True)

    # Expanded followup prefixes
    followup_prefixes = [
        "Ah", "Beh", "Mmh", "Mmm", "Senti", "Senta", "Invece", "A proposito", 
        "Ma allora", "Ma quindi", "Ma insomma", "Ma scusa", "Ma dai", "Allora", 
        "E invece", "E allora", "E quindi", "E riguardo", "E sul", "E sui", 
        "E sulla", "E per quanto", "E mi", "E se", "E dimmi", "E che", 
        "E nemmeno", "E pure", "Capisco", "Capito", "D'accordo", "Ok", "Okay", 
        "Bene", "Perfetto", "Grazie", "Certo", "Sì", "Si", "Fantastico", 
        "Ottimo", "Interessante", "Che bello", "Che interessante", "Dai",
        "Beh no", "No grazie", "No no", "Vabbè", "Vabbe", "Va bene", "E"
    ]
    # Match prefix followed by space or punctuation
    pattern_str = r'^(' + '|'.join([re.escape(p) for p in followup_prefixes]) + r')[\s,!\.]'
    followup_pattern = re.compile(pattern_str, re.IGNORECASE)

    # Specific exclusion keywords for starters
    exclusion_keywords = ["FS", "carrozze", "carrozza", "Frecce", "Trenitalia", "Anas"]

    starters = []
    followups = []

    for text in data:
        text_lower = text.lower()
        
        # 1. Check if it's a followup based on "almeno" or starting prefixes
        is_followup = followup_pattern.search(text) or "almeno" in text_lower
        
        if is_followup:
            followups.append(text)
        else:
            # 2. For potential starters, filter out station mentions or keywords
            contains_station = any(s.lower() in text_lower for s in all_stations)
            contains_keyword = any(kw.lower() in text_lower for kw in exclusion_keywords)
            
            if not (contains_station or contains_keyword):
                starters.append(text)
            else:
                # Optionally log or discard. Here we discard to keep starters clean.
                pass

    with open(starters_path, 'w', encoding='utf-8') as f:
        json.dump(starters, f, indent=2, ensure_ascii=False)
    
    with open(followups_path, 'w', encoding='utf-8') as f:
        json.dump(followups, f, indent=2, ensure_ascii=False)

    print(f"Classification complete:")
    print(f" - Starters: {len(starters)}")
    print(f" - Followups: {len(followups)}")

if __name__ == "__main__":
    classify()
