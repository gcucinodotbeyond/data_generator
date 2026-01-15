from jinja2 import Template
import json

def test_jinja2_hydration():
    print("Testing Jinja2 Hydration Logic...")
    
    # 1. Define the exact template from resources/system_prompt.md
    template_content = """Sei Talìa, l'assistente virtuale di Trenitalia.
<ctx>
data: {{date}}
ora: {{ctx_time}}
stazione: {{origin}}
</ctx>

<ui>
{{ui_state}}
</ui>

<trains>
{{trains_array}}
</trains>"""

    # 2. Define a complete context
    params_complete = {
        "date": "2025-01-01",
        "ctx_time": "10:00",
        "origin": "Roma Termini",
        "ui_state": '{"state":"searching"}',
        "trains_array": '[{"id": "FR1000"}]'
    }
    
    # 3. Define a partial context to test defaults
    params_partial = {
        "date": "2025-02-02",
        # Missing ctx_time
        "origin": "Milano Centrale"
        # Missing ui_state, trains_array from explicit params
    }
    
    # Defaults (matching hydrate_dataset.py)
    defaults = {
         "origin": "UNKNOWN",
         "ctx_time": "12:00",
         "date": "2024-05-01",
         "ui_state": '{"state":"idle"}',
         "trains_array": "[]"
    }

    print("\n--- Test 1: Complete Context ---")
    try:
        t = Template(template_content)
        ctx = defaults.copy()
        ctx.update(params_complete)
        result = t.render(**ctx)
        print("Result Preview:")
        print(result)
        
        # Verify
        if "data: 2025-01-01" in result and "ora: 10:00" in result:
             print("Please check output: LOOKS GOOD")
        else:
             print("FAILURE")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Test 2: Partial Context (Defaults Validation) ---")
    try:
        ctx = defaults.copy()
        ctx.update(params_partial)
        result = t.render(**ctx)
        print("Result Preview:")
        print(result)
        
        # Verify defaults injection
        if "ora: 12:00" in result: # Default time
             print("Defaults Injection: SUCCESS")
        else:
             print("Defaults Injection: FAILURE")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_jinja2_hydration()
