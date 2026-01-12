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

# Scenarios containing flow instructions and dialogue pairs
RUDE_SCENARIOS = {
    "price_after_purchase": {
        "type": "after_purchase",
        "dialogue": [
            ("89 euro?! Ma è una follia! Siete dei ladri!", "😔 Capisco che il prezzo ti sembri alto. 😌 La tariffa varia in base a disponibilità e anticipo dell'acquisto."),
            ("Ma io non ho tempo per comprare prima! È sempre così caro?", "😌 Acquistando con anticipo trovi tariffe Economy molto più convenienti. 🤔 Posso mostrarti le opzioni la prossima volta?"),
            ("Sì va bene, ma è comunque assurdo.", "😊 Capisco. Il biglietto è valido, e se hai problemi puoi rivolgerti all'assistenza. Buon viaggio!")
        ]
    },
    "discrimination": {
        "type": "before_purchase",
        "trigger": "search_result",
        "dialogue": [
            ("Spero non ci siano quegli stranieri che fanno casino.", "😌 Ti chiedo di evitare commenti inappropriati sui passeggeri. 🙂 Vuoi procedere con l'acquisto?"),
            ("Ma io dico solo che vorrei viaggiare tranquillo senza certi tipi.", "😔 Non posso accettare generalizzazioni. Trenitalia è un servizio per tutti. 😌 Posso aiutarti con il biglietto?"),
            ("Ok ok, scusa, prendo quello.", None) # No asst reply here, proceeds to purchase
        ]
    },
    "emergency": {
        "type": "before_purchase",
        "trigger": "search_result",
        "dialogue": [
            ("Non c'è uno sconto per emergenze? Non ho molti soldi con me!", "😔 Mi dispiace, non esistono sconti per emergenze al chiosco. 😌 Però il prezzo attuale è già tra i più bassi."),
            ("Ma è un'emergenza vera! Mia madre è in ospedale!", "😔 Capisco la situazione difficile e mi dispiace sinceramente. 😌 Purtroppo le tariffe sono fisse. Posso procedere con l'acquisto?"),
            ("Ok va bene, fammelo prendere.", None)
        ]
    },
    "delay_complaint": {
        "type": "before_search", # Or immediately after tool result
        "trigger": "search_result",
        "dialogue": [
            ("Sempre promesse! L'ultima volta avete rovinato un appuntamento importante!", "😔 Capisco la tua frustrazione per quella brutta esperienza. 🤔 Per ritardi oltre 60 minuti hai diritto a indennizzo, lo sapevi?"),
            ("Sì ma non risarcisce il tempo perso! È inaccettabile!", "😌 Hai ragione che il tempo non si recupera. Possiamo solo impegnarci perché non succeda più. 😊 Vuoi procedere?"),
            ("Sì dai, speriamo bene.", None)
        ]
    },
    "service_complaint": {
         "type": "after_purchase",
         "dialogue": [
             ("Il servizio fa schifo! Biglietterie chiuse, self-service rotti!", "😔 Mi dispiace per i disagi. 😌 Come assistente digitale sono sempre disponibile però!"),
             ("Almeno tu funzioni... ma è vergognoso!", "😌 Capisco lo sfogo. Segnalerò il disservizio. 😊 Buon viaggio ora.")
         ]
    }
}

