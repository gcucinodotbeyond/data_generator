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
    ToolCallBuilder
)

class SearchFail(Scenario):
    """
    Scenario where a search returns no results, and the assistant communicates this.
    """
    @property
    def name(self) -> str:
        return "search_fail"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        # Manually build search query since SearchComponent encapsulates it 
        # but we need to inject failure in the tool response.
        
        # Copy query selection logic
        template = None
        search_queries = self.corpus.get("search_queries", [])
        
        if search_queries:
             candidates = [c for c in search_queries if "{destination}" in c]
             if not candidates:
                 candidates = search_queries
             
             if candidates:
                 template = rng.choice(candidates)
        
        if not template:
            template = "Vorrei andare a {destination}"
        
        # Parse time constraints
        base_hour, format_args = TimeManager.parse_template_constraints(template, rng)
        ctx_time = TimeManager.generate_time(rng, base_hour)
        
        format_args["destination"] = destination
        format_args["origin"] = origin
        
        user_text = template
        for k, v in format_args.items():
            user_text = user_text.replace("{" + k + "}", str(v))
            
        if self.rephrase:
            user_text = self.rephrase(rng, user_text)
        
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 4, # User + Tool + Resp + Asst
            origin=origin,
            ctx_time=ctx_time,
            ui_state='{"state":"idle"}',
            trains_array="[]"
        )
        
        msg_builder.add_user(user_text)
        
        # 2. Tool Call
        tool_call_id = f"call_search_{run_id}"
        tool_call = ToolCallBuilder.build_search_call(
            tool_call_id, origin, destination, time=ctx_time
        )
        
        # 3. Tool Output -> EMPTY
        tool_output = json.dumps({"trains": []})
        
        msg_builder.add_assistant_with_tool(tool_call)
        msg_builder.add_tool_response(tool_output, tool_call_id, "search_trains")
        
        # 4. Assistant Apology
        fail_msgs = [
            "😔 Mi dispiace, non ho trovato treni per questa tratta.",
            "😕 Nessun treno disponibile al momento.",
            "⚠️ Non ci sono soluzioni di viaggio disponibili per i parametri inseriti.",
            "😔 Non trovo nulla. Prova a cambiare orario o stazione."
        ]
        fail_msg = rng.choice(fail_msgs)
        
        msg_builder.add_assistant(fail_msg)
        
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
