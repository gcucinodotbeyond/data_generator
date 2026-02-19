"""
Context Formatter Module

Converts context snapshot parameters into XML-formatted system messages
following the schema v1.7 defined in right_context.txt.
"""

import json
from generator.logger import get_logger

logger = get_logger(__name__)


class ContextFormatter:
    """Formats context snapshots into XML system messages for LLM injection"""
    
    TRAIN_TYPE_MAP = {
        "Frecciarossa": "FR", "Frecciargento": "FA", "Frecciabianca": "FB",
        "Intercity": "IC", "Intercity Notte": "ICN", "Regionale": "REG",
        "Regionale Veloce": "RV", "Italo": "IT"
    }

    CLASS_MAP = {
        "STANDARD": "std",
        "PREMIUM": "prm",
        "BUSINESS": "bus",
        "EXECUTIVE": "exe",
        "1ª CLASSE": "1cl",
        "2ª CLASSE": "2cl",
        "ORDINARIA": "ord",
        "SILENZIO": "sil",
        "SALOTTINO": "sal"
    }
    
    @staticmethod
    def format_context(params: dict) -> str:
        """Main entry point: determines UI state and routes to appropriate formatter"""
        try:
            ui = json.loads(params.get("ui_state", '{"state": "idle"}')) if params.get("ui_state") else {"state": "idle"}
        except (json.JSONDecodeError, TypeError):
            ui = {"state": "idle"}
        state = ui.get("state", "idle")
        formatters = {
            "idle": ContextFormatter._format_search,
            "search": ContextFormatter._format_search,
            "results": ContextFormatter._format_select,
            "select": ContextFormatter._format_select,
            "customize": ContextFormatter._format_customize,
            "confirm": ContextFormatter._format_confirm,
            "purchased": ContextFormatter._format_purchased
        }
        return formatters.get(state, ContextFormatter._format_search)(params, ui)

    @staticmethod
    def _ctx(params):
        a11y = params.get("a11y")
        a11y_instr = params.get("a11y_instruction")
        a11y_attr = f' a11y="{a11y}"' if a11y else ''
        a11y_instr_attr = f' a11y_instruction="{a11y_instr}"' if a11y_instr else ''
        return f'<ctx date="{params.get("date", "2026-01-29")}" time="{params.get("ctx_time", "12:00")}" station="{params.get("origin", "Unknown")}" lang="it"{a11y_attr}{a11y_instr_attr}/>\n\n'

    @staticmethod
    def _booking(params, state, tag_type, email="false", train_info=None):
        """
        Generates the <booking> block.
        state: pending|incomplete|complete
        train_info: dict with train details (train, type, class, dep, arr, route, unit)
        """
        pax = params.get("passengers", "0")
        try:
            n = int(pax)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid passengers value '{pax}': {e}. Defaulting to 0.")
            n = 0
        
        # Build inner tags (passengers/seats)
        inner_lines = []
        
        assigned = params.get("assigned_seats") or []
        carriage = params.get("assigned_carriage", "4") # Default mock if unknown
        
        # If we have assigned seats, use them. 
        # But ensure we respect passenger count 'n'. 
        # If assigned seats > n ?? or < n ??
        # Just loop n
        
        for i in range(1, n + 1):
            if i <= len(assigned):
                 seat_code = assigned[i-1]
                 inner_lines.append(f'  <seat pax="{i}" n="{seat_code}" car="{carriage}"/>')
            else:
                 # No seat assigned yet for this pax
                 inner_lines.append(f'  <seat pax="{i}" n="" car=""/>')
        
        inner = "\n".join(inner_lines)
        
        # Train attrs (inline in booking in v1.7)
        train_attrs = ""
        if train_info:
            train_attrs = (
                f' train="{train_info.get("id", "")}"'
                f' type="{train_info.get("type", "")}"'
                f' class="{train_info.get("class", "")}"'
                f' dep="{train_info.get("dep", "")}"'
                f' arr="{train_info.get("arr", "")}"'
                f' route="{train_info.get("route", "")}"'
                f' unit="{train_info.get("unit", "")}"'
            )

        # Extras logic
        extras_list = []
        if params.get("bike_normal"): extras_list.append(f'bikes_normal="{params.get("bike_normal")}"')
        if params.get("bike_foldable"): extras_list.append(f'bikes_foldable="{params.get("bike_foldable")}"')
        if params.get("pet_small"): extras_list.append(f'pets_small="{params.get("pet_small")}"')
        if params.get("pet_big"): extras_list.append(f'pets_big="{params.get("pet_big")}"')
        
        extras_str = ""
        if extras_list:
            extras_str = f'\n  <extras {" ".join(extras_list)}/>'

        # Subtotal (mock logic)
        subtotal = "0.00"
        if train_info and train_info.get("unit"):
            try:
                subtotal = f"{float(train_info['unit']) * n:.2f}"
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Failed to calculate subtotal: {e}. Using 0.00.")
                # subtotal already initialized to "0.00"

        return (
            f'<booking{train_attrs} pax="{pax}" data="{state}" subtotal="{subtotal}">\n'
            f'{inner}\n'
            f'  <contact email="{email}" phone="false"/>'
            f'{extras_str}\n'
            f'</booking>\n\n'
        )

    @staticmethod
    def _format_search(p, ui):
        xml = '<!-- SCHEMA v1.7 | AZIONI: search=cerca, show_info=informazioni -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += '<ui state="search" phase="init" actions="search,show_info"/>\n\n'
        
        q_from = p.get("origin", "U").strip()
        q_to = p.get("destination", "").strip()
        q_date = p.get("travel_date", "").strip()
        q_time = p.get("travel_time", "").strip()
        q_pax = str(p.get("passengers", "0")).strip()
        
        # Extras in query for search phase
        extras = []
        if p.get("bike_normal"): extras.append(f'bikes_normal="{p.get("bike_normal")}"')
        if p.get("bike_foldable"): extras.append(f'bikes_foldable="{p.get("bike_foldable")}"')
        if p.get("pet_small"): extras.append(f'pets_small="{p.get("pet_small")}"')
        if p.get("pet_big"): extras.append(f'pets_big="{p.get("pet_big")}"')
        
        extras_attr = (" " + " ".join(extras)) if extras else ""
        
        xml += f'<query from="{q_from}" to="{q_to}" date="{q_date}" time="{q_time}" pax="{q_pax}"{extras_attr}/>'
        return xml

    @staticmethod
    def _format_select(p, ui):
        t = json.loads(p.get("trains_array", "[]"))
        xml = '<!-- SCHEMA v1.7 | TRENI: dep=partenza, arr=arrivo, dur=minuti, chg=cambi | CLASSI: std=standard, prm=premium, bus=business, sil=silenzio, exe=executive | PREZZO: -=esaurito (inline) | BIKE: yes/no/cond | AZIONI: next=prossimi, show_info=informazioni, filter=filtra, search=nuova ricerca -->\n\n'
        xml += ContextFormatter._ctx(p)
        
        actions = [a for a in ["next", "prev"] if ui.get("can", {}).get(a)] + ["select", "filter", "back", "show_info"]
        xml += f'<ui state="select" phase="choose_train" actions="{",".join(actions)}" page="{ui.get("page", "1/1")}"/>\n\n'
        
        dest = p.get("destination", t[0].get("destination", "U") if t else "U")
        q_from = p.get("origin", "U").strip()
        xml += f'<query from="{q_from}" to="{dest}" date="{p.get("travel_date","")}" time="{p.get("travel_time","")}" pax="{p.get("passengers","0")}"/>\n\n'
        
        if not t: return xml + '<trains total="0"/>'
        
        xml += f'<trains total="{len(t)}" page="{ui.get("page", "1/1")}">\n'
        for i, tr in enumerate(t, 1):
            abbr = ContextFormatter.TRAIN_TYPE_MAP.get(tr.get("type"), "REG")
            # Bike logic: FR/FA=cond, ICN=no, others=yes
            if abbr in ["FR", "FA"]:
                bike = "cond"
            elif abbr == "ICN":
                bike = "no"
            else:
                bike = "yes"
                
            # Inline prices logic
            # mock_api renames 'classes' to 'price' in the output
            cl_list = tr.get("price") or tr.get("classes") or []
            price_attrs = []
            for cl in cl_list:
                c_name = cl.get("class_denomination", "").upper()
                c_abbr = ContextFormatter.CLASS_MAP.get(c_name, "2cl")
                price = cl.get("price", "-") 
                if price == "null" or price is None:
                    price = "-"
                # Check for float/int and format? It seems to be string in mock_api
                price_attrs.append(f'{c_abbr}="{price}"')
            
            p_str = " ".join(price_attrs)
            xml += f'  <t pos="{i}" id="{tr.get("id")}" dep="{tr.get("dep")}" arr="{tr.get("arr")}" dur="{tr.get("duration")}" type="{abbr}" chg="{tr.get("changes")}" bike="{bike}" {p_str}/>\n'
            
        return xml + '</trains>'

    @staticmethod
    def _format_customize(p, ui):
        t_arr = json.loads(p.get("trains_array", "[]"))
        t = p.get("target_train")
        if not t and t_arr: t = t_arr[0]
        elif not t: t = {}

        xml = '<!-- SCHEMA v1.7 | SEAT: window=finestrino, aisle=corridoio | AZIONI: confirm=procedi, change_class=cambia, change_seat=cambia posto, back=indietro -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += f'<ui state="customize" phase="select_seats" actions="back,confirm,change_class,change_seat,show_info" page="{ui.get("page", "1/1")}"/>\n\n'
        
        t_id = t.get("id", "UNKNOWN")
        abbr = ContextFormatter.TRAIN_TYPE_MAP.get(t.get("type"), "FR")
        cls = p.get("session_class", "std") or "std"
        
        # Price finding
        class_list = t.get("classes", [])
        price = None  # Changed from "null" string to None
        for cl in class_list:
            if cls.upper() in cl.get("class_denomination", "").upper():
                price = cl.get("price", None)
                break
        if price is None and class_list:
            price = class_list[0].get("price", None)

        train_info = {
            "id": t_id,
            "type": abbr,
            "class": cls,
            "dep": t.get("dep", "00:00"),
            "arr": t.get("arr", "00:00"),
            "route": f"{p.get('origin')}→{p.get('destination')}",
            "unit": price if price is not None else "0.00"  # Use "0.00" as fallback
        }
        
        xml += ContextFormatter._booking(p, "pending", "seat", train_info=train_info)
        
        # Free seats Logic
        # It must include the assigned seats if they are considered "yours" to change, or free to swap?
        # Usually 'free' means available to pick. If I hold 1A, it is effectively not free for others but free for me?
        # But if the UI shows the map, 1A is "Selected".
        # Context usually lists "free" seats.
        # Let's ensure our assigned seats are in the free list so the LLM knows they exist?
        # Or maybe LLM assumes if I have 1A, it's mine.
        # User request: "nel contesto i posti assegnati non risultano liberi" -> They SHOULD be listed as free/available.
        
        assigned = p.get("assigned_seats") or []
        # Mock base list
        base_free = ["1A","1B","1C","1D","2A","2B","3A","3C","4A","4B","4D","5A","6B"]
        # Union
        final_free_set = set(base_free) | set(assigned)
        # Sort for determinism
        final_free_list = sorted(list(final_free_set))
        free_str = ",".join(final_free_list)
        
        xml += f'<seats train="{t_id}" class="{cls}" free="{free_str}"/>'
        return xml

    @staticmethod
    def _format_confirm(p, ui):
        t = p.get("target_train") or {}
        xml = '<!-- SCHEMA v1.7 | AZIONI: back=indietro, show_info=informazioni -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += '<ui state="confirm" phase="input_contact" actions="back,show_info" page="1/2"/>\n\n'
        
        t_id = t.get("id", "UNKNOWN")
        abbr = ContextFormatter.TRAIN_TYPE_MAP.get(t.get("type"), "FR")
        cls = p.get("session_class", "std") or "std"
        
        # Basic price retrieval
        class_list = t.get("classes", [])
        price = class_list[0].get("price", "0.00") if class_list else "0.00"
        # Ensure price is not None or "null" string
        if price is None or price == "null":
            price = "0.00"

        train_info = {
            "id": t_id,
            "type": abbr,
            "class": cls,
            "dep": t.get("dep", "00:00"),
            "arr": t.get("arr", "00:00"),
            "route": f"{p.get('origin')}→{p.get('destination')}",
            "unit": price
        }

        xml += ContextFormatter._booking(p, "incomplete", "seat", train_info=train_info)
        return xml

    @staticmethod
    def _format_purchased(p, ui):
        ti = json.loads(p.get("ticket_info", "{}")) if p.get("ticket_info") else {}
        xml = '<!-- SCHEMA v1.7.1 | DELIVERY: print=stampa, sms=SMS, email=email | AZIONI: show_info, print, sms, email, new -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += f'<ui state="purchased" phase="delivery" actions="show_info,print,sms,email,new" page="{ui.get("page", "1/1")}"/>\n\n'
        
        # v1.7.1: <ticket> is the main block, containing all info.
        t_id = ti.get("train_id", "UNKNOWN")
        t_type = ContextFormatter.TRAIN_TYPE_MAP.get(ti.get("train_type"), "FR")
        pnr = ti.get("pnr", "XXXXXX")
        cls = ti.get("class", "std")
        route = f"{p.get('origin')}→{p.get('destination')}"
        date = p.get("date", "01/01")[-5:] 
        dep = ti.get("dep", "00:00")
        arr = ti.get("arr", "00:00")
        platform = ti.get("platform", "5")
        pax = p.get("passengers", "1")
        unit = ti.get("price", "0.00")
        total = ti.get("total", "0.00")
        
        extras_cost = "0"
        
        xml += (
            f'<ticket pnr="{pnr}" train="{t_id}" type="{t_type}" class="{cls}" '
            f'route="{route}" date="{date}" dep="{dep}" arr="{arr}" '
            f'platform="{platform}" pax="{pax}" unit="{unit}" extras="{extras_cost}" '
            f'total="{total}" delivery="pending">\n'
        )
        
        # Nested seats
        seat_list = ti.get("seats", [])
        car_val = ti.get("car", "4")
        if car_val == "None": car_val = "4" # Fallback if tool didn't return it
        
        if seat_list:
            for s in seat_list:
                xml += f'  <seat n="{s}" car="{car_val}"/>\n'
        else:
            # Fallback for len(n)
            try:
                n = int(pax)
            except (ValueError, TypeError) as e:
                logger.debug(f"Cannot parse pax for seat fallback: {e}. Using 1.")
                n = 1
            for i in range(1, n+1):
                xml += f'  <seat n="{5+i}A" car="{car_val}"/>\n'
            
        # Nested extras
        extras_list = []
        if p.get("bike_normal"): extras_list.append(f'bikes_normal="{p.get("bike_normal")}"')
        if p.get("bike_foldable"): extras_list.append(f'bikes_foldable="{p.get("bike_foldable")}"')
        if extras_list:
             xml += f'  <extras {" ".join(extras_list)}/>\n'
             
        xml += '</ticket>'
        
        return xml