class Rude(Scenario):
    @property
    def name(self) -> str:
        return "rude"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # 1. Setup
        origin = rng.choice(STATIONS_MAJOR)
        dest = rng.choice([s for s in STATIONS_ALL if s != origin])
        ctx_time = f"{rng.randint(8, 18):02d}:{rng.randint(0, 59):02d}"
        
        scenario_key = rng.choice(list(RUDE_SCENARIOS.keys()))
        scenario = RUDE_SCENARIOS[scenario_key]
        
        type_ = scenario["type"]
        dialogue = scenario["dialogue"]
        
        messages = []
        contexts = []
        
        # System
        messages.append({"role": "system", "content": "{{SYSTEM_PROMPT}}"})
        
        # --- PHASE 1: SEARCH ---
        user_init = f"Devo andare a {dest}"
        if scenario_key == "emergency":
            user_init += ", è un'emergenza!"
        elif scenario_key == "delay_complaint":
            user_init += ", ma spero non siate in ritardo come al solito!"
            
        # Context 1: Search Prediction
        contexts.append({
            "slice_length": 2,
            "params": {
                "origin": origin,
                "ctx_time": ctx_time,
                "date": "2025-12-23",
                "ui_state": '{"state":"idle"}',
                "trains_array": "[]"
            }
        })
        
        tool_call_id_1 = "call_search"
        search_tool_call = {
             "id": tool_call_id_1,
             "type": "function",
             "function": {"name": "search_trains", "arguments": json.dumps({"origin": origin, "destination": dest, "date": "today"})}
        }
        train_price = 89.00 if "price" in scenario_key else 45.00
        mock_trains = [{"train_id": "FR9999", "departure_time": ctx_time, "arrival_time": "23:59", "price": [{"class_denomination": "Seconda Classe", "price": f"{train_price:.2f}"}]}]
        
        messages.append({"role": "user", "content": user_init})
        messages.append({"role": "assistant", "tool_calls": [search_tool_call], "content": None})
        messages.append({"role": "tool", "content": json.dumps({"trains": mock_trains}), "tool_call_id": tool_call_id_1, "name": "search_trains"})
        
        asst_search_reply = f"😊 Frecciarossa delle {ctx_time}! 🙂 Lo prendiamo?"
        messages.append({"role": "assistant", "content": asst_search_reply})
        
        # --- PHASE 2: MIDDLE (Before Purchase Conflict) ---
        if type_ == "before_purchase":
            for i, (usr_text, asst_text) in enumerate(dialogue):
                # Context for this turn
                contexts.append({
                    "slice_length": len(messages) + 1,
                    "params": {
                        "origin": origin,
                        "ui_state": '{"state":"results"}',
                        "trains_array": json.dumps(mock_trains)
                    }
                })
                messages.append({"role": "user", "content": usr_text})
                if asst_text:
                    messages.append({"role": "assistant", "content": asst_text})
        else:
            # Normal confirmation if conflict is later
            # User says "Ok"
            messages.append({"role": "user", "content": "Sì, va bene"})

        # --- PHASE 3: PURCHASE ---
        tool_call_id_2 = "call_buy"
        buy_tool_call = {
             "id": tool_call_id_2,
             "type": "function",
             "function": {"name": "purchase_ticket", "arguments": json.dumps({"train_id": "FR9999", "class": "Seconda Classe"})}
        }
        
        # In 'before_purchase' case, the last USER msg was the resolution (e.g. "Ok prendo il biglietto")
        # In 'after_purchase' case, the last USER msg was "Sì, va bene"
        
        # Add context for purchase tool call
        contexts.append({
             "slice_length": len(messages) + 1, # Predict Tool Call
             "params": {
                 "origin": origin,
                 "ui_state": '{"state":"results"}',
                 "trains_array": json.dumps(mock_trains)
             }
        })
        
        messages.append({"role": "assistant", "tool_calls": [buy_tool_call], "content": None})
        messages.append({"role": "tool", "content": json.dumps({"status": "OK", "confirmation_code": "XYZ123"}), "tool_call_id": tool_call_id_2, "name": "purchase_ticket"})
        messages.append({"role": "assistant", "content": "🎉 Biglietto confermato. Codice: XYZ123."})
        
        # --- PHASE 4: AFTER (Post Purchase Conflict) ---
        if type_ == "after_purchase":
             for i, (usr_text, asst_text) in enumerate(dialogue):
                contexts.append({
                    "slice_length": len(messages) + 1,
                    "params": {
                        "origin": origin,
                        "ui_state": '{"state":"purchased"}',
                        "trains_array": json.dumps(mock_trains)
                    }
                })
                messages.append({"role": "user", "content": usr_text})
                if asst_text:
                    messages.append({"role": "assistant", "content": asst_text})

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": contexts
            }
        }
