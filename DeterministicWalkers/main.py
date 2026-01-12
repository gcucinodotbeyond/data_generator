import argparse
import sys
from pathlib import Path

# Add project root to path to ensure imports work
sys.path.append(str(Path(__file__).parent))

from core.generator import Generator
from scenarios.search_trains import SearchTrains

def main():
    parser = argparse.ArgumentParser(description="Deterministic Data Generator")
    parser.add_argument("--output", "-o", type=str, default="data", help="Output directory")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Global random seed")
    parser.add_argument("--count", "-n", type=int, default=10, help="Samples per scenario")
    
    args = parser.parse_args()
    
    print(f"Starting Generator with Seed: {args.seed}")
    
    gen = Generator(output_dir=args.output, seed=args.seed)
    
    # Register Scenarios
    gen.register_scenario(SearchTrains)
    
    # Run
    gen.generate_all(count_per_scenario=args.count)
    
    print("Done!")

if __name__ == "__main__":
    main()
