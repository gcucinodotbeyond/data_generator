import json
import os
import sys

# Add parent dir to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator.mock_api import MockBackend
from generator.dialogue import DialogueGenerator

def verify_backend_logic():
    print("Verifying backend logic...")
    backend = MockBackend(seed=42)
    
    # 1. Search to populate results
    search_args = json.dumps({"origin": "Roma", "destination": "Milano"})
    backend.search_trains(search_args)
    
    # 2. Test show_info targets
    
    # Target: train
    print("Testing show_info target=train...")
    resp = json.loads(backend.ui_control(json.dumps({"action": "show_info", "target": "train", "train_position": 1})))
    assert resp["target"] == "train"
    assert "status" in resp
    print("  OK")
    
    # Target: station
    print("Testing show_info target=station...")
    resp = json.loads(backend.ui_control(json.dumps({"action": "show_info", "target": "station"})))
    assert resp["target"] == "station"
    assert "info" in resp
    print("  OK")
    
    # Target: city
    print("Testing show_info target=city...")
    resp = json.loads(backend.ui_control(json.dumps({"action": "show_info", "target": "city"})))
    assert resp["target"] == "city"
    assert "info" in resp
    print("  OK")
    
    # Target: help
    print("Testing show_info target=help...")
    resp = json.loads(backend.ui_control(json.dumps({"action": "show_info", "target": "help"})))
    assert resp["target"] == "help"
    assert "info" in resp
    print("  OK")

    print("Backend logic verified successfully.")

def verify_dialogue_generation():
    print("\nVerifying dialogue generation...")
    # This acts as a smoke test to ensure templates render without error
    generator = DialogueGenerator()
    dialogues = generator.generate_dialogues(count=50)
    
    found_show_info = False
    
    found_show_info = False
    
    for d in dialogues:
        messages = d["messages"]
        for i, msg in enumerate(messages):
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc["function"]["name"] == "ui_control":
                        args = json.loads(tc["function"]["arguments"])
                        if args.get("action") == "show_info":
                            found_show_info = True
                            print(f"Found ui_control(show_info) call: {args}")
                            
                            # Check NEXT assistant response
                            if i + 1 < len(messages):
                                next_msg = messages[i+1]
                                if next_msg["role"] == "assistant" and next_msg.get("content"):
                                    content = next_msg["content"]
                                    target = args.get("target")
                                    print(f"  Assistant Response: {content}")
                                    
                                    # Basic assertions
                                    if target == "station":
                                        assert "bagni" in content or "biglietteria" in content, "Response should mention station info"
                                    elif target == "city":
                                        assert "ufficio turistico" in content, "Response should mention city info"
                                    # Train target returns variable "status" string from backend, harder to assert exact match without checking backend logic again, 
                                    # but we know backend returns "Il treno..." or "Il treno è diretto..."
                                    elif target == "train":
                                        assert "treno" in content, "Response should mention train info"

    if found_show_info:
        print("Successfully generated dialogues with show_info calls and verified responses.")
    else:
        print("Warning: No show_info calls generated in 5 dialogues (might be random, but worth checking).")

if __name__ == "__main__":
    verify_backend_logic()
    verify_dialogue_generation()
