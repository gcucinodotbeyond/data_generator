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

FAIL_SCENARIOS = {
    # 1. Internal Error (Double)
    "double_internal_error": {
        "flow": "search",
        "steps": [
            {"type": "error", "content": "An internal error occurred", "silent": True},
            {"type": "error", "content": "An internal error occurred", "silent": False, 
             "reply": "😔 Doppio errore. 🙂 Un altro tentativo?", "user_response": "Vai, ripeti"},
            {"type": "success", "content": "OK", "reply": "🙂 Problema risolto! 😊 Quale ti piace?"}
        ]
    },
    # 2. Timeout
    "timeout_retry": {
        "flow": "search",
        "steps": [
            {"type": "error", "content": "Request timeout after 30s - server overloaded", "silent": True},
            {"type": "success", "content": "OK", "reply": "😊 Ecco i treni serali! 🙂 Quale preferisci?"}
        ]
    },
    # 3. No Trains (Alternative Time)
    "no_trains_alt_time": {
        "flow": "search",
        "steps": [
            {"type": "error", "content": '{"trains": [], "message": "No trains available after 22:00"}', "silent": False,
             "reply": "😔 Nessun treno disponibile a quest'ora. 😊 Controllo domani mattina presto?", "user_response": "Va bene, presto però", "change_params": {"time": "06:00", "date": "tomorrow"}},
            {"type": "success", "content": "OK", "reply": "😊 Perfetto! C'è un Frecciarossa alle 6:10. 🙂 Ti interessa?"}
        ]
    },
    # 4. Invalid Route (Suggest Hub)
    "invalid_route": {
        "flow": "search",
        "steps": [
             {"type": "error", "content": '{"error": "no_direct_connection", "message": "No direct trains. Suggested hub: Bologna Centrale"}', "silent": False,
              "reply": "😔 Non ci sono treni diretti. 🤔 Posso cercare con cambio a Bologna Centrale?", "user_response": "Ok va bene", "change_params": {"destination": "Bologna Centrale"}},
             {"type": "success", "content": "OK", "reply": "😊 Ecco i treni per Bologna! Da lì puoi cambiare. 🙂"}
        ]
    },
    # 5. Service Unavailable (Maintenance)
    "service_unavailable": {
        "flow": "search",
        "steps": [
            {"type": "error", "content": '{"error": "service_unavailable", "message": "Scheduled maintenance until 15:00"}', "silent": False,
             "reply": "😔 Sistema in manutenzione fino alle 15:00. 😊 Vuoi attendere?", "user_response": "Ok aspetto", "change_params": {"time": "15:00"}},
            {"type": "success", "content": "OK", "reply": "😊 Ore 15:00, ecco i treni disponibili! 🙂"}
        ]
    },
    # 6. Rate Limit
    "rate_limit": {
        "flow": "search",
        "steps": [
            {"type": "error", "content": '{"error": "rate_limited", "message": "Too many requests. Please wait 30 seconds"}', "silent": False,
             "reply": "😅 Un attimo, troppe richieste! 😊 Riprovo tra qualche secondo...", "user_response": "Ok"},
            {"type": "success", "content": "OK", "reply": "😊 Ecco i Frecciarossa! 🙂 Quale vuoi?"}
        ]
    },
    # 9. Payment Fail
    "payment_fail": {
        "flow": "purchase",
        "steps": [
            {"type": "error", "content": '{"error": "payment_gateway_timeout", "message": "Payment gateway did not respond in time. No charge was made."}', "silent": False,
             "reply": "😔 Problema con il pagamento, nessun addebito effettuato. 😊 Riprovo?", "user_response": "Sì vai"},
            {"type": "success", "content": "OK", "reply": "🎉 Ora sì! Biglietto confermato. Buon viaggio! 😊"}
        ]
    }
}

