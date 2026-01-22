import os
import json
import argparse
import shutil
from generator.llm_enhancer import LLMEnhancer
from generator.dialogue import DialogueGenerator
from generator.hydrator import DataSetHydrator
from pathlib import Path

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
BASE_DIR = os.path.join(os.path.dirname(__file__), 'data')
PREDATASET_DIR = os.path.join(BASE_DIR, 'predataset')
HYDRATED_DIR = os.path.join(BASE_DIR, 'hydrated-dataset')
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
DIALOGUE_FILE = os.path.join(PREDATASET_DIR, 'dialogue_dataset.jsonl')

def main():
    parser = argparse.ArgumentParser(description="Deterministic + LLM Data Generator")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM paraphrasing")
    parser.add_argument("--dialogues", type=int, default=100, help="Number of full dialogues to generate")
    args = parser.parse_args()

    # Ensure output dirs exist and are clean
    for d in [PREDATASET_DIR, HYDRATED_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)
    os.makedirs(RESOURCES_DIR, exist_ok=True)

    # Copy resources (legacy compat)
    src_prompt = Path("resources/system_prompt.md")
    if src_prompt.exists():
        shutil.copy(src_prompt, Path(RESOURCES_DIR) / "system_prompt.md")
    src_tools = Path("resources/tools.json")
    if src_tools.exists():
        shutil.copy(src_tools, Path(RESOURCES_DIR) / "tools.json")

    # 1. Initialize LLM Enhancer if needed
    enhancer = None
    if not args.no_llm:
        print("[System] Initializing LLM Enhancer for real-time paraphrasing...")
        enhancer = LLMEnhancer(CONFIG_PATH)
            
    # 2. Dialogue Generation
    if args.dialogues > 0:
        print(f"[Dialogue] Generating {args.dialogues} dialogues...")
        
        # Load distribution config if exists
        dist_config = {}
        dist_path = os.path.join(os.path.dirname(__file__), 'distribution_config.json')
        if os.path.exists(dist_path):
            try:
                with open(dist_path, 'r', encoding='utf-8') as f:
                    dist_config = json.load(f)
                    print(f"[System] Loaded distribution config from {dist_path}")
            except Exception as e:
                print(f"Warning: Could not load distribution_config.json: {e}")

        dial_gen = DialogueGenerator(enhancer=enhancer, distribution=dist_config)
        dialogues = dial_gen.generate_dialogues(count=args.dialogues)
        
        print(f"Saving {len(dialogues)} raw dialogues to {DIALOGUE_FILE}...")
        with open(DIALOGUE_FILE, 'w', encoding='utf-8') as f:
            for item in dialogues:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        # 5. Hydration
    print("Hydrating dataset...")
    template_path = Path(RESOURCES_DIR) / "system_prompt.md"
    tools_path = Path(RESOURCES_DIR) / "tools.json"
    
    hydrated_data = [] # To store for visualizer
    if template_path.exists():
        hydrator = DataSetHydrator(template_path, tools_path=tools_path)
        # Hydrate everything in predataset
        hydrator.process_directory(Path(PREDATASET_DIR), Path(HYDRATED_DIR))
        print(f"Hydrated dataset available in {HYDRATED_DIR}")
        
        # Load hydrated data for visualizer
        hydrated_file = Path(HYDRATED_DIR) / "dialogue_dataset.jsonl"
        if hydrated_file.exists():
            with open(hydrated_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        hydrated_data.append(json.loads(line))
    else:
        print("Warning: System prompt template not found, skipping hydration.")



    print("Done.")

if __name__ == "__main__":
    main()
