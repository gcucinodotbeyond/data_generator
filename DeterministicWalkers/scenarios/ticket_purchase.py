import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom

# --- Load Data Constants ---
CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"

try:
    with open(RESOURCE_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
    # Ensure distinct list
    STATIONS_ALL = sorted(list(set(STATIONS_ALL)))
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])
except FileNotFoundError:
    STATIONS_ALL = ["Roma Termini", "Milano Centrale", "Napoli Centrale", "Torino Porta Nuova", "Firenze SMN"]
    STATIONS_MAJOR = STATIONS_ALL

PREFIXES = ["Voglio comprare", "Acquista", "Prendo", "Scegli", "Compro", "Seleziono"]

class TicketPurchase(Scenario):
    @property
    def name(self) -> str:
        return "ticket_purchase"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        predataset = kwargs.get("predataset", True)
        
        # 1. Establish Context
        origin = rng.choice(STATIONS_MAJOR)
        possible_destinations = [s for s in STATIONS_ALL if s != origin]
        destination = rng.choice(possible_destinations)
        
        # Base time
        base_hour = rng.randint(7, 20)
        ctx_time = f"{base_hour:02d}:{rng.choice([0, 15, 30, 45]):02d}"
        
        # 2. Generate Search Results (Trains) according to recipe schema
        # Schema: [{"pos":1,"id":"...","dep":"...","arr":"...","type":"...","stops":0,"price":"..."}]
        num_results = rng.randint(2, 4)
        trains = []
        
        # Train types with some properties
        TRAIN_TYPES = [
            {"type": "Frecciarossa", "speed_mult": 1.0, "base_price": 50, "prefix": "FR"},
            {"type": "Intercity", "speed_mult": 1.5, "base_price": 30, "prefix": "IC"},
            {"type": "Regionale", "speed_mult": 2.0, "base_price": 10, "prefix": "RE"},
        ]
        
        current_min_from_midnight = base_hour * 60 + int(ctx_time.split(":")[1])
        
        # Start first train shortly after context time
        start_offset = 15 
        
        for i in range(num_results):
            t_type = rng.choice(TRAIN_TYPES)
            
            # Departure
            dep_min_abs = current_min_from_midnight + start_offset + (i * rng.randint(20, 60))
            dep_h = (dep_min_abs // 60) % 24
            dep_m = dep_min_abs % 60
            dep_time = f"{dep_h:02d}:{dep_m:02d}"
            
            # Duration & Arrival
            base_duration = rng.randint(60, 180) # minutes
            duration = int(base_duration * t_type["speed_mult"])
            arr_min_abs = dep_min_abs + duration
            arr_h = (arr_min_abs // 60) % 24
            arr_m = arr_min_abs % 60
            arr_time = f"{arr_h:02d}:{arr_m:02d}"
            
            # ID
            train_id = f"{t_type['prefix']}{rng.randint(1000, 9999)}"
            
            # Price
            price_val = t_type["base_price"] + rng.randint(-5, 20)
            if price_val < 5: price_val = 5
            price_str = f"{price_val}.00"
            
            # Stops
            stops = 0 if t_type["type"] == "Frecciarossa" else rng.randint(1, 10)
            
            trains.append({
                "pos": i + 1,
                "id": train_id,
                "dep": dep_time, # Schema uses 'dep'
                "arr": arr_time, # Schema uses 'arr'
                "type": t_type["type"],
                "stops": stops,
                "price": price_str
            })

        # 3. Choose Target & construct User Message
        target_idx = rng.randint(0, num_results - 1)
        target_train = trains[target_idx]
        
        # Intent: Class selection (80% Seconda, 20% Prima)
        # However, for Regionale, usually only Seconda exists or is standard.
        # Recipe says: "80% Seconda Classe, 20% Prima Classe"
        # We'll apply this. If user asks for First, we assume it exists.
        
        is_first_class = False
        if target_train["type"] != "Regionale":
             if rng.random() < 0.2:
                 is_first_class = True
        
        class_str = "Prima Classe" if is_first_class else "Seconda Classe"
        
        # User referencing strategies
        strategies = ["ordinal", "time", "type_time", "minimal"]
        strategy = rng.choice(strategies)
        
        user_text = ""
        
        if strategy == "ordinal":
            ordinals = ["il primo", "il secondo", "il terzo", "il quarto"]
            obj = ordinals[target_idx] if target_idx < len(ordinals) else "quello"
            user_text = f"{rng.choice(PREFIXES)} {obj}"
        elif strategy == "time":
            user_text = f"Quello delle {target_train['dep']}"
        elif strategy == "type_time":
            user_text = f"Il {target_train['type']} delle {target_train['dep']}"
        elif strategy == "minimal":
             user_text = f"Il {target_train['type']}" # Risk if multiple same type, but acceptable/realistic ambiguity
             
        # Add class intent to text
        if is_first_class:
            user_text += " in prima classe"
        elif rng.random() < 0.3: # Sometimes explicitly say second class
            user_text += " in seconda classe"
            
        if rng.random() < 0.2:
            user_text += ", per favore"

        # 4. Construct Tool Call
        # Recipe: purchase_ticket(train_id="...", class="...")
        tool_call_args = {
            "train_id": target_train["id"],
            "class": class_str
        }
        
        # Optional: Add seat selection if First Class (recipe hint: "Manca seat for AV")
        # For this iteration, I'll stick to the base request first, maybe add seat later or rarely.
        # Let's keep it simple as per "Golden sample 1" or "2".
        
        tool_call = {
            "name": "purchase_ticket",
            "arguments": tool_call_args
        }
        
        # 5. System Prompt Generation
        if predataset:
             system_prompt = "{{SYSTEM_PROMPT}}"
        else:
            # Fallback for raw generation
             system_prompt = (
                f"Sei Talìa...\n"
                f"<ctx>\n"
                f"stazione: {origin}\n"
                f"data: 2025-12-23\n"
                f"ora: {ctx_time}\n"
                f"</ctx>\n\n"
                f"<ui>\n"
                f'{{"state":"results","can":{{"next":false,"prev":false,"back":true}}}}\n'
                f"</ui>\n\n"
                f"<trains>\n"
                f"{json.dumps(trains)}\n"
                f"</trains>"
            )

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
                {"role": "assistant", "tool_calls": [tool_call]}
            ],
            "_meta": {
                "scenario": self.name,
                "seed": rng.seed,
                "run_id": run_id,
                "params": {
                    "origin": origin,
                    "destination": destination,
                    "ctx_time": ctx_time,
                    "date": "2025-12-23", # Fixed date as per recipe examples often use Dec
                    "ui_state": '{"state":"results","can":{"next":false,"prev":false,"back":true}}',
                    "trains_array": json.dumps(trains)
                }
            }
        }
