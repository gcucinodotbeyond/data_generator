import argparse
import json
import os
import glob
from pathlib import Path
import urllib.request
import urllib.error
from typing import List, Dict, Any, Tuple

# Configuration
CONFIG_PATH = Path("config.json")
SYSTEM_PROMPT_PATH = Path("resources/validation_prompt.md")
GOLDEN_PATH = Path("resources/golden_dataset.jsonl")

# Defaults
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:7b"

def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

config = load_config()
OLLAMA_URL = config.get("llm", {}).get("base_url", DEFAULT_OLLAMA_URL)
if not OLLAMA_URL.endswith("/api/generate"):
    OLLAMA_URL = f"{OLLAMA_URL}/api/generate"
    
MODEL = config.get("llm", {}).get("model", DEFAULT_MODEL)


class ValidationResult:
    def __init__(self, status: str, reason: str = "", fixed_data: Dict = None):
        self.status = status # VALID, INVALID, FIXED, ERROR
        self.reason = reason
        self.fixed_data = fixed_data

def load_system_prompt():
    if not SYSTEM_PROMPT_PATH.exists():
        return "You are a data validator."
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

def load_golden_examples(n=3) -> List[Dict]:
    examples = []
    if GOLDEN_PATH.exists():
        try:
            with open(GOLDEN_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        examples.append(json.loads(line))
        except Exception:
            pass
    return examples[:n]

def call_ollama(prompt: str, model: str, system: str, json_mode: bool = True) -> Dict:
    data = {
        "model": model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "format": "json" if json_mode else None,
        "options": {
            "temperature": 0.1
        }
    }
    
    try:
        req = urllib.request.Request(
            OLLAMA_URL, 
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return json.loads(result['response'])
    except Exception as e:
        print(f"Ollama Call Error: {e}")
        return {"status": "ERROR", "reason": str(e)}

# --- Level 1: Structural Checks ---

def check_structure(sample: Dict) -> Tuple[bool, str]:
    if "tools" not in sample or "messages" not in sample:
        return False, "Missing 'tools' or 'messages' keys"
    
    if not isinstance(sample["tools"], list) or len(sample["tools"]) != 3:
        return False, "Tools array must have exactly 3 items"
        
    msgs = sample["messages"]
    if not msgs or msgs[0]["role"] != "system":
        return False, "First message must be system"
        
    return True, ""

def check_tool_calls_json(sample: Dict) -> Tuple[bool, str]:
    for i, msg in enumerate(sample["messages"]):
        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                if "function" not in tc or "arguments" not in tc["function"]:
                     return False, f"Malformed tool_call in msg {i}"
                args = tc["function"]["arguments"]
                if not isinstance(args, str):
                    return False, f"Tool arguments must be string in msg {i}"
                try:
                    json.loads(args)
                except:
                    return False, f"Invalid JSON in tool arguments in msg {i}"
    return True, ""

# --- Level 2: Semantic Checks ---

def build_validation_prompt(sample: Dict, golden: List[Dict]) -> str:
    # simplify sample for prompt to save tokens
    simple_msgs = []
    ctx = ""
    for msg in sample["messages"]:
        if msg["role"] == "system":
            # Extract ctx and ui from system prompt
            content = msg["content"]
            if "<ctx>" in content:
                ctx += content[content.find("<ctx>"):content.find("</ctx>")+6]
            if "<ui>" in content:
                ctx += "\n" + content[content.find("<ui>"):content.find("</ui>")+5]
        else:
            role = msg["role"]
            content = msg.get("content")
            tcs = msg.get("tool_calls")
            
            if tcs:
                calls = [f"{tc['function']['name']}({tc['function']['arguments']})" for tc in tcs]
                simple_msgs.append(f"{role}: TOOL_CALLS: {calls}")
            elif content:
                 simple_msgs.append(f"{role}: {content}")
            else:
                 simple_msgs.append(f"{role}: [Empty]")

    conversation_text = "\n".join(simple_msgs)
    
    prompt = f"""
    CONTEXT:
    {ctx}
    
    CONVERSATION:
    {conversation_text}
    """
    return prompt

def validate_sample(sample: Dict, model: str, fix: bool) -> ValidationResult:
    # 1. Structural
    ok, err = check_structure(sample)
    if not ok: return ValidationResult("INVALID", f"Structure: {err}")
    
    ok, err = check_tool_calls_json(sample)
    if not ok: return ValidationResult("INVALID", f"JSON: {err}")
    
    # 2. Semantic
    system = load_system_prompt()
    golden = load_golden_examples()
    prompt = build_validation_prompt(sample, golden)
    
    if fix:
        prompt += "\n\nIMPORTANT: If INVALID, provide a FIXED version of the conversation in your JSON output under 'fixed_messages'."
    
    response = call_ollama(prompt, model, system)
    
    status = response.get("status", "ERROR").upper()
    reason = response.get("reason", "No reason provided")
    
    if status == "INVALID" and fix and "fixed_messages" in response:
         # Construct fixed sample
         fixed_sample = sample.copy()
         # usage of response['fixed_messages'] requires parsing it back to full message objects
         # This is complex because the LLM sees simplified text.
         # For now, let's assume the LLM returns a description of the fix or we implement a specialized fixer.
         # Re-implementing full reconstruction is hard. 
         # Let's request the LLM to just give the new turns.
         pass
         
    return ValidationResult(status, reason)

def generate_report(results: List[Tuple[str, ValidationResult]], output_dir: Path):
    html = ["<html><body><h1>Validation Report</h1><table border='1'><tr><th>File/ID</th><th>Status</th><th>Reason</th></tr>"]
    for name, res in results:
        color = "green" if res.status == "VALID" else "red"
        html.append(f"<tr><td>{name}</td><td style='color:{color}'>{res.status}</td><td>{res.reason}</td></tr>")
    html.append("</table></body></html>")
    
    with open(output_dir / "validation_report.html", "w", encoding="utf-8") as f:
        f.write("".join(html))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Input file or directory (glob patterns supported)")
    parser.add_argument("--model", "-m", default=MODEL, help=f"Ollama model to use (default: {MODEL})")
    # parser.add_argument("--fix", action="store_true", help="Attempt to fix invalid samples") # TODO: Implement fix logic in Phase 3
    args = parser.parse_args()
    
    files = glob.glob(args.input) if "*" in args.input else [args.input]
    if os.path.isdir(args.input):
        files = glob.glob(str(Path(args.input) / "*.jsonl"))
        
    results = []
    print(f"Validating {len(files)} files with model {args.model}...")
    
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip(): continue
                try:
                    sample = json.loads(line)
                    res = validate_sample(sample, args.model, fix=False)
                    print(f"[{res.status}] {Path(fpath).name} #{i}: {res.reason}")
                    results.append((f"{Path(fpath).name} #{i}", res))
                except json.JSONDecodeError:
                    print(f"[ERROR] {Path(fpath).name} #{i}: Invalid JSON Line")
                    results.append((f"{Path(fpath).name} #{i}", ValidationResult("ERROR", "Invalid JSON Line")))
    
    out_dir = Path(files[0]).parent if files else Path(".")
    generate_report(results, out_dir)
    print(f"Report generated at {out_dir / 'validation_report.html'}")

if __name__ == "__main__":
    main()
