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
├── scenarios/              # Python scripts defining generation logic
│   ├── base_scenario.py    # Shared Components (Search, Purchase, Navigation, etc.)
│   ├── search_trains.py    # Simple Search Scenario
│   ├── ticket_purchase.py  # Full Search -> Purchase Flow
│   ├── multi_turn.py       # Complex Multi-turn Interaction
│   ├── greeting_to_purchase.py # Full flow: Greeting -> Search -> Purchase
│   └── ... (see Scenarios section)
├── resources/              # Static Assets & Configuration
│   ├── corpus/             # Clean, Flat-List corpus JSON files
│   ├── stations.json       # Domain data (Stations list)
│   ├── tools.json          # Tool definitions (function calling format)
│   ├── qa_pairs.json       # Q&A pairs for QA scenario
│   └── system_prompt.md    # Template for System Prompt
├── tools/                  # Helper scripts
│   ├── corpus_builder.py   # Main script to extract/build corpus from source data
│   └── validate_dataset.py # Validation tool for generated data
├── main.py                 # Generator Entry Point
├── hydrate_dataset.py      # Context Injection Script
└── visualizer.html         # Data Visualization Dashboard
```

---

## 🛠️ Usage

### 1. Generate the Pre-Dataset
The first step generates the "Pre-Dataset". This contains the conversation flow, tool calls, and metadata, but has **placeholders** for the System Prompt and dynamic context.

```bash
# Generate 100 samples per scenario
python main.py --count 100 --seed 42
```

**Output**: A folder `data/predataset/` containing JSONL files.

### 2. Hydrate the Dataset
The "Hydration" process takes the Pre-Dataset and injects the actual System Prompt, Tools, and Dynamic Context (simulated time, location, etc.).

```bash
# Hydrate the dataset -> output to data/hydrated-dataset
python hydrate_dataset.py data
```

**Output**: A folder `data/hydrated-dataset/` containing the final, ready-to-train JSONL files.

### 3. Validate the Dataset
Run the validation tool to check for structural integrity and JSON compliance.

```bash
python tools/validate_dataset.py --input data/hydrated-dataset
```

### 4. Visualize
Open `visualizer.html` in your browser. It is automatically updated with sample data after running `main.py`.

---

## 🧠 Core Concepts

### The "Corpus" (`resources/corpus/`)
The system relies on a **linguistic corpus** to provide natural variety. This is located in `resources/corpus/` and consists of simple JSON lists of strings (flat lists) categorized by intent (e.g., `search_queries.json`, `refusals.json`).

### Scenarios (`scenarios/*.py`)
A **Scenario** is a Python class that inherits from `core.scenario.Scenario`. It deterministically constructs conversations using shared **Components**.

**Available Scenarios:**
- **`search_trains`**: Standard train search conversation.
- **`ticket_purchase`**: Full flow: Search -> Select -> Purchase.
- **`long_ticket_purchase`**: Extended flow with optional Navigation and Refinement steps.
- **`ui_navigation`**: Simulates user interacting with UI pagination (Next/Prev).
- **`qa`**: Informational Q&A about train services.
- **`refusal`**: Assistant politely refusing off-topic user queries (e.g. "What is Bitcoin?").
- **`rude`**: Handling rude/urgent user messages with polite de-escalation.
- **`search_fail`**: Simulating scenarios where no trains are found.
- **`greeting_to_purchase`**: Natural flow starting from a greeting, moving to search, then purchase.
- **`multi_turn`**: Complex composition of different components (Greeting, Refusal, Search, QA).

### Metadata (`_meta`)
Every generated line contains a `_meta` field, essential for the hydration process.

```json
"_meta": {
    "scenario": "search_trains",
    "seed": 123456,
    "run_id": 1,
    "contexts": [
        {
            "slice_length": 2, // Applies to messages[0:2]
            "params": {
                "origin": "Milano Centrale",
                "ctx_time": "14:30",
                "date": "2025-12-25" // Randomized Date
            }
        }
    ]
}
```

### New Features
- **Date Randomization**: Interactions are simulated across random dates (Dec 2025 - Jan 2026).
- **Sequential Tool IDs**: Tool calls within a single conversation are numbered sequentially (`call_001`, `call_002`, `call_003`).
- **Smart Filtering**: The generator intelligently filters "Follow-up" phrases (like "Ah capito", "Allora") when starting a new conversation topic.

---

## 🔧 Extending the System

### Adding a New Scenario
1.  Create `scenarios/my_new_scenario.py`.
2.  Inherit from `core.scenario.Scenario`.
3.  Use components like `SearchComponent` or `PurchaseComponent` from `scenarios.base_scenario`.
4.  Implement `generate(self, rng, run_id)`.

### Updating the Corpus
Use `tools/corpus_builder.py` if you have raw data to ingest, or simply edit the JSON files in `resources/corpus/` manually.
