"""
Base scenario components and utilities for composable scenario generation.

This module provides reusable building blocks for constructing complex scenarios
from simple, composable components.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from core.random import SeededRandom


# ============================================================================
# Resource Managers
# ============================================================================

class StationManager:
    """Manages station data loading and selection."""
    
    _stations_cache = None
    
    @classmethod
    def _load_stations(cls):
        """Load station data from resources (cached)."""
        if cls._stations_cache is None:
            resource_path = Path(__file__).parent.parent / "resources" / "stations.json"
            try:
                with open(resource_path, 'r', encoding='utf-8') as f:
                    stations_data = json.load(f)
                
                all_stations = []
                for category in stations_data.values():
                    all_stations.extend(category)
                
                cls._stations_cache = {
                    'all': sorted(list(set(all_stations))),
                    'major': stations_data.get("major", all_stations[:20])
                }
            except FileNotFoundError:
                cls._stations_cache = {
                    'all': ["Roma Termini", "Milano Centrale"],
                    'major': ["Roma Termini", "Milano Centrale"]
                }
        return cls._stations_cache
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all stations."""
        return cls._load_stations()['all']
    
    @classmethod
    def get_major(cls) -> List[str]:
        """Get major stations."""
        return cls._load_stations()['major']
    
    @classmethod
    def select_random(cls, rng: SeededRandom, major_only: bool = False) -> str:
        """Select a random station."""
        stations = cls.get_major() if major_only else cls.get_all()
        return rng.choice(stations)
    
    @classmethod
    def select_different(cls, rng: SeededRandom, exclude: str, major_only: bool = False) -> str:
        """Select a random station different from the excluded one."""
        stations = cls.get_major() if major_only else cls.get_all()
        candidates = [s for s in stations if s != exclude]
        return rng.choice(candidates) if candidates else exclude


class TimeManager:
    """Manages time context generation with template constraints."""
    
    @staticmethod
    def generate_time(rng: SeededRandom, base_hour: Optional[int] = None) -> str:
        """
        Generate a time string (HH:MM format).
        
        Args:
            rng: Random number generator
            base_hour: Specific hour to use (if None, generates random hour 6-22)
        
        Returns:
            Time string in HH:MM format
        """
        hour = base_hour if base_hour is not None else rng.randint(6, 22)
        minute = rng.randint(0, 59)
        return f"{hour:02d}:{minute:02d}"
    
    @staticmethod
    def generate_date(rng: SeededRandom) -> str:
        """
        Generate a random date within a reasonable range (e.g., Dec 2025 - Jan 2026).
        """
        # Simple random date generation
        # Let's say between 2025-12-01 and 2026-01-31
        year = 2025
        month = 12
        day = rng.randint(1, 31)
        
        # 20% chance of being in Jan 2026
        if rng.random() < 0.2:
            year = 2026
            month = 1
            day = rng.randint(1, 31)
        
        return f"{year}-{month:02d}-{day:02d}"

    @staticmethod
    def parse_template_constraints(template: str, rng: SeededRandom) -> Tuple[int, Dict[str, str]]:
        """
        Parse template for time constraints and return base_hour and replacements.
        
        This method analyzes user message templates for time-related placeholders
        and generates appropriate time values that match the semantic context.
        
        Returns:
            (base_hour, format_args) tuple
        """
        # Default to mid-day hours
        base_hour = rng.randint(8, 20)
        format_args = {}
        
        # Morning period
        if "{period_morning}" in template:
            base_hour = rng.randint(6, 11)
            format_args["period_morning"] = rng.choice(["stamattina", "questa mattina"])
        
        # Afternoon period
        elif "{period_afternoon}" in template:
            base_hour = rng.randint(12, 17)
            format_args["period_afternoon"] = rng.choice(["oggi pomeriggio", "questo pomeriggio"])
        
        # Evening period
        elif "{period_evening}" in template:
            base_hour = rng.randint(16, 21)
            format_args["period_evening"] = rng.choice(["stasera", "questa sera"])
        
        # Relative dates
        if "{relative_date_morning}" in template:
            format_args["relative_date_morning"] = "domani mattina"
        if "{relative_date_afternoon}" in template:
            format_args["relative_date_afternoon"] = "domani pomeriggio"
        if "{relative_date_evening}" in template:
            format_args["relative_date_evening"] = "domani sera"
        if "{relative_date}" in template:
            format_args["relative_date"] = rng.choice(["domani", "dopodomani"])
        if "{relative_today}" in template:
            format_args["relative_today"] = "oggi"
        
        # Time request
        if "{time_request}" in template:
            req_h = (base_hour + rng.randint(1, 4)) % 24
            req_m = rng.choice([0, 15, 30, 45])
            format_args["time_request"] = f"{req_h:02d}:{req_m:02d}"
        
        # Train info
        if "{train_info}" in template:
            format_args["train_info"] = TrainManager.select_random(rng)
        
        return base_hour, format_args


