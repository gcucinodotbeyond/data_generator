
from typing import Dict, List, Optional, Any
from core.random import SeededRandom
from scenarios.common.builders import MessageBuilder, ContextBuilder
from scenarios.common.corpus_utils import select_best_match

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
        ctx_time: str,
        style: Optional[Dict[str, str]] = None
    ) -> None:
        """Build greeting exchange."""
        greetings = self.corpus.get("greetings", [])
        
        user_greeting = None
        assistant_greeting = None
        
        if greetings and rng.random() < 0.8:
            # Use corpus greeting
            items = [
                 (item if isinstance(item, dict) else {"text": str(item), "attributes": {}})
                 for item in greetings
             ]
            selected = select_best_match(rng, items, criteria=style)
            user_greeting = selected['text']
            
            # Default response
            assistant_greeting = rng.choice([
                "😊 Ciao! Come posso aiutarti?",
                "🙂 Salve! Dimmi pure.",
                "😊 Buongiorno! Cerchi un treno?"
            ])
            
        if not user_greeting:
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
