import json
import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class MockBackend:
    """
    A mock backend that simulates Trenitalia API responses.
    It generates consistent, semi-realistic data for train searches and purchases.
    """
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.current_search_results: List[Dict] = []
        self.current_page = 0
        self.page_size = 3
        
        # Heuristics for realistic generation
        self.train_types = [
            {"type": "Frecciarossa", "speed": 1.5, "price_base": 50, "stops": 0},
            {"type": "Frecciargento", "speed": 1.4, "price_base": 40, "stops": 2},
            {"type": "Intercity", "speed": 1.0, "price_base": 25, "stops": 5},
            {"type": "Regionale Veloce", "speed": 0.8, "price_base": 12, "stops": 8},
            {"type": "Regionale", "speed": 0.6, "price_base": 8, "stops": 15},
        ]

    def _generate_train_id(self, train_type: str) -> str:
        prefix_map = {
            "Frecciarossa": "FR", "Frecciargento": "FA", "Frecciabianca": "FB",
            "Intercity": "IC", "Regionale Veloce": "RV", "Regionale": "R"
        }
        prefix = prefix_map.get(train_type, "TR")
        number = self.rng.randint(1000, 9999)
        return f"{prefix}{number}"

    def _parse_time(self, time_str: str) -> datetime:
        """Parses vague or specific time strings into a datetime object (today)."""
        now = datetime.now()
        base_date = now.replace(second=0, microsecond=0)
        
        if not time_str:
            return base_date

        time_str = time_str.lower()
        if time_str in ["now", "adesso", "ora", "subito"]:
            pass # Keep now
        elif time_str in ["morning", "mattina"]:
            base_date = base_date.replace(hour=8, minute=0)
        elif time_str in ["afternoon", "pomeriggio"]:
            base_date = base_date.replace(hour=14, minute=0)
        elif time_str in ["evening", "sera", "stasera"]:
            base_date = base_date.replace(hour=19, minute=0)
        elif ":" in time_str:
            try:
                parts = time_str.split(":")
                h = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 else 0
                base_date = base_date.replace(hour=h, minute=m)
            except:
                pass 
        
        return base_date

    def search_trains(self, json_args: str) -> str:
        """
        Simulates searching for trains.
        Args: json string matching schema (origin, destination, etc.)
        """
        try:
            args = json.loads(json_args)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON arguments"})

        origin = args.get("origin", "Roma Termini")
        time_str = args.get("time", "now")
        start_time = self._parse_time(time_str)
        
        # Generate 8-12 results
        num_results = self.rng.randint(5, 12)
        results = []
        
        current_dt = start_time
        
        for i in range(num_results):
            # Advance time by 15-60 mins for next train
            gap = self.rng.randint(15, 60)
            current_dt += timedelta(minutes=gap)
            
            # Pick type
            t_type = self.rng.choice(self.train_types)
            
            # Filter somewhat by 'class' or inferred need? For now random.
            
            # Calculate duration
            base_duration_mins = int(180 / t_type["speed"]) 
            duration_variation = self.rng.randint(-20, 20)
            duration_mins = max(30, base_duration_mins + duration_variation)
            
            arrival_dt = current_dt + timedelta(minutes=duration_mins)
            
            # Price logic
            price = t_type["price_base"] * (1 + (self.rng.random() * 0.4 - 0.2)) # +/- 20%
            price = round(price, 2)
            
            train = {
                "pos": i + 1,
                "id": self._generate_train_id(t_type["type"]),
                "dep": current_dt.strftime("%H:%M"),
                "arr": arrival_dt.strftime("%H:%M"),
                "type": t_type["type"],
                "stops": t_type["stops"],
                "price": price
            }
            results.append(train)

        self.current_search_results = results
        self.current_page = 0
        
        # Return first page
        page_slice = results[0:self.page_size]
        return json.dumps({"trains": page_slice})

    def ui_control(self, json_args: str) -> str:
        try:
            args = json.loads(json_args)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON arguments"})
            
        action = args.get("action")
        
        if action == "next":
            max_page = max(0, (len(self.current_search_results) - 1) // self.page_size)
            if self.current_page < max_page:
                self.current_page += 1
            
            start = self.current_page * self.page_size
            end = start + self.page_size
            page_slice = self.current_search_results[start:end]
            
            return json.dumps({"page": self.current_page + 1, "trains": page_slice})

        elif action == "prev":
            if self.current_page > 0:
                self.current_page -= 1
                
            start = self.current_page * self.page_size
            end = start + self.page_size
            page_slice = self.current_search_results[start:end]
            
            return json.dumps({"page": self.current_page + 1, "trains": page_slice})

        elif action == "show_changes":
            train_pos = args.get("train_position", 1)
            target_train = None
            
            # Find train in current results
            for t in self.current_search_results:
                if t["pos"] == train_pos:
                    target_train = t
                    break
            
            if not target_train:
                # Fallback if pos not found in current page slice
                target_train = self.current_search_results[0] if self.current_search_results else None

            if target_train:
                num_stops = target_train.get("stops", 0)
                if num_stops == 0:
                    msg = "Il treno è diretto, non effettua fermate intermedie."
                    stops = []
                else:
                    msg = f"Il treno effettua {num_stops} fermate intermedie."
                    stops = [f"Stazione {i+1}" for i in range(num_stops)]
                
                return json.dumps({
                    "status": msg,
                    "stops": stops,
                    "is_direct": num_stops == 0
                })
            else:
                return json.dumps({"error": "Train not found"})
        
        return json.dumps({"status": "ok"})

    def purchase_ticket(self, json_args: str) -> str:
        try:
            args = json.loads(json_args)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON arguments"})
            
        train_id = args.get("train_id", "UNKNOWN")
        seat = args.get("seat", f"{self.rng.randint(1,15)}{self.rng.choice(['A','B','C','D'])}")
        carriage = args.get("carriage", self.rng.randint(1, 8))
        
        price = 50.00
        found = next((t for t in self.current_search_results if t["id"] == train_id), None)
        if found:
            price = found["price"]
            
        confirmation_code = ''.join(self.rng.choices("ABCDEF0123456789", k=6))
        
        ticket = {
            "confirmation_code": confirmation_code,
            "train_id": train_id,
            "seat": seat,
            "carriage": carriage,
            "class": args.get("class", "Standard"),
            "price": price
        }
        return json.dumps(ticket)
