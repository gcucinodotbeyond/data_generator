import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom

# --- Data Constants ---
CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"
QA_RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "qa_pairs.json"

try:
    with open(RESOURCE_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])
except FileNotFoundError:
    STATIONS_ALL = ["Roma Termini", "Milano Centrale"]
    STATIONS_MAJOR = STATIONS_ALL

try:
    with open(QA_RESOURCE_PATH, 'r', encoding='utf-8') as f:
        QA_PAIRS = json.load(f)
except FileNotFoundError:
    QA_PAIRS = [
        ("Quali sono i livelli CartaFRECCIA?", "Ci sono 4 livelli: Base, Argento, Oro, Platino."),
        ("Cos'è il FRECCIAClub?", "È un circuito di sale esclusive per i clienti fidelizzati.")
    ]

class QA(Scenario):
    @property
    def name(self) -> str:
        return "qa"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # 1. Setup Context
        origin = rng.choice(STATIONS_MAJOR)
        ctx_time = f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}"
        
        # 2. Pick Q&A Pair
        q, a = rng.choice(QA_PAIRS)
        
        # 3. Construct Messages
        system_content = "{{SYSTEM_PROMPT}}"
        
        # 4. Define Context (Only one, predicting the answer)
        # Length = 2 (System + User)
        ctx_qa = {
            "slice_length": 2,
            "params": {
                "origin": origin,
                "ctx_time": ctx_time,
                "date": "2025-12-23",
                "ui_state": '{"state":"idle","can":{"next":false,"prev":false,"back":false}}',
                "trains_array": "[]"
            }
        }
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": [ctx_qa]
            }
        }
