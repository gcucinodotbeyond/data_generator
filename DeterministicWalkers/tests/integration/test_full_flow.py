import pytest
import json
import os
from generator.dialogue import DialogueGenerator

def test_full_dialogue_generation():
    """
    Integration test to ensure that the refactored DialogueGenerator
    runs a full scenario without errors and produces valid output.
    """
    # Initialize Generator
    # We might need to handle dependencies if they require files.
    # Assuming resources are in place as per existing project structure.
    
    # Use a fixed seed for reproducibility in internal components if possible, 
    # though DialogueGenerator init doesn't take a seed directly for everything.
    generator = DialogueGenerator()
    
    # Generate 1 dialogue
    try:
        dialogues = generator.generate_dialogues(count=1)
    except Exception as e:
        pytest.fail(f"Dialogue generation failed with exception: {e}")
        
    assert len(dialogues) == 1
    dialogue = dialogues[0]
    
    # Check structure
    assert "tools" in dialogue
    assert "messages" in dialogue
    assert "_meta" in dialogue
    
    messages = dialogue["messages"]
    assert len(messages) > 0, "Dialogue should have messages"
    
    # Check for expected turns
    # We expect at least a system message (injected w/ context) or greeting
    # The generator adds "user" and "assistant" turns.
    
    roles = [m["role"] for m in messages]
    assert "user" in roles
    assert "assistant" in roles
    
    # Check metadata
    meta = dialogue["_meta"]
    assert "scenario" in meta
    assert "run_id" in meta
    
    print(f"Generated scenario: {meta['scenario']}")
