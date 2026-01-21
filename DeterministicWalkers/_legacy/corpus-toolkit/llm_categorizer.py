#!/usr/bin/env python3
"""
Script per la categorizzazione automatica del corpus usando LLM (Ollama).
Legge i file corpus esistenti e usa un LLM per ricategorizzare ogni utterance.
Implementa Hybrid Filtering (Regex + LLM) per ottimizzare le performance.
"""

import argparse
import json
import os
import glob
from pathlib import Path
import urllib.request
import urllib.error
from typing import List, Dict, Any
import time
import re

# Configuration
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3:4b-instruct"
PROMPT_PATH = Path(__file__).parent / "prompts" / "categorization.md"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"
STATIONS_PATH = Path(__file__).parent.parent / "resources" / "stations.json"

# Regex Patterns for Hybrid Filtering
REGEX_RULES = [
    # GREETING: Start/End anchored, allow punctuation
    (r"^(ciao|buongiorno|buonasera|salve|ehi|hey)[!.?]*$", "GREETING"),
    
    # CONFIRMATION: Simple agreements
    (r"^(s[ìi]|ok|va bene|certo|perfetto|procedi|confermo|esatto)[!.?]*$", "CONFIRMATION"),
    
    # REFUSAL: Simple disagreements
    (r"^(no|annulla|basta|stop|fermati|cancella)[!.?]*$", "REFUSAL"),
    
    # NAVIGATION: UI commands
    (r"^(menu|indietro|home|esci|ricomincia|torna al menu|pagina principale)[!.?]*$", "NAVIGATION"),
]

def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()
OLLAMA_URL = config.get("llm", {}).get("base_url", DEFAULT_OLLAMA_URL)
if not OLLAMA_URL.endswith("/api/generate"):
    OLLAMA_URL = f"{OLLAMA_URL}/api/generate"

MODEL = config.get("llm", {}).get("model", DEFAULT_MODEL)

def load_prompt():
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(f"Prompt content not found at {PROMPT_PATH}")
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def load_stations() -> set:
    if not STATIONS_PATH.exists():
        print(f"WARNING: Stations file not found at {STATIONS_PATH}")
        return set()
    
    try:
        with open(STATIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            stations = set()
            for key, val in data.items():
                if isinstance(val, list):
                    for s in val:
                        stations.add(s.lower().strip())
            return stations
    except Exception as e:
        print(f"Error loading stations: {e}")
        return set()

def extract_json_from_text(text: str) -> Dict:
    # Attempt 1: Direct JSON parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Attempt 2: Regex for { "results": ... } or similar object
    match = re.search(r'(\{.*"results":.*\})', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass

    # Attempt 3: Regex for just the list [ ... ] -> wrap in results
    match = re.search(r'(\[.*\])', text, re.DOTALL)
    if match:
        try:
            return {"results": json.loads(match.group(1))}
        except:
            pass

    # Attempt 4: Loose regex for { ... } as fallback
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
         try:
            return json.loads(match.group(1))
         except:
            pass
            
    return {"results": []}

def call_ollama(prompt: str, model: str, system: str, retries=3) -> Dict:
    data = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096
        }
    }
    
    encoded_data = json.dumps(data).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    
    for attempt in range(retries):
        try:
            print(f"DEBUG: Calling {OLLAMA_URL} with model {model} (Attempt {attempt+1}/{retries})", flush=True)
            req = urllib.request.Request(OLLAMA_URL, data=encoded_data, headers=headers)
            
            # Add timeout to avoid hanging indefinitely
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode('utf-8'))
                raw_response = result.get('response', '')
                
                # Debug log
                try:
                    with open("llm_debug.log", "a", encoding="utf-8") as f:
                        f.write(f"\n--- PROMPT ---\n{prompt[:100]}...\n--- RESPONSE ---\n{raw_response}\n")
                except Exception:
                    pass
                
                return extract_json_from_text(raw_response)
                
        except urllib.error.URLError as e:
            print(f"Ollama Connection Error (Attempt {attempt+1}): {e}")
            time.sleep(2)
        except Exception as e:
            print(f"Ollama Call Error (Attempt {attempt+1}): {e}")
            time.sleep(1)
            
    print("All retries failed.")
    return {"results": []}

def apply_regex_filtering(text: str) -> str:
    """Returns category if matched, else None"""
    text_lower = text.strip().lower()
    for pattern, category in REGEX_RULES:
        if re.match(pattern, text_lower):
            return category
    return None

def categorize_batch(items: List[Dict], model: str, system_prompt: str, stations: set) -> List[Dict]:
    # Phase 0: Source-Based Filtering (Deterministic)
    to_check_stations = []
    results_map = {} # id -> category
    
    for item in items:
        uid = item.get("id")
        source = item.get("source", "")
        
        # Hardcoded source rules
        if source == "complete_qa_pairs_with_emojis.jsonl":
            results_map[uid] = "QA_QUESTION"
        else:
            to_check_stations.append(item)

    # Phase 0.5: Station Logic (Deterministic)
    to_process_regex = []
    for item in to_check_stations:
        uid = item.get("id")
        text = item.get("text", "").strip().lower()
        
        # Check if text is EXACTLY a station name
        if text in stations:
             results_map[uid] = "SEARCH_QUERY"
        else:
             to_process_regex.append(item)
            
    # Phase 1: Regex Filtering
    to_process_llm = []
    
    for item in to_process_regex:
        uid = item.get("id")
        text = item.get("text", "")
        
        regex_cat = apply_regex_filtering(text)
        if regex_cat:
            results_map[uid] = regex_cat
        else:
            to_process_llm.append(item)
            
    # Phase 2: LLM for the rest
    if to_process_llm:
        print(f"  > Source/Regex matched {len(items) - len(to_process_llm)}/{len(items)} items. Sending {len(to_process_llm)} to LLM.")
        
        # Prepare input json for prompt
        input_data = [{"id": item.get("id", f"temp_{i}"), "text": item.get("text", "")} for i, item in enumerate(to_process_llm)]
        user_prompt = f"Categorize these utterances:\n{json.dumps(input_data, indent=2)}"
        
        response = call_ollama(user_prompt, model, system_prompt)
        llm_results = response.get("results", [])
        
        for res in llm_results:
            results_map[res["id"]] = res.get("category", "UNKNOWN")
    
    # construct final list
    categorized = []
    for item in items:
        uid = item.get("id")
        cat = results_map.get(uid, "UNKNOWN")
        
        new_item = item.copy()
        # Overwrite primary_category
        new_item["primary_category"] = cat
        # Remove llm_category if it exists from previous runs/logic
        if "llm_category" in new_item:
            del new_item["llm_category"]
            
        categorized.append(new_item)
        
    return categorized

