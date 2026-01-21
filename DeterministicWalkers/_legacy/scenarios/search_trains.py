import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.common.resource_managers import StationManager, TimeManager
from scenarios.common.builders import MessageBuilder, ContextBuilder
from scenarios.components.search_component import SearchComponent

class SearchTrains(Scenario):
    @property
    def name(self) -> str:
        return "search_trains"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        # Build search interaction
        search_component = SearchComponent(
            origin=origin,
            destination=destination,
            corpus=self.corpus,
            rephrase_fn=self.rephrase
        )
        
        # Generate the flow
        ctx_time, trains = search_component.build(rng, run_id, msg_builder, ctx_builder)
        
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
