import json
import urllib.request
import random

class LLMEnhancer:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.llm_config = self.config.get("llm", {})
        self.base_url = self.llm_config.get("base_url", "http://localhost:11434")
        self.model = self.llm_config.get("model", "qwen3:4b-instruct") # Fallback
        self.temperature = self.llm_config.get("temperature", 0.7)
        self.paraphrase_probability = self.llm_config.get("paraphrase_probability", 0.8)

    def _load_config(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[LLM] Error loading config: {e}")
            return {}

    def generate_completion(self, prompt):
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": self.temperature
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
            print(f"[LLM] Request failed: {e}")
            return None

    def enhance_utterances(self, seed_utterances, count=20):
        """
        Takes a list of seed utterances (dicts with 'text', 'intent', and 'variables') and generates variations.
        Groups seeds by intent to ensure diversity across all categories.
        """
        if not seed_utterances:
            return []

        # Group by intent
        db_by_intent = {}
        for item in seed_utterances:
            intent = item.get("intent", "search_trains")
            if intent not in db_by_intent:
                db_by_intent[intent] = []
            db_by_intent[intent].append(item)

        all_results = []
        
        # We divide the total requested count among active intents
        # Or we can just generate a fixed small number per intent to ensure coverage
        # Let's say we want 'count' variations PER intent if possible, or split 'count' total.
        # The prompt implies "Generate N variations". Let's do a smaller batch per intent.
        
        per_intent_count = max(5, int(count / len(db_by_intent)))
        
        print(f"[LLM] Enhancing {len(db_by_intent)} intents (approx {per_intent_count} vars each)...")

        for intent, seeds in db_by_intent.items():
            # Pick a few seeds
            sampled = random.sample(seeds, min(len(seeds), 5))
            seed_texts = [s['text'] for s in sampled]
            
            # Custom instruction based on intent
            intent_desc = f"intent '{intent}'"
            if intent == "search_trains":
                intent_desc = "searching for trains in Italian"
            elif intent == "greeting":
                intent_desc = "greetings in Italian"
            elif intent == "confirmation":
                intent_desc = "confirmations and positive agreements in Italian"
            elif intent == "refusal":
                intent_desc = "refusals and negative responses in Italian"
            elif intent == "qa":
                intent_desc = "questions about policies, pets, luggage, wifi, etc."
            
            prompt = f"""
You are a creative data generator for an Italian train booking assistant.
Category: {intent_desc}
Examples:
{json.dumps(seed_texts, indent=2, ensure_ascii=False)}

Task: Generate {per_intent_count} NEW and UNIQUE Italian utterances for this category.
Rules:
1. Make them distinct from the examples (slang, different phrasing, different politeness levels).
2. Keep the intent clear.
3. Output ONLY a JSON array of strings. Do not output anything else.

Example output:
["Esempio 1", "Esempio 2", "Esempio 3"]
"""
            response = self.generate_completion(prompt)
            if response:
                generated = self._parse_response(response)
                for text in generated:
                    all_results.append({
                        "text": text,
                        "intent": intent,
                        "generator": "llm_variations",
                        "variables": {} 
                    })
        
        print(f"[LLM] Successfully generated {len(all_results)} variations across all intents.")
        return all_results

    def _parse_response(self, response):
        clean_response = response.strip()
        # Clean markdown wrappers
        if clean_response.startswith("```json"):
            clean_response = clean_response[7:]
        if clean_response.startswith("```"):
            clean_response = clean_response[3:]
        if clean_response.endswith("```"):
            clean_response = clean_response[:-3]
        clean_response = clean_response.strip()
        
        try:
            data = json.loads(clean_response)
            if isinstance(data, list):
                return [str(x) for x in data if isinstance(x, (str, int, float))]
        except json.JSONDecodeError as e:
            print(f"[LLM] JSON Decode Error: {e} for response start: {clean_response[:50]}")
        
        return []

    def paraphrase_utterance(self, text, intent, context_str=""):
        """
        Rewrites a single utterance using LLM to increase variety.
        """
        # Minimalist prompt for strict paraphrasing
        prompt = f"""
Riscrivi la seguente frase in italiano in modo naturale e colloquiale, mantenendo ESATTAMENTE lo stesso significato e tutti i dati (orari, stazioni, prezzi).
Non aggiungere commenti, non rispondere alla frase, scrivi SOLO la parafrasi.

Frase originale: "{text}"
Parafrasi:
"""
        response = self.generate_completion(prompt)
        if response:
             # Basic cleanup
             clean = response.strip().strip('"').strip("'")
             # If it returns multiple lines or verbose, try to take first non-empty
             lines = [l for l in clean.split('\n') if l.strip()]
             if lines:
                 return lines[0]
        return text
