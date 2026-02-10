"""
pytest configuration and shared fixtures.

This file contains fixtures that are available to all test files.
"""
import pytest
import json
import os
from pathlib import Path
from typing import Dict, Any


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def generator_dir(project_root: Path) -> Path:
    """Return the generator directory."""
    return project_root / "generator"


@pytest.fixture
def resources_dir(project_root: Path) -> Path:
    """Return the resources directory."""
    return project_root / "resources"


@pytest.fixture
def sample_context() -> Dict[str, Any]:
    """Return a sample context for dialogue generation."""
    return {
        "origin": "Milano Centrale",
        "destination": "Roma Termini",
        "date": "2026-05-10",
        "time": "14:30",
        "passengers": 2,
        "class": "Standard",
        "rudeness": "polite",
        "verbose": "standard",
    }


@pytest.fixture
def sample_ui_state() -> Dict[str, Any]:
    """Return a sample UI state."""
    return {
        "state": "search",
        "phase": "input_pax",
        "can": {
            "next": False,
            "prev": False,
            "back": True
        }
    }


@pytest.fixture
def sample_train() -> Dict[str, Any]:
    """Return a sample train object."""
    return {
        "id": "FR9624",
        "type": "Frecciarossa",
        "dep": "08:30",
        "arr": "11:45",
        "duration": "3h15m",
        "changes": 0,
        "price_standard": 45.90,
        "price_prima": 89.90,
        "available_seats_standard": 120,
        "available_seats_prima": 45
    }


@pytest.fixture
def sample_context_params() -> Dict[str, Any]:
    """Return sample parameters for ContextFormatter."""
    return {
        "origin": "Milano Centrale",
        "destination": "Roma Termini",
        "travel_date": "today",
        "travel_time": "14:30",
        "passengers": "2",
        "ui_state": '{"state": "search", "phase": "input_pax"}',
        "trains_array": "[]",
        "ctx_time": "14:30",
        "date": "2026-05-10",
        "ticket_info": None
    }


@pytest.fixture
def mock_backend_seed():
    """Return a deterministic seed for MockBackend."""
    return 42


@pytest.fixture
def sample_search_args() -> str:
    """Return sample JSON arguments for search_trains."""
    return json.dumps({
        "origin": "Milano Centrale",
        "destination": "Roma Termini",
        "passengers": 2,
        "time": "14:30",
        "date": "today"
    })


@pytest.fixture
def sample_qa_pair() -> Dict[str, str]:
    """Return a sample QA pair."""
    return {
        "question": "Posso portare il cane sul treno?",
        "answer": "Sì, i cani di piccola taglia possono viaggiare gratuitamente in trasportino. I cani di taglia grande necessitano di biglietto ridotto.",
        "metadata": {
            "labels": [{"category": "policies", "subcategory": "pets"}],
            "entities": ["cane", "animali"],
            "contextual_tags": ["general_info"]
        }
    }


@pytest.fixture(autouse=True)
def reset_random_seed():
    """Reset random seed before each test for reproducibility."""
    import random
    random.seed(42)
    yield
    # Cleanup if needed


@pytest.fixture
def temp_config_file(tmp_path: Path) -> Path:
    """Create a temporary config.json file."""
    config = {
        "llm": {
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model": "qwen3:4b-instruct",
            "temperature": 0.1,
            "paraphrase_probability": 0.0  # Disabled for testing
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config, indent=2))
    return config_file


@pytest.fixture
def sample_jinja_template(tmp_path: Path) -> Path:
    """Create a sample Jinja2 template for testing."""
    template_content = """
{% for item in items %}
{"text": "Test {{ item }}", "intent": "test"}
{% endfor %}
"""
    template_file = tmp_path / "test_template.j2"
    template_file.write_text(template_content)
    return template_file
