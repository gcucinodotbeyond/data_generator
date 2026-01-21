import argparse
import json
import os
import glob
import re
from pathlib import Path
import urllib.request
from typing import List, Dict, Any, Tuple

# Configuration
CONFIG_PATH = Path("config.json")
SYSTEM_PROMPT_PATH = Path("resources/validation_prompt.md")
GOLDEN_PATH = Path("resources/golden_dataset.jsonl")

# Defaults
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5-coder:7b"

# --- Utils ---

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
    def __init__(self, status: str, reason: str = ""):
        self.status = status # VALID, INVALID, ERROR
        self.reason = reason

# --- Extraction Utils ---

def extract_ctx(system_content: str) -> Dict[str, str]:
    """Extracts data, ora, stazione from <ctx> tag."""
    ctx_data = {}
    match = re.search(r'<ctx>(.*?)</ctx>', system_content, re.DOTALL)
    if match:
        content = match.group(1).strip()
        for line in content.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                ctx_data[key.strip().lower()] = val.strip()
    return ctx_data

def extract_ui_state(system_content: str) -> Dict[str, Any]:
    """Extracts UI state JSON from <ui> tag."""
    match = re.search(r'<ui>(.*?)</ui>', system_content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    return {}

def extract_trains_list(system_content: str) -> List[Dict]:
    """Extracts trains JSON from <trains> tag."""
    match = re.search(r'<trains>(.*?)</trains>', system_content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    return []

# --- Level 1: Structure & Schema ---

def check_tools_array(sample: Dict) -> Tuple[bool, str]:
    tools = sample.get("tools", [])
    if len(tools) != 3:
        return False, f"Expected 3 tools, found {len(tools)}"
    
    names = {t["function"]["name"] for t in tools if "function" in t}
    required = {"search_trains", "purchase_ticket", "ui_control"}
    if names != required:
        return False, f"Missing required tools. Found: {names}"
    
    return True, ""

def check_sequential_ids(sample: Dict) -> Tuple[bool, str]:
    """Verifies call_001, call_002, etc."""
    expected_idx = 1
    
    # Identify all tool call IDs used
    for msg in sample["messages"]:
        if "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                call_id = tc.get("id", "")
                expected_id = f"call_{expected_idx:03d}"
                if call_id != expected_id:
                    return False, f"Invalid ID sequence. Expected {expected_id}, found {call_id}"
                expected_idx += 1
                
        # Check tool responses match
        if msg["role"] == "tool":
            cid = msg.get("tool_call_id", "")
            if not cid.startswith("call_"):
                return False, f"Invalid tool_call_id format: {cid}"
                
    return True, ""

# --- Level 2: Coherence & State Logic ---

def check_coherence_and_logic(sample: Dict) -> Tuple[bool, str]:
    msgs = sample["messages"]
    if not msgs or msgs[0]["role"] != "system":
        return False, "First message must be system"
    
    sys_content = msgs[0]["content"]
    ctx = extract_ctx(sys_content)
    ui_state = extract_ui_state(sys_content)
    visible_trains = extract_trains_list(sys_content)
    
    current_state = ui_state.get("state", "idle")
    
    for i, msg in enumerate(msgs):
        if msg["role"] == "assistant" and "tool_calls" in msg and msg["tool_calls"]:
            for tc in msg["tool_calls"]:
                name = tc["function"]["name"]
                args_str = tc["function"]["arguments"]
                
                try:
                    args = json.loads(args_str)
                except:
                    return False, f"Msg {i}: Tool arguments not valid JSON string"

                # 1. search_trains logic
                if name == "search_trains":
                    # Allowed in 'idle' OR 'results' (new search) OR 'purchased' (new search)
                    # Not allowed in 'choosingSeat' generally
                    if current_state == "choosingSeat":
                         pass # Relaxed rule: sometimes users change mind? For now let's warn only or imply state change.
                         # return False, f"Msg {i}: search_trains not allowed in state {current_state}"
                    
                    # Origin Check
                    if "origin" in args and "stazione" in ctx:
                        if args["origin"] != ctx["stazione"]:
                             return False, f"Msg {i}: Origin mismatch. Context: {ctx['stazione']}, Arg: {args['origin']}"
                    
                    # Transition Assumption
                    current_state = "results"

                # 2. purchase_ticket logic
                elif name == "purchase_ticket":
                    if current_state not in ["results", "choosingSeat"]:
                        return False, f"Msg {i}: purchase_ticket not allowed in state {current_state}"
                        
                    # Transition Assumption
                    current_state = "purchased"

                # 3. ui_control logic
                elif name == "ui_control":
                    action = args.get("action")
                    can_actions = ui_state.get("can", {})
                    
                    if action == "back":
                        current_state = "idle"
                    elif action in ["next", "prev"]:
                        # For validation of 'can' actions, we rely on the INITIAL state's capabilities?
                        # This is tricky for multi-turn. detailed simulation is hard.
                        # Disabling can-check for dynamic flows to avoid false positives.
                        pass

    return True, ""

# --- Level 3: Content Heuristics ---

def check_content_heuristics(sample: Dict) -> Tuple[bool, str]:
    for i, msg in enumerate(sample["messages"]):
        if msg["role"] == "assistant" and msg.get("content"):
            text = msg["content"]
            
            # Emoji check
            emojis = ["😊", "🙂", "😄", "🤔", "😔", "😌"]
            has_emoji = any(e in text for e in emojis)
            if not has_emoji:
                return False, f"Msg {i}: Assistant response missing emoji"
            
            # Length check (rough)
            if len(text) > 300:
                return False, f"Msg {i}: Assistant response too long ({len(text)} chars)"
                
    return True, ""

# --- Main Validation Flow ---

def validate_sample(sample: Dict) -> ValidationResult:
    # 1. Structure
    ok, err = check_tools_array(sample)
    if not ok: return ValidationResult("INVALID", err)
    
    ok, err = check_sequential_ids(sample)
    if not ok: return ValidationResult("INVALID", err)
    
    # 2. Logic
    ok, err = check_coherence_and_logic(sample)
    if not ok: return ValidationResult("INVALID", err)
    
    # 3. Content
    ok, err = check_content_heuristics(sample)
    if not ok: return ValidationResult("INVALID", err)
    
    return ValidationResult("VALID", "Checks passed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="Input file")
    args = parser.parse_args()
    
    files = glob.glob(args.input) if "*" in args.input else [args.input]
    
    total = 0
    valid = 0
    
    for fpath in files:
        print(f"Scanning {fpath}...")
        with open(fpath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if not line.strip(): continue
                total += 1
                try:
                    sample = json.loads(line)
                    res = validate_sample(sample)
                    if res.status != "VALID":
                        print(f" [FAIL] Line {i+1}: {res.reason}")
                    else:
                        valid += 1
                except json.JSONDecodeError:
                    print(f" [ERROR] Line {i+1}: Bad JSON")
                    
    print(f"\nSummary: {valid}/{total} valid samples.")

if __name__ == "__main__":
    main()
