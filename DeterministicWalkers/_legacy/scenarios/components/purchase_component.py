
import json
from typing import Dict, List, Optional, Any
from core.random import SeededRandom
from scenarios.common.builders import MessageBuilder, ContextBuilder, ToolCallBuilder
from scenarios.common.resource_managers import TimeManager
from scenarios.common.corpus_utils import select_best_match, get_templatized_text

class PurchaseComponent:
    """Encapsulates ticket purchase logic."""
    # ... (init unchanged) ...

    # ... (inside build) ...

    
    def __init__(
        self,
        trains: List[Dict],
        corpus: Optional[Dict[str, List[Any]]] = None,
        rephrase_fn: Optional[callable] = None,
        seat_selection: bool = False
    ):
        self.trains = trains
        self.corpus = corpus or {}
        self.rephrase_fn = rephrase_fn
        self.seat_selection = seat_selection
    
    def build(
        self,
        rng: SeededRandom,
        run_id: int,
        msg_builder: MessageBuilder,
        ctx_builder: ContextBuilder,
        origin: str,
        style: Optional[Dict[str, str]] = None
    ) -> None:
        """Build purchase interaction."""
        if not self.trains:
            return
        
        # Select target train
        target_idx = rng.randint(0, len(self.trains) - 1)
        target_train = self.trains[target_idx]
        
        # Determine class
        is_first_class = False
        if target_train.get("type") != "Regionale":
            if rng.random() < 0.2:
                is_first_class = True
        
        class_str = "Prima Classe" if is_first_class else "Seconda Classe"
        
        # Try to use purchase intents from corpus
        template = None
        purchase_intents = self.corpus.get("purchase_intents", [])
        
        if purchase_intents and rng.random() < 0.7:
             # Normalize first
             items = [
                 (item if isinstance(item, dict) else {"text": str(item), "attributes": {}})
                 for item in purchase_intents
             ]
             
             selected = select_best_match(rng, items, criteria=style)
             template = selected['text']
        
        if template:
            # Parse time constraints (to get baseline if needed, but we have target train)
            _, format_args = TimeManager.parse_template_constraints(template, rng)
            
            # Forced replacements from target train
            format_args["time_request"] = target_train["dep"]
            format_args["train_info"] = target_train["type"] if rng.random() < 0.8 else target_train["id"]
            
            # Hydrate
            user_text = template
            for k, v in format_args.items():
                user_text = user_text.replace("{" + k + "}", str(v))
        else:
            # Fallback to strategy-based generation
            strategies = ["ordinal", "time", "type_time", "minimal"]
            strategy = rng.choice(strategies)
            
            if strategy == "ordinal":
                ordinals = ["il primo", "il secondo", "il terzo", "il quarto"]
                obj = ordinals[target_idx] if target_idx < len(ordinals) else "quello"
                prefixes = ["Voglio comprare", "Acquista", "Prendo", "Scegli", "Compro"]
                user_text = f"{rng.choice(prefixes)} {obj}"
            elif strategy == "time":
                user_text = f"Quello delle {target_train['dep']}"
            elif strategy == "type_time":
                user_text = f"Il {target_train['type']} delle {target_train['dep']}"
            elif strategy == "minimal":
                user_text = f"Il {target_train['type']}"
            
            if is_first_class:
                user_text += " in prima classe"
            elif rng.random() < 0.3:
                user_text += " in seconda classe"
            
            if rng.random() < 0.2:
                user_text += ", per favore"
        
        # Apply rephrasing
        if self.rephrase_fn:
            user_text = self.rephrase_fn(rng, user_text)
        
        # Add context (Context for the Purchase User Turn)
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 4, # User + ToolCall + ToolResp + Asst
            origin=origin,
            ui_state='{"state":"results"}',
            trains_array=json.dumps(self.trains)
        )
        
        # Add user message
        msg_builder.add_user(user_text)
        
        # Seat selection flow
        if self.seat_selection:
            msg_builder.add_assistant("Preferisci finestrino o corridoio?")
            
            seat_pref = rng.choice(["Finestrino", "Corridoio", "Indifferente"])
            user_seat_msg = f"{seat_pref}, grazie"
            if self.rephrase_fn:
                user_seat_msg = self.rephrase_fn(rng, user_seat_msg)
            
            # Context for Seat Selection
            ctx_builder.add_context(
                 slice_length=msg_builder.current_length() + 1,
                 origin=origin,
                 ui_state='{"state":"results"}',
                 trains_array=json.dumps(self.trains)
            )

            msg_builder.add_user(user_seat_msg)
        
        # Build purchase tool call
        tool_call_id = msg_builder.generate_tool_call_id()
        tool_call = ToolCallBuilder.build_purchase_call(
            tool_call_id,
            target_train["id"],
            class_str
        )
        
        response_json = ToolCallBuilder.execute_purchase(rng, run_id, tool_call)
        
        # Add tool call and response
        msg_builder.add_assistant_with_tool(tool_call)
        msg_builder.add_tool_response(response_json, tool_call_id, "purchase_ticket")
        
        # Final reply
        msg_builder.add_assistant("😊 Il tuo biglietto è stato acquistato! Buon viaggio.")
