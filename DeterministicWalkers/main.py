import argparse
import sys
from pathlib import Path

# Add project root to path to ensure imports work
sys.path.append(str(Path(__file__).parent))

from core.generator import Generator
from scenarios.search_trains import SearchTrains
from scenarios.ticket_purchase import TicketPurchase
from scenarios.long_ticket_purchase import LongTicketPurchase

def main():
    parser = argparse.ArgumentParser(description="Deterministic Data Generator")
    parser.add_argument("--output", "-o", type=str, default="data", help="Output directory")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Global random seed")
    parser.add_argument("--count", "-n", type=int, default=10, help="Samples per scenario")
    parser.add_argument("--hydrated", action="store_true", help="Generate fully hydrated dataset (default is predataset)")
    
    args = parser.parse_args()
    
    print(f"Starting Generator with Seed: {args.seed}")
    
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
    
    # So we pass predataset_dir as the output_dir to the Generator
    gen = Generator(output_dir=str(predataset_dir), seed=args.seed, predataset=not args.hydrated)
    
    # Register Scenarios
    gen.register_scenario(SearchTrains)
    gen.register_scenario(TicketPurchase)
    gen.register_scenario(LongTicketPurchase)
    
    # Run
    gen.generate_all(count_per_scenario=args.count)
    
    print("Done!")

if __name__ == "__main__":
    main()
