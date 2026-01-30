import json
import argparse
import sys
import os

# Add parent directory to path to allow absolute imports if running as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from judge.validator import DatasetValidator

def main():
    parser = argparse.ArgumentParser(description="LLM-as-a-Judge Dataset Validator")
    parser.add_argument("--file", type=str, required=True, help="Path to the .jsonl dataset file")
    parser.add_argument("--sample", type=int, default=5, help="Number of items to sample")
    parser.add_argument("--model", type=str, default="qwen3:4b-instruct", help="Ollama model name")
    parser.add_argument("--output", type=str, help="Path to save the validation results")
    
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: File {args.file} not found.")
        return

    validator = DatasetValidator(model=args.model)
    results = []

    print(f"[*] Starting validation on {args.file} (Sample size: {args.sample})...")
    
    count = 0
    with open(args.file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                item = json.loads(line)
                print(f"[*] Judging dialogue {count + 1}/{args.sample}...")
                
                judge_result = validator.validate_item(item)
                
                results.append({
                    "dialogue_index": count,
                    "judge_result": judge_result
                })
                
                # Print summary to console
                score = judge_result.get("overall_score", "N/A")
                verdict = judge_result.get("verdict", "UNKNOWN")
                print(f"    - Score: {score} | Verdict: {verdict}")
                
            except Exception as e:
                print(f"    - Error processing item {count}: {e}")
            
            count += 1
            if count >= args.sample:
                break

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[*] Results saved to {args.output}")

    # Final Summary
    passed = len([r for r in results if r["judge_result"].get("verdict") == "PASS"])
    print(f"\n--- Validation Summary ---")
    print(f"Total evaluated: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(results) - passed}")

if __name__ == "__main__":
    main()
