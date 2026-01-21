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
    QAComponent
)

class QA(Scenario):
    """
    Scenario for Question-Answer interactions using a dedicated QA dataset.
    """
    _qa_pairs_cache = None

    @property
    def name(self) -> str:
        return "qa"
        
    def _load_qa_pairs(self) -> List[List[str]]:
        if QA._qa_pairs_cache is None:
            # Look in resources/qa_pairs.json
            path = Path(__file__).parent.parent / "resources" / "qa_pairs.json"
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    QA._qa_pairs_cache = json.load(f)
            else:
                QA._qa_pairs_cache = []
        return QA._qa_pairs_cache

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # Setup
        origin = StationManager.select_random(rng, major_only=True)
        
        # Build messages
        msg_builder = MessageBuilder(predataset=kwargs.get("predataset", True))
        ctx_builder = ContextBuilder(default_date=TimeManager.generate_date(rng))
        
        msg_builder.add_system(origin)
        
        # QA Logic
        qa_pairs = self._load_qa_pairs()
        
        # If no QA pairs found, use fallback
        if not qa_pairs:
            qa_pairs = [("Come stai?", "Tutto bene, sono un assistente virtuale.")]
            
        qa_component = QAComponent(qa_pairs=qa_pairs)
        
        # Generate 1 to 3 QA turns
        num_turns = rng.randint(1, 3)
        ctx_time = TimeManager.generate_time(rng)
        
        qa_component.build(rng, msg_builder, ctx_builder, origin, ctx_time, num_exchanges=num_turns)
        
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
