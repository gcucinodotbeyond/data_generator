import sys
import os
import json
import random

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from generator.dialogue import DialogueGenerator

def verify():
    print("Initializing DialogueGenerator...")
    generator = DialogueGenerator()
    
    print("Generating 100 dialogues to catch disability cases...")
    dialogues = generator.generate_dialogues(count=100)
    
    disability_count = 0
    valid_tool_calls = 0
    
    print("\n--- Inspecting Dialogues ---")
    for i, d in enumerate(dialogues):
        # Check context for disability
        # We need to peek into the internal state if possible, but here we inspect the output messages
        
        has_disability_msg = False
        has_tool_param = False
        disability_type = None
        
        for msg in d["messages"]:
            if msg["role"] == "user":
                content = msg.get("content", "").lower()
                # Check ALL user messages for disability phrases
                if any(phrase in content for phrase in ["cieco", "sordo", "sedia a rotelle", "disabilità", "autistico", "non ci sento", "problemi di vista", "problemi di udito", "difficoltà a camminare", "stampelle", "guida", "assistenza"]):
                    has_disability_msg = True
            
            if msg["role"] == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    if tc["function"]["name"] == "search_trains":
                        args = json.loads(tc["function"]["arguments"])
                        if args.get("disability_type"):
                            has_tool_param = True
                            disability_type = args["disability_type"]
                            #print(f"[{i}] Tool Call: disability_type={disability_type}")

        meta_disabled = d.get("_meta", {}).get("user_profile", {}).get("disabilities")

        if has_disability_msg and has_tool_param:
            if meta_disabled == disability_type:
                disability_count += 1
                valid_tool_calls += 1
                print(f"[{i}] SUCCESS: Found disability conversation. Type: {disability_type}. Meta verified.")
            else:
                print(f"[{i}] FAILURE: Meta mismatch! Tool says {disability_type} but Meta says {meta_disabled}")
        elif has_disability_msg and not has_tool_param:
             print(f"[{i}] FAILURE: User mentioned disability but tool param missing!")
        elif has_tool_param and not has_disability_msg:
             print(f"[{i}] WEIRD: Tool param present but no user mention found (maybe obscure phrase?)")

    with open("verification_results.txt", "w") as f:
        f.write(f"Total dialogues with disability correctly handled: {disability_count}\n")
        if disability_count > 0:
            f.write("VERIFICATION SUCCESSFUL\n")
        else:
            f.write("VERIFICATION FAILED (No disability cases generated or handled)\n")
    
    print(f"\nTotal dialogues with disability correctly handled: {disability_count}")
    
    if disability_count > 0:
        print("VERIFICATION SUCCESSFUL")
    else:
        print("VERIFICATION FAILED (No disability cases generated or handled)")

if __name__ == "__main__":
    verify()
