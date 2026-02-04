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

        self.dates = ["oggi", "per oggi", "per domani", "domani", "sabato", "domenica prossima", "il 15 del mese", "per venerdì"]
        self.times = ["mattina", "pomeriggio", "sera", "10:00", "15:30", "subito"]
        
        self.refusal_reasons = ["too_expensive", "too_late", "wrong_type"]

        # Load QA Pairs (Strictly use classified LLM version)
        qa_path = os.path.join(os.path.dirname(__file__), '..', 'qa', 'qa_classified_llm.json')
        self.qa_pairs = []
        try:
            if os.path.exists(qa_path):
                with open(qa_path, 'r', encoding='utf-8') as f:
                    self.qa_pairs = json.load(f)
                print(f"[Dialogue] Loaded {len(self.qa_pairs)} classified QA pairs from {os.path.basename(qa_path)}")
            else:
                print(f"Warning: Classified QA file not found at {qa_path}")
        except Exception as e:
            print(f"Warning: Could not load QA pairs ({e}).")

        # Load OOD Questions (Refusals)
        # Load OOD Questions (Refusals)
        starters_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'ood_starters.json')
        followups_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'ood_followups.json')

        self.ood_starters = []
        self.ood_followups = []
        try:
            if os.path.exists(starters_path):
                with open(starters_path, 'r', encoding='utf-8') as f:
                    self.ood_starters = json.load(f)
            if os.path.exists(followups_path):
                with open(followups_path, 'r', encoding='utf-8') as f:
                    self.ood_followups = json.load(f)
            # if os.path.exists(user_nuances_path):
            #     with open(user_nuances_path, 'r', encoding='utf-8') as f:
            #         self.user_nuances = json.load(f)

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

        # Verbose selection
        verbose_dist = self.distribution.get("verbose_distribution", {})
        if verbose_dist:
            population = list(verbose_dist.keys())
            weights = list(verbose_dist.values())
            verbose = random.choices(population, weights=weights, k=1)[0]
        else:
            verbose = random.choice(["concise", "standard", "verbose"])

        initial_context = {
            "run_id": run_id,
            "origin": origin,
            "destination": dest,
            "date": random.choice(self.dates),
            "time": random.choice(self.times),
            "passengers": random.randint(1, 3),
            "class": random.choice(["Standard", "Prima", "Business"]),
            "tone": random.choice(["formal", "informal"]), # Used by templates if supported
            "rudeness": rudeness, # Weighted or random choice
            "verbose": verbose, # Weighted or random choice
            
            # Session-discovered state (to avoid leaking simulation ground truth to LLM)
            "session_to": "",
            "session_date": "",
            "session_time": "",
            "session_pax_discovered": False,
            "session_pax": 1,
            "session_class": None,
            
            # Internal tracking
            "generated_messages": [],
            "current_trains": [], # Result from mock backend
            "ui_state": {"state": "idle", "can": {"next": False, "prev": False, "back": False}},
            "ctx_time": f"{random.randint(6, 22):02d}:{random.randint(0, 59):02d}", 
            "ctx_date": (datetime.now() + timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
            "call_counter": 0
        }

        # Inject INITIAL system prompt with context
        from generator.context_formatter import ContextFormatter
        initial_params = {
            "origin": initial_context["origin"],
            "destination": "",
            "travel_date": "",
            "travel_time": "",
            "passengers": "0",
            "ui_state": json.dumps(initial_context["ui_state"]),
            "trains_array": "[]",
            "ctx_time": initial_context["ctx_time"],
            "date": initial_context["ctx_date"],
            "ticket_info": None
        }
        initial_xml = ContextFormatter.format_context(initial_params)
        full_system_content = "{SYSTEM_PROMPT}\n\n" + initial_xml
        initial_context["generated_messages"].append({"role": "system", "content": full_system_content})

        return initial_context

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
        if "time" in render_vars and "time_type" not in render_vars:
            t = str(render_vars["time"]).lower()
            if any(char.isdigit() for char in t) and ":" in t:
                render_vars["time_type"] = "numeric"
            elif t in ["subito", "ora", "adesso", "immediatamente"]:
                render_vars["time_type"] = "relative_now"
            else:
                render_vars["time_type"] = "relative_future"
        
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
                print(f"[LLM] Paraphrasing intent '{intent}' (persona: {context.get('rudeness', 'polite')}, verbose: {context.get('verbose', 'standard')}): {result['text'][:50]}...")
                new_text = self.enhancer.paraphrase_utterance(
                    result['text'], 
                    intent, 
                    persona=context.get('rudeness', 'polite'),
                    verbose=context.get('verbose', 'standard')
                )
                if new_text and new_text != result['text']:
                    result['text'] = new_text
                    result['generator'] = 'llm_paraphrased'

        return result

    def _render_utterance(self, intent, context, **overrides):
        return self._render_utterance_data(intent, context, **overrides)['text']

    @staticmethod
    def _clean_temporal(val):
        if not val: return val
        d = str(val).lower().strip()
        prefixes = [
            "per il ", "per l'", "per ", "il ", "l' ", 
            "dalle ", "dopo le ", "alle ", "verso le ", "intorno alle ",
            "per questa ", "per questo ", "per la "
        ]
        for p in prefixes:
            if d.startswith(p):
                d = d[len(p):].strip()
        # Common redundant words or phrase endings
        d = d.replace(" del mese", "")
        return d

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

    def _inject_system_context(self, context, meta_contexts):
        """
        Inject XML-formatted system message based on current context state
        Called after key interactions (tool responses, state changes)
        """
        from generator.context_formatter import ContextFormatter

        # Resolve travel date/time using symbolic names for Context v1.5
        # If destination is known, we assume a search is in progress or done
        res_date = context.get("session_date", "")
        if not res_date and context.get("session_to"):
            res_date = "today"
            
        res_time = context.get("session_time", "")
        if not res_time and context.get("session_to"):
            res_time = "now"

        # Create snapshot params
        snapshot_pax = context.get("session_pax", 1) if context.get("session_pax_discovered") else 0

        snapshot_params = {
            "origin": context["origin"],
            "destination": context.get("session_to", ""),
            "travel_date": res_date,
            "travel_time": res_time,
            "passengers": str(snapshot_pax),
            "ui_state": context["ui_state"], # Stringified in finalize
            "trains_array": context["current_trains"], # Stringified in finalize
            "ctx_time": context["ctx_time"],
            "date": context["ctx_date"],
            "ticket_info": context.get("ticket_info"),
            
            # Additional dynamic data for Formatter
            "target_train": context.get("target_train"),
            "session_class": context.get("session_class")
        }
        
        # Format as XML
        # Note: We need to pass stringified versions to Formatter if it expects them, 
        # but our current simplified Formatter can handle dicts/lists if we update it or stringify here.
        # To match the simplified Formatter precisely:
        formatter_params = snapshot_params.copy()
        formatter_params["ui_state"] = json.dumps(snapshot_params["ui_state"])
        formatter_params["trains_array"] = json.dumps(snapshot_params["trains_array"])
        if snapshot_params["ticket_info"]:
            formatter_params["ticket_info"] = json.dumps(snapshot_params["ticket_info"])

        system_content = ContextFormatter.format_context(formatter_params)
        
        # Add system message
        context["generated_messages"].append({
            "role": "system",
            "content": system_content
        })

        # Track in meta_contexts
        meta_contexts.append({
            "turn_index": len(context["generated_messages"]),
            "params": snapshot_params
        })

    def _get_contextual_qa(self, ctx):
        """Selects a QA pair based on the current context (train type, stations, UI state)."""
        if not self.qa_pairs:
            return None, None
            
        # If we have legacy format (list of lists/tuples), just pick random
        if self.qa_pairs and isinstance(self.qa_pairs[0], (list, tuple)):
            return random.choice(self.qa_pairs)

        candidates = []
        
        # Determine context attributes
        target_train = ctx.get("target_train")
        train_type = target_train["type"] if target_train else None
        origin = ctx.get("origin")
        destination = ctx.get("destination")
        ui_state = ctx.get("ui_state", {}).get("state", "idle")
        
        # Scoring system
        scored_candidates = []
        for item in self.qa_pairs:
            score = 0
            metadata = item.get("metadata", {})
            entities = [e.lower() for e in metadata.get("entities", [])]
            tags = metadata.get("contextual_tags", [])
            
            # Match Train Type
            if train_type:
                for tt in ["Frecciarossa", "Intercity", "Italo", "Regionale"]:
                    if tt.lower() in train_type.lower() and tt.lower() in entities:
                        score += 15
            
            # Match Stations
            if origin and origin.lower() in entities:
                score += 10
            if destination and destination.lower() in entities:
                score += 10
                
            # Contextual Tags matching UI State
            if ui_state in ["results", "choosingSeat"]:
                if "requires_train_type" in tags or "requires_ticket_type" in tags:
                    score += 12
            elif ui_state == "purchased":
                if "general_info" in tags or "location_specific" in tags:
                    score += 8
            
            # Global fallback
            if "general_info" in tags:
                score += 2
                
            scored_candidates.append((score, item))
            
        # Sort by score and pick from top-N high-scoring ones
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Filter items with at least some relevance if possible
        high_score = scored_candidates[0][0]
        if high_score > 0:
            threshold = max(high_score * 0.5, 1)
            pool = [item for score, item in scored_candidates if score >= threshold]
            choice = random.choice(pool[:10]) # Top 10 suitable
        else:
            choice = random.choice(self.qa_pairs)
            
        return choice.get("question"), choice.get("answer"), choice.get("metadata", {}).get("labels", [{}])[0].get("subcategory", "general")

    def _try_interruption(self, context):
        """
        With some probability, inserts a QA or UI side-track.
        Updates context['generated_messages'] directly.
        Returns True if interrupted (and resolved), False otherwise.
        """
        if random.random() > 0.1: # 10% chance of interruption per call point
            return False
            
        interruption_type = random.choice(["qa", "qa", "ood"]) 
        
        if interruption_type == "qa":
            q, a, topic = self._get_contextual_qa(context)
            if q and a:
                u_text = self._render_utterance("qa", context, question=q, topic=topic)
                self._add_turn(context, "user", u_text)
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

    def _step_search(self, ctx, meta_contexts):
        # 1. User performs initial search (often without passengers in natural language)
        search_data = self._render_utterance_data("search_trains", ctx)
        u_search = search_data['text']
        self._add_turn(ctx, "user", u_search)
        
        # Tool Call 1: Initial Search
        call_id = self._get_next_call_id(ctx)
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
                     "time": self._clean_temporal(tool_time),
                     "date": self._clean_temporal(tool_date)
                 })
             }
        }
        
        # Execute tool 1
        resp_json_1 = self.backend.search_trains(tool_call_1["function"]["arguments"])
        resp_data_1 = json.loads(resp_json_1)
        
        # Assistant Turn 1: Call tool AND ask for passengers
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call_1], tool_output=resp_json_1)
        
        # Discover session params AFTER tool 1 but BEFORE injection if we want them in Turn 4
        # CRITICAL: Use variables from search_data to avoid leaking simulation ground truth
        ctx["session_to"] = search_vars.get("destination", ctx["destination"])
        ctx["session_date"] = search_vars.get("date", "")
        ctx["session_time"] = search_vars.get("time", "")
        
        # Update UI state for intermediate step
        ctx["ui_state"] = {"state": "search", "phase": "input_pax", "actions": "show_info"}
        self._inject_system_context(ctx, meta_contexts)
        
        # Verbal response asking for pax
        resp_ask_pax = self._render_utterance("assistant_responses", ctx, category="ask_passengers")
        self._add_turn(ctx, "assistant", resp_ask_pax)
        
        # Potential interruption after verbal response
        self._try_interruption(ctx)
        
        # 2. User provides passenger count
        u_pax = self._render_utterance("refinement", ctx, aspect="passengers", count=ctx["passengers"])
        self._add_turn(ctx, "user", u_pax)
        
        call_id_2 = self._get_next_call_id(ctx)
        tool_call_2 = {
            "id": call_id_2,
            "type": "function",
            "function": {
                "name": "search_trains",
                "arguments": json.dumps({
                    "origin": ctx["origin"], 
                    "destination": ctx["destination"], 
                    "passengers": ctx["passengers"],
                    "time": self._clean_temporal(tool_time),
                    "date": self._clean_temporal(tool_date)
                })
            }
        }
        
        # Execute search
        resp_json_2 = self.backend.search_trains(tool_call_2["function"]["arguments"])
        resp_data_2 = json.loads(resp_json_2)
        ctx["current_trains"] = resp_data_2.get("trains", [])
        
        # Discover session pax
        ctx["session_pax"] = ctx["passengers"]
        ctx["session_pax_discovered"] = True
        
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
        
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call_2], tool_output=resp_json_2)
        self._inject_system_context(ctx, meta_contexts)
        
        # Final Search Result Msg
        n_trains = len(ctx["current_trains"])
        if n_trains > 0:
            first = ctx["current_trains"][0]
            resp_success = self._render_utterance("assistant_responses", ctx, category="search_success", n_trains=n_trains, destination=ctx['destination'], first_dep=first['dep'])
            self._add_turn(ctx, "assistant", resp_success)
        else:
            resp_empty = self._render_utterance("assistant_responses", ctx, category="search_empty", destination=ctx['destination'])
            self._add_turn(ctx, "assistant", resp_empty)
            return False 

        # Potential interruption after verbal results
        self._try_interruption(ctx)

        return True

    def _step_qa(self, ctx, meta_contexts):
        q, a, topic = self._get_contextual_qa(ctx)
        if q and a:
            u_text = self._render_utterance("qa", ctx, question=q, topic=topic)
            self._add_turn(ctx, "user", u_text)
            self._add_turn(ctx, "assistant", a)

    def _step_ui(self, ctx, meta_contexts):
        # Determine available actions based on UI state
        available_actions = ["status", "back"]
        if ctx["ui_state"].get("can", {}).get("next"):
            available_actions.append("next")
        if ctx["ui_state"].get("can", {}).get("prev"):
            available_actions.append("prev")
        
        # Add show_info possibilities
        available_actions.append("show_info")
            
        action = random.choice(available_actions)
        target = None
        
        if action == "show_info":
            # Determine suitable targets based on state
            targets = ["station", "city", "help"]
            if ctx["ui_state"].get("state") == "results":
                targets.append("train") # Equivalent to old show_changes
            if ctx["ui_state"].get("state") == "purchased":
                targets.append("ticket")
                
            # Weight targets? For now random
            target = random.choice(targets)

        # If show_info(train) is picked but no target/position is in ctx yet
        if action == "show_info" and target == "train" and not ctx.get("target_train") and not ctx.get("position_word"):
            pos_map = ["primo", "secondo", "terzo"]
            target_idx = random.randint(0, min(2, len(ctx["current_trains"]) - 1)) if ctx.get("current_trains") else 0
            ctx["position_word"] = pos_map[target_idx]

        u_text = self._render_utterance("ui_navigation", ctx, action=action, 
                                       target=target,
                                       target_train=ctx.get("target_train"), 
                                       position_word=ctx.get("position_word")) 
        self._add_turn(ctx, "user", u_text)
        
        # Tool Call
        call_id = self._get_next_call_id(ctx)
        args = {"action": action}
        
        if action == "show_info":
            args["target"] = target
            if target == "train":
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
            ctx["ui_state"]["page"] = f"{self.backend.current_page + 1}/{max_page + 1}"
        elif action == "back":
            ctx["ui_state"] = {"state": "idle", "can": {"next": False, "prev": False, "back": False}}
            ctx["current_trains"] = []

        # Assistant turn with tool response
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call], tool_output=resp_json)
        
        # Inject system context (NOW, before verbal response)
        self._inject_system_context(ctx, meta_contexts)
        
        # Final verbal confirmation
        # Final verbal confirmation
        category_map = {
            "next": "ui_action",
            "prev": "ui_action",
            "back": "greeting_response", 
            "status": "ui_action",
            "show_info": "show_info_response"
        }
        
        # Prepare overrides for show_info response
        overrides = {}
        if action == "show_info":
            overrides["target"] = resp_data.get("target")
            overrides["status"] = resp_data.get("status")
            overrides["info"] = resp_data.get("info")
            
        resp = self._render_utterance("assistant_responses", ctx, category=category_map.get(action, "ui_action"), **overrides)
        self._add_turn(ctx, "assistant", resp)
        
        # Potential interruption after UI response
        self._try_interruption(ctx)

    def _step_ood(self, ctx, meta_contexts, starter=False):
        if starter:
            if self.ood_starters:
                q = random.choice(self.ood_starters)
                u_ood = self._render_utterance("ood", ctx, question=q)
                self._add_turn(ctx, "user", u_ood)
                resp = self._render_utterance("assistant_responses", ctx, category="ood_redirect")
                self._add_turn(ctx, "assistant", resp)
        else:
            if self.ood_followups:
                q = random.choice(self.ood_followups)
                u_text = self._render_utterance("ood", ctx, question=q)
                self._add_turn(ctx, "user", u_text)
                
                resp = self._render_utterance("assistant_responses", ctx, category="ood_redirect")
                self._add_turn(ctx, "assistant", resp)

    def _step_selection_purchase(self, ctx, meta_contexts):
        if not ctx.get("current_trains"):
            return

        # 1. INITIALIZATION & RANDOMIZATION
        target_index = random.choice(range(len(ctx['current_trains']))) if len(ctx["current_trains"]) > 1 else 0
        target_train = ctx["current_trains"][target_index]
        pos_map = ["primo", "secondo", "terzo"]
        pos_word = pos_map[target_index] if target_index < 3 else "questo"
        
        ctx["target_train"] = target_train
        ctx["position_word"] = pos_word

        # Deterministic class choice based on train prices
        available_classes = [p["class_denomination"] for p in target_train.get("classes", [])]
        chosen_class = random.choice(available_classes) if available_classes else "Standard"
        # Sync context class so templates use the correct denomination
        ctx["class"] = chosen_class
        
        # Map to short codes for ContextFormatter if needed
        # std, bus, prm, sil, exe
        cls_map = {"STANDARD": "std", "PREMIUM": "prm", "BUSINESS": "bus", "EXECUTIVE": "exe", "2ª CLASSE": "std", "1ª CLASSE": "prm", "ORDINARIA": "ord"}
        ctx["session_class"] = cls_map.get(chosen_class.upper(), "std")

        # --- PHASE 1: TRAIN & CLASS SELECTION ---
        provide_class_initially = random.random() < 0.5
        
        if provide_class_initially:
            # Case A: User provides both at once
            u_sel = self._render_utterance("refinement", ctx, train=target_train, aspect="train_plus_class", 
                                           position_word=pos_word, class_name=chosen_class)
            self._add_turn(ctx, "user", u_sel)
            
            call_id = self._get_next_call_id(ctx)
            args = {"train_id": target_train["id"], "class": chosen_class}
            tool_call = {
                "id": call_id, "type": "function",
                "function": {"name": "purchase_ticket", "arguments": json.dumps(args)}
            }
            resp_json = self.backend.purchase_ticket(json.dumps(args))
            self._add_turn(ctx, "assistant", None, tool_calls=[tool_call], tool_output=resp_json)
        else:
            # Case B: Two-step selection (Train then Class)
            u_sel = self._render_utterance("refinement", ctx, train=target_train, aspect="train", position_word=pos_word)
            self._add_turn(ctx, "user", u_sel)
            
            # Initial tool call (class missing)
            call_id = self._get_next_call_id(ctx)
            args_init = {"train_id": target_train["id"]}
            tool_call_init = {
                "id": call_id, "type": "function",
                "function": {"name": "purchase_ticket", "arguments": json.dumps(args_init)}
            }
            resp_json_init = self.backend.purchase_ticket(json.dumps(args_init))
            self._add_turn(ctx, "assistant", None, tool_calls=[tool_call_init], tool_output=resp_json_init)
            
            # Assistant asks for class
            resp_ask_class = self._render_utterance("assistant_responses", ctx, category="class_prompt")
            self._add_turn(ctx, "assistant", resp_ask_class)
            
            # Potential interruption
            self._try_interruption(ctx)
            
            # User provides class
            u_class = self._render_utterance("refinement", ctx, aspect="class", class_name=chosen_class)
            self._add_turn(ctx, "user", u_class)
            
            # Finalize Phase 1 tool call
            call_id_fin = self._get_next_call_id(ctx)
            args_fin = {"train_id": target_train["id"], "class": chosen_class}
            tool_call_fin = {
                "id": call_id_fin, "type": "function",
                "function": {"name": "purchase_ticket", "arguments": json.dumps(args_fin)}
            }
            resp_json_fin = self.backend.purchase_ticket(json.dumps(args_fin))
            self._add_turn(ctx, "assistant", None, tool_calls=[tool_call_fin], tool_output=resp_json_fin)

        # --- PHASE 2: SEAT SELECTION ---
        # Update UI: Choose Seats
        ctx["ui_state"] = {"state": "customize", "phase": "select_seats", "actions": "confirm,change_class,change_seat,back,show_info", "page": "1/2"}
        self._inject_system_context(ctx, meta_contexts)
        
        # Assistant asks for seats
        resp_ask_seats = self._render_utterance("assistant_responses", ctx, category="seat_prompt")
        self._add_turn(ctx, "assistant", resp_ask_seats)
        
        # Potential interruption
        self._try_interruption(ctx)
        
        # User provides seats
        u_seats = self._render_utterance("refinement", ctx, aspect="seat_multiselect") 
        if not u_seats: u_seats = f"Ho selezionato i posti 4A e 4B in carrozza 4"
        self._add_turn(ctx, "user", u_seats)
        
        # Trigger tool call with seats
        call_id_seats = self._get_next_call_id(ctx)
        args_seats = {"train_id": target_train["id"], "class": chosen_class, "seats": "4A,4B", "carriage": 4}
        tool_call_seats = {
            "id": call_id_seats, "type": "function",
            "function": {"name": "purchase_ticket", "arguments": json.dumps(args_seats)}
        }
        resp_json_seats = self.backend.purchase_ticket(json.dumps(args_seats))
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call_seats], tool_output=resp_json_seats)

        # --- PHASE 3: CONTACT DATA ---
        # Update UI: Confirm / Contact Input
        ctx["ui_state"] = {"state": "confirm", "phase": "input_contact", "actions": "back,show_info", "page": "1/2"}
        self._inject_system_context(ctx, meta_contexts)
        
        # Assistant asks for contact data
        resp_ask_data = self._render_utterance("assistant_responses", ctx, category="ask_data")
        self._add_turn(ctx, "assistant", resp_ask_data)
        
        # Potential interruption
        self._try_interruption(ctx)
        
        # User confirms they entered data
        u_confirm = self._render_utterance("confirmation", ctx)
        self._add_turn(ctx, "user", u_confirm)

        # Final tool call to complete purchase
        call_id_final = self._get_next_call_id(ctx)
        tool_call_final = {
            "id": call_id_final, "type": "function",
            "function": {"name": "purchase_ticket", "arguments": json.dumps(args_seats)}
        }
        resp_json_final = self.backend.purchase_ticket(json.dumps(args_seats))
        self._add_turn(ctx, "assistant", None, tool_calls=[tool_call_final], tool_output=resp_json_final)
        
        # --- PHASE 4: COMPLETION ---
        ctx["ticket_info"] = json.loads(resp_json_final)
        ctx["ui_state"] = {"state": "purchased", "phase": "delivery", "actions": "show_info,print,sms,email,new", "page": "1/2"}
        self._inject_system_context(ctx, meta_contexts)
        
        # Final handover
        resp_handover = self._render_utterance("assistant_responses", ctx, category="ticket_handover")
        self._add_turn(ctx, "assistant", resp_handover)

    def _step_complaint(self, ctx, meta_contexts):
        u_complaint = self._render_utterance("complaint", ctx)
        self._add_turn(ctx, "user", u_complaint)
        resp = self._render_utterance("assistant_responses", ctx, category="complaint_response")
        self._add_turn(ctx, "assistant", resp)

    def _step_farewell(self, ctx, meta_contexts):
        is_success = ctx.get("ui_state", {}).get("state") == "purchased"
        sentiment = "positive" if is_success else "neutral"
        
        u_bye = self._render_utterance("farewell", ctx, sentiment=sentiment)
        self._add_turn(ctx, "user", u_bye)
        resp_farewell = self._render_utterance("assistant_responses", ctx, category="farewell")
        self._add_turn(ctx, "assistant", resp_farewell)

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
                "verbose": ctx.get("verbose", "standard"),
                "contexts": meta_contexts
            }
        }
