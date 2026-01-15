import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.base_scenario import (
    StationManager,
    TimeManager,
    MessageBuilder,
    ContextBuilder,
    SearchComponent,
    PurchaseComponent,
    ToolCallBuilder
)

class LongTicketPurchase(Scenario):
    """
    Demonstrates composition: Search → optional Navigation → optional Refine → Purchase.
    This scenario shows how complex flows can be built from simple components.
    """
    
    @property
    def name(self) -> str:
        return "long_ticket_purchase"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        # Determine flow 
        steps = ["search"]
        
        if rng.random() < 0.3:  # 30% chance for navigation
            steps.append("navigation")
        
        if rng.random() < 0.4:  # 40% chance for refinement
            steps.append("refine")
        
        steps.append("purchase")
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        current_trains = []
        ctx_time = None
        
        for step_idx, step in enumerate(steps):
            if step == "search":
                # Initial search
                search_component = SearchComponent(
                    origin=origin,
                    destination=destination,
                    corpus=self.corpus,
                    rephrase_fn=self.rephrase
                )
                ctx_time, current_trains = search_component.build(
                    rng, run_id + step_idx, msg_builder, ctx_builder, is_starter=True
                )
            
            elif step == "navigation":
                # Navigate to next page
                corpus_nav = self.corpus.get("navigation", [])
                user_text = rng.choice(corpus_nav) if corpus_nav else "Fammi vedere i prossimi"
                user_text = self.rephrase(rng, user_text)
                
                ctx_builder.add_context(
                    slice_length=msg_builder.current_length() + 4, # User + Tool + Resp + Asst
                    origin=origin,
                    ui_state='{"state":"results","can":{"next":true}}',
                    trains_array=json.dumps(current_trains)
                )
                
                msg_builder.add_user(user_text)
                
                # UI control tool call
                tool_call_id = msg_builder.generate_tool_call_id()
                tool_call = {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": "ui_control",
                        "arguments": json.dumps({"action": "next"})
                    }
                }
                
                # Execute navigation directly calling helper to simulate result
                # We need to update current trains
                # Simpler: just rotate them or dummy update
                
                # We need to simulate the backend call
                import sys
                if str(Path(__file__).parent.parent) not in sys.path:
                     sys.path.append(str(Path(__file__).parent.parent))
                from mock_api import MockBackend
                
                backend = MockBackend(seed=rng.seed + run_id)
                # Init backend state
                backend.search_trains(json.dumps({"origin": origin, "destination": destination}))
                nav_response = backend.ui_control(json.dumps({"action": "next"}))
                nav_data = json.loads(nav_response)
                
                if "trains" in nav_data:
                    current_trains = nav_data["trains"]
                
                msg_builder.add_assistant_with_tool(tool_call)
                msg_builder.add_tool_response(nav_response, tool_call_id, "ui_control")
                msg_builder.add_assistant("😊 Ecco altri risultati.")
            
            elif step == "refine":
                # Refine search (as a followup search)
                # In current corpus, we don't distinguish STARTER vs FOLLOWUP, so just use SearchComponent
                # It will pick a query like "Vorrei andare a X" which is acceptable as a refinement 
                # e.g. "Actually I want to go to Y".
                # Or if we had proper refinement intent, we'd use it.
                # Since replacements are limited, we re-use SearchComponent
                
                # Maybe change destination?
                new_dest = StationManager.select_different(rng, origin, major_only=False)
                search_component = SearchComponent(
                    origin=origin,
                    destination=new_dest,
                    corpus=self.corpus,
                    rephrase_fn=self.rephrase
                )
                ctx_time, current_trains = search_component.build(
                    rng, run_id + step_idx, msg_builder, ctx_builder
                )
            
            elif step == "purchase":
                # Purchase flow
                purchase_component = PurchaseComponent(
                    trains=current_trains,
                    corpus=self.corpus,
                    rephrase_fn=self.rephrase,
                    seat_selection=rng.random() < 0.2
                )
                purchase_component.build(
                    rng, run_id + step_idx, msg_builder, ctx_builder, origin
                )
                
        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": msg_builder.get_messages(),
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": ctx_builder.get_contexts()
            }
        }
