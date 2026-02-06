import sys
import os
import json

# Add parent directory to path to import generator
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from generator.context_formatter import ContextFormatter

def run_verification():
    output = []
    output.append("=== VERIFYING SCHEMA v1.7 UPDATE ===\n")

    # 1. Search State
    output.append("--- 1. SEARCH STATE ---")
    p_search = {
        "ui_state": '{"state": "search"}',
        "origin": "Roma Termini",
        "date": "2026-02-06",
        "passengers": "2",
        "bike_normal": "1"
    }
    xml_search = ContextFormatter.format_context(p_search)
    output.append(xml_search)
    if 'SCHEMA v1.7' not in xml_search: output.append("FAIL: Schema version not updated")
    if 'bikes_normal="1"' not in xml_search: output.append("FAIL: Extras not in query")

    # 2. Select State (Inline Prices)
    output.append("\n--- 2. SELECT STATE (INLINE PRICES) ---")
    
    # Mock train data
    trains = [
          {
            "id": "FR9633",
            "type": "Frecciarossa",
            "dep": "10:00",
            "arr": "11:10",
            "duration": "70",
            "changes": "0",
            "destination": "Napoli Centrale",
            "classes": [
                {"class_denomination": "2ª CLASSE", "price": "45.00", "available_seats": 10},
                {"class_denomination": "1ª CLASSE", "price": "65.00", "available_seats": 5}
            ]
          }
    ]
    
    p_select = {
        "ui_state": '{"state": "select", "page": "1/1", "can": {"next": true}}',
        "origin": "Roma Termini",
        "destination": "Napoli Centrale",
        "trains_array": json.dumps(trains)
    }
    xml_select = ContextFormatter.format_context(p_select)
    output.append(xml_select)
    if '2cl="45.00"' not in xml_select: output.append("FAIL: Inline price for 2cl missing")
    if '1cl="65.00"' not in xml_select: output.append("FAIL: Inline price for 1cl missing")
    if 'bike="cond"' not in xml_select: output.append("FAIL: FR should have bike=cond")

    # 3. Customize State (No <selected>, check <booking>)
    output.append("\n--- 3. CUSTOMIZE STATE ---")
    target_train = trains[0]
    p_customize = {
        "ui_state": '{"state": "customize"}',
        "origin": "Roma Termini",
        "destination": "Napoli Centrale",
        "target_train": target_train,
        "session_class": "1cl",
        "passengers": "1"
    }
    xml_customize = ContextFormatter.format_context(p_customize)
    output.append(xml_customize)
    if '<selected' in xml_customize: output.append("FAIL: <selected> tag should be gone")
    if '<booking' not in xml_customize: output.append("FAIL: <booking> tag missing")
    if 'train="FR9633"' not in xml_customize: output.append("FAIL: booking tag missing train attr")

    # 4. Purchased State (New <ticket> structure)
    output.append("\n--- 4. PURCHASED STATE ---")
    ticket_info = {
        "pnr": "ABC1234",
        "train_id": "FR9633",
        "train_type": "Frecciarossa",
        "class": "1cl",
        "dep": "10:00",
        "arr": "11:10",
        "price": "65.00",
        "total": "65.00"
    }
    p_purchased = {
        "ui_state": '{"state": "purchased"}',
        "origin": "Roma Termini",
        "destination": "Napoli Centrale",
        "ticket_info": json.dumps(ticket_info),
        "passengers": "1",
        "date": "2026-02-06"
    }
    xml_purchased = ContextFormatter.format_context(p_purchased)
    output.append(xml_purchased)
    if 'SCHEMA v1.7.1' not in xml_purchased: output.append("FAIL: Header version mismatch")
    if '<ticket pnr="ABC1234"' not in xml_purchased: output.append("FAIL: <ticket> tag structure issue")
    
    output.append("\n=== VERIFICATION COMPLETE ===")

    with open("verify_output.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    run_verification()
