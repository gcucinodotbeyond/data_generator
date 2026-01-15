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
    GreetingComponent,
    SearchComponent,
    ConfirmationComponent,
    PurchaseComponent,
    QAComponent,
    RefusalComponent
)

class TenTurnTest(Scenario):
    """
    Deterministically generates a 10-turn conversation for slicing verification.
    Flow:
    1. Greeting
    2. ChitChat
    3. QA
    4. QA
    5. Refusal
    6. Refusal
    7. Search
    8. Confirmation
    9. Purchase
    10. Farewell
    """
    
    _qa_pairs_cache = None
    
    @property
    def name(self) -> str:
        return "ten_turn_test"

    def _load_qa_pairs(self) -> List[List[str]]:
        if self._qa_pairs_cache is None:
            path = Path(__file__).parent.parent / "resources" / "qa_pairs.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    self._qa_pairs_cache = json.load(f)
            else:
                self._qa_pairs_cache = [["Come stai?", "Bene grazie!"]]
        return self._qa_pairs_cache

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        # System Message
        msg_builder.add_system(origin)
        ctx_time = TimeManager.generate_time(rng)
        
        # 1. Greeting
        greeting_comp = GreetingComponent(corpus=self.corpus)
        greeting_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time)
        
        # 2. ChitChat (Custom implementation)
        chitchat_corpus = self.corpus.get("chitchat", [])
        if not chitchat_corpus: chitchat_corpus = ["Che bella stazione!", "C'è molta gente oggi."]
        
        user_chitchat = rng.choice(chitchat_corpus)
        asst_chitchat = "😊 Già! Ma dimmi, come posso aiutarti con i treni?"
        
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 2, # User + Asst
            origin=origin,
            ctx_time=ctx_time,
            ui_state='{"state":"idle"}',
            trains_array="[]"
        )
        msg_builder.add_user(user_chitchat)
        msg_builder.add_assistant(asst_chitchat)
        
        # 3. QA
        qa_pairs = self._load_qa_pairs()
        qa_comp = QAComponent(qa_pairs=qa_pairs)
        qa_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_exchanges=1)
        
        # 4. QA (Second one)
        qa_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_exchanges=1)
        
        # 5. Refusal
        ref_comp = RefusalComponent(corpus=self.corpus)
        ref_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_refusals=1)
        
        # 6. Refusal (Second one)
        ref_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_refusals=1)

        # 7. Search
        search_comp = SearchComponent(origin, destination, self.corpus, self.rephrase)
        ctx_time, trains = search_comp.build(rng, run_id, msg_builder, ctx_builder, is_starter=False)
        
        # 8. Confirmation (Explicit User Confirmation step)
        confirmation_comp = ConfirmationComponent(corpus=self.corpus)
        confirmation_comp.build(rng, msg_builder, ctx_builder, origin, trains_array=json.dumps(trains))

        # 9. Purchase
        purchase_comp = PurchaseComponent(
            trains=trains,
            corpus=self.corpus,
            rephrase_fn=self.rephrase
        )
        purchase_comp.build(rng, run_id, msg_builder, ctx_builder, origin)
        
        # 10. Farewell (Custom implementation)
        farewell_corpus = self.corpus.get("farewells", [])
        if not farewell_corpus: farewell_corpus = ["Arrivederci!", "Grazie, ciao!"]
        
        user_farewell = rng.choice(farewell_corpus)
        asst_farewell = "👋 Grazie a te! Buon viaggio!"
        
        ctx_builder.add_context(
            slice_length=msg_builder.current_length() + 2, # User + Asst
            origin=origin,
            ctx_time=ctx_time,
            ui_state='{"state":"idle"}', # Resetting to idle/final state
            trains_array=json.dumps(trains)
        )
        msg_builder.add_user(user_farewell)
        msg_builder.add_assistant(asst_farewell)

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
