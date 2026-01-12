import argparse
import json
import sys
from pathlib import Path

def hydrate_line(line_idx: int, line_content: str, template: str, remove_meta: bool = False) -> str:
    try:
        data = json.loads(line_content)
    except json.JSONDecodeError:
        print(f"Error decoding JSON on line {line_idx}")
        return line_content

    messages = data.get("messages", [])
    if not messages:
        return line_content

    system_message = next((m for m in messages if m["role"] == "system"), None)
    if not system_message:
        return line_content

    if system_message["content"] == "{{SYSTEM_PROMPT}}":
        # Hydrate!
        meta_params = data.get("_meta", {}).get("params", {})
        
        # Prepare dynamic context
        p = meta_params # shorthand
        
        # Defaults
        origin = p.get("origin", "UNKNOWN")
        ctx_time = p.get("ctx_time", "12:00")
        date = p.get("date", "2024-05-01")
        ui_state = p.get("ui_state", '{"state":"idle","can":{"next":false,"prev":false,"back":false}}')
        trains_array = p.get("trains_array", "[]")

        # Construct block
        # Matches format:
        # <ctx>
        # data: 2024-05-01
        # ora: 12:00
        # stazione: Roma Termini
        # </ctx>
        # 
        # <ui>
        # ...
        # </ui>
        # 
        # <trains>
        # ...
        # </trains>
        
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

        hydrated_prompt = template.replace("{{DYN_CONTEXT}}", dyn_context_str)
        system_message["content"] = hydrated_prompt
    
    # Keep _meta by default unless requested to remove
    if remove_meta:
        data.pop("_meta", None)
        
    return json.dumps(data, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="Hydrate system prompts in a dataset")
    parser.add_argument("--input", "-i", type=str, required=True, help="Input JSONL file")
    parser.add_argument("--output", "-o", type=str, required=True, help="Output JSONL file")
    parser.add_argument("--template", "-t", type=str, help="Path to system prompt template. If not provided, looks in ../resources/system_prompt.md relative to input.")
    parser.add_argument("--remove-meta", action="store_true", help="Remove the _meta field from the output dataset")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file {input_path} does not exist.")
        sys.exit(1)

    # Determine template path
    if args.template:
        template_path = Path(args.template)
    else:
        # Default: input_dir/../resources/system_prompt.md
        template_path = input_path.parent.parent / "resources" / "system_prompt.md"

    if not template_path.exists():
        print(f"Error: Template file {template_path} does not exist.")
        sys.exit(1)

    print(f"Using template: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    print(f"Hydrating {input_path} to {args.output}...")
    
    count = 0
    with open(input_path, 'r', encoding='utf-8') as fin, \
         open(args.output, 'w', encoding='utf-8') as fout:
        
        for idx, line in enumerate(fin):
            line = line.strip()
            if not line:
                continue
                
            new_line = hydrate_line(idx + 1, line, template_content, args.remove_meta)
            fout.write(new_line + '\n')
            count += 1
            
    print(f"Processed {count} lines.")

if __name__ == "__main__":
    main()
