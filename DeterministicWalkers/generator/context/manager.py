import random
import json
import os
from datetime import datetime, timedelta
from generator.context_formatter import ContextFormatter

class ContextManager:
    def __init__(self, distribution=None):
        self.distribution = distribution or {}
        
        # Load stations
        stations_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'stations.json')
        try:
            with open(stations_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.major_stations = data.get("major", [])
                # Flatten all stations for destinations
                all_stations = []
                for key in data:
                    if isinstance(data[key], list):
                        all_stations.extend(data[key])
                self.origins = self.major_stations
                self.destinations = list(set(all_stations)) # unique
        except Exception as e:
            print(f"Warning: Could not load stations.json ({e}), using defaults.")
            self.origins = ["Milano Centrale", "Roma Termini", "Napoli Centrale"]
            self.destinations = ["Roma", "Milano", "Napoli", "Firenze"]

        self.dates = ["oggi", "per oggi", "per domani", "domani", "sabato", "domenica prossima", "il 15 del mese", "per venerdì"]
        self.times = ["mattina", "pomeriggio", "sera", "10:00", "15:30", "subito"]
        
        # Load QA Pairs (Strictly use classified LLM version)
        qa_path = os.path.join(os.path.dirname(__file__), '..', '..', 'qa', 'qa_classified_llm.json')
        self.qa_pairs = []
        try:
            if os.path.exists(qa_path):
                with open(qa_path, 'r', encoding='utf-8') as f:
                    self.qa_pairs = json.load(f)
                print(f"[ContextManager] Loaded {len(self.qa_pairs)} classified QA pairs from {os.path.basename(qa_path)}")
            else:
                print(f"Warning: Classified QA file not found at {qa_path}")
        except Exception as e:
            print(f"Warning: Could not load QA pairs ({e}).")

    def init_context(self, run_id):
        """Randomly initializes the global context variables for this dialogue."""
        origin = random.choice(self.origins)
        dest = random.choice([d for d in self.destinations if d[:3] != origin[:3]]) # Avoid same city
        
        # Rudeness selection
        rudeness_dist = self.distribution.get("rudeness_distribution", {})
        if rudeness_dist:
            population = list(rudeness_dist.keys())
            weights = list(rudeness_dist.values())
            rudeness = random.choices(population, weights=weights, k=1)[0]
        else:
            rudeness = random.choice(["polite", "rude", "neutral"])

        # Verbose selection
        verbose_dist = self.distribution.get("verbose_distribution", {})
        if verbose_dist:
            population = list(verbose_dist.keys())
            weights = list(verbose_dist.values())
            verbose = random.choices(population, weights=weights, k=1)[0]
        else:
            verbose = random.choice(["concise", "standard", "verbose"])

        initial_context = {
            "run_id": run_id,
            "origin": origin,
            "destination": dest,
            "date": random.choice(self.dates),
            "time": random.choice(self.times),
            "passengers": random.randint(1, 3),
            "class": random.choice(["Standard", "Prima", "Business"]),
            "tone": random.choice(["formal", "informal"]), # Used by templates if supported
            "rudeness": rudeness, # Weighted or random choice
            "verbose": verbose, # Weighted or random choice
            
            # Session-discovered state
            "session_to": "",
            "session_date": "",
            "session_time": "",
            "session_pax_discovered": False,
            "session_pax": 1,
            "session_class": None,
            
            # Internal tracking
            "generated_messages": [],
            "current_trains": [], # Result from mock backend
            "ui_state": {"state": "idle", "can": {"next": False, "prev": False, "back": False}},
            "ctx_time": f"{random.randint(6, 22):02d}:{random.randint(0, 59):02d}", 
            "ctx_date": (datetime.now() + timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
            "call_counter": 0,
            
            # Randomly assign Pet (Independent 20%)
            "pet_object": (lambda x: {"phrase": x["phrase"], "type": x["type"]} if x else None)(random.choice([
                {"phrase": "un cane", "type": "large"}, 
                {"phrase": "il mio cane", "type": "large"},
                {"phrase": "un gatto", "type": "small"},
                {"phrase": "il trasportino con il gatto", "type": "small"},
                {"phrase": "un cane di piccola taglia", "type": "small"},
                {"phrase": "un cane grosso", "type": "large"},
                {"phrase": "il mio pastore tedesco", "type": "large"},
                {"phrase": "un cane guida", "type": "assistance"},
                {"phrase": "il cane da assistenza", "type": "assistance"}
            ]) if random.random() < 0.2 else None),

            # Randomly assign Bike (Independent 20%)
            "bike_object": (lambda x: {"phrase": x["phrase"], "type": x["type"]} if x else None)(random.choice([
                {"phrase": "la bici", "type": "normal"}, 
                {"phrase": "una bici", "type": "normal"},
                {"phrase": "le bici", "type": "normal"},
                {"phrase": "la bici pieghevole", "type": "foldable"},
                {"phrase": "una pieghevole", "type": "foldable"},
                {"phrase": "le bici pieghevoli", "type": "foldable"}
            ]) if random.random() < 0.2 else None),

            # Randomly assign Disability (Independent 20%)
            "disability_object": (lambda x: {"phrase": x["phrase"], "type": x["type"]} if x else None)(random.choice([
                {"phrase": "sono in sedia a rotelle", "type": "wheelchair"},
                {"phrase": "uso la carrozzina", "type": "wheelchair"},
                {"phrase": "ho difficoltà a camminare", "type": "motor_ambulatory"},
                {"phrase": "faccio fatica a fare le scale", "type": "motor_ambulatory"},
                {"phrase": "uso le stampelle", "type": "motor_ambulatory"},
                {"phrase": "sono un po' anziano", "type": "elderly"}, 
                {"phrase": "sono anziana", "type": "elderly"},
                {"phrase": "sono incinta", "type": "pregnant"},
                {"phrase": "aspetto un bambino", "type": "pregnant"},
                {"phrase": "sono cieco", "type": "visual"}, 
                {"phrase": "sono ipovedente", "type": "visual"},
                {"phrase": "sono sordo", "type": "hearing"},
                {"phrase": "ho problemi di udito", "type": "hearing"},
                {"phrase": "ho una disabilità cognitiva", "type": "cognitive"},
                {"phrase": "ho bisogno di indicazioni semplici", "type": "cognitive"}
            ]) if random.random() < 0.2 else None)
        }
        
        # Unpack for template easier usage
        initial_context["pet_phrase"] = initial_context["pet_object"]["phrase"] if initial_context["pet_object"] else None
        initial_context["pet_type"] = initial_context["pet_object"]["type"] if initial_context["pet_object"] else None
        initial_context["pet_count"] = 1 if initial_context["pet_object"] else 0

        initial_context["bike_phrase"] = initial_context["bike_object"]["phrase"] if initial_context["bike_object"] else None
        initial_context["bike_type"] = initial_context["bike_object"]["type"] if initial_context["bike_object"] else None
        initial_context["bike_count"] = 1 if initial_context["bike_object"] else 0

        initial_context["disability_phrase"] = initial_context["disability_object"]["phrase"] if initial_context["disability_object"] else None
        initial_context["disability_type"] = initial_context["disability_object"]["type"] if initial_context["disability_object"] else None

        # Inject INITIAL system prompt with context
        initial_params = {
            "origin": initial_context["origin"],
            "destination": "",
            "travel_date": "",
            "travel_time": "",
            "passengers": "0",
            "ui_state": json.dumps(initial_context["ui_state"]),
            "trains_array": "[]",
            "ctx_time": initial_context["ctx_time"],
            "date": initial_context["ctx_date"],
            "ticket_info": None
        }
        initial_xml = ContextFormatter.format_context(initial_params)
        full_system_content = "{SYSTEM_PROMPT}\n\n" + initial_xml
        initial_context["generated_messages"].append({"role": "system", "content": full_system_content})

        return initial_context

    def get_contextual_qa(self, ctx):
        """Selects a QA pair based on the current context (train type, stations, UI state)."""
        if not self.qa_pairs:
            return None, None, "general"
            
        # If we have legacy format (list of lists/tuples), just pick random
        if self.qa_pairs and isinstance(self.qa_pairs[0], (list, tuple)):
            choice = random.choice(self.qa_pairs)
            return choice[0], choice[1], "general"

        candidates = []
        
        # Determine context attributes
        target_train = ctx.get("target_train")
        train_type = target_train["type"] if target_train else None
        origin = ctx.get("origin")
        destination = ctx.get("destination")
        ui_state = ctx.get("ui_state", {}).get("state", "idle")
        
        # Scoring system
        scored_candidates = []
        for item in self.qa_pairs:
            score = 0
            metadata = item.get("metadata", {})
            entities = [e.lower() for e in metadata.get("entities", [])]
            tags = metadata.get("contextual_tags", [])
            
            # Match Train Type
            if train_type:
                for tt in ["Frecciarossa", "Intercity", "Italo", "Regionale"]:
                    if tt.lower() in train_type.lower() and tt.lower() in entities:
                        score += 15
            
            # Match Stations
            if origin and origin.lower() in entities:
                score += 10
            if destination and destination.lower() in entities:
                score += 10
                
            # Contextual Tags matching UI State
            if ui_state in ["results", "choosingSeat"]:
                if "requires_train_type" in tags or "requires_ticket_type" in tags:
                    score += 12
            elif ui_state == "purchased":
                if "general_info" in tags or "location_specific" in tags:
                    score += 8
            
            # Global fallback
            if "general_info" in tags:
                score += 2
                
            scored_candidates.append((score, item))
            
        # Sort by score and pick from top-N high-scoring ones
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        
        # Filter items with at least some relevance if possible
        high_score = scored_candidates[0][0]
        if high_score > 0:
            threshold = max(high_score * 0.5, 1)
            pool = [item for score, item in scored_candidates if score >= threshold]
            choice = random.choice(pool[:10]) # Top 10 suitable
        else:
            choice = random.choice(self.qa_pairs)
            
        subcategory = "general"
        if choice.get("metadata", {}).get("labels"):
            subcategory = choice["metadata"]["labels"][0].get("subcategory", "general")

        return choice.get("question"), choice.get("answer"), subcategory
