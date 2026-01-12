# DeterministicWalkers

A deterministic, observable payload generator for training data. This system is designed to replace template-based LLM generation with a pure-Python, 100% reproducible approach.

## Key Features

- **100% Deterministic**: Run the same seed, get the exact same bytes. Guaranteed.
- **Observable**: Every generated sample includes a `_meta` field explaining exactly *why* it was generated (scenario name, seed, parameters used).
- **Fast**: No LLM calls at runtime. Generates thousands of samples in seconds.
- **Python-First**: Scenarios are defined as Python classes, not YAML templates.

## Usage

### Generating Data

To generate a dataset, run the `main.py` script:

```bash
# Generate 100 samples per scenario with default seed
python main.py --count 100

# Specify a seed for reproducibility
python main.py --count 100 --seed 42 --output my_dataset_v1
```

### Output Format

By default, the output is "Rich JSONL" containing metadata:

```json
{
  "messages": [...],
  "_meta": {
    "scenario": "search_trains",
    "seed": 123456789,
    "run_id": 5,
    "params": { ... }
  }
}
```

### Preparing for Training

Before training, remove the `_meta` fields using the provided utility:

```bash
python utils/clean_meta.py data/search_trains.jsonl data/search_trains_clean.jsonl
```

## Project Structure

- `core/`: Core logic (`Generator`, `Scenario` base class, `SeededRandom`).
- `scenarios/`: Scenario definitions (e.g., `search_trains.py`).
- `resources/`: Shared data resources (e.g., `stations.json`).
- `utils/`: Utility scripts.
- `main.py`: Entry point.

## Adding Scenarios

1. Create a new file in `scenarios/`.
2. Define a class inheriting from `core.scenario.Scenario`.
3. Implement the `generate(self, rng, run_id)` method.
4. Register the scenario in `main.py`.

## Resources

- **Stations**: `resources/stations.json` contains a comprehensive list of Italian railway stations categorized by region/importance.
