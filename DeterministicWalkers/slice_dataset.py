import argparse
import json
import sys
from pathlib import Path

# Reuse hydrate_dataset logic for template replacement
def hydrate_content(template: str, params: dict) -> str:
    # Defaults
    origin = params.get("origin", "UNKNOWN")
    ctx_time = params.get("ctx_time", "12:00")
    date = params.get("date", "2024-05-01")
    ui_state = params.get("ui_state", '{"state":"idle","can":{"next":false,"prev":false,"back":false}}')
    trains_array = params.get("trains_array", "[]")

    dyn_context_str = (
        f"<ctx>\n"
        f"data: {date}\n"
        f"ora: {ctx_time}\n"
        f"stazione: {origin}\n"
        f"</ctx>\n\n"
        f"<ui>\n"
        f"{ui_state}\n"
        f"</ui>\n\n"
        f"<trains>\n"
        f"{trains_array}\n"
        f"</trains>"
    )

    return template.replace("{{DYN_CONTEXT}}", dyn_context_str)

def process_file(input_file: Path, output_file: Path, template_content: str, tools_content: list = None):
    print(f"Processing {input_file.name} -> {output_file.name}")
    count_in = 0
    count_out = 0
    
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        
        for line in fin:
            line = line.strip()
            if not line:
                continue
            count_in += 1
            
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line in {input_file.name}")
                continue

            # 1. Hydrate Tools
            if tools_content and data.get("tools") == "{{TOOL_DEFINITION}}":
                data["tools"] = tools_content

            messages = data.get("messages", [])
            meta = data.get("_meta", {})
            contexts = meta.get("contexts", [])
            
            # If no contexts array, treat as single sample (legacy/standard behavior)
            if not contexts:
                # Fallback: create one context from base params if present
                base_params = meta.get("params")
                if base_params:
                    contexts = [{"slice_length": len(messages), "params": base_params}]
                else:
                    # No params? Write as is (with tools hydrated if present)
                    fout.write(json.dumps(data, ensure_ascii=False) + "\n")
                    count_out += 1
                    continue
            
            # Process each slice
            for ctx_def in contexts:
                # slice_length: Number of messages to keep from the start (0 to N).
                # Example: 2 means keep keys 0 and 1 (System + User).
                slice_len = ctx_def.get("slice_length")
                params = ctx_def.get("params")
                
                if slice_len is None or slice_len > len(messages):
                    continue
                
                # Slice messages
                sliced_msgs = [m.copy() for m in messages[:slice_len]]
                
                # Find System Prompt
                sys_msg = next((m for m in sliced_msgs if m["role"] == "system"), None)
                if sys_msg and sys_msg["content"] == "{{SYSTEM_PROMPT}}":
                    sys_msg["content"] = hydrate_content(template_content, params)
                
                # Construct new sample
                new_sample = {
                    "tools": data.get("tools"), # Pass through hydrated tools
                    "messages": sliced_msgs,
                    # Optional: preserve some meta, maybe track origin id
                    "_meta": {
                        "original_run_id": meta.get("run_id"),
                        "slice_length": slice_len
                    }
                }
                
                fout.write(json.dumps(new_sample, ensure_ascii=False) + "\n")
                count_out += 1
                
    print(f"  Read {count_in} samples, Wrote {count_out} slices.")

def main():
    parser = argparse.ArgumentParser(description="Slice and hydrate long conversations")
    parser.add_argument("dataset_dir", help="Path to the dataset directory containing 'predataset' folder")
    parser.add_argument("--template", "-t", type=str, help="Path to system prompt template.")
    args = parser.parse_args()

    base_dir = Path(args.dataset_dir)
    input_dir = base_dir / "predataset"
    output_dir = base_dir / "hydrated-dataset" # Slicing implies hydration here
    
    if not input_dir.exists():
        print(f"Error: input directory {input_dir} does not exist.")
        sys.exit(1)
        
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Template
    if args.template:
            template_path = Path(args.template)
    else:
            template_path = base_dir / "resources" / "system_prompt.md"
            
    if not template_path.exists():
        print(f"Error: Template file {template_path} not found.")
        sys.exit(1)
        
    print(f"Using template: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Load Tools Definition
    tools_path = template_path.parent / "tools.json"
    tools_content = None
    if tools_path.exists():
        print(f"Using tools definition: {tools_path}")
        with open(tools_path, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
            tools_content = tools_data.get("tools")
    else:
        print(f"Warning: Tools definition file {tools_path} not found.")

    for f in input_dir.glob("*.jsonl"):
        out_f = output_dir / f.name
        process_file(f, out_f, template_content, tools_content)

if __name__ == "__main__":
    main()
