
from typing import Dict, List, Optional, Any
from core.random import SeededRandom
from scenarios.common.builders import MessageBuilder, ContextBuilder
from scenarios.common.corpus_utils import select_best_match

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
        trains_array: str = "[]",
        style: Optional[Dict[str, str]] = None
    ) -> None:
        """Build confirmation exchange."""
        confirmations = self.corpus.get("confirmations", [])
        user_text = None
        asst_text = None
        
        if confirmations:
            items = [
                 (item if isinstance(item, dict) else {"text": str(item), "attributes": {}})
                 for item in confirmations
             ]
            selected = select_best_match(rng, items, criteria=style)
            user_text = selected['text']
        
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
