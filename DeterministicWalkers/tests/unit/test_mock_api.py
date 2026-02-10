"""Tests for the MockBackend module."""
import pytest
import json
from generator.mock_api import MockBackend


class TestMockBackendDeterminism:
    """Test deterministic behavior of MockBackend."""

    def test_same_seed_produces_identical_results(self):
        """Test that same seed produces identical train results."""
        backend1 = MockBackend(seed=42)
        backend2 = MockBackend(seed=42)
        
        args = json.dumps({
            "origin": "Milano Centrale",
            "destination": "Roma Termini",
            "passengers": 2
        })
        
        result1 = json.loads(backend1.search_trains(args))
        result2 = json.loads(backend2.search_trains(args))
        
        assert result1 == result2, "Same seed should produce identical results"
        assert len(result1["trains"]) > 0

    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        backend1 = MockBackend(seed=42)
        backend2 = MockBackend(seed=99)
        
        args = json.dumps({
            "origin": "Milano Centrale",
            "destination": "Roma Termini",
            "passengers": 2
        })
        
        result1 = json.loads(backend1.search_trains(args))
        result2 = json.loads(backend2.search_trains(args))
        
        # Results should be different (at least prices or seat counts)
        assert result1 != result2


class TestSearchTrains:
    """Test the search_trains functionality."""

    @pytest.fixture
    def backend(self, mock_backend_seed):
        """Create a MockBackend instance."""
        return MockBackend(seed=mock_backend_seed)

    def test_search_trains_basic(self, backend):
        """Test basic train search."""
        args = json.dumps({
            "origin": "Milano Centrale",
            "destination": "Roma Termini",
            "passengers": 1
        })
        
        result = json.loads(backend.search_trains(args))
        
        assert "trains" in result
        assert isinstance(result["trains"], list)
        assert len(result["trains"]) > 0

    def test_search_trains_required_fields(self, backend):
        """Test that search results contain required fields."""
        args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 2
        })
        
        result = json.loads(backend.search_trains(args))
        trains = result["trains"]
        
        # Check first train has all required fields
        train = trains[0]
        required_fields = ["id", "type", "dep", "arr", "duration", "changes"]
        for field in required_fields:
            assert field in train, f"Train missing required field: {field}"

    def test_search_trains_with_time(self, backend):
        """Test search with specific time parameter."""
        args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 1,
            "time": "14:30"
        })
        
        result = json.loads(backend.search_trains(args))
        
        assert "trains" in result
        assert len(result["trains"]) > 0

    def test_search_trains_with_pets(self, backend):
        """Test search with pet parameters."""
        args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 1,
            "pet_small": 1,
            "pet_big": 0
        })
        
        result = json.loads(backend.search_trains(args))
        
        assert "trains" in result
        # Should still return results with pets

    def test_search_trains_with_bikes(self, backend):
        """Test search with bike parameters."""
        args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 1,
            "bike_normal": 1,
            "bike_foldable": 0
        })
        
        result = json.loads(backend.search_trains(args))
        
        assert "trains" in result
        # Bikes should be supported

    def test_search_trains_with_disability(self, backend):
        """Test search with disability parameter."""
        args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 1,
            "disability_type": "wheelchair"
        })
        
        result = json.loads(backend.search_trains(args))
        
        assert "trains" in result
        # Should handle disability parameter

    def test_search_trains_pagination(self, backend):
        """Test that search returns appropriate number of results."""
        args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 2
        })
        
        result = json.loads(backend.search_trains(args))
        trains = result["trains"]
        
        # Should return page_size trains (default 3)
        assert len(trains) <= backend.page_size


