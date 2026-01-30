import re

def debug():
    text = "Allora magari puoi spiegami come funziona la blockchain"
    
    fillers = [
        "allora", "magari", "puoi", "spiegami", "come" 
    ]
    # "come" is NOT in the real list. but the others are.
    
    # Real list subset
    fillers = ["allora", "magari", "puoi", "spiegami"]
    
    sorted_fillers = sorted(fillers, key=len, reverse=True)
    
    print(f"Original: '{text}'")
    
    changed = True
    while changed:
        changed = False
        
        # Clean non-alphanum start
        text_cleaned = re.sub(r"^[\W_]+", "", text).strip()
        if text_cleaned != text:
            print(f"Cleaned punct: '{text_cleaned}'")
            text = text_cleaned
            changed = True
            if not text: break
        
        text_lower = text.lower()
        
        for filler in sorted_fillers:
            pattern = r"^" + re.escape(filler) + r"(\b|[\s\.\?!,])"
            match = re.match(pattern, text_lower)
            if match:
                print(f"Matched filler: '{filler}' with pat '{pattern}'")
                remove_len = match.end()
                text = text[remove_len:].strip()
                print(f"Remaining: '{text}'")
                changed = True
                break 
    
    print(f"Final: '{text}'")

if __name__ == "__main__":
    debug()
