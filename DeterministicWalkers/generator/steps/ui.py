import random
import json
from .base import DialogueStep

class UIStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        try_interruption = kwargs.get("try_interruption")
        # Determine available actions based on UI state
        available_actions = ["status", "back"]
        if ctx["ui_state"].get("can", {}).get("next"):
            available_actions.append("next")
        if ctx["ui_state"].get("can", {}).get("prev"):
            available_actions.append("prev")
        
        available_actions.append("show_info")
            
        action = random.choice(available_actions)
        target = None
        
        if action == "show_info":
            targets = ["station", "city", "help"]
            if ctx["ui_state"].get("state") == "results":
                targets.append("train")
            if ctx["ui_state"].get("state") == "purchased":
                targets.append("ticket")
            target = random.choice(targets)

        if action == "show_info" and target == "train" and not ctx.get("target_train") and not ctx.get("position_word"):
            pos_map = ["primo", "secondo", "terzo"]
            target_idx = random.randint(0, min(2, len(ctx["current_trains"]) - 1)) if ctx.get("current_trains") else 0
            ctx["position_word"] = pos_map[target_idx]

        u_text = self.turn_gen.render_utterance("ui_navigation", ctx, action=action, 
                                       target=target,
                                       target_train=ctx.get("target_train"), 
                                       position_word=ctx.get("position_word")) 
        self.turn_gen.add_turn(ctx, "user", u_text)
        
        # Tool Call
        call_id = self.turn_gen.get_next_call_id(ctx)
        args = {"action": action}
        
        if action == "show_info":
            args["target"] = target
            if target == "train":
                pos_map = ["primo", "secondo", "terzo"]
                if ctx.get("position_word") in pos_map:
                    args["train_position"] = pos_map.index(ctx["position_word"]) + 1
                elif ctx.get("target_train"):
                    t_id = ctx["target_train"]["id"]
                    args["train_position"] = 1
                    for i, t in enumerate(ctx.get("current_trains", [])):
                        if t["id"] == t_id:
                            args["train_position"] = i + 1
                            break
                else:
                    args["train_position"] = random.randint(1, min(3, len(ctx.get("current_trains", [])) or 1))
            
        tool_call = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": "ui_control",
                "arguments": json.dumps(args)
            }
        }
        
        resp_json = self.backend.ui_control(tool_call["function"]["arguments"])
        resp_data = json.loads(resp_json)
        
        # Update context based on tool output
        if action in ["next", "prev"]:
            ctx["current_trains"] = resp_data.get("trains", [])
            max_page = max(0, (len(self.backend.current_search_results) - 1) // self.backend.page_size)
            ctx["ui_state"]["can"]["next"] = self.backend.current_page < max_page
            ctx["ui_state"]["can"]["prev"] = self.backend.current_page > 0
            ctx["ui_state"]["page"] = f"{self.backend.current_page + 1}/{max_page + 1}"
        elif action == "back":
            ctx["ui_state"] = {"state": "idle", "can": {"next": False, "prev": False, "back": False}}
            ctx["current_trains"] = []

        self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call], tool_output=resp_json)
        self.turn_gen.inject_system_context(ctx, meta_contexts)
        
        category_map = {
            "next": "ui_action",
            "prev": "ui_action",
            "back": "greeting_response", 
            "status": "ui_action",
            "show_info": "show_info_response"
        }
        
        overrides = {}
        if action == "show_info":
            overrides["target"] = resp_data.get("target")
            overrides["status"] = resp_data.get("status")
            overrides["info"] = resp_data.get("info")
            
        resp = self.turn_gen.render_utterance("assistant_responses", ctx, category=category_map.get(action, "ui_action"), **overrides)
        self.turn_gen.add_turn(ctx, "assistant", resp)
        
        if try_interruption:
            try_interruption(ctx)
        
        return True
