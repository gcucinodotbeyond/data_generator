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
        template = rng.choice(USER_TEMPLATES)
        user_text = template.format(destination=destination)
        
        # Add varied time/date info to user text strictly deterministically
        if rng.random() < 0.3:
            user_text += f" {date_request}"
        if time_period and rng.random() < 0.3:
            user_text += f" di {time_period}"
            
        # 5. Construct Expected Tool Call
        # We assume the system resolves relative dates (oggi/domani) to actual params if possible,
        # but for search_trains tool, it often accepts 'today', 'tomorrow' strings or just dates.
        # Let's align with the previous system's behavior or standard API.
        # Looking at previous templates: keys are origin, destination, date, time, passengers.
        
        tool_call = {
            "name": "search_trains",
            "arguments": {
                "origin": origin,
                "destination": destination,
                "passengers": passengers,
                # Simple logic: if user didn't specify, we might infer or leave null. 
                # For deterministic ground truth, we populate what is known.
                "date": "today" if "oggi" in user_text else ("tomorrow" if "domani" in user_text else None),
                "time": None # Simplified for now
            }
        }
        
        # Remove None values to clean up arguments
        tool_call["arguments"] = {k: v for k, v in tool_call["arguments"].items() if v is not None}
        
        # 6. Construct System Prompt Context
        # The kiosk needs to know where it is and what time it is.
        ctx_time = f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}"
        
        if predataset:
             system_prompt = "{{SYSTEM_PROMPT}}"
        else:
            system_prompt = (
                f"Sei Talìa, l'assistente virtuale di Trenitalia.\n"
                f"<ctx>\n"
                f"stazione: {origin}\n"
                f"data: 2024-05-01\n" # Fixed date for reproducibility or derived from seed? Fixed is safer for now.
                f"ora: {ctx_time}\n"
                f"</ctx>\n"
                f"Oggi è mercoledì."
            )

        return {
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
                    "passengers": passengers,
                    "template": template,
                    "ctx_time": ctx_time,
                    "date": "2024-05-01",
                    "ui_state": '{"state":"idle","can":{"next":false,"prev":false,"back":false}}',
                    "trains_array": "[]"
                }
            }
        }

