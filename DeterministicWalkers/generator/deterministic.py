import os
import jinja2
import json
import itertools
import random

class DeterministicGenerator:
    def __init__(self, template_dir=None):
        if template_dir is None:
            # Default to the templates directory relative to this file
            self.template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        else:
            self.template_dir = template_dir
            
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.env.globals.update(random=random.random)

        # Domain Variables
        self.destinations = ["Roma", "Milano", "Napoli", "Firenze", "Bologna", "Torino", "Venezia"]
        self.times = [
            {"value": "8:00", "type": "numeric"},
            {"value": "9:30", "type": "numeric"},
            {"value": "14:00", "type": "numeric"},
            {"value": "18:45", "type": "numeric"},
            {"value": "subito", "type": "relative_now"},
            {"value": "ora", "type": "relative_now"},
            {"value": "adesso", "type": "relative_now"},
            {"value": "domani mattina", "type": "relative_future"},
            {"value": "stasera", "type": "relative_future"}
        ]

        self.dates = ["oggi", "domani", "venerdì prossimo", "il 15"]
    
    
    def generate(self):
        all_results = []
        
        # 1. SEARCH TRAINS
        print("[Deterministic] Generating 'search_trains'...")
        all_results.extend(self._generate_search_trains())

        # 2. GREETINGS
        print("[Deterministic] Generating 'greetings'...")
        all_results.extend(self._generate_simple("greetings.j2", "greeting"))

        # 3. CONFIRMATIONS
        print("[Deterministic] Generating 'confirmations'...")
        all_results.extend(self._generate_confirmations())

        # 4. REFUSALS
        print("[Deterministic] Generating 'refusals'...")
        all_results.extend(self._generate_refusals())

        # 5. FAREWELLS
        print("[Deterministic] Generating 'farewells'...")
        all_results.extend(self._generate_simple("farewells.j2", "farewell"))

        # 6. UI NAVIGATION
        print("[Deterministic] Generating 'ui_navigation'...")
        all_results.extend(self._generate_simple("ui_navigation.j2", "ui_navigation"))

        # 7. QA
        print("[Deterministic] Generating 'qa'...")
        all_results.extend(self._generate_qa())

        # 8. REFINEMENTS (Pets)
        print("[Deterministic] Generating 'refinements'...")
        all_results.extend(self._generate_refinements())
        
        # Sort by text for consistency
        results_sorted = sorted(all_results, key=lambda x: x['text'])
        print(f"[Deterministic] Generated {len(results_sorted)} total unique utterances.")
        return results_sorted

    def _get_template_path(self, basename, rudeness):
        if rudeness == 'rude':
            return f"user/rude/{basename}"
        return f"user/non-rude/{basename}"

    def _generate_search_trains(self):
        unique_items = set()
        combinations = list(itertools.product(self.destinations, self.times))
        
        for rudeness in ['rude', 'polite', 'neutral']:
            tmpl_path = self._get_template_path('utterances.j2', rudeness)
            try:
                template = self.env.get_template(tmpl_path)
            except jinja2.TemplateNotFound:
                continue

            for dest, time_obj in combinations:
                # 1. Standard search (no date)
                rendered_block = template.render(
                    destination=dest, 
                    time=time_obj["value"],
                    time_type=time_obj["type"],
                    rudeness=rudeness,
                    verbose='standard',
                    to_json=json.dumps
                )
                self._parse_and_add(rendered_block, unique_items)
                
                # 2. Add search with date (pick one date for variety)
                date_val = random.choice(self.dates)
                rendered_block_with_date = template.render(
                    destination=dest, 
                    time=time_obj["value"],
                    time_type=time_obj["type"],
                    date=date_val,
                    rudeness=rudeness,
                    verbose='standard',
                    to_json=json.dumps
                )
                self._parse_and_add(rendered_block_with_date, unique_items)
                
        return self._items_to_list(unique_items, "search_trains")

    def _generate_simple(self, template_name, intent_name):
        unique_items = set()
        for rudeness in ['rude', 'polite', 'neutral']:
            tmpl_path = self._get_template_path(template_name, rudeness)
            try:
                template = self.env.get_template(tmpl_path)
                rendered_block = template.render(rudeness=rudeness, verbose='standard', to_json=json.dumps)
                self._parse_and_add(rendered_block, unique_items)
            except jinja2.TemplateNotFound:
                pass
        return self._items_to_list(unique_items, intent_name)

    def _generate_confirmations(self):
        unique_items = set()
        
        for rudeness in ['rude', 'polite', 'neutral']:
            tmpl_path = self._get_template_path('confirmations.j2', rudeness)
            try:
                template = self.env.get_template(tmpl_path)
            except jinja2.TemplateNotFound:
                continue
            
            # Contextual mixes
            # Destinations
            for dest in self.destinations:
                rendered = template.render(destination=dest, rudeness=rudeness, verbose='standard', to_json=json.dumps)
                self._parse_and_add(rendered, unique_items)
                
            # Times (subset to avoid explosion)
            for time_obj in self.times[:4]: 
                rendered = template.render(time=time_obj["value"], rudeness=rudeness, verbose='standard', to_json=json.dumps)
                self._parse_and_add(rendered, unique_items)

            # Classes
            classes = ["prima classe", "seconda classe", "standard", "business"]
            for cls in classes:
                rendered = template.render(class_type=cls, rudeness=rudeness, verbose='standard', to_json=json.dumps)
                self._parse_and_add(rendered, unique_items)
                
            # Base (no variables)
            rendered = template.render(rudeness=rudeness, verbose='standard', to_json=json.dumps)
            self._parse_and_add(rendered, unique_items)
        
        return self._items_to_list(unique_items, "confirmation")

    def _generate_refusals(self):
        unique_items = set()
        
        for rudeness in ['rude', 'polite', 'neutral']:
            tmpl_path = self._get_template_path('refusals.j2', rudeness)
            try:
                template = self.env.get_template(tmpl_path)
            except jinja2.TemplateNotFound:
                continue

            # Times 
            for time_obj in self.times[:4]: 
                rendered = template.render(time=time_obj["value"], rudeness=rudeness, verbose='standard', to_json=json.dumps)
                self._parse_and_add(rendered, unique_items)
                
            # Base
            rendered = template.render(rudeness=rudeness, verbose='standard', to_json=json.dumps)
            self._parse_and_add(rendered, unique_items)
        
        return self._items_to_list(unique_items, "refusal")

    def _generate_qa(self):
        unique_items = set()
        
        pets = ["cane", "gatto", "cagnolino", "animale domestico", "pappagallo"]
        luggage = ["una valigia grande", "lo zaino", "la bici", "il monopattino"]
        services = ["wifi", "ristorante", "bar", "aria condizionata", "presa elettrica"]
        
        for rudeness in ['rude', 'polite', 'neutral']:
            tmpl_path = self._get_template_path('qa.j2', rudeness)
            try:
                template = self.env.get_template(tmpl_path)
            except jinja2.TemplateNotFound:
                continue

            for p in pets:
                self._parse_and_add(template.render(pet=p, rudeness=rudeness, verbose='standard', to_json=json.dumps), unique_items)
            for l in luggage:
                self._parse_and_add(template.render(luggage=l, rudeness=rudeness, verbose='standard', to_json=json.dumps), unique_items)
            for s in services:
                self._parse_and_add(template.render(service=s, rudeness=rudeness, verbose='standard', to_json=json.dumps), unique_items)
                
            # General
            self._parse_and_add(template.render(rudeness=rudeness, verbose='standard', to_json=json.dumps), unique_items)
        
        return self._items_to_list(unique_items, "qa")

    def _generate_refinements(self):
        unique_items = set()
        pet_phrases = [
            "un cane", "il mio cane", "un gatto", "il trasportino con il gatto",
            "un cane di piccola taglia", "un cane grosso", "il mio pastore tedesco",
            "un cane guida", "il cane da assistenza"
        ]
        
        disability_phrases = [
             "sono in sedia a rotelle", "uso la carrozzina", # wheelchair
             "ho difficoltà a camminare", "faccio fatica a fare le scale", "uso le stampelle", # motor_ambulatory
             "sono un po' anziano", "sono anziana", # elderly
             "sono incinta", "aspetto un bambino", # pregnant
             "sono cieco", "sono ipovedente", # visual
             "sono sordo", "ho problemi di udito", # hearing
             "ho una disabilità cognitiva", "ho bisogno di indicazioni semplici" # cognitive
        ]
        
        counts = [1, 2, 3]
        
        for rudeness in ['rude', 'polite', 'neutral']:
            tmpl_path = self._get_template_path('refinement.j2', rudeness)
            try:
                template = self.env.get_template(tmpl_path)
            except jinja2.TemplateNotFound:
                continue

            for count in counts:
                # 1. Standard (no pet)
                for verbose in ['concise', 'standard', 'verbose']:
                    rendered = template.render(aspect="passengers", count=count, rudeness=rudeness, verbose=verbose, to_json=json.dumps)
                    self._parse_and_add(rendered, unique_items)

                # 2. With Pet
                for pet in pet_phrases:
                    for verbose in ['concise', 'standard', 'verbose']:
                        rendered = template.render(
                            aspect="passengers", 
                            count=count, 
                            pet_phrase=pet, 
                            rudeness=rudeness, 
                            verbose=verbose, 
                            to_json=json.dumps
                        )
                        self._parse_and_add(rendered, unique_items)

                # 3. With Bike
                bike_phrases = [
                    "la bici", "una bici", "le bici",
                    "la bici pieghevole", "una pieghevole", "le bici pieghevoli"
                ]
                for bike in bike_phrases:
                    for verbose in ['concise', 'standard', 'verbose']:
                        rendered = template.render(
                            aspect="passengers", 
                            count=count, 
                            bike_phrase=bike, 
                            rudeness=rudeness, 
                            verbose=verbose, 
                            to_json=json.dumps
                        )
                        self._parse_and_add(rendered, unique_items)
                        
                # 4. Combined Pet + Bike
                for pet in pet_phrases:
                        for verbose in ['concise', 'standard', 'verbose']:
                            rendered = template.render(
                                aspect="passengers", 
                                count=count, 
                                pet_phrase=pet,
                                bike_phrase=bike, 
                                rudeness=rudeness, 
                                verbose=verbose, 
                                to_json=json.dumps
                            )
                            self._parse_and_add(rendered, unique_items)
                            
                            
                 # 5. With Disability (Standalone)
                for dis in disability_phrases:
                    for verbose in ['concise', 'standard', 'verbose']:
                        rendered = template.render(
                            aspect="disability", # Use specific aspect
                            disability_phrase=dis,
                            rudeness=rudeness,
                            verbose=verbose,
                            to_json=json.dumps
                        )
                        self._parse_and_add(rendered, unique_items)

               # 6. Combined Disability + Pet (Subset) -- REMOVED as we split turns
               # We only generate passengers+pet/bike on aspect="passengers" 
               # and Disability on aspect="disability"

                            
        return self._items_to_list(unique_items, "refinement")

    def render(self, intent, context):
        """
        Renders a single utterance for a specific intent using the provided context variables.
        """
        template_name = ""
        
        # 1. Assistant Responses Routing
        if intent == "assistant_responses":
            category = context.get("category")
            if category in ["searching", "search_success", "search_empty", "ask_passengers", "disability_ack"]:
                template_name = "assistant/search.j2"
            elif category in ["seat_prompt", "seat_ack", "selection_refinement", "class_prompt", "class_ack", "handshake", "ticket_handover", "ask_data"]:
                template_name = "assistant/booking.j2"
            elif category in ["greeting_response", "refusal_ack", "farewell"]:
                template_name = "assistant/chitchat.j2"
            else: # ui_action, show_info_response, qa_answer, ood_redirect, complaint_response
                template_name = "assistant/info.j2"
                
            try:
                template = self.env.get_template(template_name)
                # Ensure vars present
                render_context = context.copy()
                rendered_block = template.render(**render_context, to_json=json.dumps)
                unique_items = set()
                self._parse_and_add(rendered_block, unique_items)
                results = self._items_to_list(unique_items, "assistant_response")
                if not results: return {"text": "[Assistant generation failed]"}
                return random.choice(results)
            except jinja2.TemplateNotFound:
                return {"text": f"Error: Template {template_name} not found"}

        # 2. User Intents Routing
        # Map intent to filename
        if intent == "search_trains": basename = "utterances.j2"
        elif intent == "greeting": basename = "greetings.j2"
        elif intent == "confirmation": basename = "confirmations.j2"
        elif intent == "refusal": basename = "refusals.j2"
        elif intent == "farewell": basename = "farewells.j2"
        elif intent == "qa": basename = "qa.j2"
        elif intent == "ui_navigation": basename = "ui_navigation.j2"
        elif intent == "complaint": basename = "complaint.j2"
        elif intent == "ood": basename = "ood.j2"
        elif intent == "refinement": basename = "refinement.j2"
        else: basename = f"{intent}.j2"
        
        rudeness = context.get("rudeness", "neutral")
        template_path = self._get_template_path(basename, rudeness)
        
        try:
            template = self.env.get_template(template_path)
        except jinja2.TemplateNotFound:
            # Fallback to non-rude if rude not found (or vice versa? no, just error)
            return {"text": f"Error: Template {template_path} not found", "variables": context}

        # Render
        render_context = context.copy()
        if "date" not in render_context:
            render_context["date"] = None

        rendered_block = template.render(**render_context, to_json=json.dumps)
        
        unique_items = set()
        self._parse_and_add(rendered_block, unique_items)
        
        results = self._items_to_list(unique_items, intent)
        if not results:
            print(f"[Deterministic] Warning: Generation failed for intent '{intent}' context={context.keys()}")
            return {"text": f"[{intent} generation failed]", "variables": context}
            
        return random.choice(results)
    
    def _parse_and_add(self, rendered_block, unique_set):
        # Handle concatenated JSON objects (e.g. }{ -> } \n {)
        cleaned_block = rendered_block.replace('}{', '}\n{')
        lines = [line.strip() for line in cleaned_block.split('\n') if line.strip()]
        for line in lines:
            unique_set.add(line)

    def _items_to_list(self, unique_set, intent):
        results = []
        for item_str in unique_set:
            try:
                item = json.loads(item_str)
                if "intent" not in item:
                    item["intent"] = intent
                item["generator"] = "deterministic_jinja2"
                results.append(item)
            except json.JSONDecodeError as e:
                print(f"[Deterministic] JSON Error parsing line for intent '{intent}': {e} | Line: {item_str[:50]}...")
        return results

