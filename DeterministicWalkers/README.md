# DeterministicWalkers

A **Hybrid Deterministic + LLM** data generator for conversational AI.
This system combines the reliability of template-based logic with the linguistic variety of Large Language Models (LLMs).

---

## 🚀 Key Philosophy

1.  **Hybrid Approach**: Uses Python and Jinja2 templates for core logic and slot accuracy, then optionally employs an LLM to paraphrase results for natural variety.
2.  **Observable & Traceable**: Every generated sample includes `_meta` information detailing the scenario, seed, and parameters used.
3.  **Dynamic Hydration**: Conversations are generated as "skeletons" and then "hydrated" with system prompts, tool definitions, and dynamic context (time, dates).
4.  **Schema v1.7 XML**: Context is injected into the system prompt using a rich XML schema that simulates a real application's UI state and backend data.
5.  **Modular Components**: Generation logic is divided into reusable Jinja2 templates and a mock backend for consistent state transitions.

---

## 📂 Project Structure

```text
DeterministicWalkers/
├── data/                   # Output directory (generated & hydrated datasets)
│   ├── predataset/         # Raw output from the generator (includes full metadata)
│   ├── clean_predataset/   # Stripped metadata, keeps messages and logical context
│   └── hydrated-dataset/   # Final output with rendered system prompts
├── generator/              # Core generation engine
│   ├── templates/          # Jinja2 templates for different intents (search, complaint, etc.)
│   ├── scenarios/          # Text files defining sequences of intents for variations
│   ├── dialogue.py         # Main dialogue state machine & flow logic
│   ├── deterministic.py    # Template renderer and base generator
│   ├── context_formatter.py# Formats internal state into Schema v1.5 XML
│   ├── llm_enhancer.py     # LLM integration (Ollama) for paraphrasing
│   ├── hydrator.py         # Data hydration logic (system prompt injection)
│   └── mock_api.py         # Mock backend for train searches and purchases
├── judge/                  # LLM-as-a-Judge Validation
│   ├── validator.py        # Logic to evaluate generated dialogues using an LLM
│   └── run_validation.py   # Script to run the LLM evaluation suite
├── qa/                     # QA Pair Analysis & Classification
│   ├── qa_classifier.py    # Classifies QA pairs into taxonomy
│   └── taxonomy.json       # Taxonomy definitions for QA
├── resources/              # Domain data and templates
│   ├── stations.json       # List of Italian train stations
│   ├── tools.json          # Tool/Function definitions for the assistant
│   ├── qa_pairs.json       # Dataset for Q&A interruptions
│   └── system_prompt.md    # System prompt template with Jinja2 placeholders
├── stani_txt/              # Reference / Gold Standard Data
│   └── right_output.txt    # Example of correct output structure and XML format
├── tools/                  # Utility scripts
│   ├── validate_dataset.py # Structural and heuristic validation (rules-based)
│   ├── run_visualizer.py   # Local server for the data visualizer
│   └── corpus_builder.py   # Corpus extraction and management tools
├── config.json             # Global configuration (LLM settings, probabilities)
├── distribution_config.json # Probabilistic distributions (scenarios, tones)
├── main.py                 # Main entry point for generation
├── visualizer.html         # Web dashboard to inspect generated dialogues
└── TRAINING_SCHEMA.md      # Detailed schema definition for training data
```

---

## 🛠️ Usage

### 0. Installation
**Quick Start:**
```bash
pip install -r requirements.txt
```

**For Development (with testing and linting tools):**
```bash
pip install -e .[dev]
```

See [INSTALL.md](INSTALL.md) for detailed installation instructions and troubleshooting.

### 1. Configure the Generator
Edit `config.json` to set your LLM parameters (Ollama) and the paraphrase probability.
```json
{
    "llm": {
        "paraphrase_probability": 0.1,
        "model": "qwen3:4b-instruct"
    }
}
```

### 2. Generate Dialogues
Run the main script to generate and hydrate the data.
```bash
# Generate 100 dialogues using the default distributions
python main.py --dialogues 100

# Force a specific scenario (e.g., UI-heavy flow)
python main.py --dialogues 10 --scenario ui_heavy

# Skip LLM paraphrasing for fast testing
python main.py --dialogues 5 --no-llm
```
**Outputs**:
- `data/predataset/`: Raw dialogues with all metadata.
- `data/hydrated-dataset/`: Final dialogues with system prompts rendered.

### 3. Visualize
Inspect the generated quality in a user-friendly web interface.
```bash
python tools/run_visualizer.py
```
Open [http://localhost:8000/visualizer.html](http://localhost:8000/visualizer.html) in your browser.

### 4. Validate
The system provides two levels of validation:

**Structural Validation (Rules-based)**:
Checks for sequential IDs, tool definitions, and basic logic.
```bash
python tools/validate_dataset.py --input data/hydrated-dataset/dialogue_dataset.jsonl
```

**LLM-as-a-Judge (Semantic)**:
Uses a critic LLM to evaluate the coherence and "vibe" of the dialogues.
```bash
python judge/run_validation.py --file data/hydrated-dataset/dialogue_dataset.jsonl --sample 5
```

---

## 🧠 Core Features

- **Slot-First Logic**: Templates ensure that critical entities (cities, times) are always correctly placed.
- **Contextual XML Injection**: Uses `generator/context_formatter.py` to inject `<ctx>`, `<ui>`, `<query>`, and `<trains>` tags into the system prompt, providing the LLM with a structured "screen" of the current application state.
- **Natural Paraphrasing**: The LLM rewrites user utterances on-the-fly to ensure the training data isn't repetitive.
- **Dynamic Context**: Simulated date/time randomization across a 2-month window.
- **Mock Backend**: Real function-calling simulation with `search_trains` and `purchase_ticket`.
- **Interruption Simulation**: Randomly injects Q&A or UI navigation turns within the main flow.

---

## 🔧 Maintenance

### Adding New Scenarios
1. Create a `.txt` file in `generator/scenarios/`.
2. List the intent sequence (one per line). These intents must match the filenames in `generator/templates/`.
3. (Optional) Update `distribution_config.json` to include your new scenario in the random generation mix.

### Updating the XML Schema
The XML injection logic is centralized in `generator/context_formatter.py`. Refer to `stani_txt/right_output.txt` for the current gold-standard format of Schema v1.7.

---

## 📚 References

- **[TRAINING_SCHEMA.md](TRAINING_SCHEMA.md)**: Full specification of the output data schema, token formats, and XML tags used in the dataset.
- **`stani_txt/`**: Reference examples demonstrating the ideal structure of tools, system prompts, and conversation flow.

