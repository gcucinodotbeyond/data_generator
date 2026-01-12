from abc import ABC, abstractmethod
from typing import Any, Dict, List
from .random import SeededRandom

class Scenario(ABC):
    """
    Abstract Base Class for all scenarios.
    A Scenario defines the logic to generate a single conversation sample.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the scenario (e.g., 'search_trains')."""
        pass

    @abstractmethod
    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        """
        Generate a single sample deterministically.
        
        Args:
            rng: The seeded random instance for this specific sample generation.
            run_id: The index/ID of this specific run (useful for tracking).
            
        Returns:
            A dictionary representing the generated sample (messages + _meta).
        """
        pass