class SearchFail(Scenario):
    @property
    def name(self) -> str:
        return "search_fail"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # 1. Setup
        origin = rng.choice(STATIONS_MAJOR)
        dest = rng.choice([s for s in STATIONS_ALL if s != origin])
        ctx_time = f"{rng.randint(8, 20):02d}:{rng.randint(0, 59):02d}"
        
        scenario_key = rng.choice(list(FAIL_SCENARIOS.keys()))
        scenario = FAIL_SCENARIOS[scenario_key]
        
        messages = []
        contexts = []
        
        # System
        messages.append({"role": "system", "content": "{{SYSTEM_PROMPT}}"})
        
        # Initial Request
        messages.append({"role": "user", "content": f"Un treno per {dest}"})
        
        # Common Tools
        base_search_args = {"origin": origin, "destination": dest, "date": "today", "time": "now"}
        mock_trains = [{"train_id": "FR123", "departure_time": ctx_time, "arrival_time": "23:59", "price": [{"class_denomination": "2a", "price": "50.00"}]}]
        
        # Helper to add context
        def add_context(state="idle", trains="[]"):
            contexts.append({
                "slice_length": len(messages) + 1,
                "params": {
                    "origin": origin,
                    "ctx_time": ctx_time,
                    "date": "2025-12-23",
                    "ui_state": f'{{"state":"{state}"}}',
                    "trains_array": trains
                }
            })

        call_counter = 1
        
        if scenario["flow"] == "search":
            current_args = base_search_args.copy()
            
            for step in scenario["steps"]:
                add_context("idle", "[]") # Predict tool call
                
                # Apply param changes if any
                if "change_params" in step:
                    current_args.update(step["change_params"])
                    
                tool_call_id = f"call_{call_counter:03d}"
                call_counter += 1
                
                tool_call = {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": "search_trains", "arguments": json.dumps(current_args)}
                }
                messages.append({"role": "assistant", "tool_calls": [tool_call], "content": None})
                
                # Tool Output
                if step["content"] == "OK":
                    tool_out = json.dumps({"trains": mock_trains})
                else:
                    tool_out = step["content"]
                    
                messages.append({"role": "tool", "content": tool_out, "tool_call_id": tool_call_id, "name": "search_trains"})
                
                # Assistant Reply
                if not step.get("silent", False):
                    # Check if 'reply' is present, otherwise skip (some steps might be silent tool errors without reply, but our structure usually has silent=True for that)
                    if "reply" in step:
                        messages.append({"role": "assistant", "content": step["reply"]})
                        if "user_response" in step:
                            messages.append({"role": "user", "content": step["user_response"]})
                        
        elif scenario["flow"] == "purchase":
            # 1. Do successful search first
            add_context("idle", "[]")
            tool_call_id_s = f"call_{call_counter:03d}"
            call_counter += 1
            search_call = {
                 "id": tool_call_id_s,
                 "type": "function",
                 "function": {"name": "search_trains", "arguments": json.dumps(base_search_args)}
            }
            messages.append({"role": "assistant", "tool_calls": [search_call], "content": None})
            messages.append({"role": "tool", "content": json.dumps({"trains": mock_trains}), "tool_call_id": tool_call_id_s, "name": "search_trains"})
            messages.append({"role": "assistant", "content": "Ecco i treni."})
            messages.append({"role": "user", "content": "Prendo il primo"})
            
            # 2. Purchase loop
            for step in scenario["steps"]:
                add_context("results", json.dumps(mock_trains))
                
                tool_call_id = f"call_{call_counter:03d}"
                call_counter += 1
                
                tool_call = {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {"name": "purchase_ticket", "arguments": json.dumps({"train_id": "FR123", "class": "2a"})}
                }
                messages.append({"role": "assistant", "tool_calls": [tool_call], "content": None})
                
                if step["content"] == "OK":
                    tool_out = json.dumps({"status": "OK", "confirmation_code": "ABC"})
                else:
                    tool_out = step["content"]
                
                messages.append({"role": "tool", "content": tool_out, "tool_call_id": tool_call_id, "name": "purchase_ticket"})
                
                if not step.get("silent", False):
                     if "reply" in step:
                         messages.append({"role": "assistant", "content": step["reply"]})
                         if "user_response" in step:
                            messages.append({"role": "user", "content": step["user_response"]})

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": contexts
            }
        }
