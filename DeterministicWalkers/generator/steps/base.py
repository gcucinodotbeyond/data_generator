from abc import ABC, abstractmethod

class DialogueStep(ABC):
    def __init__(self, turn_generator, context_manager, backend=None):
        self.turn_gen = turn_generator
        self.ctx_mgr = context_manager
        self.backend = backend
    
    @abstractmethod
    def execute(self, ctx, meta_contexts, **kwargs):
        """Execute this dialogue step"""
        pass
