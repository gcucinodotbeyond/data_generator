
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class DataSetHydrator:
    """
    Handles hydration of dataset files by injecting context into system prompts.
    Decoupled from specific prompt formats; uses placeholder replacement.
    """
    
    def __init__(self, template_path: Path, tools_path: Optional[Path] = None, remove_meta: bool = False):
        self.template_path = template_path
        self.tools_path = tools_path
        self.remove_meta = remove_meta
        self.template_content = self._load_template()
        self.tools_content = self._load_tools()

    def _load_template(self) -> str:
        if not self.template_path.exists():
            raise FileNotFoundError(f"Template file not found: {self.template_path}")
        with open(self.template_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_tools(self) -> Optional[Any]:
        if not self.tools_path or not self.tools_path.exists():
            return None
        try:
            with open(self.tools_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("tools") if isinstance(data, dict) and "tools" in data else data
        except json.JSONDecodeError:
            print(f"Warning: Invalid JSON in tools definition file: {self.tools_path}")
            return None

    def hydrate_line(self, line_content: str) -> str:
        """Hydrate a single JSONL line."""
        try:
            data = json.loads(line_content)
        except json.JSONDecodeError:
            return line_content # Return raw line on error to avoid data loss, but logging would be good

        # 1. Hydrate Tools
        if self.tools_content and data.get("tools") == "{{TOOL_DEFINITION}}":
            data["tools"] = self.tools_content

        # 2. Hydrate Messages (System Prompt)
        messages = data.get("messages", [])
        if messages:
            # Find system message
            system_message = next((m for m in messages if m["role"] == "system"), None)
            
            if system_message and system_message.get("content") == "{{SYSTEM_PROMPT}}":
                # Extract meta params for hydration
                meta_params = self._extract_params(data)
                
                # Perform substitution using Jinja2
                try:
                    from jinja2 import Template
                    template = Template(self.template_content)
                    
                    # Defaults
                    defaults = {
                         "origin": "UNKNOWN",
                         "ctx_time": "12:00",
                         "date": "2024-05-01",
                         "ui_state": '{"state":"idle"}',
                         "trains_array": "[]"
                    }
                    
                    # Merge defaults with actual params
                    hydration_context = defaults.copy()
                    hydration_context.update(meta_params)
                    
                    hydrated_content = template.render(**hydration_context)
                    system_message["content"] = hydrated_content
                    
                except ImportError:
                    print("Error: jinja2 not found. Please install with 'pip install jinja2'")
                    raise
                except Exception as e:
                    print(f"Error rendering template: {e}")
                    return json.dumps(data, ensure_ascii=False)

        # 3. Remove Meta if requested
        if self.remove_meta:
            data.pop("_meta", None)

        return json.dumps(data, ensure_ascii=False)

    def _extract_params(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract hydration parameters from _meta field."""
        meta = data.get("_meta", {})
        
        # New structure: meta -> contexts -> [0] -> params
        if "contexts" in meta and isinstance(meta["contexts"], list) and meta["contexts"]:
            return meta["contexts"][0].get("params", {})
        
        # Legacy/Fallback
        return meta.get("params", {})

    def process_file(self, input_path: Path, output_path: Path) -> int:
        """Process a single file and return hydrated line count."""
        count = 0
        with open(input_path, 'r', encoding='utf-8') as fin, \
             open(output_path, 'w', encoding='utf-8') as fout:
            for line in fin:
                line = line.strip()
                if not line: continue
                new_line = self.hydrate_line(line)
                fout.write(new_line + '\n')
                count += 1
        return count

    def process_directory(self, input_dir: Path, output_dir: Path) -> int:
        """Process all .jsonl files in a directory."""
        if not input_dir.exists():
            print(f"Error: Input directory {input_dir} does not exist.")
            return 0
        
        output_dir.mkdir(parents=True, exist_ok=True)
        total_files = 0
        total_lines = 0
        
        for f in input_dir.glob("*.jsonl"):
            out_f = output_dir / f.name
            print(f"  Hydrating {f.name}...")
            lines_done = self.process_file(f, out_f)
            total_files += 1
            total_lines += lines_done
            
        print(f"Hydration complete: {total_files} files, {total_lines} lines.")
        return total_lines

def main():
    parser = argparse.ArgumentParser(description="Hydrate system prompts in a dataset")
    parser.add_argument("dataset_dir", nargs='?', help="Path to the dataset directory containing 'predataset' folder")
    parser.add_argument("--template", "-t", type=str, help="Path to system prompt template.")
    parser.add_argument("--remove-meta", action="store_true", help="Remove the _meta field from the output dataset")
    
    args = parser.parse_args()
    
    if not args.dataset_dir:
        # Check if we verify a 'Legacy' single file usage or just fail
        # For this refactor, let's enforce directory structure or add legacy support if needed.
        # But for 'clean up', sticking to the standard directory structure is better.
        parser.print_help()
        sys.exit(1)

    base_dir = Path(args.dataset_dir)
    input_dir = base_dir / "predataset"
    output_dir = base_dir / "hydrated-dataset"
    
    # Defaults
    template_path = Path(args.template) if args.template else base_dir / "resources" / "system_prompt.md"
    tools_path = base_dir / "resources" / "tools.json"
    
    try:
        hydrator = DataSetHydrator(template_path, tools_path, args.remove_meta)
        hydrator.process_directory(input_dir, output_dir)
    except Exception as e:
        print(f"Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
