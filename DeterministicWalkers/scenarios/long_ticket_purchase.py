import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.ticket_purchase import TicketPurchase

# Inherit helper data loading from TicketPurchase or duplicate needed parts
# For simplicity, we assume TicketPurchase setup is available or copy basics.
# To avoid import issues if TicketPurchase assumes things, let's copy the light constants.

CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"
try:
    with open(RESOURCE_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
    STATIONS_ALL = sorted(list(set(STATIONS_ALL)))
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])
except FileNotFoundError:
    STATIONS_ALL = ["Roma Termini", "Milano Centrale"]
    STATIONS_MAJOR = STATIONS_ALL

class LongTicketPurchase(Scenario):
    @property
    def name(self) -> str:
        return "long_ticket_purchase"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        predataset = kwargs.get("predataset", True)
        
        # 1. Setup Context
        origin = rng.choice(STATIONS_MAJOR)
        dest = rng.choice([s for s in STATIONS_ALL if s != origin])
        
        # 2. Determine Flow (Pace)
        # 0 = Short (Search -> Purchase)
        # 1 = Medium (Search -> Refine -> Purchase)
        # 2 = Long (Search -> Nav -> Refine -> Purchase) OR (Search -> Nav -> Purchase)
        
        steps = ["search"]
        
        # 30% chance for Navigation
        if rng.random() < 0.3:
            steps.append("navigation")
            
        # 40% chance for Refinement
        if rng.random() < 0.4:
            steps.append("refine")
            
        steps.append("purchase")
        
        # --- EXECUTION ---
        messages = []
        contexts = []
        
        # System Prompt
        if predataset:
            sys_content = "{{SYSTEM_PROMPT}}"
        else:
            sys_content = f"Sei Talìa... <ctx>stazione: {origin}</ctx>" # Simplified for non-predataset
            
        messages.append({"role": "system", "content": sys_content})
        
        current_trains_list = []
        
        # Keep track of tool calls count for IDs
        tool_counter = 1
        
        # Define base context time - will be refined if search step has constraints
        base_hour = rng.randint(6, 22)
        ctx_time = f"{base_hour:02d}:{rng.randint(0, 59):02d}"
        
        for step_idx, step in enumerate(steps):
            
            # --- STEP: SEARCH ---
            if step == "search":
                # User Msg
                corpus_search = self.corpus.get("search_queries", [])
                
                # Default User Text
                user_text = f"Voglio andare a {dest}"
                
                if corpus_search and rng.random() < 0.8:
                    tmpl = rng.choice(corpus_search)
                    
                    # --- Check Time Constraints ---
                    if "{period_morning}" in tmpl:
                        base_hour = rng.randint(6, 11)
                        tmpl = tmpl.replace("{period_morning}", rng.choice(["stamattina", "questa mattina"]))
                    elif "{period_afternoon}" in tmpl:
                        base_hour = rng.randint(12, 17)
                        tmpl = tmpl.replace("{period_afternoon}", rng.choice(["oggi pomeriggio", "questo pomeriggio"]))
                    elif "{period_evening}" in tmpl:
                        base_hour = rng.randint(16, 21)
                        tmpl = tmpl.replace("{period_evening}", rng.choice(["stasera", "questa sera"]))
                        
                    # Update ctx_time based on constraints
                    ctx_time = f"{base_hour:02d}:{rng.randint(0, 59):02d}"
                    
                    # Prepare formatting args
                    user_text = tmpl.replace("{destination}", dest).replace("{origin}", origin)
                    
                    # Handle relative date placeholders
                    replacements = {
                        "{relative_date_morning}": "domani mattina",
                        "{relative_date_afternoon}": "domani pomeriggio",
                        "{relative_date_evening}": "domani sera",
                        "{relative_date}": rng.choice(["domani", "dopodomani"]),
                        "{relative_today}": "oggi"
                    }
                    for k, v in replacements.items():
                        user_text = user_text.replace(k, v)

                    if "{time_request}" in user_text:
                        # Construct a time request relative to 'now' (10:00ish)
                        req_h = (base_hour + rng.randint(1, 4)) % 24
                        req_m = rng.choice([0, 15, 30])
                        user_text = user_text.replace("{time_request}", f"{req_h:02d}:{req_m:02d}")
                else:
                    user_text = f"Voglio andare a {dest}"
                
                # Rephrase
                user_text = self.rephrase(rng, user_text)
                
                messages.append({"role": "user", "content": user_text})
                
                # Context Capture for Search Prediction
                # (When we predict the assistant call)
                contexts.append({
                    "slice_length": len(messages), 
                    "params": {
                        "origin": origin,
                        "destination": dest, # Added dest for completeness
                        "ctx_time": ctx_time, # Added ctx_time
                        "date": "2024-05-01", # Added date default
                        "ui_state": '{"state":"idle"}',
                        "trains_array": "[]"
                    }
                })
                
                # Assistant Call
                tool_id = f"call_{tool_counter:03d}"
                tool_counter += 1
                
                call_args = {"origin": origin, "destination": dest, "date": "today", "time": "now", "passengers": 1}
                msgs_tool = {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {"name": "search_trains", "arguments": json.dumps(call_args)}
                    }],
                    "content": None
                }
                messages.append(msgs_tool)
                
                # Tool Result
                # Generate random trains
                current_trains_list = [
                    {"pos": 1, "id": f"FR{rng.randint(1000,9999)}", "dep": "10:00", "arr": "11:30", "type": "Frecciarossa", "stops": 0, "price": "45.00"},
                    {"pos": 2, "id": f"IC{rng.randint(1000,9999)}", "dep": "10:30", "arr": "12:30", "type": "Intercity", "stops": 2, "price": "25.00"}
                ]
                
                # Ensure we strictly follow schema if needed, but for dynamic we keep it realistic
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"trains": current_trains_list}),
                    "tool_call_id": tool_id,
                    "name": "search_trains"
                })
                
                # Assistant Reply
                messages.append({
                    "role": "assistant", 
                    "content": f"😊 Ho trovato {len(current_trains_list)} treni per {dest}. Quale preferisci?"
                })

            # --- STEP: NAVIGATION ---
            elif step == "navigation":
                # User Msg
                corpus_nav = self.corpus.get("navigation", [])
                if corpus_nav:
                    user_text = rng.choice(corpus_nav)
                else:
                    user_text = "Fammi vedere i prossimi"
                    
                user_text = self.rephrase(rng, user_text)
                messages.append({"role": "user", "content": user_text})
                
                contexts.append({
                    "slice_length": len(messages),
                    "params": {
                        "origin": origin,
                        "ui_state": '{"state":"results","can":{"next":true}}',
                        "trains_array": json.dumps(current_trains_list)
                    }
                })
                
                # Assistant Call
                tool_id = f"call_{tool_counter:03d}"
                tool_counter += 1
                
                msgs_tool = {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {"name": "ui_control", "arguments": json.dumps({"action": "next"})}
                    }],
                    "content": None
                }
                messages.append(msgs_tool)
                
                # Tool Result (New Page)
                current_trains_list = [
                    {"pos": 1, "id": f"RV{rng.randint(1000,9999)}", "dep": "11:00", "arr": "13:00", "type": "Regionale", "stops": 5, "price": "12.00"},
                ]
                
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"trains": current_trains_list, "page": 2}),
                    "tool_call_id": tool_id,
                    "name": "ui_control"
                })
                
                messages.append({
                    "role": "assistant", 
                    "content": "😊 Ecco altri risultati."
                })

            # --- STEP: REFINE ---
            elif step == "refine":
                # User Msg
                corpus_refine = self.corpus.get("refinements", [])
                # Filter refinements to ensure they make sense? 
                # Some are specific like "To Rome". We should stick to generic or hope rng is fun.
                # Or use simple generated ones if corpus is weird.
                # Let's use corpus but fallback if empty
                if corpus_refine and rng.random() < 0.8:
                    user_text = rng.choice(corpus_refine)
                    # Hydrate if needed
                    user_text = user_text.replace("{destination}", dest).replace("{origin}", origin)
                    
                    if "{time_request}" in user_text:
                         # For refinement, usually implies "later" or "after X"
                         req_h = rng.randint(12, 22)
                         req_m = rng.choice([0, 15, 30])
                         user_text = user_text.replace("{time_request}", f"{req_h:02d}:{req_m:02d}")
                    
                    # Hydrate relative time placeholders (generic fallback)
                    replacements = {
                        "{period_morning}": rng.choice(["domani mattina", "la mattina", "in mattinata"]),
                        "{period_afternoon}": rng.choice(["di pomeriggio", "nel pomeriggio"]),
                        "{period_evening}": rng.choice(["stasera", "di sera"]),
                        "{relative_date}": "domani",
                        "{relative_date_morning}": "domani mattina",
                        "{relative_date_afternoon}": "domani pomeriggio",
                        "{relative_date_evening}": "domani sera",
                        "{relative_today}": "oggi"
                    }
                    for k, v in replacements.items():
                        user_text = user_text.replace(k, v)
                else:
                    user_text = "C'è qualcosa dopo le 12?"
                
                user_text = self.rephrase(rng, user_text)
                messages.append({"role": "user", "content": user_text})
                
                contexts.append({
                    "slice_length": len(messages),
                    "params": {
                        "origin": origin,
                        "ui_state": '{"state":"results"}',
                        "trains_array": json.dumps(current_trains_list)
                    }
                })
                
                # Assistant Call
                tool_id = f"call_{tool_counter:03d}"
                tool_counter += 1
                
                # In strict logic we should parse user intent for args. 
                # For deterministic gen, we just fake the args to match intent or just generic "later"
                call_args = {"origin": origin, "destination": dest, "date": "today", "time": "12:00"}
                
                msgs_tool = {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {"name": "search_trains", "arguments": json.dumps(call_args)}
                    }],
                    "content": None
                }
                messages.append(msgs_tool)
                
                # Tool Result
                current_trains_list = [
                    {"pos": 1, "id": f"FR{rng.randint(5000,5999)}", "dep": "12:15", "arr": "13:45", "type": "Frecciarossa", "stops": 0, "price": "45.00"}
                ]
                
                messages.append({
                    "role": "tool",
                    "content": json.dumps({"trains": current_trains_list}),
                    "tool_call_id": tool_id,
                    "name": "search_trains"
                })
                
                messages.append({
                    "role": "assistant", 
                    "content": f"😊 Ho trovato nuove soluzioni."
                })

            # --- STEP: PURCHASE ---
            elif step == "purchase":
                # User Msg
                # User Msg
                corpus_buy = self.corpus.get("purchase_intents", [])
                if corpus_buy and rng.random() < 0.8:
                    user_text = rng.choice(corpus_buy)
                else:
                    user_text = "Prendo il primo"
                
                # Hydrate purchase intent
                # We assume User picks the first one from latest list available in context
                target_train_info = current_trains_list[0]
                user_text = user_text.replace("{time_request}", target_train_info["dep"])
                user_text = user_text.replace("{destination}", dest).replace("{origin}", origin)
                
                user_text = self.rephrase(rng, user_text)
                messages.append({"role": "user", "content": user_text})
                
                contexts.append({
                    "slice_length": len(messages),
                    "params": {
                        "origin": origin,
                        "ui_state": '{"state":"results"}',
                        "trains_array": json.dumps(current_trains_list)
                    }
                })
                
                # Assistant Call
                tool_id = f"call_{tool_counter:03d}"
                tool_counter += 1
                
                # We assume User picks the first one from latest list
                target = current_trains_list[0]
                call_args = {"train_id": target["id"], "class": "Seconda Classe"}
                
                msgs_tool = {
                    "role": "assistant",
                    "tool_calls": [{
                        "id": tool_id,
                        "type": "function",
                        "function": {"name": "purchase_ticket", "arguments": json.dumps(call_args)}
                    }],
                    "content": None
                }
                messages.append(msgs_tool)
                
                # Tool Result
                messages.append({
                    "role": "tool",
                    "content": json.dumps({
                        "status": "OK", 
                        "ticket_id": f"TK{rng.randint(100000,999999)}", 
                        "train_id": target["id"],
                        "class": "Seconda Classe",
                        "price": target["price"],
                        "payment_method": "card",
                        "confirmation_code": f"CONF{rng.randint(100,999)}"
                    }),
                    "tool_call_id": tool_id,
                    "name": "purchase_ticket"
                })
                
                messages.append({
                    "role": "assistant", 
                    "content": "🎉 Biglietto acquistato! Buon viaggio!"
                })

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": contexts
            }
        }
