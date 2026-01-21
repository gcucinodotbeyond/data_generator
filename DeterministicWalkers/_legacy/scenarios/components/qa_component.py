
from typing import List, Tuple
from core.random import SeededRandom
from scenarios.common.builders import MessageBuilder, ContextBuilder

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
