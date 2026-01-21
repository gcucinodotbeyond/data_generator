
import os
import sys
import json
import glob
from pathlib import Path

# Setup paths
curr_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(curr_dir)
sys.path.append(curr_dir) # For train_categorizer
sys.path.append(os.path.join(project_root, 'corpus-toolkit')) # For toolkit

from train_categorizer import TrainAssistantCategorizer

def load_raw_data(fs_builder_path):
    sentences = set()
    print(f"Scanning {fs_builder_path}...")
    
    # Look for _synth_* directories
    synth_dirs = glob.glob(os.path.join(fs_builder_path, 'parsing', '_synth_*'))
    print(f"Found synth dirs: {len(synth_dirs)}")
    
    for d in synth_dirs:
        # We assume there might be JSONL or TXT files inside
        files = glob.glob(os.path.join(d, '**', '*.jsonl'), recursive=True) + \
                glob.glob(os.path.join(d, '**', '*.txt'), recursive=True)
        
        print(f"Dir {os.path.basename(d)}: Found {len(files)} files")
        
        for f in files:
            print(f"Processing {f}...")
            try:
                with open(f, 'r', encoding='utf-8') as fh:
                    if f.endswith('.jsonl'):
                        for line in fh:
                            try:
                                obj = json.loads(line)
                                
                                # Handle List of Messages ( OpenAI format )
                                if isinstance(obj, list):
                                    for msg in obj:
                                        if isinstance(msg, dict) and msg.get('role') == 'user':
                                            sentences.add(msg.get('content', ''))
                                            
                                # Handle Dict
                                elif isinstance(obj, dict):
                                    # Common fields
                                    if 'text' in obj: sentences.add(obj['text'])
                                    elif 'message' in obj: sentences.add(obj['message'])
                                    elif 'question' in obj: sentences.add(obj['question']) # For QA
                                    elif 'domanda' in obj: sentences.add(obj['domanda']) # For QA IT
                                    elif 'Q' in obj: sentences.add(obj['Q']) # For QA
                                    elif 'content' in obj: sentences.add(obj['content'])
                                    
                                    # Conversation or Turns field
                                    elif 'conversation' in obj: 
                                        for msg in obj['conversation']:
                                            if isinstance(msg, dict) and msg.get('role') == 'user':
                                                content = msg.get('content')
                                                if content:
                                                    sentences.add(str(content))
                                    elif 'turns' in obj:
                                        for msg in obj['turns']:
                                            if isinstance(msg, dict) and msg.get('role') == 'user':
                                                content = msg.get('content')
                                                if content:
                                                    sentences.add(str(content))
                                                
                                # Handle String
                                elif isinstance(obj, str):
                                    sentences.add(obj)
                            except Exception as e: 
                                # print(f"Warning: {e} in {line[:50]}")
                                pass
            except Exception as e:
                print(f"Error reading {f}: {e}")
                
    return list(sentences)

def main():
    fs_path = os.path.abspath(os.path.join(project_root, '..', 'FS_dataset_builder'))
    output_dir = os.path.join(project_root, 'resources', 'corpus')
    
    # 1. Load Data
    raw_sentences = load_raw_data(fs_path)
    print(f"Loaded {len(raw_sentences)} unique raw sentences.")
    
    if not raw_sentences:
        print("No data found! Check path.")
        return

    # 2. Categorize
    print("Categorizing...")
    categorizer = TrainAssistantCategorizer()
    results = categorizer.categorize_corpus(raw_sentences)
    
    # 3. Filter & Map
    mapping = {
        'OPENING': 'greetings.json',
        'INFORMATION_REQUEST': 'search_queries.json',
        'SPECIFICATION': 'refinements.json',
        'TRANSACTION': 'purchase_intents.json',
        'CONFIRMATION': 'confirmations.json',
        'CLOSING': 'farewells.json',
        'QA': 'qa_questions.json',
        'NAVIGATION': 'navigation_commands.json',
        'FEEDBACK': 'user_feedback.json',
        'OOD': 'ood_phrases.json'
    }
    
    final_collections = {k: [] for k in mapping.values()}
    
    for item in results:
        cat = item['primary_category']
        conf = item['confidence']
        
        if cat in mapping and conf > 0.6: # Confidence Threshold
            fname = mapping[cat]
            
            # Simplified output format: List of strings or Objects? 
            # Existing corpus uses lists of strings mostly, or simple objects.
            # Let's default to just the text string for compatibility unless we know otherwise.
            # Wait, QA might need Q/A pairs. But from raw sentences we only have Qs usually.
            
            final_collections[fname].append(item)

    # 4. Write
    os.makedirs(output_dir, exist_ok=True)
    for fname, data in final_collections.items():
        out_p = os.path.join(output_dir, fname)
        with open(out_p, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Wrote {len(data)} items to {fname}")

if __name__ == "__main__":
    main()
