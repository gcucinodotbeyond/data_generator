from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.base_scenario import (
    StationManager,
    TimeManager,
    MessageBuilder,
    ContextBuilder
)

class Rude(Scenario):
    """
    Scenario for handling rude user messages with polite de-escalation.
    """
    @property
    def name(self) -> str:
        return "rude"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        ctx_time = TimeManager.generate_time(rng)
        
        # Get rude phrases
        rude_phrases = self.corpus.get("rude_phrases", [])
        if not rude_phrases:
            rude_phrases = ["Sei inutile!", "Non capisci niente.", "Voglio parlare con un umano!"]
            
        # Get de-escalation responses (could be from corpus if available, otherwise hardcoded)
        # Assuming we don't have a specific 'deescalation' key in corpus, use generic polite responses.
        deescalations = [
            "😊 Mi dispiace che tu sia arrabbiato. Come posso aiutarti meglio?",
            "😔 Scusa se non sono stato d'aiuto. Proviamo a ricominciare?",
            "😟 Mi spiace per l'inconveniente. Dimmi come posso assisterti.",
            "🙂 Capisco la frustrazione. Sono qui per aiutarti a trovare il tuo treno."
        ]
        
        user_msg = rng.choice(rude_phrases)
        assistant_msg = rng.choice(deescalations)
        
        # Add context (assuming start of conversation or mid-conversation implies idle state)
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 2, # User + Asst
            origin=origin,
            ctx_time=ctx_time,
            ui_state='{"state":"idle"}',
            trains_array="[]"
        )
        
        msg_builder.add_user(user_msg)
        msg_builder.add_assistant(assistant_msg)
        
        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": msg_builder.get_messages(),
            "_meta": {
                "scenario": self.name,
                "seed": rng.seed,
                "run_id": run_id,
                "contexts": ctx_builder.get_contexts()
            }
        }
