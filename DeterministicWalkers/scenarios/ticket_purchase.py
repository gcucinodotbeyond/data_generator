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
    print(f"Loaded {len(STATIONS_DATA)} regions from stations.json")
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
    # Ensure distinct list
    STATIONS_ALL = sorted(list(set(STATIONS_ALL)))
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])
except FileNotFoundError:
    print("Fallback stations")
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
        num_results = rng.randint(2, 4)
        trains = []
        
        TRAIN_TYPES = [
            {"type": "Frecciarossa", "speed_mult": 1.0, "base_price": 50, "prefix": "FR"},
            {"type": "Intercity", "speed_mult": 1.5, "base_price": 30, "prefix": "IC"},
            {"type": "Regionale", "speed_mult": 2.0, "base_price": 10, "prefix": "RE"},
        ]
        
        current_min_from_midnight = base_hour * 60 + int(ctx_time.split(":")[1])
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
            
            train_id = f"{t_type['prefix']}{rng.randint(1000, 9999)}"
            price_val = t_type["base_price"] + rng.randint(-5, 20)
            if price_val < 5: price_val = 5
            price_str = f"{price_val}.00"
            stops = 0 if t_type["type"] == "Frecciarossa" else rng.randint(1, 10)
            
            trains.append({
                "pos": i + 1,
                "id": train_id,
                "dep": dep_time, 
                "arr": arr_time, 
                "type": t_type["type"],
                "stops": stops,
                "price": price_str
            })

        # 3. Choose Target & construct User Message
        target_idx = rng.randint(0, num_results - 1)
        target_train = trains[target_idx]
        
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
             user_text = f"Il {target_train['type']}"
             
        if is_first_class:
            user_text += " in prima classe"
        elif rng.random() < 0.3: 
            user_text += " in seconda classe"
            
        if rng.random() < 0.2:
            user_text += ", per favore"
            
        # --- PACE VARIATION ---
        # 30% chance for Seat Selection Flow (Multi-turn)
        # Flow: User -> Asst (Ask Seat) -> User (Answer) -> Asst (Purchase)
        
        add_seat_selection = rng.random() < 0.3
        
        messages = []
        if predataset:
             system_prompt = "{{SYSTEM_PROMPT}}"
        else:
            system_prompt = (f"Sei Talìa... <ctx>stazione: {origin}</ctx>")

        messages.append({"role": "system", "content": system_prompt})
        
        # Turn 1: User Intent
        messages.append({"role": "user", "content": self.rephrase(rng, user_text)})
        
        if add_seat_selection:
            # Assistant asks clarifying question
            # We skip tool call here, just text
            messages.append({
                "role": "assistant",
                "content": "Preferisci finestrino o corridoio?" 
            })
            
            # User answers
            seat_pref = rng.choice(["Finestrino", "Corridoio", "Indifferente"])
            user_seat_msg = f"{seat_pref}, grazie"
            messages.append({"role": "user", "content": self.rephrase(rng, user_seat_msg)})
        
        # Purchase Tool Call
        # We don't actually pass seat_pref to tool because schema doesn't support it standardly? 
        # Or maybe add as extra arg if we want flexible schema? 
        # Safe bet: Standard args.
        tool_call_args = {
            "train_id": target_train["id"],
            "class": class_str
        }
        
        tool_call_id = "call_001"
        tool_call_obj = {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "purchase_ticket",
                "arguments": json.dumps(tool_call_args)
            }
        }
        
        # Assistant Tool Call Msg
        messages.append({"role": "assistant", "tool_calls": [tool_call_obj], "content": None})
        
        # Tool Response
        tool_msg = {
            "role": "tool",
            "content": json.dumps({
                "confirmation_code": f"TICKET-{rng.randint(10000,99999)}",
                "train_id": target_train["id"],
                "seat": f"{rng.randint(1,10)}A",
                "price": target_train["price"]
            }),
            "tool_call_id": tool_call_id,
            "name": "purchase_ticket"
        }
        messages.append(tool_msg)
        
        # Final Reply
        messages.append({
            "role": "assistant",
            "content": "😊 Il tuo biglietto è stato acquistato! Buon viaggio."
        })

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "seed": rng.seed,
                "run_id": run_id,
                "contexts": [
                    {
                        "slice_length": len(messages) - 3, # Just before purchase tool call
                        "params": {
                            "origin": origin,
                            "destination": destination,
                            "ctx_time": ctx_time,
                            "date": "2025-12-23", 
                            "ui_state": '{"state":"results","can":{"next":false,"prev":false,"back":true}}',
                            "trains_array": json.dumps(trains)
                        }
                    }
                ]
            }
        }
