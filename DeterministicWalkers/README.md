# DeterministicWalkers

A **Hybrid Deterministic + LLM** data generator for conversational AI.  
This system combines the reliability of template-based logic with the linguistic variety of Large Language Models (LLMs).

---

## 🚀 Key Philosophy

1.  **Hybrid Approach**: Uses Python and Jinja2 templates for core logic and slot accuracy, then optionally employs an LLM to paraphrase results for natural variety.
2.  **Observable & Traceable**: Every generated sample includes `_meta` information detailing the scenario, seed, and parameters used.
3.  **Dynamic Hydration**: Conversations are generated as "skeletons" and then "hydrated" with system prompts, tool definitions, and dynamic context (time, dates).
4.  **Modular Components**: Generation logic is divided into reusable Jinja2 templates and a mock backend for consistent state transitions.

---

## 📂 Project Structure

```text
DeterministicWalkers/
├── data/                   # Output directory (generated & hydrated datasets)
├── generator/              # Core generation engine
│   ├── templates/          # Jinja2 templates for different intents
│   ├── dialogue.py         # Main dialogue state machine & flow logic
│   ├── deterministic.py    # Template renderer and base generator
│   ├── llm_enhancer.py     # LLM integration (Ollama) for paraphrasing
│   ├── hydrator.py         # Data hydration logic (system prompt injection)
│   └── mock_api.py         # Mock backend for train searches and purchases
├── resources/              # Domain data and templates
│   ├── stations.json       # List of Italian train stations
│   ├── tools.json          # Tool/Function definitions for the assistant
│   ├── qa_pairs.json       # Dataset for Q&A interruptions
│   └── system_prompt.md    # System prompt template with placeholders
├── tools/                  # Utility scripts
│   ├── validate_dataset.py # Structural and semantic validation
│   ├── run_visualizer.py   # Local server for the data visualizer
│   └── corpus_builder.py   # Corpus extraction and management tools
├── config.json             # Global configuration (LLM settings, probabilities)
├── main.py                 # Main entry point for generation
└── visualizer.html         # Web dashboard to inspect generated dialogues
```

---

## 🛠️ Usage

### 1. Configure the Generator
Edit `config.json` to set your LLM parameters (Ollama) and the paraphrase probability.
```json
{
    "llm": {
        "paraphrase_probability": 0.1,
        "model": "qwen3:4b-instruct",
        "temperature": 0.1
    }
}
```

### 2. Generate Dialogues
Run the main script to generate the pre-dataset.
```bash
# Generate 10 dialogues with real-time LLM support
python main.py --dialogues 10
```
**Output**: `data/predataset/dialogue_dataset.jsonl`

### 3. Hydrate the Dataset
Inject the system prompt and tool definitions into the generated conversations.
```bash
# This is usually done automatically by main.py, but can be run manually
# (Requires system_prompt.md and tools.json in resources/)
```
**Output**: `data/hydrated-dataset/dialogue_dataset.jsonl`

### 4. Visualize and Validate
Use the visualizer to inspect the quality and the validation tool for structural checks.
```bash
# Start the visualizer
python tools/run_visualizer.py
# Run validation
python tools/validate_dataset.py --input data/hydrated-dataset
```

---

## 🧠 Core Features

- **Slot-First Logic**: Templates ensure that critical entities (cities, times) are always correctly placed.
- **Natural Paraphrasing**: The LLM rewrites user utterances on-the-fly to ensure the training data isn't repetitive.
- **Dynamic Context**: Simulated date/time randomization across a 2-month window.
- **Mock Backend**: Real function-calling simulation with `search_trains` and `purchase_ticket`.
- **Interruption Simulation**: Randomly injects Q&A or UI navigation turns within the main flow.

---

## 🔧 Maintenance
The system corpus and templates can be found in `generator/templates/`. These use Jinja2 syntax and can be updated to add new phrasings or intents.
