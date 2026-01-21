
from typing import Dict, List, Optional, Any
from core.random import SeededRandom
from scenarios.common.builders import MessageBuilder, ContextBuilder
from scenarios.common.corpus_utils import select_best_match

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
        num_refusals: int = 2,
        style: Optional[Dict[str, str]] = None
    ) -> None:
        """Build refusal exchanges."""
        # Use ood_phrases from corpus if available
        ood_phrases = self.corpus.get("ood_phrases", [])
        
        # We need pairs of (Query, Refusal).
        # Typically the refusal scenario generates a fake query like "Who won the match?" and the assistant refuses.
        # If corpus has OOD queries, we use them.
        
        queries = self.DEFAULT_QUERIES
        if ood_phrases:
             # Normalize
             items = [
                 (item if isinstance(item, dict) else {"text": str(item), "attributes": {}})
                 for item in ood_phrases
             ]
             # For OOD, style might be less relevant for the QUERY, but good to support.
             # We want multiple queries, so we might pick multiple times?
             # select_best_match only returns one.
             # For logic simplicity, we'll pick from filtered pool or loop
             
             queries = [] # Rebuild pool
             # This is tricky because we need N queries. 
             # Let's simple pick N times using selector
             pass 
        
        # Re-implement loop to pick N queries using selector
        used_queries = []
        for _ in range(num_refusals):
            query = None
            if ood_phrases:
                 # Normalize inside loop to support different selections??
                 # Or just pass list
                 items = [
                     (item if isinstance(item, dict) else {"text": str(item), "attributes": {}})
                     for item in ood_phrases
                 ]
                 # Filter out used
                 items = [i for i in items if i['text'] not in used_queries]
                 
                 if items:
                    selected = select_best_match(rng, items, criteria=style)
                    query = selected['text']

            if not query: 
                candidates = [q for q in self.DEFAULT_QUERIES if q not in used_queries]
                if candidates:
                    query = rng.choice(candidates)
                else:
                    query = rng.choice(self.DEFAULT_QUERIES)

            used_queries.append(query)
            
            refusal = rng.choice(self.DEFAULT_REFUSALS)
            
            ctx_builder.add_context(
                slice_length=msg_builder.current_length() + 2, # System + Prev + User + Asst
                origin=origin,
                ctx_time=ctx_time,
                ui_state='{"state":"idle"}',
                trains_array="[]"
            )
            
            msg_builder.add_user(query)
            msg_builder.add_assistant(refusal)