def load_corpus_files(input_path: str) -> List[Dict]:
    items = []
    
    files = glob.glob(input_path) if "*" in input_path else [input_path]
    if os.path.isdir(input_path):
        files = glob.glob(str(Path(input_path) / "*.json"))
        
    print(f"Loading files: {files}")
    
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Add useful metadata like source file
                    for x in data:
                        if isinstance(x, dict):
                            x["source_file"] = Path(fpath).name
                            items.append(x)
                elif isinstance(data, dict):
                    # Handle single object or wrapped lists if necessary
                     pass
        except Exception as e:
            print(f"Error loading {fpath}: {e}")
            
    return items

def main():
    parser = argparse.ArgumentParser(description='LLM-based Corpus Categorizer')
    parser.add_argument('--input', '-i', required=True, help='Input file or directory (glob)')
    parser.add_argument('--output', '-o', default='categorized_corpus_llm', help='Output directory')
    # Default to config model if not specified, which we updated to qwen3
    parser.add_argument('--model', '-m', default=MODEL, help=f'Ollama model (default: {MODEL})')
    parser.add_argument('--batch-size', '-b', type=int, default=20, help='Batch size for LLM calls')
    parser.add_argument('--limit', type=int, default=0, help='Limit number of items to process (for testing)')
    parser.add_argument('--source', '-s', help='Filter processing by specific source filename')
    parser.add_argument('--list-sources', action='store_true', help='List all available source filenames and exit')
    
    args = parser.parse_args()
    
    # Setup output
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Load Prompt
    system_prompt = load_prompt()

    # Load Stations
    stations = load_stations()
    print(f"Loaded {len(stations)} valid station names for deterministic check.")
    
    # Load Data
    all_items = load_corpus_files(args.input)
    print(f"Total items loaded: {len(all_items)}")

    # Handle List Sources
    if args.list_sources:
        sources = sorted(list(set(item.get("source", "unknown") for item in all_items)))
        print("\nAvailable Sources:")
        for s in sources:
            count = sum(1 for i in all_items if i.get("source") == s)
            print(f"  - {s} ({count} items)")
        return

    # Filter by Source
    if args.source:
        print(f"Filtering by source: {args.source}")
        all_items = [i for i in all_items if i.get("source") == args.source]
        print(f"Items after filtering: {len(all_items)}")
        if not all_items:
            print(f"No items found for source '{args.source}'. Exiting.")
            return

    if args.limit > 0:
        all_items = all_items[:args.limit]
        print(f"Limiting to first {args.limit} items.")
    
    # OUTPUT FILE (JSONL)
    output_file_jsonl = out_dir / "categorized_corpus.jsonl"
    
    # RESUME LOGIC
    processed_ids = set()
    if output_file_jsonl.exists():
        print(f"Checking existing progress in {output_file_jsonl}...")
        with open(output_file_jsonl, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    line = line.strip()
                    if not line: continue
                    record = json.loads(line)
                    processed_ids.add(record["id"])
                except:
                    pass
        print(f"Found {len(processed_ids)} already processed items.")

    # Filter items to process
    items_to_process = [i for i in all_items if i["id"] not in processed_ids]
    print(f"Items remaining to process: {len(items_to_process)}")
    
    if not items_to_process:
        print("All items processed!")
        return

    # Process in batches
    total_len = len(items_to_process)
    
    print(f"Starting classification with model {args.model}...")
    
    # Open file in append mode
    with open(output_file_jsonl, "a", encoding="utf-8") as f_out:
        for i in range(0, total_len, args.batch_size):
            batch = items_to_process[i : i + args.batch_size]
            current_batch_idx = i // args.batch_size + 1
            total_batches_remaining = (total_len + args.batch_size - 1) // args.batch_size
            
            print(f"Processing batch {current_batch_idx}/{total_batches_remaining} ({len(batch)} items)...")
            
            try:
                results = categorize_batch(batch, args.model, system_prompt, stations)
                
                # Write immediately
                for res in results:
                    f_out.write(json.dumps(res, ensure_ascii=False) + "\n")
                f_out.flush() # Ensure it hits disk
                
            except Exception as e:
                print(f"Error in batch {i}: {e}")
                # Log error but try to continue or skip?
                # If we skip writing, they won't be in processed_ids next time, so they retry.
                # But if it's a permanent error, we loop forever.
                # Let's write them as ERROR so we move on.
                for item in batch:
                   item["primary_category"] = "PROCESS_ERROR"
                   f_out.write(json.dumps(item, ensure_ascii=False) + "\n")
                f_out.flush()

    print(f"\nDone! Results saved to {output_file_jsonl}")
    
    # Optional: Convert to full JSOn if needed, but JSONL is better for large datasets

if __name__ == "__main__":
    main()
