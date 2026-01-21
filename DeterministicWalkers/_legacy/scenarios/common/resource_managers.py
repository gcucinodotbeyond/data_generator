
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from core.random import SeededRandom

class StationManager:
    """Manages station data loading and selection."""
    
    _stations_cache = None
    
    @classmethod
    def _load_stations(cls):
        """Load station data from resources (cached)."""
        if cls._stations_cache is None:
            # Adjust path: scenarios/common/../../../resources/stations.json
            resource_path = Path(__file__).parent.parent.parent / "resources" / "stations.json"
            try:
                with open(resource_path, 'r', encoding='utf-8') as f:
                    stations_data = json.load(f)
                
                all_stations = []
                for category in stations_data.values():
                    all_stations.extend(category)
                
                cls._stations_cache = {
                    'all': sorted(list(set(all_stations))),
                    'major': stations_data.get("major", all_stations[:20])
                }
            except FileNotFoundError:
                print(f"Warning: Stations file not found at {resource_path}")
                cls._stations_cache = {
                    'all': ["Roma Termini", "Milano Centrale"],
                    'major': ["Roma Termini", "Milano Centrale"]
                }
        return cls._stations_cache
    
    @classmethod
    def get_all(cls) -> List[str]:
        """Get all stations."""
        return cls._load_stations()['all']
    
    @classmethod
    def get_major(cls) -> List[str]:
        """Get major stations."""
        return cls._load_stations()['major']
    
    @classmethod
    def select_random(cls, rng: SeededRandom, major_only: bool = False) -> str:
        """Select a random station."""
        stations = cls.get_major() if major_only else cls.get_all()
        return rng.choice(stations)
    
    @classmethod
    def select_different(cls, rng: SeededRandom, exclude: str, major_only: bool = False) -> str:
        """Select a random station different from the excluded one."""
        stations = cls.get_major() if major_only else cls.get_all()
        candidates = [s for s in stations if s != exclude]
        return rng.choice(candidates) if candidates else exclude


class TrainManager:
    """Manages train type and ID generation."""
    
    TRAIN_TYPES = [
        "Frecciarossa", "Frecciargento", "Frecciabianca", 
        "Intercity", "Intercity Notte", "Regionale Veloce", "Regionale",
        "Eurocity"
    ]
    
    TRAIN_PREFIXES = {
        "Frecciarossa": "FR",
        "Frecciargento": "FA",
        "Frecciabianca": "FB",
        "Intercity": "IC",
        "Intercity Notte": "ICN",
        "Regionale Veloce": "RV",
        "Regionale": "R",
        "Eurocity": "EC"
    }
    
    @classmethod
    def select_random_type(cls, rng: SeededRandom) -> str:
        """Select a random train type name."""
        return rng.choice(cls.TRAIN_TYPES)
    
    @classmethod
    def generate_id(cls, rng: SeededRandom, train_type: Optional[str] = None) -> str:
        """Generate a random train ID."""
        if not train_type or train_type not in cls.TRAIN_PREFIXES:
            train_type = cls.select_random_type(rng)
        
        prefix = cls.TRAIN_PREFIXES.get(train_type, "TR")
        number = rng.randint(1000, 9999)
        return f"{prefix}{number}"
    
    @classmethod
    def select_random(cls, rng: SeededRandom) -> str:
        """Select either a type or an ID randomly."""
        if rng.random() < 0.7:
            return cls.select_random_type(rng)
        else:
            return cls.generate_id(rng)


class TimeManager:
    """Manages time context generation with template constraints."""
    
    @staticmethod
    def generate_time(rng: SeededRandom, base_hour: Optional[int] = None) -> str:
        """
        Generate a time string (HH:MM format).
        
        Args:
            rng: Random number generator
            base_hour: Specific hour to use (if None, generates random hour 6-22)
        
        Returns:
            Time string in HH:MM format
        """
        hour = base_hour if base_hour is not None else rng.randint(6, 22)
        minute = rng.randint(0, 59)
        return f"{hour:02d}:{minute:02d}"
    
    @staticmethod
    def generate_date(rng: SeededRandom) -> str:
        """
        Generate a random date within a reasonable range (e.g., Dec 2025 - Jan 2026).
        """
        # Simple random date generation
        # Let's say between 2025-12-01 and 2026-01-31
        year = 2025
        month = 12
        day = rng.randint(1, 31)
        
        # 20% chance of being in Jan 2026
        if rng.random() < 0.2:
            year = 2026
            month = 1
            day = rng.randint(1, 31)
        
        return f"{year}-{month:02d}-{day:02d}"

    @staticmethod
    def parse_template_constraints(template: str, rng: SeededRandom) -> Tuple[int, Dict[str, str]]:
        """
        Parse template for time constraints and return base_hour and replacements.
        
        This method analyzes user message templates for time-related placeholders
        and generates appropriate time values that match the semantic context.
        
        Returns:
            (base_hour, format_args) tuple
        """
        # Default to mid-day hours
        base_hour = rng.randint(8, 20)
        format_args = {}
        
        # Morning period
        if "{period_morning}" in template:
            base_hour = rng.randint(6, 11)
            format_args["period_morning"] = rng.choice(["stamattina", "questa mattina"])
        
        # Afternoon period
        elif "{period_afternoon}" in template:
            base_hour = rng.randint(12, 17)
            format_args["period_afternoon"] = rng.choice(["oggi pomeriggio", "questo pomeriggio"])
        
        # Evening period
        elif "{period_evening}" in template:
            base_hour = rng.randint(16, 21)
            format_args["period_evening"] = rng.choice(["stasera", "questa sera"])
        
        # Relative dates
        if "{relative_date_morning}" in template:
            format_args["relative_date_morning"] = "domani mattina"
        if "{relative_date_afternoon}" in template:
            format_args["relative_date_afternoon"] = "domani pomeriggio"
        if "{relative_date_evening}" in template:
            format_args["relative_date_evening"] = "domani sera"
        if "{relative_date}" in template:
            format_args["relative_date"] = rng.choice(["domani", "dopodomani"])
        if "{relative_today}" in template:
            format_args["relative_today"] = "oggi"
        
        # Time request
        if "{time_request}" in template:
            req_h = (base_hour + rng.randint(1, 4)) % 24
            req_m = rng.choice([0, 15, 30, 45])
            format_args["time_request"] = f"{req_h:02d}:{req_m:02d}"
        
        # Train info
        if "{train_info}" in template:
            format_args["train_info"] = TrainManager.select_random(rng)
        
        return base_hour, format_args