class TrainManager:
    """Manages train type and ID generation."""
    
    TRAIN_TYPES = [
        "Frecciarossa", "Frecciargento", "Frecciabianca", 
        "Intercity", "Intercity Notte", "Regionale Veloce", "Regionale",
        "Eurocity"
    ]
    
    TRAIN_PREFIXES = {
        "Frecciarossa": "FR",
        "Frecciargento": "FA",
        "Frecciabianca": "FB",
        "Intercity": "IC",
        "Intercity Notte": "ICN",
        "Regionale Veloce": "RV",
        "Regionale": "R",
        "Eurocity": "EC"
    }
    
    @classmethod
    def select_random_type(cls, rng: SeededRandom) -> str:
        """Select a random train type name."""
        return rng.choice(cls.TRAIN_TYPES)
    
    @classmethod
    def generate_id(cls, rng: SeededRandom, train_type: Optional[str] = None) -> str:
        """Generate a random train ID."""
        if not train_type or train_type not in cls.TRAIN_PREFIXES:
            train_type = cls.select_random_type(rng)
        
        prefix = cls.TRAIN_PREFIXES.get(train_type, "TR")
        number = rng.randint(1000, 9999)
        return f"{prefix}{number}"
    
    @classmethod
    def select_random(cls, rng: SeededRandom) -> str:
        """Select either a type or an ID randomly."""
        if rng.random() < 0.7:
            return cls.select_random_type(rng)
        else:
            return cls.generate_id(rng)


# ============================================================================
# Message Builders
# ============================================================================

