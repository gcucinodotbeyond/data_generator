from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.base_scenario import (
    StationManager,
    TimeManager,
    MessageBuilder,
    ContextBuilder,
    RefusalComponent
)

class Refusal(Scenario):
    """
    Scenario for generating refusals to off-topic queries.
    """
    @property
    def name(self) -> str:
        return "refusal"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        refusal_component = RefusalComponent(corpus=self.corpus)
        
        ctx_time = TimeManager.generate_time(rng)
        
        # Generate 1 to 2 refusal turns
        num_turns = rng.randint(1, 2)
        refusal_component.build(
            rng, msg_builder, ctx_builder, 
            origin=origin, 
            ctx_time=ctx_time, 
            num_refusals=num_turns
        )
        
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
