import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom

# --- Data Constants ---
CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"

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

OFF_TOPIC_QUERIES = [
    # Crypto/Finance
    "Cosa ne pensi di Bitcoin? Conviene investire ora?",
    "E gli NFT? Potrebbero essere un buon investimento?",
    "Come va la borsa oggi?",
    "Mi consigli un fondo pensione?",
    
    # Sport
    "Secondo te chi vincerà lo scudetto quest'anno?",
    "E la Champions League? Pronostico?",
    "Hai visto la partita ieri?",
    "Chi è il miglior giocatore del mondo?",
    
    # Cooking
    "Mi dai la ricetta della carbonara perfetta?",
    "E il tiramisù? Come si fa?",
    "Come cucino l'arrosto?",
    "Tempo di cottura della pasta?",
    
    # Gardening
    "Come si coltivano i pomodori in balcone?",
    "E le piante grasse? Come si annaffiano?",
    "Quanto spesso devo potare le rose?",
    "Il ficus sta perdendo foglie, che faccio?",
    
    # Tech
    "Qual è il miglior smartphone del 2025?",
    "E i migliori laptop per lavorare?",
    "Meglio iOS o Android?",
    "Come formattare il PC?",
    
    # Movies/TV
    "Che film mi consigli da vedere stasera?",
    "E serie TV su Netflix?",
    "Chi ha vinto l'Oscar?",
    "Ti piace Star Wars?",
    
    # Politics/History
    "Cosa ne pensi del governo attuale?",
    "E le prossime elezioni?",
    "Raccontami la storia del Rinascimento",
    "E la Seconda Guerra Mondiale?",
    
    # Weather
    "Che tempo farà domani a Venezia?",
    "E dopodomani?",
    "Pioverà nel weekend?",
    "Fa freddo fuori?"
]

REFUSAL_TEMPLATES = [
    "😔 Non è la mia specialità! 😊 Sono qui per i treni invece.",
    "😔 Non me ne occupo. 😄 Viaggi in treno da organizzare?",
    "😕 Quello non è il mio campo! 😊 Per i treni invece perfetto.",
    "🤔 Non posso aiutarti con questo. 😊 Biglietti da comprare?",
    "😔 Mi dispiace, non so rispondere. 😄 Treni però sì!",
    "😔 Non posso dare consigli su questo! 😊 Chiedimi pure di orari e stazioni.",
    "😕 Argomento fuori dalla mia portata! 😄 Posso cercarti un treno?",
    "🤔 Non saprei proprio! 😊 Concentriamoci sul tuo viaggio in treno.",
    "😔 Non sono programmata per questo! 😄 Ma sono un asso con i treni Frecce."
]

class Refusal(Scenario):
    @property
    def name(self) -> str:
        return "refusal"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # 1. Setup
        origin = rng.choice(STATIONS_MAJOR)
        
        messages = []
        contexts = []
        
        # System
        system_content = "{{SYSTEM_PROMPT}}"
        messages.append({"role": "system", "content": system_content})
        
        # 2. Generate Refusal Loop (2-4 turns)
        num_refusals = rng.randint(2, 4)
        used_queries = []
        
        # Random time context
        ctx_time = f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}"
        
        for i in range(num_refusals):
            # Pick unique query
            query = rng.choice([q for q in OFF_TOPIC_QUERIES if q not in used_queries])
            used_queries.append(query)
            
            refusal = rng.choice(REFUSAL_TEMPLATES)
            
            # Predict this refusal
            contexts.append({
                "slice_length": len(messages) + 1,
                "params": {
                    "origin": origin,
                    "ctx_time": ctx_time,
                    "date": "2025-12-23",
                    "ui_state": '{"state":"idle","can":{"next":false,"prev":false,"back":false}}',
                    "trains_array": "[]"
                }
            })
            
            messages.append({"role": "user", "content": query})
            messages.append({"role": "assistant", "content": refusal})
            
        # 3. Optional Final Valid Search (27.5% chance ~ 0.275)
        if rng.random() < 0.275:
            dest = rng.choice([s for s in STATIONS_ALL if s != origin])
            
            # User transition
            transitions = [
                f"Va bene, cercami un treno per {dest}",
                f"Ok, devo andare a {dest}",
                f"Lascia stare. Un biglietto per {dest}",
                f"Allora portami a {dest}",
                f"Vabbè, andiamo a {dest}"
            ]
            user_msg = rng.choice(transitions)
            
            # Mock Search
            tool_call_id = "call_refusal_search"
            trains = [{"train_id": "FR1234", "departure_time": ctx_time, "arrival_time": "23:59", "train_type": "Frecciarossa"}]
            tool_block = {
                "role": "assistant",
                "tool_calls": [{
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": "search_trains",
                        "arguments": json.dumps({"origin": origin, "destination": dest, "date": "today", "time": "now", "passengers": 1})
                    }
                }],
                "content": None
            }
            tool_res = {
                "role": "tool",
                "content": json.dumps({"trains": trains}),
                "tool_call_id": tool_call_id,
                "name": "search_trains"
            }
            final_reply = {
                "role": "assistant",
                "content": f"😊 Frecciarossa delle {ctx_time} per {dest}! 🙂 Questo sì che posso aiutarti!"
            }
            
            contexts.append({
                "slice_length": len(messages) + 1,
                "params": {
                    "origin": origin,
                    "ctx_time": ctx_time,
                    "ui_state": '{"state":"idle"}',
                    "trains_array": "[]"
                }
            })
            
            messages.append({"role": "user", "content": user_msg})
            messages.append(tool_block)
            messages.append(tool_res)
            messages.append(final_reply)

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": contexts
            }
        }
