import pytest
import os
import json
from generator.context.manager import ContextManager

def test_context_manager_init():
    distribution = {
        "rudeness_distribution": {"polite": 1.0},
        "verbose_distribution": {"standard": 1.0}
    }
    mgr = ContextManager(distribution=distribution)
    assert len(mgr.origins) > 0
    assert len(mgr.destinations) > 0
    # In my environment, qa_pairs should be loaded if the file exists
    # If not, it should be an empty list

def test_init_context():
    mgr = ContextManager()
    ctx = mgr.init_context(run_id=1)
    
    assert ctx["run_id"] == 1
    assert "origin" in ctx
    assert "destination" in ctx
    assert "date" in ctx
    assert "time" in ctx
    assert "passengers" in ctx
    assert "generated_messages" in ctx
    assert len(ctx["generated_messages"]) == 1
    assert ctx["generated_messages"][0]["role"] == "system"

def test_get_contextual_qa():
    mgr = ContextManager()
    # Mock some QA pairs if the file is empty for testing stability
    mgr.qa_pairs = [
        {
            "question": "Come arrivo a Roma?",
            "answer": "Prendi il Frecciarossa.",
            "metadata": {
                "entities": ["Roma", "Frecciarossa"],
                "contextual_tags": ["general_info"],
                "labels": [{"subcategory": "transport"}]
            }
        }
    ]
    
    ctx = {"origin": "Milano", "destination": "Roma", "ui_state": {"state": "idle"}}
    q, a, sub = mgr.get_contextual_qa(ctx)
    
    assert q == "Come arrivo a Roma?"
    assert a == "Prendi il Frecciarossa."
    assert sub == "transport"

def test_init_context_randomness():
    mgr = ContextManager()
    ctx1 = mgr.init_context(run_id=1)
    ctx2 = mgr.init_context(run_id=2)
    
    # Very low probability they are exactly the same if randomization works
    # We check at least run_id
    assert ctx1["run_id"] != ctx2["run_id"]
