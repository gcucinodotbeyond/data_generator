import argparse
import sys
from pathlib import Path

# Add project root to path to ensure imports work
sys.path.append(str(Path(__file__).parent))

from core.generator import Generator
from scenarios.search_trains import SearchTrains
from scenarios.ticket_purchase import TicketPurchase
from scenarios.long_ticket_purchase import LongTicketPurchase
from scenarios.ui_navigation import UiNavigation
from scenarios.multi_turn import MultiTurn
from scenarios.qa import QA
from scenarios.refusal import Refusal
from scenarios.rude import Rude
from scenarios.search_fail import SearchFail
from scenarios.greeting_to_purchase import GreetingToPurchase
from scenarios.ten_turn_test import TenTurnTest
    
def main():
    parser = argparse.ArgumentParser(description="Deterministic Data Generator")
    parser.add_argument("--output", "-o", type=str, default="data", help="Output directory")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Global random seed")
    parser.add_argument("--count", "-n", type=int, default=10, help="Samples per scenario")
    parser.add_argument("--hydrated", action="store_true", help="Generate fully hydrated dataset (default is predataset)")
    parser.add_argument("--scenario", type=str, help="Run only a specific scenario (by name)")
    parser.add_argument("--random", action="store_true", help="Use random seed (time-based) instead of fixed seed")
    parser.add_argument("--paraphrase", action="store_true", help="Use LLM to paraphrase user messages (requires Ollama/OpenAI)")
    
    args = parser.parse_args()

    seed = args.seed
    if args.random:
        import time
        seed = int(time.time() * 1000)
        print(f"Random mode enabled. Using seed: {seed}")
    
    print(f"Starting Generator with Seed: {seed}")
    
    # Initialize Paraphraser if requested
    paraphraser = None
    if args.paraphrase:
        from core.paraphraser import Paraphraser
        print("Initializing Paraphraser (checking connection)...")
        paraphraser = Paraphraser(use_ollama=True) # Default to Ollama for now
        if paraphraser.disabled:
            print("Warning: Paraphraser init failed or no connection. Paraphrasing will be skipped.")
    
    # Create the base output directory structure
    base_output_dir = Path(args.output)
    predataset_dir = base_output_dir / "predataset"
    hydrated_dir = base_output_dir / "hydrated-dataset"
    resources_dir = base_output_dir / "resources"
    
    for d in [predataset_dir, hydrated_dir, resources_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    # Copy system prompt to resources
    import shutil
    src_prompt = Path("resources/system_prompt.md")
    if src_prompt.exists():
        shutil.copy(src_prompt, resources_dir / "system_prompt.md")
    else:
        print("Warning: resources/system_prompt.md not found. Skipping copy.")

    src_tools = Path("resources/tools.json")
    if src_tools.exists():
        shutil.copy(src_tools, resources_dir / "tools.json")
    else:
        print("Warning: resources/tools.json not found. Skipping copy.")

    # Generator outputs to predataset folder by default now
    # If hydrated flag is passed, we might still output to predataset first then hydrate? 
    # Or for now just let generator write to predataset folder. 
    # The requirement says:
    # dataset
    # |--- predataset/
    # |--- hydrated-dataset/
    # |--- resources
    
    # Generator output should always be predataset (templates etc)
    # The hydration step (if requested) will take this and produce the hydrated dataset
    gen = Generator(output_dir=str(predataset_dir), seed=seed, predataset=True, paraphraser=paraphraser)
    
    # Register Scenarios
    gen.register_scenario(SearchTrains)
    gen.register_scenario(TicketPurchase)
    gen.register_scenario(LongTicketPurchase)
    gen.register_scenario(UiNavigation)
    gen.register_scenario(MultiTurn)
    gen.register_scenario(QA)
    gen.register_scenario(Refusal)
    gen.register_scenario(Rude)
    gen.register_scenario(SearchFail)
    gen.register_scenario(GreetingToPurchase)  # NEW: Demonstration scenario
    gen.register_scenario(TenTurnTest)
    
    # Run
    if args.scenario:
        gen.generate_scenario(args.scenario, count=args.count)
    else:
        gen.generate_all(count_per_scenario=args.count)
        
    print("Predataset generation complete.")

    if args.hydrated:
        print("Starting Hydration Process...")
        # Use direct import for hydration (Refactor Phase 1)
        try:
            from hydrate_dataset import DataSetHydrator
            
            # Setup paths
            base_output_dir = Path(base_output_dir)
            template_path = base_output_dir / "resources" / "system_prompt.md"
            tools_path = base_output_dir / "resources" / "tools.json"
            input_dir = base_output_dir / "predataset"
            output_dir = base_output_dir / "hydrated-dataset"
            
            print(f"Initializing Hydrator with template: {template_path}")
            hydrator = DataSetHydrator(template_path, tools_path=tools_path)
            hydrator.process_directory(input_dir, output_dir)
            
        except ImportError as e:
            print(f"Error importing hydrate_dataset: {e}")
        except Exception as e:
            print(f"Error during hydration: {e}")

    # Always update the visualizer with the latest data
    print("Updating visualizer data...")
    generate_visualizer_data(base_output_dir, hydrated=args.hydrated)

    print("Done!")


def generate_visualizer_data(base_output_dir, hydrated=False):
    """Generate visualizer_data.js for the visualizer."""
    import json
    import glob
    
    base_output_dir = Path(base_output_dir)
    
    # Choose source: hydrated if available and requested, otherwise predataset
    if hydrated:
        data_source = base_output_dir / "hydrated-dataset"
    else:
        data_source = base_output_dir / "predataset"
    
    js_output_path = Path(__file__).parent / "visualizer_data.js"
        
    if not data_source.exists():
        print(f"  Warning: Data source {data_source} not found")
        return
    
    # Load all JSONL files
    data = {}
    files = glob.glob(str(data_source / "*.jsonl"))
    
    for file_path in files:
        filename = Path(file_path).name
        conversations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        conversations.append(json.loads(line))
            data[filename] = conversations
        except Exception as e:
            print(f"  Error loading {filename}: {e}")
    
    if not data:
        print("  No data files found to process.")
        return
    
    # Write JS file
    data_js = f"window.PRELOADED_DATA = {json.dumps(data, ensure_ascii=False)};"
    
    with open(js_output_path, 'w', encoding='utf-8') as f:
        f.write(data_js)
    
    print(f"  Generated {js_output_path.name} with {len(data)} files.")

if __name__ == "__main__":
    main()
