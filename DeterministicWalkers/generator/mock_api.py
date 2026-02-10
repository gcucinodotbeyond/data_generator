import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import zlib

class MockBackend:
    """
    A mock backend that simulates Trenitalia API responses.
    It generates consistent, semi-realistic data for train searches and purchases
    matching the v1.5 schema requirements.
    """
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.current_search_results: List[Dict] = []
        self.current_page = 0
        self.page_size = 3
        
        # Purchase flow state
        self.purchase_phase = "init" # init -> selected -> data_input -> complete
        self.current_passengers = 1
        
        # Heuristics for realistic generation
        self.train_types = [
            {"type": "Frecciarossa", "speed": 1.5, "price_base": 50, "stops": 0, "abbr": "FR"},
            {"type": "Frecciargento", "speed": 1.4, "price_base": 40, "stops": 2, "abbr": "FA"},
            {"type": "Intercity", "speed": 1.0, "price_base": 25, "stops": 5, "abbr": "IC"},
            {"type": "Regionale Veloce", "speed": 0.8, "price_base": 12, "stops": 8, "abbr": "RV"},
            {"type": "Regionale", "speed": 0.6, "price_base": 8, "stops": 15, "abbr": "REG"},
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
        Now requires passengers count to proceed fully.
        """
        try:
            args = json.loads(json_args)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON arguments"})

        origin = args.get("origin", "Roma Termini")
        destination = args.get("destination", "Napoli Centrale")
        destination = args.get("destination", "Napoli Centrale")
        passengers = args.get("passengers")
        if passengers:
            try:
                self.current_passengers = int(passengers)
            except:
                pass
        disability_type = args.get("disability_type") # e.g. "visual", "hearing", "motor"
        
        # Step 1: Check passengers
        if not passengers:
            return json.dumps({
                "status": "awaiting_passengers",
                "message": "L'utente deve dire quanti passeggeri sono. Quando lo dice, richiama search_trains CON il parametro passengers.",
                "origin": origin,
                "destination": destination,
                "date": args.get("date", "today"),
                "time": args.get("time", "now"),
                "next_action": "Quando l'utente dice il numero (es. 'siamo in 2'), chiama search_trains(origin='...', destination='...', passengers=N)"
            })
            
        # Step 1b: Acknowledge disability if present
        disability_msg = ""
        if disability_type:
             map_msg = {
                 "visual": "Servizio assistenza per disabilità visiva attivato.",
                 "hearing": "Nota: Assistenza uditiva registrata.",
                 "motor": "Posti riservati per carrozzina evidenziati.",
                 "cognitive": "Assistenza cognitiva richiesta.",
                 "other": "Assistenza speciale richiesta."
             }
             disability_msg = map_msg.get(disability_type, "Assistenza speciale richiesta.")

        # Step 2: Generate Results
        time_str = args.get("time", "now")
        start_time = self._parse_time(time_str)
        
        num_results = self.rng.randint(5, 8)
        results = []
        
        current_dt = start_time
        
        for i in range(num_results):
            # Advance time
            gap = self.rng.randint(15, 60)
            current_dt += timedelta(minutes=gap)
            
            # Pick type
            t_type = self.rng.choice(self.train_types)
            
            # Duration
            base_duration_mins = int(180 / t_type["speed"]) 
            duration_variation = self.rng.randint(-20, 20)
            duration_mins = max(30, base_duration_mins + duration_variation)
            arrival_dt = current_dt + timedelta(minutes=duration_mins)
            
            # Base price
            base_price = t_type["price_base"] * (1 + (self.rng.random() * 0.4 - 0.2)) # +/- 20%
            base_price = round(base_price * int(passengers), 2)
            
            # Build Class List with granular seats
            classes = []
            if t_type["type"] in ["Frecciarossa", "Frecciargento"]:
                 classes = [
                     {"class_denomination": "STANDARD", "price": f"{base_price:.2f}"},
                     {"class_denomination": "PREMIUM", "price": f"{base_price*1.2:.2f}"},
                     {"class_denomination": "BUSINESS", "price": f"{base_price*1.4:.2f}"},
                     {"class_denomination": "EXECUTIVE", "price": f"{base_price*2.5:.2f}"}
                 ]
            elif t_type["type"] == "Intercity":
                classes = [
                     {"class_denomination": "2ª CLASSE", "price": f"{base_price:.2f}"},
                     {"class_denomination": "1ª CLASSE", "price": f"{base_price*1.3:.2f}"}
                ]
            else:
                 classes = [
                     {"class_denomination": "ORDINARIA", "price": f"{base_price:.2f}"}
                 ]

            # Total seats (random simulation since detailed seats are gone)
            total_seats = self.rng.randint(20, 300)

            train_id = self._generate_train_id(t_type["type"])
            dep_str = current_dt.strftime("%H:%M")
            arr_str = arrival_dt.strftime("%H:%M")

            train = {
                "pos": i + 1,
                "id": train_id,
                "dep": dep_str,
                "arr": arr_str,
                "type": t_type["type"],
                "duration": duration_mins,
                "changes": 0,
                "stops": t_type["stops"],
                "available_seats": total_seats,
                "delay": 0,
                "classes": classes
            }
            results.append(train)

        self.current_search_results = results
        self.current_page = 0
        
        # Return first page similar to prompt format
        page_slice = results[0:self.page_size]
        
        # Rename classes to price for the output to match simple_llm_session.txt
        for r in page_slice:
            if "classes" in r:
                r["price"] = r.pop("classes")
                
        return json.dumps({"trains": page_slice})

    def ui_control(self, json_args: str) -> str:
        try:
            args = json.loads(json_args)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON arguments"})
            
        action = args.get("action")
        target = args.get("target")
        
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

        elif action == "show_info":
            if target == "station":
                return json.dumps({
                    "success": True,
                    "message": "La sala d'attesa è Freccia Lounge, primo piano. Solo con biglietto Freccia",
                    "info": {
                        "name": "Roma Termini",
                        "waiting_room": {"location": "Freccia Lounge, primo piano", "hours": "06:00-22:00", "note": "Solo con biglietto Freccia"},
                        "wc": "Binario 1",
                        "bar": "Piano superiore"
                    }
                })
            
            elif target == "ticket":
                 # Mock of ticket info
                 return json.dumps({
                    "success": True,
                    "message": "Dettagli biglietto mostrati a schermo.",
                    "info": {
                        "train_id": "FR9535",
                        "class": "prm",
                        "seats": ["7A", "8A"],
                        "car": 4, 
                        "platform": "6",
                        "pnr": "QL0Q3F"
                    }
                })
            elif target == "train":
                return json.dumps({
                    "success": True, 
                    "message": "Informazioni sul treno visualizzate.",
                    "info": {"stops": ["Stop A", "Stop B"], "services": ["Bar", "Bici"]}
                })

        return json.dumps({"status": "ok", "action": action})

    def purchase_ticket(self, json_args: str) -> str:
        """
        Stateful purchase flow:
        1. Train Selection (Partial or Complete)
        2. Just Train+Class -> Request Seat Selection
        3. +Seats -> Request Personal Data
        4. +Confirmation -> Finalize
        """
        try:
            args = json.loads(json_args)
        except json.JSONDecodeError:
            return json.dumps({"error": "Invalid JSON arguments"})
            
        train_id = args.get("train_id", "UNKNOWN")
        train_class = args.get("class")
        seats = args.get("seats")
        carriage = args.get("carriage")
        
        # State Machine Logic

        # 0. Class Selection Required (if not provided in initial call)
        if not train_class:
            return json.dumps({
                "status": "class_selection_required",
                "message": "Scegli la classe di viaggio (Standard, Premium, Business, ecc.).",
                "train_id": train_id,
                "instruction": "L'utente deve specificare la classe. Chiedi 'In che classe vuoi viaggiare?' se non l'ha già detto."
            })
        
        # 1. Seat Selection Required
        if not seats:
            self.purchase_phase = "seat_selection"
            # Auto-assign logic to match simple_llm_session.txt
            # Auto-assign logic: Deterministic based on Train ID + Carriage
            # Default to carriage 5 if not specified
            target_carriage = carriage or "5"
            
            # Seed generation: Stable hash of train + carriage
            seed_str = f"{train_id}_carriage_{target_carriage}"
            # Use zlib.adler32 for simple stable integer hash across runs
            seed_val = zlib.adler32(seed_str.encode('utf-8'))
            
            # Use a separate RNG for this carriage to be deterministic
            carriage_rng = random.Random(seed_val)
            
            # Generate Layout & Availability (Rows 1-15, A-D)
            free_seats = []
            seat_map = [] # List of seats in order
            
            rows = 15
            cols = ["A", "B", "C", "D"]
            
            for r in range(1, rows + 1):
                for c in cols:
                    seat_code = f"{r}{c}"
                    seat_map.append(seat_code)
                    # Check status
                    val = carriage_rng.random()
                    if val < 0.7:
                        free_seats.append(seat_code)
            
            # Select N Adjacent Seats
            # Simple adjacency strategy: slide a window of size N over the full map
            # checking if all in window are in free_seats set
            
            needed = self.current_passengers
            assigned_seats = []
            
            # Heuristic: Try to find N contiguous free seats
            # If not found, just take first N free seats
            
            free_set = set(free_seats)
            found_block = False
            
            # iterate window
            for i in range(len(seat_map) - needed + 1):
                candidate_block = seat_map[i : i + needed]
                
                # Check 1: All must be free
                if all(s in free_set for s in candidate_block):
                    # Check 2: Must be in same row (heuristic for adjacency)
                    # e.g. 1A, 1B is good. 1D, 2A is technically adjacent in list but usually not preferred?
                    # Let's assume strict row adjacency OR just strictly list adjacency for simplicity as per "find adjacent"
                    # For simplicity: list adjacency is enough for this mock
                    
                    # Refinement: Don't span rows if possible? 
                    # 1A 1B 1C 1D | 2A... 
                    # 1D and 2A are neighbors? physically maybe back-to-back.
                    # Let's check row consistency just to be nice
                    rows_in_block = {s[:-1] for s in candidate_block}
                    if len(rows_in_block) == 1:
                        assigned_seats = candidate_block
                        found_block = True
                        break
                        
            if not found_block:
                # Fallback: Just take first N free seats
                assigned_seats = free_seats[:needed]
                if len(assigned_seats) < needed:
                     # Emergency fallback if train full: generate N fake seats using high row logic
                     # This shouldn't really happen with 0.7 free rate on 60 seats (42 free) and small N
                     start_fake = 20
                     assigned_seats = [f"{start_fake}{cols[i%4]}" for i in range(needed)]

            return json.dumps({
                "status": "seat_selection_required",
                "message": f"Ho assegnato i posti {', '.join(assigned_seats)} in carrozza {target_carriage}. Conferma o scegli altri posti sullo schermo.",
                "train_id": train_id,
                "train_type": "Frecciarossa",
                "auto_assigned_seats": assigned_seats,
                "auto_assigned_carriage": target_carriage,
                "instruction": "Attendi che l'utente confermi o modifichi i posti, poi chiedi i dati personali. Quando conferma, RICHIAMA purchase_ticket con gli stessi parametri."
            })
            
        # 2. Personal Data Required (First time receiving seats)
        if self.purchase_phase != "awaiting_confirm":
            self.purchase_phase = "awaiting_confirm"
            return json.dumps({
                "status": "personal_data_required",
                "message": "Posti confermati. Chiedi all'utente di inserire nome, cognome ed email sullo schermo.",
                "train_id": train_id,
                "instruction": "Attendi che l'utente inserisca nome, cognome ed email via touch. Quando l'utente dice 'procedi' o 'conferma', RICHIAMA purchase_ticket con gli stessi parametri (train_id, class, seats) per completare l'acquisto."
            })
            
        # 3. Finalize Purchase
        self.purchase_phase = "complete" # Reset or done
        
        # Retrieve price from current results if possible
        price = "50.00"
        found = next((t for t in self.current_search_results if t.get("id") == train_id), None)
        if found:
            # Try to match class price
            # Simplified map
            class_list = found.get("classes", [])
            # Naive string match or default
            p_obj = next((p for p in class_list if train_class.upper() in p["class_denomination"].upper()), class_list[0] if class_list else {})
            price = p_obj.get("price", "50.00")

        # Parse seats to count
        seat_list = [s.strip() for s in seats.split(",")]
        pax_count = len(seat_list)
        unit_price = float(price)
        total_price = unit_price * pax_count + 15.0 # Add some extras cost as in example
        
        return json.dumps({
            "status": "OK",
            "pnr": "PNR" + str(self.rng.randint(100000, 999999)),
            "platform": str(self.rng.randint(1, 20)),
            "train_id": train_id,
            "class": train_class.upper(),
            "price": f"{unit_price:.2f}",
            "total": f"{total_price:.2f}",
            "email_sent": True,
            "passengers": pax_count,
            "seats": seat_list,
            "car": str(carriage)
        })
