import json
import os
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
        """Hydrate a single JSONL line (1:1 mapping)."""
        try:
            data = json.loads(line_content)
        except json.JSONDecodeError:
            return line_content

        # 1. Hydrate Tools
        if self.tools_content and data.get("tools") == "{{TOOL_DEFINITION}}":
            data["tools"] = self.tools_content

        # 2. Hydrate Messages (System Prompt)
        messages = data.get("messages", [])
        if messages:
            system_message = next((m for m in messages if m["role"] == "system"), None)
            
            # Allow both placeholder and initial Talìa prompt for re-hydration if needed
            if system_message and (system_message.get("content") == "{SYSTEM_PROMPT}" or "{SYSTEM_PROMPT}" in system_message.get("content", "")):
                # Extract meta params
                # For 1:1, we use the first context (start state) as it's the most common for starting-point system prompts
                meta = data.get("_meta", {})
                params = {}
                if "contexts" in meta and isinstance(meta["contexts"], list) and meta["contexts"]:
                    params = meta["contexts"][0].get("params", {})
                else:
                    params = meta.get("params", {})
                
                prepared_params = self._prepare_params(params)
                
                try:
                    from jinja2 import Template
                    template = Template(self.template_content)
                    
                    defaults = {
                         "origin": "UNKNOWN",
                         "ctx_time": "12:00",
                         "date": "2024-05-01",
                         "ui_state": '{"state":"idle"}',
                         "trains_array": "[]",
                         "ticket_info": None
                    }
                    
                    hydration_context = defaults.copy()
                    hydration_context.update(prepared_params)
                    
                    # Ensure ui_state_raw is there
                    if "ui_state_raw" not in hydration_context:
                        hydration_context["ui_state_raw"] = json.loads(hydration_context["ui_state"])
                    
                    hydrated_content = template.render(**hydration_context)
                    system_message["content"] = hydrated_content
                    
                except Exception as e:
                    print(f"Error rendering template: {e}")

        # 3. Remove Meta if requested
        if self.remove_meta:
            data.pop("_meta", None)

        return json.dumps(data, ensure_ascii=False)

    def _prepare_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare raw parameters for Jinja2."""
        p = params.copy()
        
        # ui_state -> ui_state_raw
        if "ui_state" in p and isinstance(p["ui_state"], str):
            try:
                p["ui_state_raw"] = json.loads(p["ui_state"])
            except:
                p["ui_state_raw"] = {"state": "unknown"}
        elif "ui_state" in p and isinstance(p["ui_state"], dict):
            p["ui_state_raw"] = p["ui_state"]
            p["ui_state"] = json.dumps(p["ui_state"])
        else:
            p["ui_state_raw"] = {"state": "unknown"}

        # ticket_info
        if "ticket_info" in p and isinstance(p["ticket_info"], str):
             try:
                 p["ticket_info"] = json.loads(p["ticket_info"])
             except:
                 pass
                 
        return p

    def process_file(self, input_path: Path, output_path: Path) -> int:
        """Process a single file."""
        count = 0
        with open(input_path, 'r', encoding='utf-8') as fin, \
             open(output_path, 'w', encoding='utf-8') as fout:
            for line in fin:
                line = line.strip()
                if not line: continue
                new_line = self.hydrate_line(line)
                fout.write(new_line + "\n")
                count += 1
        return count

    def process_directory(self, input_dir: Path, output_dir: Path) -> int:
        """Process all .jsonl files in a directory."""
        if not input_dir.exists():
            return 0
        
        output_dir.mkdir(parents=True, exist_ok=True)
        total_lines = 0
        for f in input_dir.glob("*.jsonl"):
            out_f = output_dir / f.name
            print(f"  Hydrating {f.name}...")
            total_lines += self.process_file(f, out_f)
        return total_lines
