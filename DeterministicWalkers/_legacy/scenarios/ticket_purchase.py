import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.base_scenario import (
    StationManager,
    TimeManager,
    MessageBuilder,
    ContextBuilder,
    PurchaseComponent,
    SearchComponent,
    ToolCallBuilder
)

class TicketPurchase(Scenario):
    """
    Scenario for purchasing a train ticket.
    Refactored to show the full flow: Search -> Results -> Purchase.
    """
    @property
    def name(self) -> str:
        return "ticket_purchase"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        # 1. Search Step (Use is_starter=True to ensure clean start)
        search_component = SearchComponent(
            origin=origin,
            destination=destination,
            corpus=self.corpus,
            rephrase_fn=self.rephrase
        )
        
        ctx_time, trains = search_component.build(
            rng, run_id, msg_builder, ctx_builder, is_starter=True
        )
        
        # 2. Purchase Step
        # PurchaseComponent will pick one of the trains and simulate the user buying it.
        purchase_component = PurchaseComponent(
            trains=trains,
            corpus=self.corpus,
            rephrase_fn=self.rephrase,
            seat_selection=rng.random() < 0.3 # 30% chance of seat selection
        )
        
        purchase_component.build(rng, run_id, msg_builder, ctx_builder, origin)
        
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
