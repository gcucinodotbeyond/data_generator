import random
import json
import os
from generator.context_formatter import ContextFormatter

class TurnGenerator:
    def __init__(self, renderer, enhancer=None):
        """
        renderer: DeterministicGenerator instance
        enhancer: LLMEnhancer instance (optional)
        """
        self.renderer = renderer
        self.enhancer = enhancer

    def get_next_call_id(self, context):
        if "call_counter" not in context:
            context["call_counter"] = 0
        context["call_counter"] += 1
        return f"call_{context['call_counter']:03d}"

    def clean_temporal(self, val):
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

    def render_utterance_data(self, intent, context, **overrides):
        """Helper to render an utterance using current context + overrides."""
        render_vars = context.copy()
        render_vars.update(overrides)
        
        # Special handling for list-based variables in templates
        if "destination" in render_vars:
            render_vars["destinations"] = [render_vars["destination"]]
        
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

    def render_utterance(self, intent, context, **overrides):
        return self.render_utterance_data(intent, context, **overrides)['text']

    def add_turn(self, context, role, content, tool_calls=None, tool_output=None):
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

    def inject_system_context(self, context, meta_contexts):
        """
        Inject XML-formatted system message based on current context state
        Called after key interactions (tool responses, state changes)
        """
        # Resolve travel date/time using symbolic names for Context v1.5
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
            "ui_state": context["ui_state"],
            "trains_array": context["current_trains"],
            "ctx_time": context["ctx_time"],
            "date": context["ctx_date"],
            "ticket_info": context.get("ticket_info"),
            
            "target_train": context.get("target_train"),
            "session_class": context.get("session_class"),
            "pet_small": context.get("session_pet_small", 0),
            "pet_big": context.get("session_pet_big", 0),
            "bike_normal": context.get("session_bike_normal", 0),
            "bike_foldable": context.get("session_bike_foldable", 0),
            "disability_type": context.get("session_disability"),
            "assigned_seats": context.get("assigned_seats"),
            "assigned_carriage": context.get("assigned_carriage")
        }
        
        # A11Y Context injection
        dis_type = context.get("session_disability")
        if dis_type:
             snapshot_params["a11y"] = dis_type
             a11y_instr_map = {
                 "wheelchair": "Utente in sedia a rotelle: segnala accessibilità carrozze e assistenza in stazione",
                 "motor_ambulatory": "Utente con difficoltà motorie: segnala percorsi con pochi cambi e vicini ai servizi",
                 "elderly": "Utente anziano: suggerisci soluzioni comode e vicine ai servizi",
                 "pregnant": "Utente in gravidanza: suggerisci soluzioni comode",
                 "visual": "Utente non vedente: descrivi verbalmente dettagli viaggio e stazioni",
                 "hearing": "Utente non udente: fornisci conferme scritte e visive",
                 "cognitive": "Utente con disabilità cognitiva: usa un linguaggio semplice e guida passo passo"
             }
             snapshot_params["a11y_instruction"] = a11y_instr_map.get(dis_type, "Segnala assistenza speciale")
        
        # Format as XML
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
