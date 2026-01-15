import json
import glob
import sys
from pathlib import Path
import re

def validate_corpus_file(filepath):
    print(f"Checking {filepath.name}...")
    issues = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                issues.append("File is empty (0 bytes or whitespace)")
                return issues
                
            data = json.loads(content)
            
            if not isinstance(data, list):
                issues.append("Root element is not a JSON list")
                return issues
            
            if len(data) == 0:
                issues.append("List is empty []")
                return issues
                
            # Content checks
            for i, entry in enumerate(data):
                if not isinstance(entry, str):
                    issues.append(f"Item #{i} is not a string")
                    continue
                
                # Check for empty strings
                if not entry.strip():
                    issues.append(f"Item #{i} is empty string")
                
                # Check for placeholders
                # We expect placeholders like {destination}, {time_request}, etc.
                # But we want to flag if there represent "variables" that are NOT standard (might be typos)
                placeholders = re.findall(r'\{([a-zA-Z0-9_]+)\}', entry)
                valid_placeholders = {
                    "destination", "origin", "time_request", 
                    "relative_date", "relative_date_morning", "relative_date_afternoon", "relative_date_evening",
                    "relative_today", 
                    "period_morning", "period_afternoon", "period_evening",
                    "train_info"
                }
                
                for p in placeholders:
                    if p not in valid_placeholders:
                        # Some scenarios might use others, but let's warn
                        issues.append(f"Item #{i}: Unknown placeholder '{{{p}}}'")

    except json.JSONDecodeError as e:
        issues.append(f"Invalid JSON: {e}")
    except Exception as e:
        issues.append(f"Error reading file: {e}")
        
    return issues

def main():
    corpus_dir = Path(__file__).parent.parent / "resources" / "corpus"
    if not corpus_dir.exists():
        print(f"Corpus directory not found at {corpus_dir}")
        sys.exit(1)
        
    print(f"Validating corpus in {corpus_dir}\n")
    
    found_issues = False
    for json_file in corpus_dir.glob("*.json"):
        issues = validate_corpus_file(json_file)
        if issues:
            found_issues = True
            print(f"  ❌ ISSUES found in {json_file.name}:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"  ✅ {json_file.name} OK")
    
    if found_issues:
        sys.exit(1)
    else:
        print("\nAll corpus files passed structure check.")

if __name__ == "__main__":
    main()
