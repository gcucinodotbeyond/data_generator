import os
import jinja2
import json
import itertools

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
        
        # Sort by text for consistency
        results_sorted = sorted(all_results, key=lambda x: x['text'])
        print(f"[Deterministic] Generated {len(results_sorted)} total unique utterances.")
        return results_sorted

    def _generate_search_trains(self):
        template = self.env.get_template('utterances.j2')
        unique_items = set()
        
        combinations = list(itertools.product(self.destinations, self.times))
        
        for dest, time_obj in combinations:
            rendered_block = template.render(
                destination=dest, 
                time=time_obj["value"],
                time_type=time_obj["type"],
                to_json=json.dumps
            )
            self._parse_and_add(rendered_block, unique_items)
                
        return self._items_to_list(unique_items, "search_trains")

    def _generate_simple(self, template_name, intent_name):
        template = self.env.get_template(template_name)
        unique_items = set()
        rendered_block = template.render(to_json=json.dumps)
        self._parse_and_add(rendered_block, unique_items)
        return self._items_to_list(unique_items, intent_name)

    def _generate_confirmations(self):
        template = self.env.get_template('confirmations.j2')
        unique_items = set()
        
        # Contextual mixes
        # Destinations
        for dest in self.destinations:
            rendered = template.render(destination=dest, to_json=json.dumps)
            self._parse_and_add(rendered, unique_items)
            
        # Times (subset to avoid explosion)
        for time_obj in self.times[:4]: 
            rendered = template.render(time=time_obj["value"], to_json=json.dumps)
            self._parse_and_add(rendered, unique_items)

        # Classes
        classes = ["prima classe", "seconda classe", "standard", "business"]
        for cls in classes:
            rendered = template.render(class_type=cls, to_json=json.dumps)
            self._parse_and_add(rendered, unique_items)
            
        # Base (no variables)
        rendered = template.render(to_json=json.dumps)
        self._parse_and_add(rendered, unique_items)
        
        return self._items_to_list(unique_items, "confirmation")

    def _generate_refusals(self):
        template = self.env.get_template('refusals.j2')
        unique_items = set()
        
        # Times 
        for time_obj in self.times[:4]: 
            rendered = template.render(time=time_obj["value"], to_json=json.dumps)
            self._parse_and_add(rendered, unique_items)
            
        # Base
        rendered = template.render(to_json=json.dumps)
        self._parse_and_add(rendered, unique_items)
        
        return self._items_to_list(unique_items, "refusal")

    def _generate_qa(self):
        template = self.env.get_template('qa.j2')
        unique_items = set()
        
        pets = ["cane", "gatto", "cagnolino", "animale domestico", "pappagallo"]
        luggage = ["una valigia grande", "lo zaino", "la bici", "il monopattino"]
        services = ["wifi", "ristorante", "bar", "aria condizionata", "presa elettrica"]
        
        for p in pets:
            self._parse_and_add(template.render(pet=p, to_json=json.dumps), unique_items)
        for l in luggage:
            self._parse_and_add(template.render(luggage=l, to_json=json.dumps), unique_items)
        for s in services:
            self._parse_and_add(template.render(service=s, to_json=json.dumps), unique_items)
            
        # General
        self._parse_and_add(template.render(to_json=json.dumps), unique_items)
        
        return self._items_to_list(unique_items, "qa")

    def render(self, intent, context):
        """
        Renders a single utterance for a specific intent using the provided context variables.
        """
        template_name = "utterances.j2" if intent == "search_trains" else f"{intent}.j2"
        # Map some intent nicknames if files are named differently
        if intent == "greeting": template_name = "greetings.j2"
        if intent == "confirmation": template_name = "confirmations.j2"
        if intent == "refusal": template_name = "refusals.j2"
        if intent == "farewell": template_name = "farewells.j2"
        if intent == "qa": template_name = "qa.j2"
        if intent == "ui_navigation": template_name = "ui_navigation.j2"
        
        try:
            template = self.env.get_template(template_name)
        except jinja2.TemplateNotFound:
            # Fallback or error
            return {"text": f"Error: Template {template_name} not found", "variables": context}

        # Render with the full context context
        rendered_block = template.render(**context, to_json=json.dumps)
        
        # Parse the JSON lines
        unique_items = set()
        self._parse_and_add(rendered_block, unique_items)
        
        # Pick one random item that matches our constraints?
        # Actually simplest is: render with specific vars implies we get specific output.
        # But our templates iterate loops. We need to trick the template? 
        # No, we should rely on the template variables.
        # IF template uses "for dest in destinations", and we pass "destinations=[context.destination]", 
        # then loop runs once.
        
        results = self._items_to_list(unique_items, intent)
        if not results:
            return {"text": f"[{intent} generation failed]", "variables": context}
            
        # If we got multiple (e.g. variations in template), pick one.
        import random
        return random.choice(results)
    
    def _parse_and_add(self, rendered_block, unique_set):
        lines = [line.strip() for line in rendered_block.split('\n') if line.strip()]
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
            except json.JSONDecodeError:
                pass
        return results
