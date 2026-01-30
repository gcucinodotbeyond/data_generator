import json
import os
from .ollama_client import OllamaJudgeClient
from .prompts import SYSTEM_PROMPT, format_user_prompt

class DatasetValidator:
    def __init__(self, model="qwen3:4b-instructed"):
        self.client = OllamaJudgeClient(model=model)

    def validate_item(self, item):
        """
        Validates a single dialogue item and returns the judge's response.
        """
        user_prompt = format_user_prompt(item)
        response = self.client.generate_completion(SYSTEM_PROMPT, user_prompt)
        
        if not response:
            return {"error": "Failed to get response from LLM"}

        return self._parse_json_response(response)

    def _parse_json_response(self, response):
        """
        Tries to extract and parse JSON from the LLM response.
        """
        clean = response.strip()
        if "```json" in clean:
            clean = clean.split("```json")[-1].split("```")[0].strip()
        elif "```" in clean:
            clean = clean.split("```")[-1].split("```")[0].strip()
        
        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            # Fallback if it's not perfect JSON
            print(f"[Validator] Warning: Could not parse JSON response: {response[:100]}...")
            return {"raw_response": response, "error": "JSON parse error"}
