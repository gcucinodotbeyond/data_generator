
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, Any, Optional

class LLMClient:
    """Client for interacting with LLM (Ollama)."""
    
    DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
    DEFAULT_MODEL = "qwen2.5-coder:7b"
    
    def __init__(self, config_path: str = "config.json"):
        self.config = self._load_config(config_path)
        self.base_url = self.config.get("llm", {}).get("base_url", self.DEFAULT_OLLAMA_URL)
        if not self.base_url.endswith("/api/generate"):
            self.base_url = f"{self.base_url}/api/generate"
        self.model = self.config.get("llm", {}).get("model", self.DEFAULT_MODEL)

    def _load_config(self, path_str: str) -> Dict[str, Any]:
        path = Path(path_str)
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def call(self, prompt: str, system: str, json_mode: bool = True) -> Dict:
        """Make a call to Ollama."""
        data = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "format": "json" if json_mode else None,
            "options": {
                "temperature": 0.7 # Higher temperature for creative rewriting
            }
        }
        
        try:
            req = urllib.request.Request(
                self.base_url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return json.loads(result['response'])
        except Exception as e:
            print(f"LLM Call Error: {e}")
            return {"error": str(e)}

    def rewrite_text(self, text: str, target_attributes: Dict[str, str]) -> str:
        """
        Rewrite text to match target attributes.
        """
        system = "You are a linguistic style transfer assistant. Rewrite the user's text to match the requested style attributes. Output JSON."
        
        attributes_desc = ", ".join([f"{k}: {v}" for k, v in target_attributes.items()])
        
        prompt = f"""
        ORIGINAL TEXT: "{text}"
        
        TARGET STYLE: {attributes_desc}
        
        Rewrite the text to match the target style. Preserve the original meaning and intent (e.g. if it's a search for Rome, keep it a search for Rome).
        
        Return ONLY a JSON object with this format:
        {{
            "rewritten_text": "..."
        }}
        """
        
        result = self.call(prompt, system, json_mode=True)
        return result.get("rewritten_text", text)
