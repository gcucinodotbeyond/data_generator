import json
import urllib.request
import time

class OllamaJudgeClient:
    def __init__(self, base_url="http://localhost:11434", model="qwen3:4b-instruct"):
        self.base_url = base_url
        self.model = model

    def generate_completion(self, system_prompt, user_prompt, temperature=0.1):
        """
        Sends a request to the Ollama /api/generate endpoint.
        """
        url = f"{self.base_url}/api/generate"
        
        # Combine system and user prompt for /api/generate
        full_prompt = f"{system_prompt}\n\nUser Input:\n{user_prompt}\n\nAssistant Response (JSON):"
        
        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(data).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result.get("response", "")
        except Exception as e:
            print(f"[Judge-LLM] Request failed: {e}")
            return None
