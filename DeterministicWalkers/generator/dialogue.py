import random
import json
import os
from datetime import datetime, timedelta
from generator.deterministic import DeterministicGenerator
from generator.mock_api import MockBackend

class DialogueGenerator:
    def __init__(self, corpus=None, enhancer=None, distribution=None):
        # We don't strictly need corpus anymore, but we keep the signature compatible for now.
        # We rely on DeterministicGenerator instance for rendering.
        self.renderer = DeterministicGenerator()
        self.enhancer = enhancer
        self.backend = MockBackend()
        self.distribution = distribution or {}
        
        # Load stations
        stations_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'stations.json')
        try:
            with open(stations_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.major_stations = data.get("major", [])
                # Flatten all stations for destinations
                all_stations = []
                for key in data:
                    if isinstance(data[key], list):
                        all_stations.extend(data[key])
                self.origins = self.major_stations
                self.destinations = list(set(all_stations)) # unique
        except Exception as e:
            print(f"Warning: Could not load stations.json ({e}), using defaults.")
            self.origins = ["Milano Centrale", "Roma Termini", "Napoli Centrale"]
            self.destinations = ["Roma", "Milano", "Napoli", "Firenze"]

        self.dates = ["oggi", "domani", "venerdì", "il 25 aprile"]
        self.times = ["mattina", "pomeriggio", "sera", "10:00", "15:30", "subito"]
        
        self.refusal_reasons = ["too_expensive", "too_late", "wrong_type"]

        # Load QA Pairs
        qa_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'qa_pairs.json')
        self.qa_pairs = []
        try:
            if os.path.exists(qa_path):
                with open(qa_path, 'r', encoding='utf-8') as f:
                    self.qa_pairs = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load qa_pairs.json ({e}).")

        # Load OOD Questions (Refusals)
        starters_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'refusal_starters.json')
        followups_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'refusal_followups.json')
        self.ood_starters = []
        self.ood_followups = []
        try:
            if os.path.exists(starters_path):
                with open(starters_path, 'r', encoding='utf-8') as f:
                    self.ood_starters = json.load(f)
            if os.path.exists(followups_path):
                with open(followups_path, 'r', encoding='utf-8') as f:
                    self.ood_followups = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load refusal files ({e}). OOD will be disabled.")

    def generate_dialogues(self, count=100):
        dialogues = []
        print(f"[Dialogue] Generating {count} dynamic dialogues...")
        
        for i in range(count):
            self.backend = MockBackend(seed=i) # Reset backend per dialogue
            try:
                d = self._build_dynamic_flow(i)
                dialogues.append(d)
            except Exception as e:
                print(f"Error generating dialogue {i}: {e}")
                
        return dialogues
    def _init_context(self, run_id):
        """Randomly initializes the global context variables for this dialogue."""
        origin = random.choice(self.origins)
        dest = random.choice([d for d in self.destinations if d[:3] != origin[:3]]) # Avoid same city
        
        # Rudeness selection
        rudeness_dist = self.distribution.get("rudeness_distribution", {})
        if rudeness_dist:
            population = list(rudeness_dist.keys())
            weights = list(rudeness_dist.values())
            rudeness = random.choices(population, weights=weights, k=1)[0]
        else:
            rudeness = random.choice(["polite", "rude", "neutral"])

        return {
            "run_id": run_id,
            "origin": origin,
            "destination": dest,
            "date": random.choice(self.dates),
            "time": random.choice(self.times),
            "passengers": random.randint(1, 3),
            "class": random.choice(["Standard", "Prima", "Business"]),
            "tone": random.choice(["formal", "informal"]), # Used by templates if supported
            "rudeness": rudeness, # Weighted or random choice
            
            # Internal tracking
            "generated_messages": [{"role": "system", "content": "{SYSTEM_PROMPT}"}],
            "current_trains": [], # Result from mock backend
            "ui_state": {"state": "idle", "can": {"next": False, "prev": False, "back": False}},
            "ctx_time": f"{random.randint(6, 22):02d}:{random.randint(0, 59):02d}", 
            "ctx_date": (datetime.now() + timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
            "call_counter": 0
        }

    def _get_next_call_id(self, context):
        if "call_counter" not in context:
            context["call_counter"] = 0
        context["call_counter"] += 1
        return f"call_{context['call_counter']:03d}"

    def _render_utterance_data(self, intent, context, **overrides):
        """Helper to render an utterance using current context + overrides."""
        render_vars = context.copy()
        render_vars.update(overrides)
        
        # Special handling for list-based variables in templates
        # If template iterates over 'destinations', we force it to see only OUR destination
        render_vars["destinations"] = [render_vars["destination"]]
        
        # Map 'time' to template expectations if needed, but template usually handles raw strings
        
        result = self.renderer.render(intent, render_vars)
        
        # ATTEMPT PARAPHRASE
        if self.enhancer and result.get("text"):
            # Only paraphrase USER intents for better stability of assistant responses
            user_intents = ["search_trains", "greeting", "confirmation", "refusal", "qa", "ui_navigation", "refinement", "ood", "complaint"]
            if intent not in user_intents:
                return result

            # Use probability from enhancer
            prob = self.enhancer.paraphrase_probability if hasattr(self.enhancer, 'paraphrase_probability') else 0.1
            
            if random.random() < prob:
                print(f"[LLM] Paraphrasing intent '{intent}' (persona: {context.get('rudeness', 'polite')}): {result['text'][:50]}...")
                new_text = self.enhancer.paraphrase_utterance(result['text'], intent, persona=context.get('rudeness', 'polite'))
                if new_text and new_text != result['text']:
                    result['text'] = new_text
                    result['generator'] = 'llm_paraphrased'

        return result

    def _render_utterance(self, intent, context, **overrides):
        return self._render_utterance_data(intent, context, **overrides)['text']

    def _add_turn(self, context, role, content, tool_calls=None, tool_output=None):
        msgs = context["generated_messages"]
        
        if role == "user":
            msgs.append({"role": "user", "content": content})
            
        elif role == "assistant":
            # Constraint: No consecutive assistant turns
            merged = False
            if msgs and msgs[-1]["role"] == "assistant":
                last = msgs[-1]
                # Case: Both have text content, no tool calls involved
                if not last.get("tool_calls") and not tool_calls:
                    if content:
                        current_content = last.get("content", "") or ""
                        new_content = f"{current_content} {content}".strip()
                        last["content"] = new_content
                        merged = True
                
                # Case: Last had tool calls, new has text -> INVALID by schema if we just append
                # But we can't merge text into tool_calls message (content must be null)
                # So we must allow it IF there's an intervening tool message? 
                # Wait, if msgs[-1] is assistant, check if msgs[-2] was tool?
                # Actually, if msgs[-1] is assistant, we cannot add another assistant.
                
                # If we couldn't merge (e.g. tool calls involved), we ideally shouldn't be here.
                # But if we must, we proceed (and violate constraint) or we try to merge intelligently?
                
                # If last was tool_call and we add text... effective pattern is Asst(Call) -> Asst(Text).
                # This is strictly invalid in some APIs. 
                # However, for this generator, let's assume text-text merging is the main goal.
            
            if not merged:
                msg = {"role": "assistant", "content": content}
                if tool_calls:
                    msg["tool_calls"] = tool_calls
                    msg["content"] = None # Usually null if tool calling
                msgs.append(msg)
            
            if tool_output:
                # Assuming single tool call for now
                call_id = tool_calls[0]["id"]
                name = tool_calls[0]["function"]["name"]
                msgs.append({
                    "role": "tool",
                    "tool_call_id": call_id, 
                    "name": name, 
                    "content": tool_output
                })

    def _snapshot_meta(self, context, slice_len):
        ctx_snapshot = {
            "slice_length": slice_len,
            "params": {
                "origin": context["origin"],
                "ui_state": json.dumps(context["ui_state"]) if isinstance(context["ui_state"], dict) else str(context["ui_state"]), 
                "trains_array": json.dumps(context["current_trains"]),
                "ctx_time": context["ctx_time"],
                "date": context["ctx_date"],
                "ticket_info": json.dumps(context.get("ticket_info", {})) if context.get("ticket_info") else None
            }
        }
        return ctx_snapshot

    def _try_interruption(self, context):
        """
        With some probability, inserts a QA or UI side-track.
        Updates context['generated_messages'] directly.
        Returns True if interrupted (and resolved), False otherwise.
        """
        if random.random() > 0.3: # 30% chance of interruption?
            return False
            
        interruption_type = random.choice(["qa", "qa", "ui", "ood"]) # Added ood
        
        if interruption_type == "qa":
            if self.qa_pairs:
                q, a = random.choice(self.qa_pairs)
                self._add_turn(context, "user", q)
                self._add_turn(context, "assistant", a)
                return True
            return False
            
        elif interruption_type == "ui":
            return self._step_ui(context, []) # Reuse existing logic, but might need to handle meta_contexts better if needed inside interruption
            
        elif interruption_type == "ood":
            if self.ood_followups:
                q = random.choice(self.ood_followups)
                u_text = self._render_utterance("ood", context, question=q)
                self._add_turn(context, "user", u_text)
                
                # Asst redirects
                resp = self._render_utterance("assistant_responses", context, category="ood_redirect")
                self._add_turn(context, "assistant", resp)
                return True

        return False


    def _step_greeting(self, ctx, meta_contexts):
        u_greet = self._render_utterance("greeting", ctx)
        self._add_turn(ctx, "user", u_greet)
        resp = self._render_utterance("assistant_responses", ctx, category="greeting_response")
        self._add_turn(ctx, "assistant", resp)
        meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _step_search(self, ctx, meta_contexts):
        # User performs search
        search_data = self._render_utterance_data("search_trains", ctx)
        u_search = search_data['text']
        self._add_turn(ctx, "user", u_search)
        
        # Tool Call
        call_id = self._get_next_call_id(ctx)
        
        # Resolve time for tool call
        search_vars = search_data.get("variables", {})
        tool_time = search_vars.get("time")
        
        if not tool_time or tool_time in ["mattina", "pomeriggio", "sera", "subito", "ora", "adesso"]:
             tool_time = ctx["ctx_time"]

        tool_call = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": "search_trains",
                "arguments": json.dumps({"origin": ctx["origin"], "destination": ctx["destination"], "time": tool_time})
            }
        }
        
        # Mock Backend Response
        resp_json = self.backend.search_trains(tool_call["function"]["arguments"])
        resp_data = json.loads(resp_json)
        ctx["current_trains"] = resp_data.get("trains", [])
        
        # UI State update after search
        ctx["ui_state"] = {
            "state": "results",
            "can": {
                "next": len(self.backend.current_search_results) > self.backend.page_size,
                "prev": False,
                "back": True
            }
        }
        
        resp_searching = self._render_utterance("assistant_responses", ctx, category="searching")
        self._add_turn(ctx, "assistant", resp_searching, tool_calls=[tool_call], tool_output=resp_json)
        
        # Asst Result msg
        n_trains = len(ctx["current_trains"])
        if n_trains > 0:
            first = ctx["current_trains"][0]
            resp_success = self._render_utterance("assistant_responses", ctx, category="search_success", n_trains=n_trains, destination=ctx['destination'], first_dep=first['dep'])
            self._add_turn(ctx, "assistant", resp_success)
        else:
            resp_empty = self._render_utterance("assistant_responses", ctx, category="search_empty", destination=ctx['destination'])
            self._add_turn(ctx, "assistant", resp_empty)
            # End here if no trains
            meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))
            return False # Stop flow if empty

        meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))
        return True

    def _step_qa(self, ctx, meta_contexts):
        if self.qa_pairs:
            q, a = random.choice(self.qa_pairs)
            self._add_turn(ctx, "user", q)
            self._add_turn(ctx, "assistant", a)
            meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _step_ui(self, ctx, meta_contexts):
        # Determine available actions based on UI state
        available_actions = ["status", "back"]
        if ctx["ui_state"].get("can", {}).get("next"):
            available_actions.append("next")
        if ctx["ui_state"].get("can", {}).get("prev"):
            available_actions.append("prev")
        if ctx["ui_state"].get("state") == "results":
            available_actions.append("show_changes")
            
        action = random.choice(available_actions)
        
        # If show_changes is picked but no target/position is in ctx yet, 
        # we pick one to simulate a specific request (e.g., "how many changes for the first one?")
        if action == "show_changes" and not ctx.get("target_train") and not ctx.get("position_word"):
            pos_map = ["primo", "secondo", "terzo"]
            target_idx = random.randint(0, min(2, len(ctx["current_trains"]) - 1)) if ctx.get("current_trains") else 0
            ctx["position_word"] = pos_map[target_idx]

        u_text = self._render_utterance("ui_navigation", ctx, action=action, 
                                       target_train=ctx.get("target_train"), 
                                       position_word=ctx.get("position_word")) 
        self._add_turn(ctx, "user", u_text)
        
        # Tool Call
        call_id = self._get_next_call_id(ctx)
        args = {"action": action}
        if action == "show_changes":
            # Use the index from position_word if available, or just a default
            pos_map = ["primo", "secondo", "terzo"]
            if ctx.get("position_word") in pos_map:
                args["train_position"] = pos_map.index(ctx["position_word"]) + 1
            elif ctx.get("target_train"):
                # Find current position of target_train
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
        elif action == "back":
            ctx["ui_state"] = {"state": "idle", "can": {"next": False, "prev": False, "back": False}}
            ctx["current_trains"] = []

        # Assistant turn with tool response
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call], tool_output=resp_json)
        
        # Final verbal confirmation
        category_map = {
            "next": "ui_action",
            "prev": "ui_action",
            "back": "greeting_response", # Or something similar
            "status": "ui_action",
            "show_changes": "ui_action"
        }
        resp = self._render_utterance("assistant_responses", ctx, category=category_map.get(action, "ui_action"))
        self._add_turn(ctx, "assistant", resp)
        
        meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _step_ood(self, ctx, meta_contexts, starter=False):
        if starter:
            if self.ood_starters:
                q = random.choice(self.ood_starters)
                u_ood = self._render_utterance("ood", ctx, question=q)
                self._add_turn(ctx, "user", u_ood)
                resp = self._render_utterance("assistant_responses", ctx, category="ood_redirect")
                self._add_turn(ctx, "assistant", resp)
                meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))
        else:
            if self.ood_followups:
                q = random.choice(self.ood_followups)
                u_text = self._render_utterance("ood", ctx, question=q)
                self._add_turn(ctx, "user", u_text)
                
                resp = self._render_utterance("assistant_responses", ctx, category="ood_redirect")
                self._add_turn(ctx, "assistant", resp)
                meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _step_selection_purchase(self, ctx, meta_contexts):
        if not ctx.get("current_trains"):
            return

        target_index = 0
        if len(ctx["current_trains"]) > 1:
            target_index = random.choice(range(len(ctx['current_trains'])))
        
        target_train = ctx["current_trains"][target_index]
        pos_map = ["primo", "secondo", "terzo"]
        pos_word = pos_map[target_index] if target_index < 3 else "questo"
        
        ctx["target_train"] = target_train
        ctx["position_word"] = pos_word

        # Explicit Selection
        u_sel = self._render_utterance("refinement", ctx, train=target_train, aspect="train", position_word=pos_word)
        self._add_turn(ctx, "user", u_sel)
        current_response = self._render_utterance("assistant_responses", ctx, category="selection_refinement", dep_time=target_train['dep'])
        
        # Class Check
        premium_types = ["Frecciarossa", "Frecciargento", "Frecciabianca", "Intercity", "Intercity Notte", "Italo"]
        is_premium = any(pt in target_train["type"] for pt in premium_types)
        
        if is_premium:
            prompt = self._render_utterance("assistant_responses", ctx, category="class_prompt")
            self._add_turn(ctx, "assistant", f"{current_response} {prompt}")
            
            chosen_class = random.choice(["Standard", "Prima", "Business"])
            ctx["class"] = chosen_class
            u_class = self._render_utterance("refinement", ctx, class_name=chosen_class, aspect="class")
            self._add_turn(ctx, "user", u_class)
            
            current_response = self._render_utterance("assistant_responses", ctx, category="class_ack", class_name=chosen_class)
        else:
            ctx["class"] = "Standard"

        # Check if AV train
        av_types = ["Frecciarossa", "Frecciargento", "Frecciabianca"]
        is_av = any(at in target_train["type"] for at in av_types)

        if is_av:
            # Transition to choosingSeat
            ctx["ui_state"] = {"state": "choosingSeat", "can": {"next": True, "prev": True, "back": True}}
            
            # Seat Prompt (concatenated with whatever was the last response)
            seat_prompt = self._render_utterance("assistant_responses", ctx, category="seat_prompt")
            self._add_turn(ctx, "assistant", f"{current_response} {seat_prompt}".strip())
            
            # User chooses seat
            u_seat_data = self._render_utterance_data("refinement", ctx, aspect="seat")
            u_seat = u_seat_data['text']
            seat_type = u_seat_data.get("variables", {}).get("seat", "window")
            self._add_turn(ctx, "user", u_seat)
            
            # Acknowledge seat choice
            current_response = self._render_utterance("assistant_responses", ctx, category="seat_ack", seat_type=seat_type)
            ctx["chosen_seat"] = "4A" if seat_type == "window" else "4B"

        # Handshake (Price + Confirmation)
        handshake = self._render_utterance("assistant_responses", ctx, category="handshake", price=target_train['price'])
        self._add_turn(ctx, "assistant", f"{current_response} {handshake}".strip())
        
        u_yes = self._render_utterance("confirmation", ctx, time=None, class_type=None, destination=None)
        self._add_turn(ctx, "user", u_yes)

        # Single Purchase Call
        call_id = self._get_next_call_id(ctx)
        purchase_args = {"train_id": target_train["id"], "class": ctx["class"]}
        if is_av:
            purchase_args["seat"] = ctx.get("chosen_seat", "4A")
            purchase_args["carriage"] = random.randint(1, 8)
            
        tool_call = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": "purchase_ticket",
                "arguments": json.dumps(purchase_args)
            }
        }
        resp_json = self.backend.purchase_ticket(tool_call["function"]["arguments"])
        resp_data = json.loads(resp_json)
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call], tool_output=resp_json)
        
        # Final Handover
        resp_handover = self._render_utterance("assistant_responses", ctx, category="ticket_handover")
        self._add_turn(ctx, "assistant", resp_handover)
        
        ctx["ticket_info"] = resp_data
        ctx["ui_state"] = {"state": "purchased", "can": {"next": False, "prev": False, "back": False}}
        meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _step_complaint(self, ctx, meta_contexts):
        u_complaint = self._render_utterance("complaint", ctx)
        self._add_turn(ctx, "user", u_complaint)
        resp = self._render_utterance("assistant_responses", ctx, category="complaint_response")
        self._add_turn(ctx, "assistant", resp)
        meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _step_farewell(self, ctx, meta_contexts):
        is_success = ctx.get("ui_state", {}).get("state") == "purchased"
        sentiment = "positive" if is_success else "neutral"
        
        u_bye = self._render_utterance("farewell", ctx, sentiment=sentiment)
        self._add_turn(ctx, "user", u_bye)
        resp_farewell = self._render_utterance("assistant_responses", ctx, category="farewell")
        self._add_turn(ctx, "assistant", resp_farewell)
        meta_contexts.append(self._snapshot_meta(ctx, len(ctx["generated_messages"])))

    def _build_dynamic_flow(self, run_id):
        # Default scenario steps
        scenario_steps = ["greeting", "search", "selection_purchase", "farewell"]
        scenario_name = "default"
        
        # Scenario Selection based on distribution
        scenario_dist = self.distribution.get("scenario_distribution", {})
        scenario_dir = os.path.join(os.path.dirname(__file__), 'scenarios')
        
        if scenario_dist and os.path.exists(scenario_dir):
            population = list(scenario_dist.keys())
            weights = list(scenario_dist.values())
            # Ensure only existing files are in population? 
            # For simplicity, we assume config is correct or we filter now.
            population = [p for p in population if os.path.exists(os.path.join(scenario_dir, f"{p}.txt"))]
            # Adjust weights after filtering population
            weights = [scenario_dist[p] for p in population]
            
            if population:
                scenario_name = random.choices(population, weights=weights, k=1)[0]
                scenario_path = os.path.join(scenario_dir, f"{scenario_name}.txt")
                with open(scenario_path, 'r', encoding='utf-8') as f:
                    scenario_steps = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        elif os.path.exists(scenario_dir):
            # Fallback to pure random if no distribution
            all_files = [f for f in os.listdir(scenario_dir) if f.endswith(".txt")]
            if all_files:
                scenario_file = random.choice(all_files)
                scenario_name = scenario_file.replace(".txt", "")
                scenario_path = os.path.join(scenario_dir, scenario_file)
                with open(scenario_path, 'r', encoding='utf-8') as f:
                    scenario_steps = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        print(f"[Dialogue] Run {run_id} using scenario: '{scenario_name}'")
        
        ctx = self._init_context(run_id)
        meta_contexts = []

        for raw_line in scenario_steps:
            # Handle composite steps: "search + complaint (price)"
            sub_steps = [s.strip() for s in raw_line.split("+")]
            
            for sub_step in sub_steps:
                # Extract optional parameter: "complaint (price)" -> step="complaint", param="price"
                step = sub_step
                param = None
                if "(" in sub_step and ")" in sub_step:
                    import re
                    match = re.search(r"([^(]+)\s*\(([^)]+)\)", sub_step)
                    if match:
                        step = match.group(1).strip()
                        param = match.group(2).strip()
                
                # If param exists, we might want to inject it into context for the specific step
                # For now, we support 'topic' as the most common parameter
                if param:
                    ctx["topic"] = param

                if step == "greeting":
                    self._step_greeting(ctx, meta_contexts)
                elif step == "search":
                    if not self._step_search(ctx, meta_contexts):
                        break # Stop if no trains
                elif step == "qa":
                    self._step_qa(ctx, meta_contexts)
                elif step == "ui":
                    self._step_ui(ctx, meta_contexts)
                elif step == "ood":
                    # If first turn, it's a starter
                    is_starter = len(ctx["generated_messages"]) <= 1
                    self._step_ood(ctx, meta_contexts, starter=is_starter)
                elif step == "complaint":
                    self._step_complaint(ctx, meta_contexts)
                elif step == "selection_purchase":
                    self._step_selection_purchase(ctx, meta_contexts)
                elif step == "farewell":
                    self._step_farewell(ctx, meta_contexts)
        
        result = self._finalize(ctx, meta_contexts)
        result["_meta"]["scenario_name"] = scenario_name # Add to metadata
        return result

    def _finalize(self, ctx, meta_contexts):
        # Fix UI state stringification for snapshots
        # In _snapshot_meta we did str(ui_state), but legacy expects "{\"state\":\"...\"}"
        for snap in meta_contexts:
            if isinstance(snap["params"]["ui_state"], dict):
                 snap["params"]["ui_state"] = json.dumps(snap["params"]["ui_state"])
            # Ensure trains array is stringified json
            if isinstance(snap["params"]["trains_array"], list):
                 snap["params"]["trains_array"] = json.dumps(snap["params"]["trains_array"])

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": ctx["generated_messages"],
            "_meta": {
                "scenario": "dynamic_v3",
                "seed": random.randint(1000,999999), 
                "run_id": ctx["run_id"],
                "rudeness": ctx["rudeness"],
                "contexts": meta_contexts
            }
        }
