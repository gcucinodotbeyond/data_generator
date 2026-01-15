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
    GreetingComponent,
    PurchaseComponent
)

class MultiTurn(Scenario):
    """
    Randomly composes different components to create varied multi-turn dialogues.
    Uses a State Machine approach for dynamic flow generation.
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
        
        # --- State Machine ---
        state = "GREETING" # Start state
        turns = 0
        MAX_TURNS = 10
        current_trains_array = "[]"
        search_results = []
        
        # If we have chitchat in corpus, load it
        chitchat_corpus = self.corpus.get("chitchat", [])
        farewell_corpus = self.corpus.get("farewells", [])
        
        # Override start state probabilistically
        if rng.random() < 0.3:
            state = "SEARCH"
        elif rng.random() < 0.1:
            state = "QA"
            
        while state != "END" and turns < MAX_TURNS:
            turns += 1
            
            if state == "GREETING":
                GreetingComponent(self.corpus).build(rng, msg_builder, ctx_builder, origin, ctx_time)
                
                # Transitions
                draw = rng.random()
                if draw < 0.6: state = "SEARCH"
                elif draw < 0.8: state = "CHITCHAT"
                else: state = "QA"
                
            elif state == "CHITCHAT":
                # Explicit inline logic for ChitChat
                user_msg = "Come va?"
                asst_msg = "😊 Tutto bene, grazie! E a te?"
                
                if chitchat_corpus:
                    user_msg = rng.choice(chitchat_corpus)
                    asst_msg = "😊 Ma dimmi, come posso aiutarti con i treni?" 
                    # Simple fallback response since we don't have a chatty bot engine
                
                ctx_builder.add_context(
                    slice_length=msg_builder.current_length() + 2,
                    origin=origin,
                    ctx_time=ctx_time,
                    ui_state='{"state":"idle"}',
                    trains_array=current_trains_array
                )
                msg_builder.add_user(user_msg)
                msg_builder.add_assistant(asst_msg)
                
                # Transitions
                draw = rng.random()
                if draw < 0.8: state = "SEARCH"
                else: state = "QA"
                
            elif state == "QA":
                qa_pairs = self._load_qa_pairs()
                QAComponent(qa_pairs).build(rng, msg_builder, ctx_builder, origin, ctx_time, current_trains_array, num_exchanges=1)
                
                # Transitions
                draw = rng.random()
                if draw < 0.5: state = "SEARCH"
                elif draw < 0.8: state = "REFUSAL"
                else: state = "FAREWELL"

            elif state == "REFUSAL":
                RefusalComponent(self.corpus).build(rng, msg_builder, ctx_builder, origin, ctx_time, num_refusals=1)
                
                state = "SEARCH" # Almost always redirect to search
                
            elif state == "SEARCH":
                # Search interaction
                # If we already have results, this might be a refinement or new search
                dest = destination
                if search_results and rng.random() < 0.5:
                    dest = StationManager.select_different(rng, origin, major_only=False)
                
                search_comp = SearchComponent(origin, dest, self.corpus, self.rephrase)
                new_time, new_trains = search_comp.build(rng, run_id + turns, msg_builder, ctx_builder, is_starter=(turns <= 2))
                
                if new_time: ctx_time = new_time
                if new_trains: 
                    search_results = new_trains
                    current_trains_array = json.dumps(new_trains)
                
                # Transitions
                draw = rng.random()
                if new_trains and draw < 0.6: state = "PURCHASE" # If found trains, likely buy
                elif draw < 0.8: state = "QA"
                else: state = "FAREWELL" # Gave up or satisfied
                
                # If no trains found, maybe refine or quit
                if not new_trains:
                     if rng.random() < 0.5: state = "SEARCH" # Retry
                     else: state = "FAREWELL"

            elif state == "PURCHASE":
                # Can only purchase if we have trains
                if not search_results:
                    state = "SEARCH"
                    continue
                    
                PurchaseComponent(
                    search_results, self.corpus, self.rephrase, 
                    seat_selection=(rng.random() < 0.3)
                ).build(rng, run_id + turns, msg_builder, ctx_builder, origin)
                
                # After purchase, usually done
                state = "FAREWELL"
                
            elif state == "FAREWELL":
                user_msg = "Grazie, ciao!"
                asst_msg = "👋 A presto!"
                
                if farewell_corpus:
                    user_msg = rng.choice(farewell_corpus)
                
                ctx_builder.add_context(
                    slice_length=msg_builder.current_length() + 2,
                    origin=origin,
                    ctx_time=ctx_time,
                    ui_state='{"state":"idle"}',
                    trains_array=current_trains_array
                )
                msg_builder.add_user(user_msg)
                msg_builder.add_assistant(asst_msg)
                
                state = "END"
        
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
