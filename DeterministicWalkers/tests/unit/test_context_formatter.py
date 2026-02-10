"""Tests for the ContextFormatter module."""
import pytest
import json
from generator.context_formatter import ContextFormatter


class TestContextFormatter:
    """Test suite for ContextFormatter class."""

    def test_format_context_search_state(self, sample_context_params):
        """Test formatting context in search state."""
        result = ContextFormatter.format_context(sample_context_params)
        
        # Basic structure assertions - XML starts after HTML comment
        assert "<!-- SCHEMA v1.7" in result
        assert "<ctx" in result
        assert "</ctx>" in result or "/>" in result  # Self-closing or full tag
        assert "<ui" in result
        assert "/>" in result  # Self-closing tags
        
        # Content assertions
        assert "Milano Centrale" in result
        assert "Roma Termini" in result
        assert 'state="search"' in result

    def test_format_context_with_trains(self, sample_context_params, sample_train):
        """Test formatting context with train results."""
        params = sample_context_params.copy()
        params["trains_array"] = json.dumps([sample_train])
        params["ui_state"] = '{"state": "results"}'
        
        result = ContextFormatter.format_context(params)
        
        assert "<trains" in result
        assert "FR9624" in result
        assert "Frecciarossa" in result or "FR" in result  # Abbreviated form

    def test_format_context_idle_state(self):
        """Test formatting context in idle state (initial)."""
        params = {
            "origin": "Milano Centrale",
            "destination": "",
            "travel_date": "",
            "travel_time": "",
            "passengers": "0",
            "ui_state": '{"state": "idle"}',
            "trains_array": "[]",
            "ctx_time": "10:00",
            "date": "2026-05-10",
            "ticket_info": None
        }
        
        result = ContextFormatter.format_context(params)
        
        assert 'state="search"' in result  # idle maps to search
        assert "<trains>" not in result  # No trains in search phase

    def test_format_context_with_passengers(self, sample_context_params):
        """Test that passenger count is correctly formatted."""
        params = sample_context_params.copy()
        params["passengers"] = "3"
        params["ui_state"] = '{"state": "customize"}'
        params["target_train"] = {
            "id": "FR9624",
            "type": "Frecciarossa",
            "dep": "08:30",
            "arr": "11:45"
        }
        
        result = ContextFormatter.format_context(params)
        
        # In customize/booking state, should have seat tags
        assert "<seat" in result or "pax=" in result

    def test_format_context_with_extras(self, sample_context_params):
        """Test formatting with pets and bikes."""
        params = sample_context_params.copy()
        params["pet_small"] = 1
        params["bike_normal"] = 1
        
        result = ContextFormatter.format_context(params)
        
        # Check for extras in context
        assert 'pets_small="1"' in result or 'pet_small="1"' in result
        assert 'bikes_normal="1"' in result or 'bike_normal="1"' in result

    def test_format_context_with_disability(self, sample_context_params):
        """Test A11Y context injection for disability."""
        params = sample_context_params.copy()
        params["disability_type"] = "wheelchair"
        params["a11y"] = "wheelchair"
        params["a11y_instruction"] = "Utente in sedia a rotelle"
        
        result = ContextFormatter.format_context(params)
        
        assert 'a11y="wheelchair"' in result
        assert "sedia a rotelle" in result.lower() or "wheelchair" in result.lower()

    def test_ctx_block_structure(self, sample_context_params):
        """Test the <ctx> block has correct structure."""
        result = ContextFormatter.format_context(sample_context_params)
        
        # Should have ctx tag (self-closing)
        assert "<ctx" in result
        assert "Milano Centrale" in result or 'station=' in result

    def test_ui_block_structure(self, sample_context_params):
        """Test the <ui> block has correct attributes."""
        result = ContextFormatter.format_context(sample_context_params)
        
        # UI block should exist
        assert "<ui " in result
        
        # Should have state attribute
        assert 'state=' in result

    def test_train_type_mapping(self, sample_context_params, sample_train):
        """Test that train types are correctly abbreviated."""
        params = sample_context_params.copy()
        
        # Test Frecciarossa -> FR
        train_fr = sample_train.copy()
        train_fr["type"] = "Frecciarossa"  
        params["trains_array"] = json.dumps([train_fr])
        params["ui_state"] = '{"state": "results"}'
        
        result = ContextFormatter.format_context(params)
        assert 'type="FR"' in result

    def test_empty_trains_array(self, sample_context_params):
        """Test handling of empty trains array."""
        params = sample_context_params.copy()
        params["trains_array"] = "[]"
        params["ui_state"] = '{"state": "results"}'
        
        result = ContextFormatter.format_context(params)
        
        # Should have trains block but empty
        assert '<trains total="0"' in result or "<trains" not in result

    def test_invalid_json_handling(self, sample_context_params):
        """Test that invalid JSON in params doesn't crash."""
        params = sample_context_params.copy()
        params["ui_state"] = "INVALID_JSON"
        
        # Should not raise exception - defaults to idle
        try:
            result = ContextFormatter.format_context(params)
            assert result is not None
            assert "<ctx" in result
        except Exception as e:
            pytest.fail(f"Should handle invalid JSON gracefully: {e}")


class TestContextFormatterEdgeCases:
    """Edge case tests for ContextFormatter."""

    def test_missing_required_params(self):
        """Test behavior with minimal/missing parameters."""
        params = {
            "origin": "Milano",
            "ui_state": '{"state": "idle"}'
        }
        
        # Should handle missing params gracefully
        result = ContextFormatter.format_context(params)
        assert result is not None
        assert "<ctx" in result

    def test_special_characters_in_station_names(self):
        """Test handling of special characters in station names."""
        params = {
            "origin": "L'Aquila",
            "destination": "Sant'Antioco",
            "ui_state": '{"state": "search"}',
            "trains_array": "[]",
            "ctx_time": "10:00",
            "date": "2026-01-01"
        }
        
        result = ContextFormatter.format_context(params)
        
        # Should properly escape or handle apostrophes
        assert "Aquila" in result
        assert "Antioco" in result

    def test_very_long_train_list(self, sample_train):
        """Test performance with many trains."""
        trains = [sample_train.copy() for _ in range(50)]
        for i, train in enumerate(trains):
            train["id"] = f"FR{9600 + i}"
        
        params = {
            "origin": "Milano",
            "destination": "Roma",
            "ui_state": '{"state": "results"}',
            "trains_array": json.dumps(trains),
            "ctx_time": "10:00",
            "date": "2026-01-01",
            "passengers": "1"
        }
        
        result = ContextFormatter.format_context(params)
        
        # Should handle large lists
        assert result is not None
        assert len(result) > 0
        assert '<trains total="50"' in result
