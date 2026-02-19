import json
from .base import DialogueStep

class SearchStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        try_interruption = kwargs.get("try_interruption")
        # 1. User performs initial search
        search_data = self.turn_gen.render_utterance_data("search_trains", ctx)
        u_search = search_data['text']
        self.turn_gen.add_turn(ctx, "user", u_search)
        
        # Tool Call 1: Initial Search
        call_id = self.turn_gen.get_next_call_id(ctx)
        search_vars = search_data.get("variables", {})
        tool_time = search_vars.get("time", "now")
        tool_date = search_vars.get("date", "today")

        tool_call_1 = {
             "id": call_id,
             "type": "function",
             "function": {
                 "name": "search_trains",
                 "arguments": json.dumps({
                     "origin": ctx["origin"],
                     "destination": ctx["destination"],
                     "time": self.turn_gen.clean_temporal(tool_time),
                     "date": self.turn_gen.clean_temporal(tool_date)
                 })
             }
        }
        
        # Execute tool 1
        resp_json_1 = self.backend.search_trains(tool_call_1["function"]["arguments"])
        
        # Assistant Turn 1: Call tool AND ask for passengers
        self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call_1], tool_output=resp_json_1)
        
        # Discover session params
        ctx["session_to"] = search_vars.get("destination", ctx["destination"])
        ctx["session_date"] = search_vars.get("date", "")
        ctx["session_time"] = search_vars.get("time", "")
        
        # Update UI state for intermediate step
        ctx["ui_state"] = {"state": "search", "phase": "input_pax", "actions": "show_info"}
        self.turn_gen.inject_system_context(ctx, meta_contexts)
        
        # Verbal response asking for pax
        resp_ask_pax = self.turn_gen.render_utterance("assistant_responses", ctx, category="ask_passengers")
        self.turn_gen.add_turn(ctx, "assistant", resp_ask_pax)
        
        # Potential interruption
        if try_interruption:
            try_interruption(ctx)
        
        # Note: Disability step is handled by the orchestrator in the flow
        # But in original code it was called here. 
        # To maintain exact behavior, we might need a way to call other steps.
        # For now, we assume the flow builder handles it.
        # Wait, the original code had:
        # self._step_disability(ctx, meta_contexts)
        
        # I'll keep it for now but maybe it should be part of the flow.
        # If I want to match original exactly:
        from .disability import DisabilityStep
        DisabilityStep(self.turn_gen, self.ctx_mgr).execute(ctx, meta_contexts)

        # 2b. User provides passenger count
        u_pax = self.turn_gen.render_utterance("refinement", ctx, aspect="passengers", count=ctx["passengers"], 
                                      pet_phrase=ctx.get("pet_phrase"), bike_phrase=ctx.get("bike_phrase"),
                                      disability_phrase=None)
        self.turn_gen.add_turn(ctx, "user", u_pax)
        
        call_id_2 = self.turn_gen.get_next_call_id(ctx)
        tool_call_2 = {
            "id": call_id_2,
            "type": "function",
            "function": {
                "name": "search_trains",
                "arguments": json.dumps({
                    "origin": ctx["origin"], 
                    "destination": ctx["destination"], 
                    "passengers": ctx["passengers"],
                    "pet_small": 1 if ctx.get("pet_type") == "small" else 0,
                    "pet_big": 1 if ctx.get("pet_type") == "large" else 0,
                    "bike_normal": 1 if ctx.get("bike_type") == "normal" else 0,
                    "bike_foldable": 1 if ctx.get("bike_type") == "foldable" else 0,
                    "disability_type": ctx.get("disability_type"),
                    "time": self.turn_gen.clean_temporal(tool_time),
                    "date": self.turn_gen.clean_temporal(tool_date)
                })
            }
        }
        
        # Execute search
        resp_json_2 = self.backend.search_trains(tool_call_2["function"]["arguments"])
        resp_data_2 = json.loads(resp_json_2)
        ctx["current_trains"] = resp_data_2.get("trains", [])
        
        # Discover session pax and pets
        ctx["session_pax"] = ctx["passengers"]
        ctx["session_pax_discovered"] = True
        ctx["session_pet_small"] = 1 if ctx.get("pet_type") == "small" else 0
        ctx["session_pet_big"] = 1 if ctx.get("pet_type") == "large" else 0
        ctx["session_bike_normal"] = 1 if ctx.get("bike_type") == "normal" else 0
        ctx["session_bike_foldable"] = 1 if ctx.get("bike_type") == "foldable" else 0
        ctx["session_disability"] = ctx.get("disability_type")
        
        # Update UI State -> Results
        ctx["ui_state"] = {
            "state": "results",
            "can": {
                "next": len(self.backend.current_search_results) > self.backend.page_size,
                "prev": False,
                "back": True
            },
            "page": f"1/{max(0, (len(self.backend.current_search_results) - 1) // self.backend.page_size) + 1}"
        }
        
        self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call_2], tool_output=resp_json_2)
        self.turn_gen.inject_system_context(ctx, meta_contexts)
        
        # Final Search Result Msg
        n_trains = len(ctx["current_trains"])
        if n_trains > 0:
            first = ctx["current_trains"][0]
            resp_success = self.turn_gen.render_utterance("assistant_responses", ctx, category="search_success", n_trains=n_trains, destination=ctx['destination'], first_dep=first['dep'])
            self.turn_gen.add_turn(ctx, "assistant", resp_success)
        else:
            resp_empty = self.turn_gen.render_utterance("assistant_responses", ctx, category="search_empty", destination=ctx['destination'])
            self.turn_gen.add_turn(ctx, "assistant", resp_empty)
            return False 

        # Potential interruption
        if try_interruption:
            try_interruption(ctx)

        return True
