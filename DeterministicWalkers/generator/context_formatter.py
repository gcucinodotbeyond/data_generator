"""
Context Formatter Module

Converts context snapshot parameters into XML-formatted system messages
following the schema v1.5 defined in right_context.txt.
"""

import json


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
        ui = json.loads(params.get("ui_state", '{"state": "idle"}')) if params.get("ui_state") else {"state": "idle"}
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
    def _booking(params, state, tag, email="false"):
        pax = params.get("passengers", "0")
        try: n = int(pax)
        except: n = 0
    @staticmethod
    def _booking(params, state, tag, email="false"):
        pax = params.get("passengers", "0")
        try: n = int(pax)
        except: n = 0
        inner = "\n".join([f'  {tag.format(id=i)}' for i in range(1, n + 1)])
        return f'<booking pax="{pax}" data="{state}">\n{inner}\n  <contact email="{email}" phone="false"/>\n  <extras bike_normal="{params.get("bike_normal", 0)}" bike_foldable="{params.get("bike_foldable", 0)}" pet_small="{params.get("pet_small", 0)}" pet_big="{params.get("pet_big", 0)}" luggage="0"/>\n</booking>\n\n'

    @staticmethod
    def _format_search(p, ui):
        xml = '<!-- SCHEMA v1.5 | AZIONI: search=cerca, show_info=informazioni -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += '<ui state="search" phase="init" actions="search,show_info"/>\n\n'
        
        # Raw query info should reflect what's in session, not resolved ground truth
        q_from = p.get("origin", "U").strip()
        q_to = p.get("destination", "").strip()
        q_date = p.get("travel_date", "").strip()
        q_time = p.get("travel_time", "").strip()
        q_pax = str(p.get("passengers", "0")).strip()
        
        xml += f'<query from="{q_from}" to="{q_to}" date="{q_date}" time="{q_time}" pax="{q_pax}" bike_normal="{p.get("bike_normal", 0)}" bike_foldable="{p.get("bike_foldable", 0)}" pet_small="{p.get("pet_small", 0)}" pet_big="{p.get("pet_big", 0)}"/>'
        return xml

    @staticmethod
    def _format_select(p, ui):
        t = json.loads(p.get("trains_array", "[]"))
        xml = '<!-- SCHEMA v1.5 | TRENI: dep=arr=dur=chg | CLASSI: std=prm=bus=sil=exe | PREZZO: null=esaurito | BIKE: yes/no/cond | AZIONI: select= filter= back=indietro -->\n\n'
        xml += ContextFormatter._ctx(p)
        actions = [a for a in ["next", "prev"] if ui.get("can", {}).get(a)] + ["select", "filter", "back", "show_info"]
        xml += f'<ui state="select" phase="choose_train" actions="{",".join(actions)}" page="{ui.get("page", "1/1")}"/>\n\n'
        dest = p.get("destination", t[0].get("destination", "U") if t else "U")
        q_from = p.get("origin", "U").strip()
        q_to = dest.strip()
        q_date = p.get("travel_date", "").strip()
        q_time = p.get("travel_time", "").strip()
        q_pax = str(p.get("passengers", "0")).strip()
        xml += f'<query from="{q_from}" to="{q_to}" date="{q_date}" time="{q_time}" pax="{q_pax}" bike_normal="{p.get("bike_normal", 0)}" bike_foldable="{p.get("bike_foldable", 0)}" pet_small="{p.get("pet_small", 0)}" pet_big="{p.get("pet_big", 0)}"/>\n\n'
        if not t: return xml + '<trains total="0"/>'
        xml += f'<trains total="{len(t)}" page="{ui.get("page", "1/1")}">\n'
        for i, tr in enumerate(t, 1):
            abbr = ContextFormatter.TRAIN_TYPE_MAP.get(tr.get("type"), "REG")
            bike = "cond" if abbr in ["FR", "FA"] else ("no" if abbr == "ICN" else "yes")
            xml += f'  <t pos="{i}" id="{tr.get("id")}" dep="{tr.get("dep")}" arr="{tr.get("arr")}" dur="{tr.get("duration")}" type="{abbr}" chg="{tr.get("changes")}" bike="{bike}">\n    '
            # Extract classes and prices
            cl_list = tr.get("classes", [])
            p_tags = []
            for cl in cl_list:
                c_name = cl.get("class_denomination", "").upper()
                c_abbr = ContextFormatter.CLASS_MAP.get(c_name, "2cl")
                price = cl.get("price", "null")
                seats = cl.get("available_seats", "0")
                p_tags.append(f'<p class="{c_abbr}" v="{price}" s="{seats}"/>')
            
            xml += "".join(p_tags) + "\n  </t>\n"
        return xml + '</trains>'

    @staticmethod
    def _format_customize(p, ui):
        t_arr = json.loads(p.get("trains_array", "[]"))
        # Try to find target_train, otherwise default to first in list
        t = p.get("target_train")
        if not t and t_arr:
            t = t_arr[0]
        elif not t:
            t = {}

        xml = '<!-- SCHEMA v1.5 | SEAT: window=finestrino, aisle=corridoio | AZIONI: confirm=procedi, change_class=cambia, change_seat=cambia posto, back=indietro -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += f'<ui state="customize" phase="select_seats" actions="confirm,change_class,change_seat,back,show_info" page="{ui.get("page", "1/1")}"/>\n\n'
        
        t_id = t.get("id", "UNKNOWN")
        abbr = ContextFormatter.TRAIN_TYPE_MAP.get(t.get("type"), "FR")
        cls = p.get("session_class", "std") or "std"
        
        # Determine price for the selected class
        class_list = t.get("classes", [])
        price = "null"
        for cl in class_list:
            if cls.upper() in cl.get("class_denomination", "").upper():
                price = cl.get("price", "null")
                break
        if price == "null" and class_list:
            price = class_list[0].get("price", "null")

        xml += f'<selected train="{t_id}" type="{abbr}" class="{cls}" dep="{t.get("dep", "00:00")}" arr="{t.get("arr", "00:00")}" route="{p.get("origin")}→{p.get("destination")}" unit="{price}"/>\n\n'
        xml += ContextFormatter._booking(p, "pending", '<pax id="{id}" seat="" pref="window"/>')
        return xml + f'<seats train="{t_id}" class="{cls}" free="1A,1B,1C,1D,2A,2B,3A,3C,4A,4B,4D,5A,6B"/>'

    @staticmethod
    def _format_confirm(p, ui):
        t = p.get("target_train") or {}
        xml = '<!-- SCHEMA v1.5 | AZIONI: back=indietro, show_info=informazioni -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += '<ui state="confirm" phase="input_contact" actions="back,show_info" page="1/2"/>\n\n'
        
        t_id = t.get("id", "UNKNOWN")
        abbr = ContextFormatter.TRAIN_TYPE_MAP.get(t.get("type"), "FR")
        cls = p.get("session_class", "std") or "std"
        
        # Basic price retrieval
        class_list = t.get("classes", [])
        price = class_list[0].get("price", "0.00") if class_list else "0.00"

        xml += f'<selected train="{t_id}" type="{abbr}" class="{cls}" dep="{t.get("dep", "00:00")}" arr="{t.get("arr", "00:00")}" route="{p.get("origin")}→{p.get("destination")}" unit="{price}"/>\n\n'
        return xml + ContextFormatter._booking(p, "pending", '<seat pax="{id}" n="8C" car="4"/>')

    @staticmethod
    def _format_purchased(p, ui):
        ti = json.loads(p.get("ticket_info", "{}")) if p.get("ticket_info") else {}
        xml = '<!-- SCHEMA v1.5 | DELIVERY: print=stampa, sms=SMS, email=email | AZIONI: show_info, print, sms, email, new, help -->\n\n'
        xml += ContextFormatter._ctx(p)
        xml += f'<ui state="purchased" phase="delivery" actions="show_info,print,sms,email,new" page="{ui.get("page", "1/1")}"/>\n\n'
        xml += ContextFormatter._booking(p, "complete", '<pax id="{id}" seat="4A" car="4" />', "true")
        
        t_id = ti.get("train_id", "UNKNOWN")
        t_type = ContextFormatter.TRAIN_TYPE_MAP.get(ti.get("train_type"), "FR")
        
        xml += f'<ticket pnr="{ti.get("pnr")}" train="{t_id}" type="{t_type}" class="{ti.get("class", "std")}" route="{p.get("origin")}→{p.get("destination")}" date="{p.get("date")[-5:]}" dep="{ti.get("dep", "00:00")}" arr="{ti.get("arr", "00:00")}" platform="{ti.get("platform", "5")}" unit="{ti.get("price")}" extras="0" total="{ti.get("total")}" delivery="pending"/>\n\n'
        return xml + '<station_info>\n  <platform number="5" access="scale mobili"/>\n  <timing walk_minutes="5" boarding_opens="" boarding_closes=""/>\n  <services wc="binario 1" bar="piano superiore"/>\n</station_info>'
