import json
import sys
from pathlib import Path

def clean_file(input_path: str, output_path: str):
    """
    Remove _meta field from all lines in a JSONL file.
    """
    print(f"Cleaning {input_path} -> {output_path}")
    count = 0
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(output_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            if not line.strip():
                continue
            data = json.loads(line)
            if "_meta" in data:
                del data["_meta"]
            fout.write(json.dumps(data, ensure_ascii=False) + "\n")
            count += 1
    print(f"Processed {count} lines.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m utils.clean_meta <input.jsonl> <output.jsonl>")
        sys.exit(1)
    
    clean_file(sys.argv[1], sys.argv[2])
