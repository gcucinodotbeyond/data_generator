import json
import sys
import os
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
# --- Load Data Constants from Resource File ---
# We determine the path relative to this file
CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"

try:
    with open(RESOURCE_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
        
    # Helper to flatten lists
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
        
    # Extract major stations specifically
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])

except FileNotFoundError:
    print(f"Warning: Station file not found at {RESOURCE_PATH}, using fallback.")
    STATIONS_ALL = ["Roma Termini", "Milano Centrale"]
    STATIONS_MAJOR = STATIONS_ALL


# Simple mapping for checking connectivity (simplified for now, allow all-to-all in generation logic 
# but we could enforce stricter routes if needed. For search, users might ask for anything).

USER_TEMPLATES = [
    "Vorrei andare a {destination}",
    "Treno per {destination}",
    "Devo andare a {destination}",
    "{destination}",
    "Ci sono treni per {destination}?",
    "Biglietto per {destination}",
    "Orari per {destination}",
    "Voglio partire per {destination}",
    "{destination} per favore",
    "Mi serve un treno per {destination}",
]

TIME_PERIODS = ["mattina", "pomeriggio", "sera", "notte", "presto"]
DATES = ["oggi", "domani", "dopodomani"]

class SearchTrains(Scenario):
    @property
    def name(self) -> str:
        return "search_trains"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        predataset = kwargs.get("predataset", True) # Default to True if not specified (though generator should match)

        # 1. Establish Context (Where is the kiosk?)
        origin = rng.choice(STATIONS_MAJOR)
        
        # 2. Determine User Intent (Destination)
        # Ensure destination is different from origin
        possible_destinations = [s for s in STATIONS_ALL if s != origin]
        destination = rng.choice(possible_destinations)
        
        # 3. Determine other parameters
        passengers = rng.randint(1, 4)
        date_request = rng.choice(DATES) # User might say "domani"
        time_period = rng.choice(TIME_PERIODS) if rng.random() > 0.5 else None
        
        # 4. Construct User Message
        # Use Corpus if available
        corpus_templates = self.corpus.get("search_queries", [])
        if corpus_templates and rng.random() < 0.8: # 80% chance to use corpus
            template = rng.choice(corpus_templates)
        else:
            template = rng.choice(USER_TEMPLATES)
            
        # Define context time based on constraints in the template
        base_hour = rng.randint(6, 22) # Default
        
        # Prepare hydration arguments
        format_args = {"destination": destination}
        
        # --- Handle Relative Time Constraints ---
        # If the user says "stamattina", context should be morning. 
        if "{period_morning}" in template:
            base_hour = rng.randint(6, 11)
            format_args["period_morning"] = rng.choice(["stamattina", "questa mattina"])
            
        elif "{period_afternoon}" in template:
             base_hour = rng.randint(12, 17)
             format_args["period_afternoon"] = rng.choice(["oggi pomeriggio", "questo pomeriggio"])
             
        elif "{period_evening}" in template:
             # If user says "stasera", it could be 17:00 (planning for later) or 20:00 (now). 
             # Let's say context is late afternoon/evening.
             base_hour = rng.randint(16, 21)
             format_args["period_evening"] = rng.choice(["stasera", "questa sera"])
             
        # Future relative dates don't constrain context time much, but we need to fill the placeholder
        if "{relative_date_morning}" in template:
            format_args["relative_date_morning"] = "domani mattina"
        if "{relative_date_afternoon}" in template:
            format_args["relative_date_afternoon"] = "domani pomeriggio"
        if "{relative_date_evening}" in template:
            format_args["relative_date_evening"] = "domani sera"
        if "{relative_date}" in template:
            format_args["relative_date"] = rng.choice(["domani", "dopodomani"])
        if "{relative_today}" in template:
            format_args["relative_today"] = "oggi"
            
        # Commit to ctx_time
        ctx_time = f"{base_hour:02d}:{rng.randint(0, 59):02d}"
        
        try:
            # Generate time_request if needed (found in template)
            if "{time_request}" in template:
                req_h = (base_hour + rng.randint(1, 4)) % 24
                req_m = rng.choice([0, 15, 30, 45])
                req_time = f"{req_h:02d}:{req_m:02d}"
                format_args["time_request"] = req_time
            
            # Use safe replace for format_args to avoid KeyError for missing keys? 
            # Actually .format() raises KeyError if a key is missing in args but present in string.
            # But we are checking "if {key} in template" mostly. 
            # However, simpler to catch-all.
            
            # To be robust, we can use a SafeDict or just ensure we covered all our custom keys.
            # We covered: time_request, period_*, relative_*. destination is always there.
            
            # Perform hydration
            # We can't use format(**args) safely if we missed one.
            # Let's do partial replacement manually or just ensure we have them.
            # Our logic covers the known keys.
            
            # Note: template might have {destination} or not (if corpus vs custom).
            # normalize_corpus ensured standard keys.
            
            user_text = template
            for k, v in format_args.items():
                place = "{" + k + "}"
                user_text = user_text.replace(place, str(v))
                
        except Exception:
            # Fallback on safe hardcoded
            user_text = f"Vorrei andare a {destination}"
        
        # Add varied time/date info to user text ONLY if the template didn't specify time
        # We check the ORIGINAL template for placeholders
        time_placeholders = [
            "{time_request}", "{period_morning}", "{period_afternoon}", "{period_evening}",
            "{relative_date}", "{relative_date_morning}", "{relative_date_afternoon}", 
            "{relative_date_evening}", "{relative_today}"
        ]
        has_time_info = any(p in template for p in time_placeholders)
        
        if not has_time_info:
            if rng.random() < 0.3:
                user_text += f" {date_request}"
            if time_period and rng.random() < 0.3:
                user_text += f" di {time_period}"
            
        # 5. Construct Expected Tool Call
        # 5. Construct Expected Tool Call
        # We define context time early as it may influence tool params or train generation
        # ctx_time is already defined above

        # args dictionary
        tool_call_args = {
            "origin": origin,
            "destination": destination,
            "passengers": passengers,
            "date": "today" if "oggi" in user_text else ("tomorrow" if "domani" in user_text else "today"),
            "time": "now" # Default to now for search
        }
        
        tool_call_id = "call_001"
        tool_call_obj = {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "search_trains",
                "arguments": json.dumps(tool_call_args)
            }
        }
        
        # 6. Construct Tool Response & Follow-up
        # Generate mock trains result for the tool output
        num_results = rng.randint(2, 4)
        mock_trains = []
        base_h = int(ctx_time.split(":")[0])
        for i in range(num_results):
             dep_h = (base_h + 1 + i) % 24
             mock_trains.append({
                 "train_id": f"FR{rng.randint(9000, 9999)}",
                 "departure_time": f"{dep_h:02d}:30",
                 "arrival_time": f"{(dep_h+2)%24:02d}:30", 
                 "price": 45.0 + (i * 10),
                 "type": "Frecciarossa"
             })
             
        tool_msg = {
            "role": "tool",
            "content": json.dumps({"trains": mock_trains}),
            "tool_call_id": tool_call_id,
            "name": "search_trains"
        }
        
        asst_msg_final = {
            "role": "assistant",
            "content": f"😊 Ho trovato {num_results} soluzioni per {destination}. La prima parte alle {mock_trains[0]['departure_time']}."
        }

        # 7. Construct System Prompt Context
        if predataset:
             system_prompt = "{{SYSTEM_PROMPT}}"
        else:
            system_prompt = (
                f"Sei Talìa, l'assistente virtuale di Trenitalia.\n"
                f"<ctx>\n"
                f"stazione: {origin}\n"
                f"data: 2024-05-01\n" 
                f"ora: {ctx_time}\n"
                f"</ctx>\n"
                f"Oggi è mercoledì."
            )

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": self.rephrase(rng, user_text)},
                {"role": "assistant", "tool_calls": [tool_call_obj], "content": None},
                tool_msg,
                asst_msg_final
            ],
            "_meta": {
                "scenario": self.name,
                "seed": rng.seed,
                "run_id": run_id,
                "contexts": [
                    {
                        "slice_length": 2,
                        "params": {
                            "origin": origin,
                            "destination": destination,
                            "passengers": passengers,
                            "template": template,
                            "ctx_time": ctx_time,
                            "date": "2024-05-01",
                            "ui_state": '{"state":"idle","can":{"next":false,"prev":false,"back":false}}',
                            "trains_array": "[]"
                        }
                    }
                ]
            }
        }