class MessageBuilder:
    """Fluent interface for constructing conversation messages."""
    
    def __init__(self, predataset: bool = True):
        self.messages: List[Dict[str, Any]] = []
        self.predataset = predataset
        self.tool_call_counter = 0

    def generate_tool_call_id(self) -> str:
        """Generate a sequential tool call ID for this conversation."""
        self.tool_call_counter += 1
        return f"call_{self.tool_call_counter:03d}"
    
    def add_system(self, origin: Optional[str] = None, ctx_time: Optional[str] = None) -> 'MessageBuilder':
        """Add system message."""
        if self.predataset:
            content = "{{SYSTEM_PROMPT}}"
        else:
            # Hydrated system prompt placeholder (should usually use predataset for training generation)
            content = f"Sei Talìa, l'assistente virtuale di Trenitalia.\n<ctx>stazione: {origin}\nora: {ctx_time}\n</ctx>\n"
        
        self.messages.append({"role": "system", "content": content})
        return self
    
    def add_user(self, content: str) -> 'MessageBuilder':
        """Add user message."""
        self.messages.append({"role": "user", "content": content})
        return self
    
    def add_assistant(self, content: str) -> 'MessageBuilder':
        """Add assistant text message."""
        self.messages.append({"role": "assistant", "content": content})
        return self
    
    def add_assistant_with_tool(self, tool_call: Dict[str, Any]) -> 'MessageBuilder':
        """Add assistant message with tool call."""
        self.messages.append({
            "role": "assistant",
            "tool_calls": [tool_call],
            "content": None
        })
        return self
    
    def add_tool_response(self, content: str, tool_call_id: str, name: str) -> 'MessageBuilder':
        """Add tool response message."""
        self.messages.append({
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id,
            "name": name
        })
        return self
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages."""
        return self.messages
    
    def current_length(self) -> int:
        """Get current message count."""
        return len(self.messages)


class ContextBuilder:
    """Build _meta.contexts entries."""
    
    def __init__(self, default_date: str = "2025-12-23"):
        self.contexts: List[Dict[str, Any]] = []
        self.default_date = default_date
    
    def add_context(
        self,
        slice_length: int,
        origin: str,
        ctx_time: Optional[str] = None,
        date: Optional[str] = None,
        ui_state: str = '{"state":"idle"}',
        trains_array: str = "[]",
        **extra_params
    ) -> 'ContextBuilder':
        """Add a context entry."""
        params = {
            "origin": origin,
            "ui_state": ui_state,
            "trains_array": trains_array
        }
        
        if ctx_time:
            params["ctx_time"] = ctx_time
        
        params["date"] = date if date is not None else self.default_date
        
        # Add any extra parameters
        params.update(extra_params)
        
        self.contexts.append({
            "slice_length": slice_length,
            "params": params
        })
        return self
    
    def get_contexts(self) -> List[Dict[str, Any]]:
        """Get all contexts."""
        return self.contexts


class ToolCallBuilder:
    """Build tool calls and responses using MockBackend."""
    
    @staticmethod
    def build_search_call(
        tool_call_id: str,
        origin: str,
        destination: str,
        date: str = "today",
        time: str = "now",
        passengers: int = 1
    ) -> Dict[str, Any]:
        """Build a search_trains tool call."""
        args = {
            "origin": origin,
            "destination": destination,
            "date": date,
            "time": time,
            "passengers": passengers
        }
        
        return {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "search_trains",
                "arguments": json.dumps(args)
            }
        }
    
    @staticmethod
    def build_purchase_call(
        tool_call_id: str,
        train_id: str,
        train_class: str = "Seconda Classe"
    ) -> Dict[str, Any]:
        """Build a purchase_ticket tool call."""
        args = {
            "train_id": train_id,
            "class": train_class
        }
        
        return {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "purchase_ticket",
                "arguments": json.dumps(args)
            }
        }
    
    @staticmethod
    def execute_search(rng: SeededRandom, run_id: int, tool_call: Dict[str, Any]) -> Tuple[str, List[Dict]]:
        """
        Execute search using MockBackend.
        
        Returns:
            (tool_response_json, trains_list)
        """
        # Lazy import to avoid circular dependencies
        import sys
        if str(Path(__file__).parent.parent) not in sys.path:
             sys.path.append(str(Path(__file__).parent.parent))
        from mock_api import MockBackend
        
        backend = MockBackend(seed=rng.seed + run_id)
        
        args_json = tool_call["function"]["arguments"]
        response_json = backend.search_trains(args_json)
        response_data = json.loads(response_json)
        trains = response_data.get("trains", [])
        
        return response_json, trains
    
    @staticmethod
    def execute_purchase(rng: SeededRandom, run_id: int, tool_call: Dict[str, Any]) -> str:
        """Execute purchase using MockBackend."""
        import sys
        if str(Path(__file__).parent.parent) not in sys.path:
             sys.path.append(str(Path(__file__).parent.parent))
        from mock_api import MockBackend

        backend = MockBackend(seed=rng.seed + run_id)
        
        args_json = tool_call["function"]["arguments"]
        return backend.purchase_ticket(args_json)


# ============================================================================
# Scenario Components
# ============================================================================

class SearchComponent:
    """Encapsulates train search logic."""
    
    def __init__(
        self,
        origin: str,
        destination: str,
        corpus: Optional[Dict[str, List[str]]] = None,
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
        is_starter: bool = True
    ) -> Tuple[str, List[Dict]]:
        """
        Build search interaction.
        
        Returns:
            (ctx_time, trains_list)
        """
        # Select search query template
        template = None
        search_queries = self.corpus.get("search_queries", [])
        
        if search_queries:
            # Heuristic filtering for Starters vs Followups
             filtered_queries = []
             bad_prefixes = ["Ah ", "Allora ", "Ok ", "Comunque ", "Sì ", "Si ", "No ", "E ", "Scusa ", "Grazie ", "Perfetto ", "Bene "]
             bad_substrings = ["capito", "capisco"]
             
             for q in search_queries:
                 q_clean = q.strip()
                 is_bad = False
                 for bp in bad_prefixes:
                     if q_clean.startswith(bp):
                         is_bad = True
                         break
                 
                 # Only check substring if strict starter
                 if is_starter:
                    for bs in bad_substrings:
                         if bs in q_clean.lower():
                             is_bad = True
                             break
                 
                 if is_starter:
                     if not is_bad:
                         filtered_queries.append(q)
                 else:
                     # Non-starter: prefer bad or allow all? Allow all for variety.
                     filtered_queries.append(q)
            
             if not filtered_queries:
                 filtered_queries = search_queries

             # Prefer templates with destination placeholder
             candidates = [c for c in filtered_queries if "{destination}" in c]
             if not candidates:
                 candidates = filtered_queries
             
             if candidates:
                 template = rng.choice(candidates)
        
        if not template:
            template = "Vorrei andare a {destination}"
        
        # Parse time constraints
        base_hour, format_args = TimeManager.parse_template_constraints(template, rng)
        ctx_time = TimeManager.generate_time(rng, base_hour)
        
        # Add destination and origin to format args
        format_args["destination"] = self.destination
        format_args["origin"] = self.origin
        
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


class PurchaseComponent:
    """Encapsulates ticket purchase logic."""
    
    def __init__(
        self,
        trains: List[Dict],
        corpus: Optional[Dict[str, List[str]]] = None,
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
        origin: str
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
             template = rng.choice(purchase_intents)
        
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


class QAComponent:
    """Handles Q&A exchanges."""
    
    def __init__(self, qa_pairs: List[Tuple[str, str]]):
        self.qa_pairs = qa_pairs
    
    def build(
        self,
        rng: SeededRandom,
        msg_builder: MessageBuilder,
        ctx_builder: ContextBuilder,
        origin: str,
        ctx_time: str,
        trains_array: str = "[]",
        num_exchanges: int = 1
    ) -> None:
        """Build Q&A exchanges."""
        if not self.qa_pairs: return
        selected_pairs = rng.sample(self.qa_pairs, min(num_exchanges, len(self.qa_pairs)))
        
        for q, a in selected_pairs:
            # Add context
            ctx_builder.add_context(
                slice_length=msg_builder.current_length() + 2, # Includes Asst reply
                origin=origin,
                ctx_time=ctx_time,
                ui_state='{"state":"idle"}',
                trains_array=trains_array
            )
            
            msg_builder.add_user(q)
            msg_builder.add_assistant(a)


class RefusalComponent:
    """Handles off-topic/refusal responses."""
    
    DEFAULT_QUERIES = [
        "Cosa ne pensi di Bitcoin?",
        "Chi vincerà lo scudetto?",
        "Ricetta della carbonara?",
        "Miglior smartphone del 2025?",
        "Che film mi consigli?",
        "Che tempo farà domani?"
    ]
    
    DEFAULT_REFUSALS = [
        "😔 Non è la mia specialità! 😊 Sono qui per i treni invece.",
        "😔 Non me ne occupo. 😄 Viaggi in treno da organizzare?",
        "😕 Quello non è il mio campo! 😊 Per i treni invece perfetto.",
        "🤔 Non posso aiutarti con questo. 😊 Biglietti da comprare?",
        "😔 Mi dispiace, non so rispondere. 😄 Treni però sì!"
    ]
    
    def __init__(self, corpus: Optional[Dict[str, Any]] = None):
        self.corpus = corpus or {}

    def build(
        self,
        rng: SeededRandom,
        msg_builder: MessageBuilder,
        ctx_builder: ContextBuilder,
        origin: str,
        ctx_time: str,
        num_refusals: int = 2
    ) -> None:
        """Build refusal exchanges."""
        # Use refusals from corpus if available (list expected)
        # refusals = self.corpus.get("refusals", [])
        refusal_templates = self.DEFAULT_REFUSALS
        
        # if refusals and isinstance(refusals, list) and len(refusals) > 0:
        #     refusal_templates = refusals

        used_queries = []
        for _ in range(num_refusals):
            query = rng.choice([q for q in self.DEFAULT_QUERIES if q not in used_queries])
            used_queries.append(query)
            
            refusal = rng.choice(refusal_templates)
            
            ctx_builder.add_context(
                slice_length=msg_builder.current_length() + 2, # System + Prev + User + Asst
                origin=origin,
                ctx_time=ctx_time,
                ui_state='{"state":"idle"}',
                trains_array="[]"
            )
            
            msg_builder.add_user(query)
            msg_builder.add_assistant(refusal)


class GreetingComponent:
    """Handles greeting exchanges at conversation start."""
    
    DEFAULT_GREETINGS = [
        ("Ciao!", "😊 Ciao! Come posso aiutarti oggi?"),
        ("Buongiorno", "😊 Buongiorno! Come posso esserti utile?"),
        ("Salve", "🙂 Salve! Benvenuto, dimmi pure."),
        ("Hey", "😊 Hey! Ti ascolto, cosa ti serve?"),
        ("Buonasera", "😊 Buonasera! Sono qui per aiutarti.")
    ]
    
    def __init__(self, corpus: Optional[Dict[str, Any]] = None):
        self.corpus = corpus or {}

    def build(
        self,
        rng: SeededRandom,
        msg_builder: MessageBuilder,
        ctx_builder: ContextBuilder,
        origin: str,
        ctx_time: str
    ) -> None:
        """Build greeting exchange."""
        # Note: Greetings from corpus would be single phrases (User calls), not pairs. 
        # For simplicity, we use default pairs, but we could mix corpus greetings if we had them.
        # Since corpus greetings are empty or sparse, defaults are safer.
        user_greeting, assistant_greeting = rng.choice(self.DEFAULT_GREETINGS)
        
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 2, # System + User + Asst
            origin=origin,
            ctx_time=ctx_time,
            ui_state='{"state":"idle"}',
            trains_array="[]"
        )
        
        msg_builder.add_user(user_greeting)
        msg_builder.add_assistant(assistant_greeting)


class ConfirmationComponent:
    """Handles confirmation/acknowledgment exchanges."""
    
    DEFAULT_CONFIRMATIONS = [
        ("Ok, perfetto!", "😊 Benissimo!"),
        ("Va bene", "🙂 Ottimo!"),
        ("D'accordo", "😊 Perfetto!"),
        ("Grazie!", "😊 Prego, figurati!"),
        ("Capito", "🙂 Bene!")
    ]
    
    def __init__(self, corpus: Optional[Dict[str, Any]] = None):
        self.corpus = corpus or {}

    def build(
        self,
        rng: SeededRandom,
        msg_builder: MessageBuilder,
        ctx_builder: ContextBuilder,
        origin: str,
        trains_array: str = "[]"
    ) -> None:
        """Build confirmation exchange."""
        confirmations = self.corpus.get("confirmations", [])
        user_text = None
        
        if confirmations and isinstance(confirmations, list):
            # Already filtered by corpus_builder
            if confirmations:
                user_text = rng.choice(confirmations)
        
        if not user_text:
            pair = rng.choice(self.DEFAULT_CONFIRMATIONS)
            user_text = pair[0]
            asst_text = pair[1]
        else:
            # Need a generic assistant confirmation if we only pick user text from corpus
            asst_text = rng.choice(["😊 Benissimo!", "🙂 Ottimo!", "😊 Perfetto!", "🙂 Bene!"])
            
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 2, # User + Asst
            origin=origin,
            ui_state='{"state":"idle"}',
            trains_array=trains_array
        )
            
        msg_builder.add_user(user_text)
        msg_builder.add_assistant(asst_text)
