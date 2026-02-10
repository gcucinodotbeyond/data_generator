"""Tests for the DataSetHydrator module."""
import pytest
import json
from pathlib import Path
from generator.hydrator import DataSetHydrator


class TestDataSetHydrator:
    """Test suite for DataSetHydrator class."""

    @pytest.fixture
    def sample_template(self, tmp_path):
        """Create a sample system prompt template."""
        template_content = """# System Prompt
Current time: {{ ctx_time }}
Date: {{ date }}
Origin: {{ origin }}
{% if ui_state_raw %}
UI State: {{ ui_state_raw.state }}
{% endif %}
"""
        template_file = tmp_path / "system_prompt.md"
        template_file.write_text(template_content)
        return template_file

    @pytest.fixture
    def sample_tools(self, tmp_path):
        """Create sample tools definition."""
        tools = {
            "tools": [
                {"name": "search_trains", "description": "Search for trains"}
            ]
        }
        tools_file = tmp_path / "tools.json"
        tools_file.write_text(json.dumps(tools))
        return tools_file

    def test_hydrator_initialization(self, sample_template):
        """Test hydrator initializes correctly."""
        hydrator = DataSetHydrator(sample_template)
        
        assert hydrator.template_path == sample_template
        assert hydrator.template_content is not None
        assert len(hydrator.template_content) > 0

    def test_hydrator_with_tools(self, sample_template, sample_tools):
        """Test hydrator loads tools correctly."""
        hydrator = DataSetHydrator(sample_template, tools_path=sample_tools)
        
        assert hydrator.tools_content is not None
        assert isinstance(hydrator.tools_content, list)
        assert len(hydrator.tools_content) > 0

    def test_hydrate_line_with_system_prompt(self, sample_template):
        """Test hydrating a line with system prompt placeholder."""
        hydrator = DataSetHydrator(sample_template)
        
        dialogue_line = json.dumps({
            "messages": [
                {"role": "system", "content": "{SYSTEM_PROMPT}"}
            ],
            "_meta": {
                "contexts": [{
                    "params": {
                        "origin": "Milano",
                        "ctx_time": "14:30",
                        "date": "2026-05-10",
                        "ui_state": '{"state": "idle"}'
                    }
                }]
            }
        })
        
        result = hydrator.hydrate_line(dialogue_line)
        result_data = json.loads(result)
        
        # System message should be hydrated
        system_msg = result_data["messages"][0]
        assert "Milano" in system_msg["content"]
        assert "14:30" in system_msg["content"]

    def test_hydrate_line_with_tools_placeholder(self, sample_template, sample_tools):
        """Test hydrating tools placeholder."""
        hydrator = DataSetHydrator(sample_template, tools_path=sample_tools)
        
        dialogue_line = json.dumps({
            "tools": "{{TOOL_DEFINITION}}",
            "messages": []
        })
        
        result = hydrator.hydrate_line(dialogue_line)
        result_data = json.loads(result)
        
        # Tools should be replaced
        assert result_data["tools"] != "{{TOOL_DEFINITION}}"
        assert isinstance(result_data["tools"], list)

    def test_hydrate_line_preserves_non_system_messages(self, sample_template):
        """Test that non-system messages are preserved."""
        hydrator = DataSetHydrator(sample_template)
        
        dialogue_line = json.dumps({
            "messages": [
                {"role": "user", "content": "Ciao"},
                {"role": "assistant", "content": "Buongiorno"}
            ]
        })
        
        result = hydrator.hydrate_line(dialogue_line)
        result_data = json.loads(result)
        
        assert len(result_data["messages"]) == 2
        assert result_data["messages"][0]["content"] == "Ciao"
        assert result_data["messages"][1]["content"] == "Buongiorno"

    def test_hydrate_removes_meta_when_requested(self, sample_template):
        """Test that _meta is removed when remove_meta=True."""
        hydrator = DataSetHydrator(sample_template, remove_meta=True)
        
        dialogue_line = json.dumps({
            "messages": [],
            "_meta": {"some": "data"}
        })
        
        result = hydrator.hydrate_line(dialogue_line)
        result_data = json.loads(result)
        
        assert "_meta" not in result_data

    def test_hydrate_preserves_meta_when_not_requested(self, sample_template):
        """Test that _meta is preserved by default."""
        hydrator = DataSetHydrator(sample_template, remove_meta=False)
        
        dialogue_line = json.dumps({
            "messages": [],
            "_meta": {"some": "data"}
        })
        
        result = hydrator.hydrate_line(dialogue_line)
        result_data = json.loads(result)
        
        assert "_meta" in result_data

    def test_prepare_params_converts_ui_state(self, sample_template):
        """Test that ui_state string is converted to dict."""
        hydrator = DataSetHydrator(sample_template)
        
        params = {
            "ui_state": '{"state": "search", "phase": "input_pax"}'
        }
        
        prepared = hydrator._prepare_params(params)
        
        assert "ui_state_raw" in prepared
        assert isinstance(prepared["ui_state_raw"], dict)
        assert prepared["ui_state_raw"]["state"] == "search"

    def test_process_file(self, sample_template, tmp_path):
        """Test processing an entire file."""
        hydrator = DataSetHydrator(sample_template)
        
        # Create input file
        input_file = tmp_path / "input.jsonl"
        input_file.write_text(json.dumps({
            "messages": [{"role": "system", "content": "{SYSTEM_PROMPT}"}],
            "_meta": {"contexts": [{
                "params": {
                    "origin": "Milano",
                    "ctx_time": "10:00",
                    "date": "2026-01-01",
                    "ui_state": '{"state": "idle"}'
                }
            }]}
        }) + "\n")
        
        output_file = tmp_path / "output.jsonl"
        
        count = hydrator.process_file(input_file, output_file)
        
        assert count == 1
        assert output_file.exists()
        
        # Verify output
        output_data = json.loads(output_file.read_text())
        assert "Milano" in output_data["messages"][0]["content"]


class TestDataSetHydratorEdgeCases:
    """Edge case tests for DataSetHydrator."""

    @pytest.fixture
    def sample_template(self, tmp_path):
        template_content = "Time: {{ ctx_time }}"
        template_file = tmp_path / "template.md"
        template_file.write_text(template_content)
        return template_file

    def test_hydrate_invalid_json_line(self, sample_template):
        """Test handling of invalid JSON."""
        hydrator = DataSetHydrator(sample_template)
        
        invalid_json = "THIS IS NOT JSON"
        result = hydrator.hydrate_line(invalid_json)
        
        # Should return original or handle gracefully
        assert result == invalid_json or result is not None

    def test_hydrate_line_with_missing_meta(self, sample_template):
        """Test hydrating line without _meta."""
        hydrator = DataSetHydrator(sample_template)
        
        dialogue_line = json.dumps({
            "messages": [{"role": "system", "content": "{SYSTEM_PROMPT}"}]
        })
        
        # Should handle missing _meta gracefully
        result = hydrator.hydrate_line(dialogue_line)
        assert result is not None

    def test_process_empty_file(self, sample_template, tmp_path):
        """Test processing an empty file."""
        hydrator = DataSetHydrator(sample_template)
        
        input_file = tmp_path / "empty.jsonl"
        input_file.write_text("")
        
        output_file = tmp_path / "output.jsonl"
        
        count = hydrator.process_file(input_file, output_file)
        
        assert count == 0
