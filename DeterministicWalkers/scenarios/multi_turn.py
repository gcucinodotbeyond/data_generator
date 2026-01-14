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
    SearchComponent,
    QAComponent,
    RefusalComponent,
    GreetingComponent
)

class MultiTurn(Scenario):
    """
    Randomly composes different components to create varied multi-turn dialogues.
    """
    _qa_pairs_cache = None

    @property
    def name(self) -> str:
        return "multi_turn"
        
    def _load_qa_pairs(self) -> List[List[str]]:
        if MultiTurn._qa_pairs_cache is None:
            path = Path(__file__).parent.parent / "resources" / "qa_pairs.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    MultiTurn._qa_pairs_cache = json.load(f)
            else:
                MultiTurn._qa_pairs_cache = []
        return MultiTurn._qa_pairs_cache

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        destination = StationManager.select_different(rng, origin, major_only=False)
        
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        ctx_time = TimeManager.generate_time(rng)
        
        # Randomly choose a sequence of components
        # 0: QA only
        # 1: Refusal -> Search
        # 2: Search -> QA
        # 3: Greeting -> Search
        
        scenario_type = rng.randint(0, 3)
        
        if scenario_type == 0:
            # QA
            qa_pairs = self._load_qa_pairs()
            qa_comp = QAComponent(qa_pairs=qa_pairs)
            qa_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_exchanges=rng.randint(2, 4))
            
        elif scenario_type == 1:
            # Refusal -> Search
            ref_comp = RefusalComponent(corpus=self.corpus)
            ref_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_refusals=1)
            
            # Follow up with search
            search_comp = SearchComponent(origin, destination, self.corpus, self.rephrase)
            search_comp.build(rng, run_id, msg_builder, ctx_builder, is_starter=True)
            
        elif scenario_type == 2:
            # Search -> QA
            search_comp = SearchComponent(origin, destination, self.corpus, self.rephrase)
            ct, trains = search_comp.build(rng, run_id, msg_builder, ctx_builder, is_starter=True)
            
            # Update time from search result if needed
            if ct: ctx_time = ct
            
            # QA about the result or general
            qa_pairs = self._load_qa_pairs()
            qa_comp = QAComponent(qa_pairs=qa_pairs)
            qa_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_exchanges=1)

        elif scenario_type == 3:
            # Greeting -> Search
            greet_comp = GreetingComponent(corpus=self.corpus)
            greet_comp.build(rng, msg_builder, ctx_builder, origin, ctx_time)
            
            search_comp = SearchComponent(origin, destination, self.corpus, self.rephrase)
            search_comp.build(rng, run_id, msg_builder, ctx_builder, is_starter=True)
            
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
