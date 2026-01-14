import json
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
CORPUS_DIR = BASE_DIR / "resources" / "corpus"
STATIONS_FILE = BASE_DIR / "resources" / "stations.json"

def load_cities():
    cities = set()
    if not STATIONS_FILE.exists():
        print(f"Stations file not found: {STATIONS_FILE}")
        return []
    
    with open(STATIONS_FILE, 'r', encoding='utf-8') as f:
        stations_data = json.load(f)
        for category in stations_data.values():
            for station in category:
                # Extract first word as city (e.g., "Roma Termini" -> "Roma")
                # Also handle special cases like "Reggio Emilia"
                city = station.split()[0]
                cities.add(city)
                # Add some common multi-word cities manually if needed
                if station.startswith("Reggio"):
                    cities.add("Reggio Emilia")
                    cities.add("Reggio Calabria")
                if station.startswith("La Spezia"):
                    cities.add("La Spezia")
    
    # Sort by length descending to match longest phrases first
    return sorted(list(cities), key=len, reverse=True)

def normalize_corpus():
    if not CORPUS_DIR.exists():
        print(f"Directory not found: {CORPUS_DIR}")
        return

    json_files = list(CORPUS_DIR.glob("*.json"))
    print(f"Found {len(json_files)} corpus files.")

    cities = load_cities()
    print(f"Loaded {len(cities)} unique city names for normalization.")

    regex_exact_time = re.compile(r'\b\d{1,2}:\d{2}\b') 
    regex_hour_only = re.compile(r'\balle \d{1,2}\b(?!\:)') 
    
    # Relative time patterns
    patterns = [
        (re.compile(r'\bstasera\b', re.IGNORECASE), "{period_evening}"),
        (re.compile(r'\bquesta sera\b', re.IGNORECASE), "{period_evening}"),
        (re.compile(r'\bstamattina\b', re.IGNORECASE), "{period_morning}"),
        (re.compile(r'\bquesta mattina\b', re.IGNORECASE), "{period_morning}"),
        (re.compile(r'\bdomani mattina\b', re.IGNORECASE), "{relative_date_morning}"),
        (re.compile(r'\bdomani pomeriggio\b', re.IGNORECASE), "{relative_date_afternoon}"),
        (re.compile(r'\bdomani sera\b', re.IGNORECASE), "{relative_date_evening}"),
        (re.compile(r'\boggi pomeriggio\b', re.IGNORECASE), "{period_afternoon}"),
        (re.compile(r'\bpomeriggio\b', re.IGNORECASE), "{period_afternoon}"),
        (re.compile(r'\bdomani\b', re.IGNORECASE), "{relative_date}"),
        (re.compile(r'\boggi\b', re.IGNORECASE), "{relative_today}"),
    ]
    
    # Train patterns
    train_patterns = [
        (re.compile(r'\b(Frecciarossa|Frecciargento|Frecciabianca|Freccia|Intercity|Regionale|Eurocity|Italo|Regionale Veloce|Intercity Notte)\b', re.IGNORECASE), "{train_info}"),
        (re.compile(r'\b(FR|FA|FB|IC|ICN|RV|R|EC|EN)\d{2,}\b', re.IGNORECASE), "{train_info}"),
    ]
    
    total_modified_files = 0

    for file_path in json_files:
        print(f"Processing {file_path.name}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")
            continue
            
        if not isinstance(data, list):
            print(f"Skipping {file_path.name}: Not a list.")
            continue

        modified_count = 0
        new_data_set = set() # Use a set for deduplication
        
        for template in data:
            if not isinstance(template, str):
                continue
                
            original = template
            
            # 1. Replace city names
            # Only do this for files likely to have cities (search, refinement, etc.)
            # But safer to do it for all if we want extreme normalization
            for city in cities:
                # Use word boundaries for cities
                pat = re.compile(rf'\b{re.escape(city)}\b', re.IGNORECASE)
                if pat.search(template):
                    template = pat.sub("{destination}", template)

            # 2. Replace HH:MM
            if regex_exact_time.search(template):
                template = regex_exact_time.sub("{time_request}", template)
                
            # 3. Replace "alle X" -> "alle {time_request}"
            template = regex_hour_only.sub("alle {time_request}", template)
            
            # 4. Replace relative times
            for pat, repl in patterns:
                if pat.search(template):
                    template = pat.sub(repl, template)
            
            # 5. Replace train info
            for pat, repl in train_patterns:
                if pat.search(template):
                    template = pat.sub(repl, template)

            if template != original:
                modified_count += 1
                
            new_data_set.add(template)

        # Final cleanup: sort and write back
        final_data = sorted(list(new_data_set))
        
        if len(final_data) < len(data) or modified_count > 0:
            print(f"  Modified {modified_count} templates. Deduplicated from {len(data)} to {len(final_data)}.")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            total_modified_files += 1
        else:
            print("  No changes.")

    print(f"Done. Updated {total_modified_files} files.")

if __name__ == "__main__":
    normalize_corpus()
