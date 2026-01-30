import json
import os
import sys
import time
import argparse
import signal
from typing import List, Dict, Optional

# Add the parent directory to sys.path to import from judge
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from judge.ollama_client import OllamaJudgeClient

class QAClassifierLLM:
    def __init__(self, 
                 taxonomy_path: str = "qa/taxonomy.json",
                 input_path: str = "qa/qa_pairs.json",
                 output_path: str = "qa/qa_classified_llm.json",
                 model_name: str = "qwen3:4b-instruct"):
        self.taxonomy_path = taxonomy_path
        self.input_path = input_path
        self.output_path = output_path
        self.client = OllamaJudgeClient(model=model_name)
        
        with open(self.taxonomy_path, 'r', encoding='utf-8') as f:
            self.taxonomy = json.load(f)
            
        self.categories = list(self.taxonomy.keys())
        self.flattened_taxonomy = []
        for macro, subs in self.taxonomy.items():
            for sub in subs.keys():
                self.flattened_taxonomy.append(f"{macro} > {sub}")

    def get_system_prompt(self):
        taxonomy_str = "\n".join([f"- {item}" for item in self.flattened_taxonomy])
        return f"""Sei un esperto classificatore di domande/risposte nel settore ferroviario (Trenitalia).
Il tuo obiettivo è analizzare una coppia QA e fornire metadati strutturati per migliorare la coerenza del dataset.

Tassonomia disponibile (Macro > Sottocategoria):
{taxonomy_str}

Per ogni QA, devi restituire un oggetto JSON con:
1. "labels": lista di oggetti. Ogni oggetto deve avere:
   - "primary_category": la macro-categoria (es. "Biglietteria e Tariffe").
   - "subcategory": la sottocategoria specifica (es. "Acquisto e Pagamenti").
2. "entities": lista di nomi propri o entità chiave menzionate (nomi di stazioni come "Roma Termini", tipi di treno come "Frecciarossa", servizi come "CartaFRECCIA").
3. "contextual_tags": lista di tag tecnici per identificare cosa serve per rendere la domanda coerente in un dialogo. 
   Esempi: "requires_station", "requires_train_type", "requires_loyalty_card", "general_info", "location_specific".

RESTITUISCI SOLO IL JSON, senza testo aggiuntivo.
"""

    def classify_single(self, question: str, answer: str) -> Optional[Dict]:
        user_prompt = f"Question: {question}\nAnswer: {answer}"
        response_text = self.client.generate_completion(self.get_system_prompt(), user_prompt)
        
        if not response_text:
            return None
            
        try:
            # Clean up response in case of markdown blocks
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"):
                clean_text = clean_text[3:-3].strip()
                
            return json.loads(clean_text)
        except Exception as e:
            print(f"Error parsing JSON for question '{question[:50]}...': {e}")
            print(f"Raw response: {response_text}")
            return None

    def run(self, max_new_items: Optional[int] = None, batch_size: int = 5):
        if not os.path.exists(self.input_path):
            print(f"Input file {self.input_path} not found.")
            return

        with open(self.input_path, 'r', encoding='utf-8') as f:
            qa_pairs = json.load(f)

        # Load existing results
        results = []
        if os.path.exists(self.output_path):
            try:
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                print(f"Resuming from {len(results)} existing records.")
            except Exception as e:
                print(f"Failed to load existing output ({e}), starting fresh.")

        processed_questions = {r["question"] for r in results}
        
        count = 0
        total_in_file = len(qa_pairs)
        
        try:
            for i, (q, a) in enumerate(qa_pairs):
                if q in processed_questions:
                    continue
                
                if max_new_items is not None and count >= max_new_items:
                    print(f"Reached limit of {max_new_items} new items for this run.")
                    break
                    
                print(f"[{i+1}/{total_in_file}] Classifying: {q[:60]}...")
                metadata = self.classify_single(q, a)
                
                if metadata:
                    results.append({
                        "question": q,
                        "answer": a,
                        "metadata": metadata
                    })
                    count += 1
                
                # Save periodically or at the end
                if count > 0 and (count % batch_size == 0 or i == total_in_file - 1):
                    self._save_results(results)
                    print(f"> Progress saved: {len(results)} total records.")

        except KeyboardInterrupt:
            print("\nInterrupted by user. Saving progress...")
        finally:
            self._save_results(results)

    def _save_results(self, results):
        if not results:
            return
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify QA pairs using LLM.")
    parser.add_argument("--limit", type=int, help="Limit the number of NEW items to process in this run.")
    parser.add_argument("--batch", type=int, default=1, help="How many items to process before saving.")
    
    args = parser.parse_args()
    
    classifier = QAClassifierLLM()
    classifier.run(max_new_items=args.limit, batch_size=args.batch)
