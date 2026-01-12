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
    STATIONS_ALL = ["Roma Termini", "Milano Centrale", "Napoli Centrale"]
    STATIONS_MAJOR = STATIONS_ALL

class UiNavigation(Scenario):
    @property
    def name(self) -> str:
        return "ui_navigation"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        predataset = kwargs.get("predataset", True)
        
        # 1. Establish Context
        origin = rng.choice(STATIONS_MAJOR)
        dest = rng.choice([s for s in STATIONS_ALL if s != origin])
        ctx_time = f"{rng.randint(7, 20):02d}:{rng.randint(0, 59):02d}"
        
        # 2. Determine Action Type (Distribution matches recipe)
        p = rng.random()
        if p < 0.40:
            action_type = "next"
        elif p < 0.60:
            action_type = "prev"
        elif p < 0.75:
            action_type = "back"
        elif p < 0.90:
            action_type = "status"
        else:
            action_type = "show_changes"
            
        # 3. Setup Initial State & Trains
        # Mocking a list of trains visible on screen
        trains = [
            {"pos": 1, "id": f"FR{rng.randint(9000,9999)}", "dep": ctx_time, "arr": "12:00", "type": "Frecciarossa", "price": 50.0},
            {"pos": 2, "id": f"IC{rng.randint(500,800)}", "dep": ctx_time, "arr": "13:00", "type": "Intercity", "price": 30.0}
        ]
        
        # Set UI state flags based on action needed
        can_next = True
        can_prev = True
        
        if action_type == "next":
            can_next = True # Must be true
            user_phrases = ["Altri treni?", "Fammi vedere i prossimi", "Avanti", "Ce ne sono altri?"]
            can_prev = rng.choice([True, False])
        elif action_type == "prev":
            can_prev = True # Must be true
            user_phrases = ["Torna indietro", "Precedenti", "Voglio vedere quelli di prima", "Torna ai precedenti"]
            can_next = rng.choice([True, False])
        elif action_type == "back":
            user_phrases = ["Annulla", "Cambia ricerca", "Torna alla home", "Ricomincia"]
        elif action_type == "status":
            user_phrases = ["A che punto siamo?", "Riepilogo", "Cosa ho selezionato?", "Dettagli selezione"]
        elif action_type == "show_changes":
            user_phrases = ["Ci sono ritardi?", "E' in orario?", "Modifiche?", "Il primo è in orario?"]
        
        user_text = rng.choice(user_phrases)
        
        # 4. Construct Tool Call
        tool_call_args = {"action": action_type}
        
        # For show_changes, we typically need a train position if referring to "il primo" etc.
        if action_type == "show_changes":
            # Assume referring to first one for simplicity or random
            target_pos = 1
            tool_call_args["train_position"] = target_pos
            
        tool_call_id = "call_001"
        tool_call_obj = {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "ui_control",
                "arguments": json.dumps(tool_call_args)
            }
        }
        
        # 5. Construct Response
        tool_content_obj = {}
        asst_text = ""
        
        if action_type == "next":
            tool_content_obj = {
                "page": 2, 
                "total_pages": 3, 
                "trains": [{"pos": 1, "id": f"FR{rng.randint(8000,8999)}", "type": "Frecciarossa"}] # Simplified new list
            }
            asst_text = "😊 Ecco altri treni disponibili!"
            
        elif action_type == "prev":
            tool_content_obj = {
                "page": 1, 
                "total_pages": 3, 
                "trains": trains # Back to original
            }
            asst_text = "😊 Eccoci tornati ai treni precedenti."
            
        elif action_type == "back":
            tool_content_obj = {"state": "idle", "message": "Ricerca annullata"}
            asst_text = "😊 Ok, ricerca annullata. Dove vuoi andare?"
            
        elif action_type == "status":
            tool_content_obj = {
                "current_state": "results",
                "search_params": {"origin": origin, "destination": dest},
                "selection": None
            }
            asst_text = f"😊 Stai cercando treni da {origin} a {dest}."
            
        elif action_type == "show_changes":
            is_delayed = rng.choice([True, False])
            if is_delayed:
                tool_content_obj = {
                    "train_id": trains[0]["id"],
                    "status": "delayed",
                    "delay_minutes": rng.randint(5, 20),
                    "new_departure": "Later" 
                }
                asst_text = f"😔 Il treno ha {tool_content_obj['delay_minutes']} minuti di ritardo."
            else:
                 tool_content_obj = {
                    "train_id": trains[0]["id"],
                    "status": "on_time",
                    "changes": []
                }
                 asst_text = "😊 Tutto regolare, il treno è in orario!"

        tool_msg = {
            "role": "tool",
            "content": json.dumps(tool_content_obj),
            "tool_call_id": tool_call_id,
            "name": "ui_control"
        }
        
        asst_msg_final = {
            "role": "assistant",
            "content": asst_text
        }
        
        # 6. Build History
        if predataset:
             system_prompt = "{{SYSTEM_PROMPT}}"
        else:
             # Basic context
            system_prompt = (
                f"Sei Talìa...\n"
                f"<ctx>\n"
                f"stazione: {origin}\n"
                f"data: 2025-12-23\n"
                f"ora: {ctx_time}\n"
                f"</ctx>\n\n"
                f"<ui>\n"
                f'{{"state":"results","can":{{"next":{str(can_next).lower()},"prev":{str(can_prev).lower()},"back":true}}}}\n'
                f"</ui>\n\n"
                f"<trains>\n"
                f"{json.dumps(trains)}\n"
                f"</trains>"
            )

        # Messages: Sys -> User -> Asst(ToolCall) -> Tool -> Asst(Content)
        # However, for navigation, we often assume a previous context of search result.
        # But single-turn sample usually implies: Context is set (System), then User speaks.
        # So structure: [Sys, User, Asst(Call), Tool, Asst(Reply)] is correct for "Reactive" sample.
        
        # But wait, recipe "08_ui_navigation.md" examples often show just pure interaction.
        # e.g. "Golden 1": Sys, User("Treni per Roma" -> Search -> Tool -> Asst), User("Altri?") -> ToolCall(Next)...
        # But that's a multi-turn logical flow. 
        # Requirement: "Samples che dimostrano l'uso di ui_control".
        # If I generate a single sample starting with User: "Altri?", the System Prompt MUST contain the <ui> state and <trains> that contextually allow "next".
        # My implementation does exactly that (lines 145+ sets the System Prompt with current state).
        
        # NOTE: If we want strictly what's in the examples for Golden 1, it shows a FULL history starting from search.
        # But usually we train on single turns or slice histories. 
        # If I want to produce just the "ui_control" training sample, starting from an existing state (System) + User("Avanti") is cleanest and most efficient.
        # The Recipe Golden 8 is exactly that: [Sys, User("Avanti"), Asst(Call), Tool, Asst].
        # So I will stick to this single-turn relative to the UI state.
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
            {"role": "assistant", "tool_calls": [tool_call_obj], "content": None},
            tool_msg,
            asst_msg_final
        ]

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "seed": rng.seed,
                "run_id": run_id,
                "contexts": [
                    {
                        "slice_length": 2,
                        "params": {
                            "action": action_type,
                            "origin": origin,
                            "ctx_time": ctx_time,
                            "ui_state": f'{{"state":"results","can":{{"next":{str(can_next).lower()},"prev":{str(can_prev).lower()},"back":true}}}}',
                            "trains_array": json.dumps(trains)
                        }
                    }
                ]
            }
        }
