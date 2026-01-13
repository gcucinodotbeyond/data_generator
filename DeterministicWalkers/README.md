# DeterministicWalkers

A **deterministic, observable, and Python-first** payload generator for training data.  
This system replaces opaque LLM-based generation with a 100% reproducible approach where every sample is generated via clear Python logic, backed by a linguistic corpus.

---

## 🚀 Key Philosophy

1.  **100% Deterministic**: If you run the generator with Seed `42`, you get the *exact* same dataset, byte-for-byte. Every time.
2.  **Observable**: Every generated sample includes a `_meta` object explaining *why* it exists (which scenario created it, what parameters were chosen, what random decisions were made).
3.  **Dynamic Context Injection**: The system separates the "skeleton" of the conversation (generated in Python) from the "context" (Time, Date, Location, System Prompt), allowing you to re-hydrate the same dataset with different contexts (e.g., injecting a different System Prompt or simulating different times of day).
4.  **Corpus-Driven**: Uses a library of natural language utterances (`resources/corpus`) extracted from real data, rather than generating text from scratch.

---

## 📂 Project Structure

```text
DeterministicWalkers/
├── core/                   # Core engine (Base Scenario, SeededRandom)
├── scenarios/              # Python scripts defining generation logic (e.g., search_trains.py)
├── resources/              # Static Assets & Configuration
│   ├── corpus/             # Raw linguistic data (JSON files)
│   ├── stations.json       # Domain data (Stations list)
│   ├── tools.json          # Tool definitions (OpenAI/Qwen format)
│   └── system_prompt.md    # Template for System Prompt
├── tools/                  # Helper scripts (corpus extraction, etc.)
├── main.py                 # Generator Entry Point
└── hydrate_dataset.py      # Context Injection Script
```

---

## 🛠️ Usage

### 1. Generate the Pre-Dataset
The first step generates the "Pre-Dataset". This contains the conversation flow, tool calls, and metadata, but has **placeholders** for the System Prompt and dynamic context.

```bash
# Generate 100 samples per scenario
python main.py --count 100 --seed 42
```

**Output**: A folder `predataset/` containing JSONL files (e.g., `search_trains.jsonl`).

### 2. Hydrate the Dataset
The "Hydration" process takes the Pre-Dataset and injects the actual System Prompt, Tools, and Dynamic Context (simulated time, location, etc.).

```bash
# Hydrate the dataset using the default system prompt template
python hydrate_dataset.py predataset
```

**Output**: A folder `hydrated-dataset/` containing the final, ready-to-train JSONL files.

---

## 🧠 Core Concepts

### The "Corpus" (`resources/corpus/`)
The system relies on a **linguistic corpus** to provide natural variety. This is located in `resources/corpus/` and consists of JSON files categorized by intent (e.g., `search_queries.json`, `refusals.json`).

> **⚠️ Note on Specificity**: The corpus data is often extracted from real usage logs or external datasets. It may contain **highly specific** temporal references (e.g., "Devo partire *stasera alle 20:30*").
> 
> If your system relies on a **Dynamic Context** (e.g., the virtual system time is 10:00 AM, but the user message says "stasera"), these specific entries might create inconsistencies. 
> **Recommendation**: Review and clean `resources/corpus/` to ensure generic compatibility, or ensure your Scenarios logic can handle/override these specificities.

### Scenarios (`scenarios/*.py`)
A **Scenario** is a Python class that inherits from `core.scenario.Scenario`. It defines:
1.  **Logic**: How to construct the user intent (e.g., "Search for a train").
2.  **Parameters**: Origin, Destination, Number of passengers.
3.  **Template Selection**: It picks a phrase from the **Corpus** or a fallback template.
4.  **Tool Construction**: It deterministically builds the expected JSON for tool calls and responses.

### Metadata (`_meta`)
Every generated line contains a `_meta` field. This is the "DNA" of the sample.

```json
"_meta": {
    "scenario": "search_trains",
    "seed": 123456,
    "contexts": [
        {
            "params": {
                "origin": "Milano Centrale",
                "ctx_time": "14:30"
            }
        }
    ]
}
```
This metadata is used by `hydrate_dataset.py` to construct the `<ctx>` XML block in the system prompt.

---

## 🔧 Extending the System

### Adding a New Scenario
1.  Create `scenarios/my_new_scenario.py`.
2.  Inherit from `core.scenario.Scenario`.
3.  Implement `generate(self, rng, run_id)`.
4.  Use `self.corpus.get("my_category")` to access data.

### Updating the Corpus
Simply add or edit JSON files in `resources/corpus/`. The `Scenario` class automatically loads them into `self.corpus` at runtime.
