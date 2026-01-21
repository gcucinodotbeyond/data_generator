import os
import time
import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class Paraphraser:
    """
    Synchronous paraphraser using Ollama or OpenAI.
    Designed to be lightweight and robust for the generator.
    """
    
    def __init__(self, use_ollama: bool = True, model: str = "qwen2.5-coder"):
        self.use_ollama = use_ollama
        self.model = model
        self.ollama_url = "http://localhost:11434/api/generate"
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        
        if not use_ollama and not self.openai_key:
            logger.warning("OpenAI requested but no API key found. Paraphrasing disabled.")
            self.disabled = True
        else:
            self.disabled = False
            
    def paraphrase(self, text: str) -> str:
        """
        Rephrase the given text while maintaining the original intent and entity values.
        """
        if self.disabled:
            return text
            
        system_prompt = (
            "You are a paraphrasing assistant. Rewrite the user's message in Italian. "
            "Keep the exact same intent, entities (cities, times), and tone. "
            "Output ONLY the rewritten text, nothing else. "
            "Do not add quotes or prefixes."
        )
        
        prompt = f"Original: {text}\nReworded:"
        
        try:
            if self.use_ollama:
                return self._call_ollama(system_prompt, prompt)
            else:
                return self._call_openai(system_prompt, prompt)
        except Exception as e:
            logger.error(f"Paraphrasing failed: {e}")
            return text

    def _call_ollama(self, system: str, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": f"{system}\n{prompt}",
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
        
        try:
            resp = requests.post(self.ollama_url, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "").strip()
        except requests.exceptions.ConnectionError:
            logger.warning("Ollama connection failed. Is it running?")
            self.disabled = True # Disable to prevent further timeouts
            
        return ""

    def _call_openai(self, system: str, prompt: str) -> str:
        # Simple sync request to avoid huge dependency
        # Not implementing full OpenAI client here to keep it simple
        return "" # Placeholder - focus on Ollama first as it's free/local
