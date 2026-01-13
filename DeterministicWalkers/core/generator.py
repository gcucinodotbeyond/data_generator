import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Type, Dict, Any
from .scenario import Scenario
from .random import SeededRandom

class Generator:
    """
    Main controller for deterministic data generation.
    Manages the registration of scenarios and the generation loop.
    """
    
    def __init__(self, output_dir: str, seed: int = 42, predataset: bool = True, paraphraser: Any = None):
        self.output_dir = Path(output_dir)
        self.global_seed = seed
        self.predataset = predataset
        self.paraphraser = paraphraser
        self.scenarios: Dict[str, Type[Scenario]] = {}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def register_scenario(self, scenario_cls: Type[Scenario]):
        """Register a scenario class."""
        # Instantiate to get the name property
        # We instantiate with None just to get the name property, 
        # actual instantiation happens in generate_scenario with real deps if needed?
        # Actually generate_scenario instantiates again.
        temp_instance = scenario_cls()
        self.scenarios[temp_instance.name] = scenario_cls

    def generate_all(self, count_per_scenario: int = 100):
        """
        Generate samples for all registered scenarios.
        
        Args:
            count_per_scenario: Number of samples to generate per scenario.
        """
        for name, cls in self.scenarios.items():
            self.generate_scenario(name, count_per_scenario)

    def generate_scenario(self, scenario_name: str, count: int):
        """
        Generate samples for a specific scenario.
        
        Args:
            scenario_name: Name of the scenario to generate.
            count: Number of samples to generate.
        """
        if scenario_name not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_name}")
            
        scenario_cls = self.scenarios[scenario_name]
        scenario = scenario_cls(paraphraser=self.paraphraser) # Instantiate the scenario
        
        output_file = self.output_dir / f"{scenario_name}.jsonl"
        print(f"Generating {count} samples for '{scenario_name}' to {output_file}...")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i in range(count):
                # Deterministic seed for this specific sample
                # Combine global seed, scenario name hash (deterministic), and index
                import zlib
                scenario_hash = zlib.adler32(scenario_name.encode('utf-8'))
                sample_seed = self.global_seed + scenario_hash + i
                rng = SeededRandom(sample_seed)
                
                try:
                    sample = scenario.generate(rng, i, predataset=self.predataset)
                    f.write(json.dumps(sample, ensure_ascii=False) + '\n')
                except Exception as e:
                    print(f"Error generating sample {i} for {scenario_name}: {e}")
                    # In strict mode we might want to raise, but for now log and continue
