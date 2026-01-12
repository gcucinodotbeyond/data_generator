import random
from typing import TypeVar, Sequence, Optional, List

T = TypeVar('T')

class SeededRandom:
    """
    Deterministic wrapper around random.Random.
    Ensures that for a given seed, the sequence of choices is always identical.
    """
    
    def __init__(self, seed: int):
        self.seed = seed
        self._rng = random.Random(seed)

    def choice(self, seq: Sequence[T]) -> T:
        """Deterministically choose an element from a non-empty sequence."""
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        return self._rng.choice(seq)

    def choices(self, population: Sequence[T], weights: Optional[Sequence[float]] = None, k: int = 1) -> List[T]:
        """Deterministically choose k elements with optional weights."""
        if not population:
            raise IndexError("Cannot choose from an empty population")
        return self._rng.choices(population, weights=weights, k=k)
        
    def randint(self, a: int, b: int) -> int:
        """Return random integer in range [a, b], including both end points."""
        return self._rng.randint(a, b)
        
    def random(self) -> float:
        """Return the next random floating point number in the range [0.0, 1.0)."""
        return self._rng.random()
        
    def sample(self, population: Sequence[T], k: int) -> List[T]:
        """Return a k length list of unique elements chosen from the population sequence."""
        return self._rng.sample(population, k)

    def shuffle(self, x: List[T]) -> None:
        """Shuffle list x in place, and return None."""
        self._rng.shuffle(x)
