import json
import argparse
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple
import collections

# --- Configuration & Regex ---

# Time/Date normalization regex
REGEX_EXACT_TIME = re.compile(r'\b\d{1,2}:\d{2}\b') 
REGEX_HOUR_ONLY = re.compile(r'\balle \d{1,2}\b(?!\:)') 
TRAIN_NAME_PAT = re.compile(r'\b(Frecciarossa|Frecciargento|Frecciabianca|Freccia|Intercity|Regionale|Eurocity|Italo|Regionale Veloce|Intercity Notte)\b', re.IGNORECASE)
TRAIN_ID_PAT = re.compile(r'\b(FR|FA|FB|IC|ICN|RV|R|EC|EN)\s?\d{2,}\b', re.IGNORECASE)

TIME_PATTERNS = [
    (re.compile(r'\b(stasera|questa sera)\b', re.IGNORECASE), "{period_evening}"),
    (re.compile(r'\b(stamattina|stamani|questa mattina)\b', re.IGNORECASE), "{period_morning}"),
    (re.compile(r'\bdomani mattina\b', re.IGNORECASE), "{relative_date_morning}"),
    (re.compile(r'\bdomani pomeriggio\b', re.IGNORECASE), "{relative_date_afternoon}"),
    (re.compile(r'\bdomani sera\b', re.IGNORECASE), "{relative_date_evening}"),
    (re.compile(r'\b(oggi pomeriggio|pomeriggio)\b', re.IGNORECASE), "{period_afternoon}"),
    (re.compile(r'\bdomani\b', re.IGNORECASE), "{relative_date}"),
    (re.compile(r'\boggi\b', re.IGNORECASE), "{relative_today}"),
]

# Farewells - Strict
FAREWELL_KEYWORDS = {"arrivederci", "a presto", "ciao", "buona serata", "buona giornata", "addio", "alla prossima"}
FAREWELL_MAX_WORDS = 4

