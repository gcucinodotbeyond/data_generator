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
        # Goal: Generate a 3-turn conversation
        # Turn 1: User asks for generic (Search)
        # Turn 2: User refines (Filter/Sort - Fake tool call or just chat)
        # Turn 3: User buys (Purchase)
        
        origin = rng.choice(STATIONS_MAJOR)
        dest = rng.choice([s for s in STATIONS_ALL if s != origin])
        
        # --- PHASE 1: SEARCH ---
        ctx_time_1 = "09:00"
        date = "2025-12-23"
        
        # State 1: Idle
        sys_prompt = "{{SYSTEM_PROMPT}}"
        
        user_msg_1 = {"role": "user", "content": f"Voglio andare a {dest}"}
        
        # Fake Search Tool Call
        # In a real engine, we'd run the tool. Here we mock.
        tool_call_1 = {
             "name": "search_trains",
             "arguments": {"origin": origin, "destination": dest}
        }
        asst_msg_1 = {"role": "assistant", "tool_calls": [tool_call_1]}
        
        # Fake Tool Output (Trains List A - maybe messy/many)
        # We'll just define the final train list for simplicity of the prompt context in Turn 2
        # But to be realistic, let's say the first list was big.
        
        tool_msg_1 = {
            "role": "tool", 
            "content": '{"trains": [{"id":"many..."}]}', # Placeholder content, generator doesn't simulate full tool output logic yet aside from final state context
            "tool_call_id": "call_1" # Fake ID logic
        }
        
        asst_reply_1 = {"role": "assistant", "content": "Ho trovato molte soluzioni. Preferisci un orario specifico?"}
        
        # --- PHASE 2: REFINE ---
        user_msg_2 = {"role": "user", "content": "Solo dopo le 10"}
        
        # Let's assume the assistant does a UI filter or internal logic. 
        # For this dataset, maybe no tool call, just updating the View?
        # Or maybe re-search. Let's say re-search.
        tool_call_2 = {
             "name": "search_trains",
             "arguments": {"origin": origin, "destination": dest, "time": "10:00"}
        }
        asst_msg_2 = {"role": "assistant", "tool_calls": [tool_call_2]}
        
        # --- PHASE 3: PURCHASE ---
        # Now we present the final list (Context for Turn 3)
        trains_final = [
             {"pos": 1, "id": "FR9999", "dep": "10:15", "arr": "11:00", "type": "Frecciarossa", "price": "40.00"},
             {"pos": 2, "id": "IC8888", "dep": "10:45", "arr": "12:00", "type": "Intercity", "price": "20.00"}
        ]
        
        tool_msg_2 = {
             "role": "tool",
             "content": json.dumps({"trains": trains_final}),
             "tool_call_id": "call_2"
        }
        
        asst_reply_2 = {"role": "assistant", "content": "Ecco i treni dopo le 10. Il primo parte alle 10:15."}
        
        user_msg_3 = {"role": "user", "content": "Prendo il primo"}
        
        tool_call_3 = {
             "name": "purchase_ticket",
             "arguments": {"train_id": "FR9999", "class": "Seconda Classe"}
        }
        asst_msg_3 = {"role": "assistant", "tool_calls": [tool_call_3]}

        # --- CONSTRUCT FULL HISTORY ---
        messages = [
            {"role": "system", "content": sys_prompt},
            user_msg_1,
            asst_msg_1,
            # For simplicity in pure generation without a simulator, we often omit the tool output messages in the history 
            # if we are just training the model to make the CALL.
            # BUT, for multi-turn chat, we should ideally have them. 
            # However, the recipe "02_ticket_purchase" focuses on single turn "State -> User -> Tool".
            # The slicing script cuts everything BEFORE the target user message usually? 
            # Wait, the slicing script takes `messages[:msg_len]`. 
            # So if we want to train on Turn 3, we need the history [Sys, U1, A1, U2, A2, U3] -> A3.
            
            # Let's put minimal history.
            asst_reply_1,
            user_msg_2,
            asst_msg_2,
            asst_reply_2, 
            user_msg_3,
            asst_msg_3
        ]
        
        # --- DEFINE CONTEXTS FOR SLICING ---
        # We want to generate training samples for specific points.
        
        # 1. First Search (User says "Voglio andare...")
        # Index in messages list where this turn ends (User -> Assistant). 
        # Actually slice takes messages[:len]. 
        # If we want to predict asst_msg_1, input is [Sys, User1]. Length = 2.
        
        ctx_1 = {
            "slice_length": 2, # [Sys, U1] -> Predict A1
            "params": {
                "origin": origin,
                "ctx_time": ctx_time_1,
                "date": date,
                "ui_state": '{"state":"idle"}',
                "trains_array": "[]" # No trains yet
            }
        }
        
        # 2. Refine (User says "Solo dopo le 10")
        # History: Sys, U1, A1, Reply1, U2.
        
        ctx_2 = {
            "slice_length": 5, # [Sys, U1, A1, Reply1, U2] -> Predict A2
            "params": {
                "origin": origin,
                "ctx_time": "09:01",
                "ui_state": '{"state":"results"}', # Results from first search visible
                "trains_array": '[{"id":"generic_list"}]' # Fake previous list
            }
        }
        
        # 3. Purchase (User says "Prendo il primo")
        # List: Sys, U1, A1, Reply1, U2, A2, Reply2, U3
        # Length: 8
        ctx_3 = {
            "slice_length": 8,
            "params": {
                "origin": origin,
                "ctx_time": "09:02",
                "ui_state": '{"state":"results"}', 
                "trains_array": json.dumps(trains_final) # The specifi list for this purchase
            }
        }
        
        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": [ctx_1, ctx_2, ctx_3]
            }
        }
