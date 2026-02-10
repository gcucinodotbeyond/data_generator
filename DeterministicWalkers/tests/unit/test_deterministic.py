"""Tests for the DeterministicGenerator module."""
import pytest
import json
from generator.deterministic import DeterministicGenerator


class TestDeterministicGenerator:
    """Test suite for DeterministicGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create a DeterministicGenerator instance."""
        return DeterministicGenerator()

    def test_generator_initialization(self, generator):
        """Test that generator initializes correctly."""
        assert generator is not None
        assert generator.env is not None
        assert hasattr(generator, 'destinations')
        assert len(generator.destinations) > 0

    def test_render_search_trains_intent(self, generator, sample_context):
        """Test rendering search_trains intent."""
        result = generator.render("search_trains", sample_context)
        
        assert "text" in result
        assert "intent" in result
        assert result["intent"] == "search_trains"
        assert "variables" in result
        assert "Roma" in result["text"] or "Milano" in result["text"]

    def test_render_greeting_intent(self, generator, sample_context):
        """Test rendering greeting intent."""
        result = generator.render("greeting", sample_context)
        
        assert "text" in result
        assert result["intent"] == "greeting"
        assert len(result["text"]) > 0

    def test_render_confirmation_intent(self, generator, sample_context):
        """Test rendering confirmation intent."""
        result = generator.render("confirmation", sample_context)
        
        assert "text" in result
        assert result["intent"] == "confirmation"

    def test_render_with_rudeness_polite(self, generator, sample_context):
        """Test that rudeness affects output."""
        context_polite = sample_context.copy()
        context_polite["rudeness"] = "polite"
        
        result = generator.render("search_trains", context_polite)
        
        assert "text" in result
        # Polite version should exist
        assert len(result["text"]) > 0

    def test_render_with_rudeness_rude(self, generator, sample_context):
        """Test rude template rendering."""
        context_rude = sample_context.copy()
        context_rude["rudeness"] = "rude"
        
        result = generator.render("search_trains", context_rude)
        
        assert "text" in result

    def test_render_assistant_response(self, generator, sample_context):
        """Test rendering assistant responses."""
        context = sample_context.copy()
        context["category"] = "search_success"
        context["n_trains"] = 5
        context["first_dep"] = "08:30"
        
        result = generator.render("assistant_responses", context)
        
        assert "text" in result
        assert len(result["text"]) > 0

    def test_render_refinement_passengers(self, generator, sample_context):
        """Test rendering passenger refinement."""
        context = sample_context.copy()
        context["aspect"] = "passengers"
        context["count"] = 2
        
        result = generator.render("refinement", context)
        
        assert "text" in result
        assert "2" in result["text"] or "due" in result["text"].lower()

    def test_render_refinement_with_pet(self, generator, sample_context):
        """Test rendering refinement with pet."""
        context = sample_context.copy()
        context["aspect"] = "passengers"
        context["count"] = 1
        context["pet_phrase"] = "un cane"
        
        result = generator.render("refinement", context)
        
        assert "text" in result
        assert "cane" in result["text"].lower()

    def test_render_refinement_with_bike(self, generator, sample_context):
        """Test rendering refinement with bike."""
        context = sample_context.copy()
        context["aspect"] = "passengers"
        context["count"] = 1
        context["bike_phrase"] = "la bici"
        
        result = generator.render("refinement", context)
        
        assert "text" in result
        assert "bici" in result["text"].lower()

    def test_render_disability_refinement(self, generator, sample_context):
        """Test rendering disability declaration."""
        context = sample_context.copy()
        context["aspect"] = "disability"
        context["disability_phrase"] = "sono in sedia a rotelle"
        
        result = generator.render("refinement", context)
        
        assert "text" in result
        assert "sedia a rotelle" in result["text"].lower()

    def test_render_nonexistent_intent(self, generator, sample_context):
        """Test handling of unknown intent."""
        result = generator.render("nonexistent_intent", sample_context)
        
        # Should return error message or default
        assert "text" in result
        assert "Error" in result["text"] or "not found" in result["text"]


class TestDeterministicGeneratorTemplates:
    """Test template loading and processing."""

    @pytest.fixture
    def generator(self):
        return DeterministicGenerator()

    def test_template_path_selection_polite(self, generator):
        """Test that polite templates are selected correctly."""
        path = generator._get_template_path("greetings.j2", "polite")
        assert "non-rude" in path

    def test_template_path_selection_rude(self, generator):
        """Test that rude templates are selected correctly."""
        path = generator._get_template_path("greetings.j2", "rude")
        assert "rude" in path

    def test_template_path_selection_neutral(self, generator):
        """Test that neutral defaults to non-rude."""
        path = generator._get_template_path("greetings.j2", "neutral")
        assert "non-rude" in path


class TestDeterministicGeneratorEdgeCases:
    """Edge case tests."""

    @pytest.fixture
    def generator(self):
        return DeterministicGenerator()

    def test_render_with_missing_variables(self, generator):
        """Test rendering with minimal context."""
        minimal_context = {"rudeness": "polite"}
        
        # Should handle missing destination/time gracefully
        result = generator.render("search_trains", minimal_context)
        assert "text" in result

    def test_render_with_none_values(self, generator):
        """Test rendering with None values in context."""
        context = {
            "destination": None,
            "time": None,
            "rudeness": "polite"
        }
        
        result = generator.render("search_trains", context)
        assert "text" in result

    def test_render_with_special_characters(self, generator):
        """Test handling of special characters in variables."""
        context = {
            "destination": "L'Aquila",
            "time": "14:30",
            "rudeness": "polite"
        }
        
        result = generator.render("search_trains", context)
        assert "text" in result
        assert "Aquila" in result["text"]