class CorpusBuilder:
    def __init__(self, output_path: Path, stations_path: Path):
        self.output_path = output_path
        self.stations_path = stations_path
        self.corpus = collections.defaultdict(list)
        self.known_cities = self._load_cities()
        self.stats = collections.defaultdict(int)

    def _load_cities(self) -> List[str]:
        cities = []
        if self.stations_path.exists():
            with open(self.stations_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for cat in data.values():
                    for station in cat:
                        # Extract city name (e.g., "Roma Termini" -> "Roma")
                        # But handle multi-word cities like "Reggio Emilia"
                        if "Reggio Emilia" in station: cities.append("Reggio Emilia")
                        elif "Reggio Calabria" in station: cities.append("Reggio Calabria")
                        elif "La Spezia" in station: cities.append("La Spezia")
                        else:
                            cities.append(station.split()[0])
        cities = list(set(cities))
        cities.sort(key=len, reverse=True) # Longest first
        return cities

    def normalize_text(self, text: str, args: Dict = None) -> str:
        text = text.strip()
        
        # 1. Inject Argument Placeholders (if available from tool calls)
        if args:
            real_dest = args.get("destination", "")
            real_origin = args.get("origin", "")
            
            # Use regex to replace to avoid partial word matches if possible, 
            # though simple replace is often safer for strict matches
            if real_dest and real_dest in text:
                text = text.replace(real_dest, "{destination}")
            if real_origin and real_origin in text:
                text = text.replace(real_origin, "{origin}")
        
        # 2. Known Cities
        for city in self.known_cities:
            pat = re.compile(rf'\b{re.escape(city)}\b', re.IGNORECASE)
            if pat.search(text):
                text = pat.sub("{destination}", text) # Default to destination if ambiguous
                
        # 3. Time Patterns
        if REGEX_EXACT_TIME.search(text):
            text = REGEX_EXACT_TIME.sub("{time_request}", text)
        
        text = REGEX_HOUR_ONLY.sub("alle {time_request}", text)
        
        for pat, repl in TIME_PATTERNS:
            if pat.search(text):
                text = pat.sub(repl, text)

        # 4. Train Info
        text = TRAIN_NAME_PAT.sub("{train_info}", text)
        text = TRAIN_ID_PAT.sub("{train_info}", text)
        
        return text

    def is_valid_farewell(self, text: str) -> bool:
        lower = text.lower().strip()
        words = lower.split()
        if len(words) > FAREWELL_MAX_WORDS:
            return False
            
        # Must contain at least one strict keyword
        if not any(k in lower for k in FAREWELL_KEYWORDS):
            return False
            
        return True

    def process_file(self, file_path: Path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if isinstance(data, list):
                            # It might be a list of conversations or a list of messages representing one conversation
                            # Heuristic: if first item has 'role', assume it's one conversation
                            if data and 'role' in data[0]:
                                self._extract_conversation({"messages": data})
                            else:
                                for item in data:
                                    self._extract_conversation(item)
                        else:
                            self._extract_conversation(data)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def _extract_conversation(self, data: Dict):
        # Normalize structure
        conversations = data.get("conversations", [data])
        
        for conv in conversations:
            messages = conv.get("messages", conv.get("turns", []))
            
            has_searched = False
            
            for i, msg in enumerate(messages):
                if msg["role"] != "user":
                    continue
                    
                content = msg["content"]
                if not content: continue
                
                # Check next message for Tool Calls (Intent Detection)
                tool_name = None
                tool_args = {}
                if i + 1 < len(messages):
                    next_msg = messages[i+1]
                    if next_msg.get("tool_calls"):
                        tc = next_msg["tool_calls"][0]
                        tool_name = tc["function"]["name"]
                        try:
                            tool_args = json.loads(tc["function"]["arguments"])
                        except:
                            tool_args = {}

                # --- CATEGORIZATION ---
                
                normalized = self.normalize_text(content, tool_args)
                lower = content.lower()
                num_words = len(lower.split())

                # 1. Search Queries
                if tool_name == "search_trains":
                    # Check for Mixed Intents (e.g. contains question mark)
                    if "?" in content and not has_searched:
                        # Might be "Train to Rome?" which is fine, but "Train to Rome? And how much?" is mixed
                        pass 
                    
                    if not has_searched:
                        self.corpus["search_queries"].append(normalized)
                        self.stats["search_queries"] += 1
                        has_searched = True
                    else:
                        self.corpus["refinements"].append(normalized)
                        self.stats["refinements"] += 1
                        
                # 2. Purchase
                elif tool_name == "purchase_ticket":
                    self.corpus["purchase_intents"].append(normalized)
                    self.stats["purchase_intents"] += 1
                    
                # 3. Navigation
                elif tool_name == "ui_control":
                    self.corpus["navigation"].append(normalized)
                    self.stats["navigation"] += 1
                    
                # 4. Refusals & Rude (often from negative samples directories)
                # We often identify these by file path or explicit keywords if tool is missing
                # But here we rely on the source file logic mostly. 
                # For now, let's implement basic keyword detection if no tool
                elif tool_name is None:
                    
                    # Farewells - Strict
                    if self.is_valid_farewell(content):
                        self.corpus["farewells"].append(content) # Keep original case?
                        self.stats["farewells"] += 1
                        
                    # Greetings
                    # Relaxed check: keywords and short length
                    elif any(x in lower for x in ["ciao", "salve", "buongiorno", "buonasera"]) and num_words <= 3:
                         self.corpus["greetings"].append(content)
                         self.stats["greetings"] += 1

                    # Confirmations
                    elif any(x in lower for x in ["sì", "si", "ok", "va bene", "perfetto"]) and num_words <= 4:
                         if "?" not in content:
                             self.corpus["confirmations"].append(normalized)
                             self.stats["confirmations"] += 1

    def save(self):
        self.output_path.mkdir(parents=True, exist_ok=True)
        for key, items in self.corpus.items():
            # Deduplicate and Sort
            unique_items = sorted(list(set(items)))
            
            # Sanity Check: Remove empty items
            unique_items = [x for x in unique_items if x.strip()]
            
            if not unique_items: continue
            
            out_file = self.output_path / f"{key}.json"
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(unique_items, f, indent=2, ensure_ascii=False)
                
        print("Corpus Extraction Complete.")
        print(json.dumps(self.stats, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", "-i", type=str, nargs='+', required=True, help="Input directories or files")
    parser.add_argument("--output", "-o", type=str, required=True, help="Output directory")
    parser.add_argument("--stations", "-s", type=str, required=True, help="Path to stations.json")
    
    args = parser.parse_args()
    
    builder = CorpusBuilder(Path(args.output), Path(args.stations))
    
    files = []
    for inp in args.inputs:
        path = Path(inp)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(path.rglob("*.jsonl"))
            
    print(f"Processing {len(files)} files...")
    for f in files:
        builder.process_file(f)
        
    builder.save()
