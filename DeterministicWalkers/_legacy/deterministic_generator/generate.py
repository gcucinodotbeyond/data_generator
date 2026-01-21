import os
import jinja2
import json
import itertools

# Configuration
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'generated_utterances.jsonl')

# Domain Variables
# Domain Variables
DESTINATIONS = ["Roma", "Milano", "Napoli", "Firenze", "Bologna", "Torino", "Venezia"]
TIMES = [
    {"value": "8:00", "type": "numeric"},
    {"value": "9:30", "type": "numeric"},
    {"value": "14:00", "type": "numeric"},
    {"value": "18:45", "type": "numeric"},
    {"value": "subito", "type": "relative_now"},
    {"value": "ora", "type": "relative_now"},
    {"value": "adesso", "type": "relative_now"},
    {"value": "domani mattina", "type": "relative_future"},
    {"value": "stasera", "type": "relative_future"}
]

def render_template():
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(TEMPLATE_DIR),
        trim_blocks=True,
        lstrip_blocks=True
    )
    template = env.get_template('utterances.j2')
    
    # We use a set of strings to deduplicate, but the strings are JSON representations
    unique_items = set()
    
    combinations = list(itertools.product(DESTINATIONS, TIMES))
    print(f"Generating for {len(combinations)} destination/time combinations...")
    
    for dest, time_obj in combinations:
        # Pass json.dumps as a utility to properly format objects in the template
        rendered_block = template.render(
            destination=dest, 
            time=time_obj["value"],
            time_type=time_obj["type"],
            to_json=json.dumps
        )
        
        # Split by lines and clean up
        lines = [line.strip() for line in rendered_block.split('\n') if line.strip()]
        for line in lines:
            # Each line should now be a valid JSON string from the template
            unique_items.add(line)
            
    # Convert back to dicts to verify and sort
    results = []
    for item_str in unique_items:
        try:
            results.append(json.loads(item_str))
        except json.JSONDecodeError:
            print(f"Warning: Skipping invalid JSON line: {item_str}")
            
    # Sort by text for consistency
    return sorted(results, key=lambda x: x['text'])

def main():
    print(f"Starting deterministic generation...")
    utterances = render_template()
    
    print(f"Generated {len(utterances)} unique utterances.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for item in utterances:
            # 'item' is already a dict with text and variables.
            # We add fixed metadata.
            item["intent"] = "search_trains"
            item["generator"] = "deterministic_jinja2"
            
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
