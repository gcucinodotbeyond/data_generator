import json
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
# Paths
BASE_DIR = Path(__file__).parent.parent
CORPUS_DIR = BASE_DIR / "resources" / "corpus"

def normalize_corpus():
    if not CORPUS_DIR.exists():
        print(f"Directory not found: {CORPUS_DIR}")
        return

    json_files = list(CORPUS_DIR.glob("*.json"))
    print(f"Found {len(json_files)} corpus files.")

    regex_exact_time = re.compile(r'\b\d{1,2}:\d{2}\b') 
    regex_hour_only = re.compile(r'\balle \d{1,2}\b(?!\:)') 
    
    # Relative time patterns
    # ORDER MATTERS: Specific phrases before generic ones
    patterns = [
        (re.compile(r'\bstasera\b', re.IGNORECASE), "{period_evening}"),
        (re.compile(r'\bquesta sera\b', re.IGNORECASE), "{period_evening}"),
        (re.compile(r'\bstamattina\b', re.IGNORECASE), "{period_morning}"),
        (re.compile(r'\bquesta mattina\b', re.IGNORECASE), "{period_morning}"),
        (re.compile(r'\bdomani mattina\b', re.IGNORECASE), "{relative_date_morning}"),
        (re.compile(r'\bdomani pomeriggio\b', re.IGNORECASE), "{relative_date_afternoon}"),
        (re.compile(r'\bdomani sera\b', re.IGNORECASE), "{relative_date_evening}"),
        (re.compile(r'\boggi pomeriggio\b', re.IGNORECASE), "{period_afternoon}"),
        (re.compile(r'\bpomeriggio\b', re.IGNORECASE), "{period_afternoon}"), # Generic 'pomeriggio'
        (re.compile(r'\bdomani\b', re.IGNORECASE), "{relative_date}"), # Generic domani
        (re.compile(r'\boggi\b', re.IGNORECASE), "{relative_today}"), # Generic oggi (careful with this one?)
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
        new_data = []
        
        for template in data:
            if not isinstance(template, str):
                new_data.append(template)
                continue
                
            original = template
            
            # Replace HH:MM
            if regex_exact_time.search(template):
                template = regex_exact_time.sub("{time_request}", template)
                
            # Replace "alle X" -> "alle {time_request}"
            template = regex_hour_only.sub("alle {time_request}", template)
            
            # Replace relative times
            for pat, repl in patterns:
                if pat.search(template):
                    template = pat.sub(repl, template)
            
            if template != original:
                modified_count += 1
                
            new_data.append(template)

        if modified_count > 0:
            print(f"  Modified {modified_count} templates.")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, indent=2, ensure_ascii=False)
            total_modified_files += 1
        else:
            print("  No changes.")

    print(f"Done. Updated {total_modified_files} files.")

if __name__ == "__main__":
    normalize_corpus()
