import json
import os
import hashlib
import argparse

def get_file_hash(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def extract_utterances_from_manifest(manifest_path, output_file):
    with open(manifest_path, 'r', encoding='utf-8') as f:
        file_list = json.load(f)

    harvested = []
    seen_texts = set()

    print(f"Loaded manifest with {len(file_list)} files.")

    for file_path in file_list:
        if not os.path.exists(file_path):
            print(f"Warning: File not found: {file_path}")
            continue

        print(f"Processing {os.path.basename(file_path)}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        print(f"  Skipping invalid JSON at line {line_num+1}")
                        continue

                    utterances_to_add = []

                    # STRATEGY 1: 'domanda' field (QA pairs)
                    if isinstance(data, dict) and 'domanda' in data:
                        utterances_to_add.append(data['domanda'])

                    # STRATEGY 2: 'text' field (Simple commands)
                    elif isinstance(data, dict) and 'text' in data:
                        utterances_to_add.append(data['text'])

                    # STRATEGY 3: 'messages' list (OpenAI/Dataset format)
                    elif isinstance(data, dict) and 'messages' in data and isinstance(data['messages'], list):
                        for msg in data['messages']:
                            if msg.get('role') == 'user' and msg.get('content'):
                                utterances_to_add.append(msg['content'])

                    # STRATEGY 4: 'turns' list (FS Conversations)
                    elif isinstance(data, dict) and 'turns' in data and isinstance(data['turns'], list):
                        for turn in data['turns']:
                            if turn.get('role') == 'user' and turn.get('content'):
                                utterances_to_add.append(turn['content'])

                    # STRATEGY 5: 'conversations' wrapper (Some FS formats)
                    elif isinstance(data, dict) and 'conversations' in data and isinstance(data['conversations'], list):
                        for sub_conv in data['conversations']:
                             # Check for turns or messages inside
                             turns = sub_conv.get('turns') or sub_conv.get('messages') or []
                             for turn in turns:
                                if turn.get('role') == 'user' and turn.get('content'):
                                    utterances_to_add.append(turn['content'])

                    # STRATEGY 6: Root list of messages (Synth Func)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get('role') == 'user' and item.get('content'):
                                utterances_to_add.append(item['content'])

                    # Add extracted
                    for text in utterances_to_add:
                        text = text.strip()
                        if text and text not in seen_texts:
                            seen_texts.add(text)
                            harvested.append({
                                "id": f"utt_{get_file_hash(text)[:10]}",
                                "text": text,
                                "source": os.path.basename(file_path),
                                "primary_category": "UNCATEGORIZED" 
                            })

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    print(f"Harvested {len(harvested)} unique utterances.")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(harvested, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Harvest utterances from Manifest")
    parser.add_argument("--manifest", required=True, help="Path to JSON manifest file")
    parser.add_argument("--output", default="resources/corpus/harvested_from_fs.json", help="Path to output JSON file")
    
    args = parser.parse_args()
    
    extract_utterances_from_manifest(args.manifest, args.output)
