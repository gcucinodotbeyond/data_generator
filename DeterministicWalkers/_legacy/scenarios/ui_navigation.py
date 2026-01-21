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
    ToolCallBuilder
)

class UiNavigation(Scenario):
    @property
    def name(self) -> str:
        return "ui_navigation"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        # Generate initial state (as if we just searched)
        ctx_time = TimeManager.generate_time(rng)
        
        # Nav actions
        actions = ["next", "prev", "details"]
        action = rng.choice(actions)
        
        # User message
        # Navigation phrases often not in main "navigation" list if it's empty
        phrases = {
            "next": ["Fammi vedere i prossimi", "Successivi", "Pagina dopo", "Avanti"],
            "prev": ["Torna indietro", "Precedenti", "Pagina prima"],
            "details": ["Mostrami i dettagli", "Vedi dettagli", "Info treno"]
        }
        
        # Check corpus for overrides
        corpus_nav = self.corpus.get("navigation", [])
        if corpus_nav:
            # We don't have labeled navigation, so using random one might be risky if we need specific intent.
            # Stick to safe phrases for now.
            pass
            
        user_text = rng.choice(phrases.get(action, ["Avanti"]))
        user_text = self.rephrase(rng, user_text)
        
        # Add context
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 4, # User + ToolCall + ToolResp + Asst
            origin=origin,
            ctx_time=ctx_time,
            ui_state='{"state":"results"}',
            trains_array="[]"
        )
        
        msg_builder.add_user(user_text)
        
        # Tool call
        tool_call_id = msg_builder.generate_tool_call_id()
        tool_call = {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "ui_control",
                "arguments": json.dumps({"action": action})
            }
        }
        
        # Mock Response
        # In a real scenario we'd use backend, but for single turn nav it's simple
        response_json = json.dumps({"success": True, "action": action})
        
        msg_builder.add_assistant_with_tool(tool_call)
        msg_builder.add_tool_response(response_json, tool_call_id, "ui_control")
        msg_builder.add_assistant(f"😊 Fatto.")
        
        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": msg_builder.get_messages(),
            "_meta": {
                "scenario": self.name,
                "seed": rng.seed,
                "run_id": run_id,
                "contexts": ctx_builder.get_contexts()
            }
        }
