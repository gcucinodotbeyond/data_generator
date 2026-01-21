
from typing import Dict, List, Optional, Tuple, Any
from core.random import SeededRandom
from scenarios.common.builders import MessageBuilder, ContextBuilder, ToolCallBuilder
from scenarios.common.resource_managers import TimeManager, TrainManager
from scenarios.common.corpus_utils import select_best_match, get_templatized_text

class SearchComponent:
    """Encapsulates train search logic."""

    
    def __init__(
        self,
        origin: str,
        destination: str,
        corpus: Optional[Dict[str, List[Any]]] = None,
        rephrase_fn: Optional[callable] = None
    ):
        self.origin = origin
        self.destination = destination
        self.corpus = corpus or {}
        self.rephrase_fn = rephrase_fn
    
    def build(
        self,
        rng: SeededRandom,
        run_id: int,
        msg_builder: MessageBuilder,
        ctx_builder: ContextBuilder,
        is_starter: bool = True,
        style: Optional[Dict[str, str]] = None
    ) -> Tuple[str, List[Dict]]:
        """
        Build search interaction.
        
        Returns:
            (ctx_time, trains_list)
        """
        # Select search query template
        template = None
        search_queries = self.corpus.get("search_queries", [])
        
        # Use common selector if we have items
        if search_queries:
             # Normalize items first if they are not dicts (legacy safety)
             normalized_queries = [
                 (item if isinstance(item, dict) else {"text": str(item), "attributes": {}})
                 for item in search_queries
             ]
             
             # STRICT FILTERING: Keep only if it has 'extracted_slots' with 'destination' OR it's a string with '{destination}'
             valid_queries = []
             for item in normalized_queries:
                 if "{destination}" in item['text']:
                     valid_queries.append(item)
                 elif item.get('extracted_slots', {}).get('destination'):
                     valid_queries.append(item)
             
             # Fallback to normalized if valid is empty (should not happen with good corpus)
             candidates = valid_queries if valid_queries else normalized_queries

             # Apply heuristic filtering for Starters vs Followups
             filtered_queries = []
             bad_prefixes = ["Ah ", "Allora ", "Ok ", "Comunque ", "Sì ", "Si ", "No ", "E ", "Scusa ", "Grazie ", "Perfetto ", "Bene "]
             bad_substrings = ["capito", "capisco"]
             
             for item in candidates:
                 q_clean = item['text'].strip()
                 is_bad = False
                 for bp in bad_prefixes:
                     if q_clean.startswith(bp):
                         is_bad = True
                         break
                 
                 if is_starter:
                    for bs in bad_substrings:
                         if bs in q_clean.lower():
                             is_bad = True
                             break
                 
                 if is_starter:
                     if not is_bad:
                         filtered_queries.append(item)
                 else:
                     filtered_queries.append(item)
             
             # NOW select best match
             final_candidates = filtered_queries if filtered_queries else candidates
             if final_candidates:
                 selected_item = select_best_match(rng, final_candidates, criteria=style)
                 template = get_templatized_text(selected_item)
             else:
                 template = None

        if not template:
            template = "Vorrei andare a {destination}"
        
        # Parse time constraints
        base_hour, format_args = TimeManager.parse_template_constraints(template, rng)
        ctx_time = TimeManager.generate_time(rng, base_hour)
        
        # Add destination and origin to format args
        format_args["destination"] = self.destination
        format_args["origin"] = self.origin
        
        # Ensure {time} placeholder gets a value if present (TimeManager doesn't handle generic {time})
        if "{time}" in template:
            format_args["time"] = ctx_time
        
        # Hydrate template
        user_text = template
        for k, v in format_args.items():
            user_text = user_text.replace("{" + k + "}", str(v))
        
        # Apply rephrasing if available
        if self.rephrase_fn:
            user_text = self.rephrase_fn(rng, user_text)
        
        # Add context for this turn
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 4, # User + ToolCall + ToolResp + Asst
            origin=self.origin,
            ctx_time=ctx_time,
            ui_state='{"state":"idle"}',
            trains_array="[]"
        )
        
        # Add user message
        msg_builder.add_user(user_text)
        
        # Build and execute tool call
        tool_call_id = msg_builder.generate_tool_call_id()
        tool_call = ToolCallBuilder.build_search_call(
            tool_call_id,
            self.origin,
            self.destination,
            date="today",
            time=ctx_time
        )
        
        response_json, trains = ToolCallBuilder.execute_search(rng, run_id, tool_call)
        
        # Add tool call and response
        msg_builder.add_assistant_with_tool(tool_call)
        msg_builder.add_tool_response(response_json, tool_call_id, "search_trains")
        
        # Generate assistant reply
        if trains:
            first_dep = trains[0]["dep"]
            reply = f"😊 Ho trovato varie soluzioni per {self.destination}. La prima parte alle {first_dep}."
        else:
            reply = f"😔 Non ho trovato treni disponibili per {self.destination}."
        
        msg_builder.add_assistant(reply)
        
        return ctx_time, trains
