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
├── judge/                  # Validation & LLM Evaluation
│   ├── validator.py        # Logic to validate generated dialogues
│   └── run_validation.py   # Script to run validation suite
├── qa/                     # QA Pair Analysis & Classification
│   ├── qa_classifier.py    # Classifies QA pairs into taxonomy
│   └── taxonomy.json       # Taxonomy definitions for QA
├── resources/              # Domain data and templates
│   ├── stations.json       # List of Italian train stations
│   ├── tools.json          # Tool/Function definitions for the assistant
│   ├── qa_pairs.json       # Dataset for Q&A interruptions
│   └── system_prompt.md    # System prompt template with placeholders
├── stani_txt/              # Reference / Gold Standard Data
│   └── right_output.txt    # Example of correct output structure and format
├── tools/                  # Utility scripts
│   ├── validate_dataset.py # Structural and semantic validation
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

### 2. Configure Distributions (Optional)
Edit `distribution_config.json` to fine-tune the mix of scenarios and user behaviors.
```json
{
    "rudeness_distribution": { "polite": 0.2, "neutral": 0.3, "rude": 0.5 },
    "scenario_distribution": { "default": 0.2, "lost_user": 0.1, ... }
}
```

### 3. Generate Dialogues
Run the main script to generate the pre-dataset.
```bash
# Generate 10 dialogues with real-time LLM support
python main.py --dialogues 10
```
**Output**: `data/predataset/dialogue_dataset.jsonl`

### 4. Hydrate the Dataset
Inject the system prompt and tool definitions into the generated conversations.
*(This is usually done automatically by main.py)*
**Output**: `data/hydrated-dataset/dialogue_dataset.jsonl`

### 5. Visualize and Validate
Use the visualizer to inspect the quality and the validation tool for structural checks.
```bash
# Start the visualizer
python tools/run_visualizer.py
```
Open [http://localhost:8000/visualizer.html](http://localhost:8000/visualizer.html) in your browser.

```bash
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

## 📚 References

- **[TRAINING_SCHEMA.md](TRAINING_SCHEMA.md)**: Full specification of the output data schema, token formats, and XML tags used in the dataset.
- **`stani_txt/`**: Contains reference examples (e.g., `right_output.txt`) demonstrating the ideal structure of tools, system prompts, and conversation flow, useful as a "gold standard" for development.

---

## 🔧 Maintenance
The system corpus and templates can be found in `generator/templates/`. These use Jinja2 syntax and can be updated to add new phrasings or intents.
