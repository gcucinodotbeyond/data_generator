from abc import ABC, abstractmethod
from typing import Any, Dict, List
from .random import SeededRandom

class Scenario(ABC):
    """
    Abstract Base Class for all scenarios.
    A Scenario defines the logic to generate a single conversation sample.
    """
    
    def __init__(self, paraphraser: Any = None):
        self.paraphraser = paraphraser

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the scenario (e.g., 'search_trains')."""
        pass

    _corpus_cache = None
    @property
    def corpus(self) -> Dict[str, List[str]]:
        """Access the shared linguistic corpus."""
        if Scenario._corpus_cache is None:
            from pathlib import Path
            import json
            
            # Try loading from split corpus directory first
            resources_dir = Path(__file__).parent.parent / "resources"
            corpus_dir = resources_dir / "corpus"
            
            Scenario._corpus_cache = {}
            
            if corpus_dir.exists() and corpus_dir.is_dir():
                # Load split files
                for file_path in corpus_dir.glob("*.json"):
                    try:
                        key = file_path.stem # e.g. "search_queries"
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Store data
                            Scenario._corpus_cache[key] = data
                    except Exception as e:
                        print(f"Error loading corpus chunk {file_path}: {e}")
            else:
                print(f"Warning: Corpus directory not found at {corpus_dir}")
            
        return Scenario._corpus_cache

    def rephrase(self, rng: SeededRandom, text: str, chance: float = 0.5) -> str:
        """
        Conditionally rephrase text using the paraphraser if available.
        """
        if self.paraphraser and rng.random() < chance:
             # Use the paraphraser
             new_text = self.paraphraser.paraphrase(text)
             if new_text and len(new_text) > 3:
                 return new_text
        return text

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
