import json
import argparse
import os

def main():
    parser = argparse.ArgumentParser(description="Filter out items from a JSON string list based on a keyword.")
    parser.add_argument("--file", required=True, help="Path to the JSON file")
    parser.add_argument("--word", required=True, help="Keyword to search for and remove items containing it")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found.")
        return
        
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            print("Error: JSON content must be a list of strings.")
            return
            
        word_lower = args.word.lower()
        original_count = len(data)
        
        filtered_data = [item for item in data if word_lower not in str(item).lower()]
        removed_count = original_count - len(filtered_data)
        
        with open(args.file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2, ensure_ascii=False)
            
        print(f"Successfully processed {args.file}:")
        print(f" - Original items: {original_count}")
        print(f" - Items removed (containing '{args.word}'): {removed_count}")
        print(f" - Remaining items: {len(filtered_data)}")
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
