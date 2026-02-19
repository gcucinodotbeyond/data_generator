import random
import json
import os
from generator.deterministic import DeterministicGenerator
from generator.mock_api import MockBackend
from generator.context.manager import ContextManager
from generator.turns.turn_generator import TurnGenerator
from generator.flow.builder import DialogueFlowBuilder
from generator.steps.greeting import GreetingStep
from generator.steps.disability import DisabilityStep
from generator.steps.search import SearchStep
from generator.steps.qa import QAStep
from generator.steps.ui import UIStep
from generator.steps.ood import OODStep
from generator.steps.selection import SelectionPurchaseStep
from generator.steps.complaint import ComplaintStep
from generator.steps.farewell import FarewellStep
from generator.logger import get_logger

logger = get_logger(__name__)

class DialogueGenerator:
    def __init__(self, corpus=None, enhancer=None, distribution=None):
        self.renderer = DeterministicGenerator()
        self.enhancer = enhancer
        self.backend = MockBackend()
        self.distribution = distribution or {}
        
        self.ctx_mgr = ContextManager(self.distribution)
        self.turn_gen = TurnGenerator(self.renderer, self.enhancer)

        # Initialize Steps
        self.steps = {
            "greeting": GreetingStep(self.turn_gen, self.ctx_mgr),
            "disability": DisabilityStep(self.turn_gen, self.ctx_mgr),
            "search": SearchStep(self.turn_gen, self.ctx_mgr, self.backend),
            "qa": QAStep(self.turn_gen, self.ctx_mgr),
            "ui": UIStep(self.turn_gen, self.ctx_mgr, self.backend),
            "ood": OODStep(self.turn_gen, self.ctx_mgr),
            "selection": SelectionPurchaseStep(self.turn_gen, self.ctx_mgr, self.backend),
            "complaint": ComplaintStep(self.turn_gen, self.ctx_mgr),
            "farewell": FarewellStep(self.turn_gen, self.ctx_mgr)
        }
        
        self.flow_builder = DialogueFlowBuilder(self.ctx_mgr, self.turn_gen, self.steps, self.distribution)

        # Load OOD Questions (Refusals)
        starters_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'ood_starters.json')
        followups_path = os.path.join(os.path.dirname(__file__), '..', 'resources', 'ood_followups.json')

        self.ood_starters = []
        self.ood_followups = []
        try:
            if os.path.exists(starters_path):
                with open(starters_path, 'r', encoding='utf-8') as f:
                    self.ood_starters = json.load(f)
            if os.path.exists(followups_path):
                with open(followups_path, 'r', encoding='utf-8') as f:
                    self.ood_followups = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load refusal files ({e}). OOD will be disabled.")

    def generate_dialogues(self, count=100):
        dialogues = []
        logger.info(f"[Dialogue] Generating {count} dynamic dialogues...")
        
        for i in range(count):
            self.backend = MockBackend(seed=i) 
            # Update backend in steps
            for step in self.steps.values():
                step.backend = self.backend

            try:
                d = self.flow_builder.build_dynamic_flow(i, self._try_interruption, self.ood_starters, self.ood_followups)
                dialogues.append(d)
            except Exception as e:
                logger.error(f"Error generating dialogue {i}: {e}", exc_info=True)
                
        return dialogues

    def _try_interruption(self, context):
        if random.random() > 0.1: 
            return False
            
        interruption_type = random.choice(["qa", "qa", "ood"]) 
        if interruption_type == "qa":
            return self.steps["qa"].execute(context, [])
        elif interruption_type == "ui":
            return self.steps["ui"].execute(context, [], try_interruption=None)
        elif interruption_type == "ood":
            return self.steps["ood"].execute(context, [], ood_followups=self.ood_followups)

        return False
