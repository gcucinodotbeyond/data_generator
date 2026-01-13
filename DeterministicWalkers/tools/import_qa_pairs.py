import json
from pathlib import Path

# Paths
SOURCE_FILE = Path(r"c:\Users\gcucino\Desktop\data_generator\FS_dataset_builder\parsing\_synth_qa\_datasets\complete_qa_pairs_with_emojis.jsonl")
DEST_FILE = Path(r"c:\Users\gcucino\Desktop\data_generator\DeterministicWalkers\resources\qa_pairs.json")

def import_qa_pairs():
    if not SOURCE_FILE.exists():
        print(f"Error: Source file not found at {SOURCE_FILE}")
        return

    qa_pairs = []
    print(f"Reading from {SOURCE_FILE}...")
    
    try:
        with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if "domanda" in data and "risposta" in data:
                        qa_pairs.append([data["domanda"], data["risposta"]])
                except json.JSONDecodeError as e:
                    print(f"Skipping invalid JSON line: {e}")
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    print(f"Extracted {len(qa_pairs)} pairs.")

    # Ensure dest dir exists
    DEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    print(f"Writing to {DEST_FILE}...")
    with open(DEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
    
    print("Done.")

if __name__ == "__main__":
    import_qa_pairs()
