
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from core.random import SeededRandom

class MessageBuilder:
    """Fluent interface for constructing conversation messages."""
    
    def __init__(self, predataset: bool = True):
        self.messages: List[Dict[str, Any]] = []
        self.predataset = predataset
        self.tool_call_counter = 0

    def generate_tool_call_id(self) -> str:
        """Generate a sequential tool call ID for this conversation."""
        self.tool_call_counter += 1
        return f"call_{self.tool_call_counter:03d}"
    
    def add_system(self, origin: Optional[str] = None, ctx_time: Optional[str] = None) -> 'MessageBuilder':
        """Add system message."""
        if self.predataset:
            content = "{{SYSTEM_PROMPT}}"
        else:
            # Hydrated system prompt placeholder (should usually use predataset for training generation)
            content = f"Sei Talìa, l'assistente virtuale di Trenitalia.\n<ctx>stazione: {origin}\nora: {ctx_time}\n</ctx>\n"
        
        self.messages.append({"role": "system", "content": content})
        return self
    
    def add_user(self, content: str) -> 'MessageBuilder':
        """Add user message."""
        self.messages.append({"role": "user", "content": content})
        return self
    
    def add_assistant(self, content: str) -> 'MessageBuilder':
        """Add assistant text message."""
        self.messages.append({"role": "assistant", "content": content})
        return self
    
    def add_assistant_with_tool(self, tool_call: Dict[str, Any]) -> 'MessageBuilder':
        """Add assistant message with tool call."""
        self.messages.append({
            "role": "assistant",
            "tool_calls": [tool_call],
            "content": None
        })
        return self
    
    def add_tool_response(self, content: str, tool_call_id: str, name: str) -> 'MessageBuilder':
        """Add tool response message."""
        self.messages.append({
            "role": "tool",
            "content": content,
            "tool_call_id": tool_call_id,
            "name": name
        })
        return self
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages."""
        return self.messages
    
    def current_length(self) -> int:
        """Get current message count."""
        return len(self.messages)


class ContextBuilder:
    """Build _meta.contexts entries."""
    
    def __init__(self, default_date: str = "2025-12-23"):
        self.contexts: List[Dict[str, Any]] = []
        self.default_date = default_date
    
    def add_context(
        self,
        slice_length: int,
        origin: str,
        ctx_time: Optional[str] = None,
        date: Optional[str] = None,
        ui_state: str = '{"state":"idle"}',
        trains_array: str = "[]",
        **extra_params
    ) -> 'ContextBuilder':
        """Add a context entry."""
        params = {
            "origin": origin,
            "ui_state": ui_state,
            "trains_array": trains_array
        }
        
        if ctx_time:
            params["ctx_time"] = ctx_time
        
        params["date"] = date if date is not None else self.default_date
        
        # Add any extra parameters
        params.update(extra_params)
        
        self.contexts.append({
            "slice_length": slice_length,
            "params": params
        })
        return self
    
    def get_contexts(self) -> List[Dict[str, Any]]:
        """Get all contexts."""
        return self.contexts


class ToolCallBuilder:
    """Build tool calls and responses using MockBackend."""
    
    @staticmethod
    def build_search_call(
        tool_call_id: str,
        origin: str,
        destination: str,
        date: str = "today",
        time: str = "now",
        passengers: int = 1
    ) -> Dict[str, Any]:
        """Build a search_trains tool call."""
        args = {
            "origin": origin,
            "destination": destination,
            "date": date,
            "time": time,
            "passengers": passengers
        }
        
        return {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "search_trains",
                "arguments": json.dumps(args)
            }
        }
    
    @staticmethod
    def build_purchase_call(
        tool_call_id: str,
        train_id: str,
        train_class: str = "Seconda Classe"
    ) -> Dict[str, Any]:
        """Build a purchase_ticket tool call."""
        args = {
            "train_id": train_id,
            "class": train_class
        }
        
        return {
            "id": tool_call_id,
            "type": "function",
            "function": {
                "name": "purchase_ticket",
                "arguments": json.dumps(args)
            }
        }
    
    @staticmethod
    def execute_search(rng: SeededRandom, run_id: int, tool_call: Dict[str, Any]) -> Tuple[str, List[Dict]]:
        """
        Execute search using MockBackend.
        
        Returns:
            (tool_response_json, trains_list)
        """
        # Lazy import to avoid circular dependencies
        import sys
        # Careful with path here. Builders is in scenarios/common/
        # mock_api is in root/
        root_path = Path(__file__).parent.parent.parent
        if str(root_path) not in sys.path:
             sys.path.append(str(root_path))
        from mock_api import MockBackend
        
        backend = MockBackend(seed=rng.seed + run_id)
        
        args_json = tool_call["function"]["arguments"]
        response_json = backend.search_trains(args_json)
        response_data = json.loads(response_json)
        trains = response_data.get("trains", [])
        
        return response_json, trains
    
    @staticmethod
    def execute_purchase(rng: SeededRandom, run_id: int, tool_call: Dict[str, Any]) -> str:
        """Execute purchase using MockBackend."""
        import sys
        root_path = Path(__file__).parent.parent.parent
        if str(root_path) not in sys.path:
             sys.path.append(str(root_path))
        from mock_api import MockBackend

        backend = MockBackend(seed=rng.seed + run_id)
        
        args_json = tool_call["function"]["arguments"]
        return backend.purchase_ticket(args_json)
