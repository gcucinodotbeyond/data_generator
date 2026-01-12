import argparse
import json
import sys
from pathlib import Path

def hydrate_line(line_idx: int, line_content: str, template: str, remove_meta: bool = False, tools_content: list = None) -> str:
    try:
        data = json.loads(line_content)
    except json.JSONDecodeError:
        print(f"Error decoding JSON on line {line_idx}")
        return line_content

    # 1. Hydrate Tools
    if tools_content and data.get("tools") == "{{TOOL_DEFINITION}}":
        data["tools"] = tools_content

    # 2. Hydrate Messages
    messages = data.get("messages", [])
    if not messages:
        return json.dumps(data, ensure_ascii=False)

    system_message = next((m for m in messages if m["role"] == "system"), None)
    if not system_message:
         # Still return dump to keep tool hydration if any
        return json.dumps(data, ensure_ascii=False)

    if system_message["content"] == "{{SYSTEM_PROMPT}}":
        # Hydrate!
        if "contexts" in data.get("_meta", {}):
            # New structure: take the first context for the base hydration
            # (Slicing will handle the rest later, or we iterate if this script handled slicing)
            # Assuming we just hydrate the first System Prompt of the file.
            try:
                meta_params = data["_meta"]["contexts"][0]["params"]
            except (IndexError, KeyError):
                meta_params = {}
        else:
             # Legacy structure
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
    parser.add_argument("dataset_dir", nargs='?', help="Path to the dataset directory containing 'predataset' folder")
    parser.add_argument("--input", "-i", type=str, help="Input JSONL file (legacy usage)")
    parser.add_argument("--output", "-o", type=str, help="Output JSONL file (legacy usage)")
    parser.add_argument("--template", "-t", type=str, help="Path to system prompt template.")
    parser.add_argument("--remove-meta", action="store_true", help="Remove the _meta field from the output dataset")
    args = parser.parse_args()

    files_to_process = []
    
    # Mode 1: Directory Mode
    if args.dataset_dir:
        base_dir = Path(args.dataset_dir)
        input_dir = base_dir / "predataset"
        output_dir = base_dir / "hydrated-dataset"
        
        if not input_dir.exists():
            print(f"Error: input directory {input_dir} does not exist.")
            sys.exit(1)
            
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default template path relative to base_dir
        if args.template:
             template_path = Path(args.template)
        else:
             template_path = base_dir / "resources" / "system_prompt.md"
        
        # Gather all JSONL files
        for f in input_dir.glob("*.jsonl"):
            out_f = output_dir / f.name
            files_to_process.append((f, out_f))
            
    # Mode 2: Legacy Single File Mode
    elif args.input and args.output:
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: Input file {input_path} does not exist.")
            sys.exit(1)
            
        if args.template:
            template_path = Path(args.template)
        else:
            # Default relative fallback
            template_path = input_path.parent.parent / "resources" / "system_prompt.md"
            
        files_to_process.append((input_path, Path(args.output)))
    else:
        parser.print_help()
        sys.exit(1)

    # Validate Template
    if not template_path.exists():
        print(f"Error: Template file {template_path} does not exist.")
        sys.exit(1)

    print(f"Using template: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Load Tools Definition
    # Default location relative to template or input
    tools_path = template_path.parent / "tools.json"
    tools_content = None
    if tools_path.exists():
        print(f"Using tools definition: {tools_path}")
        with open(tools_path, 'r', encoding='utf-8') as f:
            tools_data = json.load(f)
            # We expect tools_data to be {"tools": [...]} or just [...]
            # The schema says top level has "tools": [...]
            # Our resources/tools.json has {"tools": [...]}
            # Ideally we want the list of tools to assign to data["tools"]? 
            # OR data["tools"] should be the list.
            # The placeholder is data["tools"] = "{{TOOL_DEFINITION}}".
            # The schema example shows "tools": [ ... ]. 
            # So we need the content of the "tools" key from tools.json, OR the whole object if the key matches.
            # Let's check resources/tools.json content I wrote. I wrote {"tools": [...]}.
            # So we extract the list.
            tools_content = tools_data.get("tools")
    else:
        print(f"Warning: Tools definition file {tools_path} not found.")

    total_files = len(files_to_process)
    print(f"Hydrating {total_files} file(s)...")

    for in_f, out_f in files_to_process:
        print(f"  {in_f.name} -> {out_f.name}")
        count = 0
        with open(in_f, 'r', encoding='utf-8') as fin, \
             open(out_f, 'w', encoding='utf-8') as fout:
            
            for idx, line in enumerate(fin):
                line = line.strip()
                if not line:
                    continue
                    
                # We need to pass tools_content to hydrate_line or handle it here.
                # Let's modify hydrate_line signature or do it inline/helper.
                # Since hydrate_line is a function above, let's just do it inside the loop or refactor hydrate_line.
                # Simpler to refactor hydrate_line to accept tools_content
                
                new_line = hydrate_line(idx + 1, line, template_content, args.remove_meta, tools_content)
                fout.write(new_line + '\n')
                count += 1
        print(f"    Processed {count} lines.")

if __name__ == "__main__":
    main()
