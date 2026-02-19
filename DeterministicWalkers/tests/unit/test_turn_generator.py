import pytest
import json
from unittest.mock import MagicMock
from generator.turns.turn_generator import TurnGenerator

@pytest.fixture
def mock_renderer():
    renderer = MagicMock()
    renderer.render.return_value = {"text": "Rendered message"}
    return renderer

@pytest.fixture
def turn_gen(mock_renderer):
    return TurnGenerator(renderer=mock_renderer)

def test_add_turn_user(turn_gen):
    ctx = {"generated_messages": []}
    turn_gen.add_turn(ctx, "user", "Hello")
    assert len(ctx["generated_messages"]) == 1
    assert ctx["generated_messages"][0] == {"role": "user", "content": "Hello"}

def test_add_turn_assistant_merge(turn_gen):
    ctx = {"generated_messages": [{"role": "assistant", "content": "Hello"}]}
    turn_gen.add_turn(ctx, "assistant", "World")
    assert len(ctx["generated_messages"]) == 1
    assert ctx["generated_messages"][0]["content"] == "Hello World"

def test_add_turn_assistant_no_merge(turn_gen):
    ctx = {"generated_messages": [{"role": "user", "content": "Hello"}]}
    turn_gen.add_turn(ctx, "assistant", "Hi")
    assert len(ctx["generated_messages"]) == 2
    assert ctx["generated_messages"][1]["role"] == "assistant"

def test_get_next_call_id(turn_gen):
    ctx = {}
    assert turn_gen.get_next_call_id(ctx) == "call_001"
    assert turn_gen.get_next_call_id(ctx) == "call_002"

def test_clean_temporal(turn_gen):
    assert turn_gen.clean_temporal("per il 15 del mese") == "15"
    assert turn_gen.clean_temporal("alle 10:00") == "10:00"

def test_render_utterance(turn_gen, mock_renderer):
    ctx = {"destination": "Roma"}
    text = turn_gen.render_utterance("greeting", ctx)
    assert text == "Rendered message"
    mock_renderer.render.assert_called_once()
    # Check if destinations was added to render_vars
    args, kwargs = mock_renderer.render.call_args
    assert args[0] == "greeting"
    assert args[1]["destinations"] == ["Roma"]
