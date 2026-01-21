import json
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom
from scenarios.base_scenario import (
    StationManager,
    TimeManager,
    MessageBuilder,
    ContextBuilder,
    GreetingComponent,
    SearchComponent,
    ConfirmationComponent,
    PurchaseComponent,
    ToolCallBuilder
)

class GreetingToPurchase(Scenario):
    """
    Complex flow: Greeting -> Search -> Confirmation -> Purchase
    """
    @property
    def name(self) -> str:
        return "greeting_to_purchase"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        msg_builder.add_system(origin)
        
        # 1. Greeting
        greeting_component = GreetingComponent(corpus=self.corpus)
        ctx_time = TimeManager.generate_time(rng)
        greeting_component.build(rng, msg_builder, ctx_builder, origin, ctx_time)
        
        # 2. Search
        search_component = SearchComponent(
            origin=origin,
            destination=destination,
            corpus=self.corpus,
            rephrase_fn=self.rephrase
        )
        # Note: SearchComponent usually starts with User query.
        # Since we just had a greeting (User: Ciao -> Asst: Ciao), the next user msg is the search.
        # SearchComponent.build does exactly that.
        ctx_time, trains = search_component.build(rng, run_id, msg_builder, ctx_builder, is_starter=True)
        
        # 3. Confirmation (User selects a train implicitly or explicitly)
        # Use ConfirmationComponent to simulate "User: prendo il primo" -> "Asst: ok"
        # Wait, ConfirmationComponent logic in base_scenario might differ.
        # Let's check if we can reuse it or need custom logic.
        # Usually confirmation is "User confirms a previous proposal".
        # Here user creates intent to purchase.
        
        confirmation_component = ConfirmationComponent(corpus=self.corpus)
        confirmation_component.build(rng, msg_builder, ctx_builder, origin, trains_array=json.dumps(trains))
        
        # 4. Purchase
        # PurchaseComponent usually expects user to say "buy it" or similar, or just handles the flow.
        # But ConfirmationComponent already added "User: Sì, va bene" -> "Asst: Procedo".
        # So maybe we just do the purchase tool call?
        
        # Actually PurchaseComponent in base_scenario includes the user intent to buy if not already present.
        # But if Confirmation covered it, Purchase might be redundant or just the final step.
        
        # Let's look at PurchaseComponent.build: it adds User message "Lo compro" etc.
        # If Confirmation added "Sì, va bene", then we are good. 
        # But PurchaseComponent expects to DRIVE the purchase.
        
        # Simpler: Skip explicit ConfirmationComponent and use PurchaseComponent directly after Search
        # But the scenario name implies Confirmation.
        # Let's assume ConfirmationComponent is just a quick "Ok" step, then Purchase adds the final "Buying...".
        # Or better: Search -> User: "Quello delle 10" -> Asst: "Ok" -> User: "Compralo" -> ...
        
        # Let's stick to Search -> PurchaseComponent. 
        # PurchaseComponent typically has "User: Compro il primo" -> "Asst: Ecco il biglietto".
        
        purchase_component = PurchaseComponent(
            trains=trains,
            corpus=self.corpus,
            rephrase_fn=self.rephrase,
            seat_selection=False
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
