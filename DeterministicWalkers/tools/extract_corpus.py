import json
import argparse
from pathlib import Path
from typing import List, Dict, Set
import collections

def extract_from_file(file_path: Path, corpus: Dict, unique_search: Set, unique_greetings: Set, known_cities: List[str]):
    print(f"Reading from {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    
                    # Normalize to list of conversations
                    conversations = []
                    if "conversations" in data:
                        conversations = data["conversations"]
                    else:
                        conversations = [data]
                        
                    for conv in conversations:
                        # Normalize messages/turns
                        messages = conv.get("messages", conv.get("turns", []))
                        
                        for i, msg in enumerate(messages):
                            if msg["role"] == "user":
                                content = msg["content"]
                                if not content: continue
                                
                                # Intent Detection
                                # 1. Search Query (Initial)
                                if i + 1 < len(messages):
                                    next_msg = messages[i+1]
                                    if next_msg.get("tool_calls"):
                                        tool_name = next_msg["tool_calls"][0]["function"]["name"]
                                        
                                        # SEARCH
                                        if tool_name == "search_trains":
                                            # ... (Same logic as before, just indented)
                                            try:
                                                args = json.loads(next_msg["tool_calls"][0]["function"]["arguments"])
                                            except:
                                                continue
                                                
                                            real_dest = args.get("destination", "")
                                            real_origin = args.get("origin", "")
                                            
                                            templatized = content
                                            replaced_dest = False
                                            
                                            if real_dest and real_dest in templatized:
                                                templatized = templatized.replace(real_dest, "{destination}")
                                                replaced_dest = True
                                            
                                            if real_origin and real_origin in templatized:
                                                templatized = templatized.replace(real_origin, "{origin}")
                                                
                                            if replaced_dest:
                                                unique_search.add(templatized)
                                            else:
                                                refine_text = content
                                                for city in known_cities:
                                                    if city in refine_text:
                                                        refine_text = refine_text.replace(city, "{destination}")
                                                        break
                                                
                                                if len(content.split()) > 1:
                                                    corpus["refinements"].append(refine_text)

                                        # PURCHASE
                                        elif tool_name == "purchase_ticket":
                                            corpus["purchase_intents"].append(content)
                                            
                                        # NAVIGATION
                                        elif tool_name == "ui_control":
                                            corpus["navigation"].append(content)

                                # --- GENERAL CHITCHAT & HELPERS ---
                                lower_content = content.lower().strip()
                                clean_text = "".join(c if c.isalnum() else " " for c in lower_content)
                                words_set = set(clean_text.split())
                                num_words = len(clean_text.split())
                                
                                # Greetings
                                if any(x in words_set for x in ["ciao", "salve", "buongiorno", "buonasera", "ehi", "hey"]):
                                    if num_words <= 3:
                                        unique_greetings.add(content)

                                # Confirmations
                                confirmation_keywords = ["sì", "si", "ok", "va bene", "perfetto", "ottimo", "certo", "chiaro", "d'accordo"]
                                hits_confirm = False
                                for k in confirmation_keywords:
                                    if " " in k: 
                                        if k in lower_content:
                                            hits_confirm = True; break
                                    else:
                                        if k in words_set:
                                            hits_confirm = True; break
                                            
                                if num_words <= 5 and hits_confirm:
                                    if not any(x in words_set for x in ["ma", "però", "vorrei", "cerco"]):
                                        corpus["confirmations"].append(content)
                                        
                                # Refusals
                                refusal_keywords = ["no", "non", "annulla", "ferma", "falso", "sbagliato"]
                                hits_refusal = False
                                for k in refusal_keywords:
                                    if k in words_set: 
                                        hits_refusal = True; break
                                        
                                if num_words <= 5 and hits_refusal:
                                    if "non voglio" in lower_content or "no grazie" in lower_content or lower_content == "no":
                                        corpus["refusals"].append(content)
                                        
                                # Chitchat
                                chitchat_keywords = ["grazie", "prego", "arrivederci", "a presto", "buona giornata"]
                                if any(k in lower_content for k in chitchat_keywords):
                                    if num_words <= 5:
                                        corpus["chitchat"].append(content)

                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

def extract_corpus(input_paths: List[Path], output_path: Path):
    corpus = {
        "search_queries": [], "refinements": [], "purchase_intents": [],
        "navigation": [], "greetings": [], "confirmations": [],
        "refusals": [], "chitchat": []
    }
    
    # Load stations logic
    # output_path might be "resources/corpus" (dir) or "resources/corpus.json" (legacy file)
    # Stations is expected in "resources/stations.json" usually.
    
    stations_path = None
    if output_path.suffix == '.json':
         stations_path = output_path.parent / "stations.json"
    else:
         stations_path = output_path.parent / "stations.json" 
         # If output is "resources/corpus", parent is "resources", so this works.
         
    known_cities = []
    if stations_path.exists():
        with open(stations_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for cat in data.values(): known_cities.extend(cat)
            
            simplified = set()
            for station in known_cities:
                parts = station.split()
                if len(parts) > 1: simplified.add(parts[0])
            
            manual_cities = [
                "Reggio Emilia", "Reggio Calabria", "La Spezia", "Villa San Giovanni", 
                "Sesto San Giovanni", "Civitavecchia", "Fiumicino", "Pisa", "Livorno", 
                "Padova", "Venezia", "Mestre", "Firenze", "Napoli", "Torino", "Genova",
                "Bologna", "Verona", "Bari", "Palermo", "Catania", "Messina"
            ]
            simplified.update(manual_cities)
            known_cities.extend(list(simplified))
    else:
        known_cities = ["Roma", "Milano", "Napoli", "Firenze", "Torino", "Venezia", "Bologna", "Verona", "Genova", "Bari", "Salerno"]
    
    known_cities = list(set(known_cities))
    known_cities.sort(key=len, reverse=True)

    unique_search = set()
    unique_greetings = set()
    
    # Process inputs
    files_to_process = []
    for path in input_paths:
        if path.is_file():
            files_to_process.append(path)
        elif path.is_dir():
            files_to_process.extend(path.rglob("*.jsonl"))
            
    print(f"Found {len(files_to_process)} files to process.")
    
    for file_path in files_to_process:
        extract_from_file(file_path, corpus, unique_search, unique_greetings, known_cities)

    # Post-processing
    corpus["search_queries"] = sorted(list(unique_search))
    corpus["greetings"] = sorted(list(unique_greetings))
    corpus["refinements"] = sorted(list(set(corpus["refinements"])))
    corpus["purchase_intents"] = sorted(list(set(corpus["purchase_intents"])))
    corpus["navigation"] = sorted(list(set(corpus["navigation"])))
    corpus["confirmations"] = sorted(list(set(corpus["confirmations"])))
    corpus["refusals"] = sorted(list(set(corpus["refusals"])))
    corpus["chitchat"] = sorted(list(set(corpus["chitchat"])))

    print(f"Extracted {len(corpus['search_queries'])} search queries")
    print(f"Extracted {len(corpus['refinements'])} refinements")
    print(f"Extracted {len(corpus['purchase_intents'])} purchase intents")
    print(f"Extracted {len(corpus['navigation'])} navigation commands")
    print(f"Extracted {len(corpus['greetings'])} greetings")
    print(f"Extracted {len(corpus['confirmations'])} confirmations")
    print(f"Extracted {len(corpus['refusals'])} refusals")
    print(f"Extracted {len(corpus['chitchat'])} chitchat")
    
    # Write to split files
    output_dir = output_path
    if output_dir.suffix == '.json': # user passed a file path, treat parent as dir or create subdirectory?
        # Legacy support/fallback: if it looks like a file, use its parent + 'corpus' folder
        output_dir = output_dir.parent / "corpus"
    
    print(f"Writing split corpus files to {output_dir}...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for key, data in corpus.items():
        if not data: continue # Skip empty if any
        
        # Clean key for filename
        filename = f"{key}.json"
        file_path = output_dir / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    # Also write a manifest or just rely on filenames
    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract corpus from datasets")
    parser.add_argument("--inputs", "-i", type=str, nargs='+', required=True, help="Paths to input .jsonl files or directories")
    parser.add_argument("--output", "-o", type=str, required=True, help="Path to output directory (e.g. resources/corpus)")
    
    args = parser.parse_args()
    input_paths = [Path(p) for p in args.inputs]
    extract_corpus(input_paths, Path(args.output))