class TestPurchaseTicket:
    """Test the purchase_ticket functionality."""

    @pytest.fixture
    def backend(self, mock_backend_seed):
        """Create a MockBackend with search results."""
        backend = MockBackend(seed=mock_backend_seed)
        # Perform search first to populate results
        search_args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 2
        })
        backend.search_trains(search_args)
        return backend

    def test_purchase_ticket_initial_call(self, backend):
        """Test initial purchase call (train + class selection)."""
        args = json.dumps({
            "train_id": "FR9624",
            "class": "Standard"
        })
        
        result = json.loads(backend.purchase_ticket(args))
        
        assert "status" in result
        # Should request seat selection or proceed

    def test_purchase_ticket_with_seats(self, backend):
        """Test purchase with seat selection."""
        args = json.dumps({
            "train_id": "FR9624",
            "class": "Standard",
            "seats": ["12A", "12B"]
        })
        
        result = json.loads(backend.purchase_ticket(args))
        
        assert "status" in result

    def test_purchase_ticket_full_flow(self, backend):
        """Test complete purchase flow."""
        # Step 1: Train + Class
        args1 = json.dumps({"train_id": "FR9624", "class": "Standard"})
        result1 = json.loads(backend.purchase_ticket(args1))
        
        # Step 2: Add seats
        args2 = json.dumps({
            "train_id": "FR9624",
            "class": "Standard",
            "seats": ["12A", "12B"]
        })
        result2 = json.loads(backend.purchase_ticket(args2))
        
        # Step 3: Confirm with personal data
        args3 = json.dumps({
            "train_id": "FR9624",
            "class": "Standard",
            "seats": ["12A", "12B"],
            "confirm": True
        })
        result3 = json.loads(backend.purchase_ticket(args3))
        
        # Final result should have ticket info
        assert "status" in result3
        assert result3["status"] in ["complete", "success", "ticket_issued"]


class TestUIControl:
    """Test the ui_control functionality."""

    @pytest.fixture
    def backend(self, mock_backend_seed):
        """Create a MockBackend with search results."""
        backend = MockBackend(seed=mock_backend_seed)
        search_args = json.dumps({
            "origin": "Milano",
            "destination": "Roma",
            "passengers": 2
        })
        backend.search_trains(search_args)
        return backend

    def test_ui_control_next_page(self, backend):
        """Test pagination - next page."""
        args = json.dumps({"action": "next"})
        
        result = json.loads(backend.ui_control(args))
        
        assert "trains" in result or "status" in result

    def test_ui_control_prev_page(self, backend):
        """Test pagination - previous page."""
        # Go to next page first
        backend.ui_control(json.dumps({"action": "next"}))
        
        # Then go back
        args = json.dumps({"action": "prev"})
        result = json.loads(backend.ui_control(args))
        
        assert "trains" in result or "status" in result

    def test_ui_control_show_info_train(self, backend):
        """Test show_info for train details."""
        args = json.dumps({
            "action": "show_info",
            "target": "train",
            "train_position": 1
        })
        
        result = json.loads(backend.ui_control(args))
        
        assert "info" in result or "status" in result

    def test_ui_control_back_action(self, backend):
        """Test back action."""
        args = json.dumps({"action": "back"})
        
        result = json.loads(backend.ui_control(args))
        
        assert "status" in result


class TestMockBackendEdgeCases:
    """Edge case tests for MockBackend."""

    def test_search_with_invalid_json(self):
        """Test handling of invalid JSON input."""
        backend = MockBackend()
        
        # Should handle gracefully (return error or default)
        try:
            result = backend.search_trains("INVALID JSON")
            # If it doesn't raise, check it returns valid JSON
            json.loads(result)
        except (json.JSONDecodeError, ValueError):
            # Acceptable to raise error for invalid input
            pass

    def test_search_with_missing_params(self):
        """Test search with minimal parameters."""
        backend = MockBackend()
        args = json.dumps({"origin": "Milano"})
        
        # Should handle missing destination/passengers
        result = backend.search_trains(args)
        result_data = json.loads(result)
        
        # Should return some response (may be empty or error)
        assert isinstance(result_data, dict)

    def test_purchase_without_prior_search(self):
        """Test purchase attempt without prior search."""
        backend = MockBackend()
        args = json.dumps({"train_id": "FR9999", "class": "Standard"})
        
        result = backend.purchase_ticket(args)
        result_data = json.loads(result)
        
        # Should handle gracefully
        assert isinstance(result_data, dict)
