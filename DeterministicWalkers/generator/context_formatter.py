"""
Context Formatter Module

Converts context snapshot parameters into XML-formatted system messages
following the schema v1.2 defined in right_context.txt.
"""

import json


class ContextFormatter:
    """Formats context snapshots into XML system messages for LLM injection"""
    
    # Train type abbreviations
    TRAIN_TYPE_MAP = {
        "Frecciarossa": "FR",
        "Frecciargento": "FA",
        "Frecciabianca": "FB",
        "Intercity": "IC",
        "Intercity Notte": "ICN",
        "Regionale": "REG",
        "Regionale Veloce": "RV",
        "Italo": "IT"
    }
    
    @staticmethod
    def format_context(params: dict) -> str:
        """
        Main entry point: determines UI state and routes to appropriate formatter
        
        Args:
            params: dict from _snapshot_meta with keys:
                - origin: station name
                - ui_state: JSON string with state and can dict
                - trains_array: JSON string with train list
                - ctx_time: time HH:MM
                - date: date YYYY-MM-DD
                - ticket_info: JSON string or None
        
        Returns:
            XML-formatted string for system message
        """
        try:
            ui_state = json.loads(params.get("ui_state", '{"state": "idle"}'))
        except:
            ui_state = {"state": "idle", "can": {}}
        
        state = ui_state.get("state", "idle")
        
        if state == "idle":
            return ContextFormatter._format_search(params, ui_state)
        elif state == "results":
            return ContextFormatter._format_select(params, ui_state)
        elif state == "choosingSeat":
            return ContextFormatter._format_customize(params, ui_state)
        elif state == "purchased":
            return ContextFormatter._format_purchased(params, ui_state)
        else:
            # Default to search for unknown states
            return ContextFormatter._format_search(params, ui_state)
    
    @staticmethod
    def _format_search(params: dict, ui_state: dict) -> str:
        """Format search/idle phase with <ctx>, <ui>, <query>"""
        ctx_time = params.get("ctx_time", "12:00")
        date = params.get("date", "2026-01-29")
        origin = params.get("origin", "Unknown")
        
        # Build XML
        xml = f'<ctx v="1.2" date="{date}" time="{ctx_time}" station="{origin}" lang="it"/>\n\n'
        xml += f'<ui state="search" phase="init" actions="search,help,lang"/>\n\n'
        xml += f'<query from="{origin}" to="" date="" time="" pax="1"/>'
        
        return xml
    
    @staticmethod
    def _format_select(params: dict, ui_state: dict) -> str:
        """Format select phase with train listings <trains>"""
        ctx_time = params.get("ctx_time", "12:00")
        date = params.get("date", "2026-01-29")
        origin = params.get("origin", "Unknown")
        
        # Parse trains array
        try:
            trains = json.loads(params.get("trains_array", "[]"))
        except:
            trains = []
        
        # Extract destination from first train if available
        destination = trains[0].get("destination", "Unknown") if trains else "Unknown"
        
        # Build header comment  
        xml = '<!-- SCHEMA v1.2 | TRENI: dep=partenza, arr=arrivo, dur=minuti, chg=cambi | CLASSI: std=standard, prm=premium, bus=business, sil=silenzio, exe=executive | PREZZO: null=esaurito | BIKE: yes/no/cond | AZIONI: select=scegli, filter=filtra, back=indietro -->\n\n'
        
        # CTX block
        xml += f'<ctx v="1.2" date="{date}" time="{ctx_time}" station="{origin}" lang="it"/>\n\n'
        
        # UI block
        can_flags = ui_state.get("can", {})
        xml += f'<ui state="results" phase="choose_train" actions="select,filter,sort,back,help"/>\n\n'
        
        # QUERY block - extract search params from first train
        pax = "1"  # Default, could be extracted from context if available
        xml += f'<query from="{origin}" to="{destination}" date="{date}" time="{ctx_time}" pax="{pax}"/>\n\n'
        
        # TRAINS block
        train_count = len(trains)
        if train_count == 0:
            xml += '<trains count="0"/>'
        else:
            xml += f'<trains count="{train_count}">\n'
            
            for idx, train in enumerate(trains, 1):
                # Get train type abbreviation
                train_type = train.get("type", "REG")
                type_abbr = ContextFormatter.TRAIN_TYPE_MAP.get(train_type, train_type[:3].upper())
                
                # Extract times duration and changes
                dep = train.get("dep", "00:00")
                arr = train.get("arr", "00:00")
                dur = train.get("duration", 0)
                chg = train.get("changes", 0)
                train_id = train.get("id", f"TRAIN{idx}")
                
                # Bike status
                bike = "no"  # Default - could be enhanced
                
                xml += f'  <t pos="{idx}" id="{train_id}" dep="{dep}" arr="{arr}" dur="{dur}" type="{type_abbr}" chg="{chg}" bike="{bike}">\n'
                
                # Price elements
                price_val = train.get("price", "null")
                if price_val == "null" or price_val is None:
                    price_val = "null"
                
                #  Map class based on train type
                if type_abbr in ["FR", "FA", "FB"]:
                    xml += f'    <p class="std" v="{price_val}"/><p class="prm" v="null"/><p class="bus" v="null"/>\n'
                elif type_abbr == "IC":
                    xml += f'    <p class="2cl" v="{price_val}"/><p class="1cl" v="null"/>\n'
                else:  # REG
                    xml += f'    <p class="2cl" v="{price_val}"/>\n'
                
                xml += '  </t>\n'
            
            xml += '</trains>'
        
        return xml
    
    @staticmethod
    def _format_customize(params: dict, ui_state: dict) -> str:
        """Format customize phase with <selected>, <booking>, <availability>"""
        ctx_time = params.get("ctx_time", "12:00")
        date = params.get("date", "2026-01-29")
        origin = params.get("origin", "Unknown")
        
        # Parse trains to get selected train (assume first or extract from params)
        try:
            trains = json.loads(params.get("trains_array", "[]"))
            selected_train = trains[0] if trains else {}
        except:
            selected_train = {}
        
        train_id = selected_train.get("id", "TRAIN001")
        train_type = selected_train.get("type", "Frecciarossa")
        type_abbr = ContextFormatter.TRAIN_TYPE_MAP.get(train_type, "FR")
        dep = selected_train.get("dep", "00:00")
        arr = selected_train.get("arr", "00:00")
        destination = selected_train.get("destination", "Unknown")
        price = selected_train.get("price", "100.00")
        
        # Build XML
        xml = '<!-- SCHEMA v1.2 | SEAT: window=finestrino, aisle=corridoio | AZIONI: confirm=procedi, change_class=cambia, change_seat=cambia posto, back=indietro -->\n\n'
        
        xml += f'<ctx v="1.2" date="{date}" time="{ctx_time}" station="{origin}" lang="it"/>\n\n'
        xml += '<ui state="customize" phase="select_seats" actions="confirm,change_class,change_seat,back" timeout="180"/>\n\n'
        
        xml += f'<selected train="{train_id}" type="{type_abbr}" class="std" dep="{dep}" arr="{arr}" route="{origin}→{destination}" unit="{price}"/>\n\n'
        
        xml += '<booking pax="1" bikes="0" subtotal="' + str(price) + '">\n'
        xml += '  <pax id="1" seat="" pref="window"/>\n'
        xml += '</booking>\n\n'
        
        xml += '<availability car="4" class="std">\n'
        xml += '  <row n="5">A,B,C,D</row>\n'
        xml += '  <row n="6">A,B,C,D</row>\n'
        xml += '  <row n="7">B,C</row>\n'
        xml += '</availability>'
        
        return xml
    
    @staticmethod
    def _format_purchased(params: dict, ui_state: dict) -> str:
        """Format purchased phase with <ticket>, <station_info>"""
        ctx_time = params.get("ctx_time", "12:00")
        date = params.get("date", "2026-01-29")
        origin = params.get("origin", "Unknown")
        
        # Parse ticket info if available
        try:
            ticket_info = json.loads(params.get("ticket_info", "{}")) if params.get("ticket_info") else {}
        except:
            ticket_info = {}
        
        # Extract ticket details
        pnr = ticket_info.get("pnr", "ABCDEF")
        train_id = ticket_info.get("train_id", "TRAIN001")
        total = ticket_info.get("total", "100.00")
        
        # Build XML
        xml = '<!-- SCHEMA v1.2 | DELIVERY: print=stampa, sms=SMS, email=email | AZIONI: print, sms, email, new, help -->\n\n'
        
        xml += f'<ctx v="1.2" date="{date}" time="{ctx_time}" station="{origin}" lang="it"/>\n\n'
        xml += '<ui state="purchased" phase="delivery" actions="print,sms,email,new,help"/>\n\n'
        
        xml += '<booking pax="1" bikes="0">\n'
        xml += '  <pax id="1" seat="4A" car="4"/>\n'
        xml += '</booking>\n\n'
        
        xml += f'<ticket pnr="{pnr}" train="{train_id}" type="FR" class="std"\n'
        xml += f'        route="{origin}→Unknown" date="{date[-5:]}"\n'
        xml += f'        dep="00:00" arr="00:00" platform="pending"\n'
        xml += f'        total="{total}" delivery="pending"/>\n\n'
        
        xml += '<station_info>\n'
        xml += '  <platform n="1" access="scale mobili"/>\n'
        xml += '  <timing walk="5" boarding_opens="" boarding_closes=""/>\n'
        xml += '  <services wc="binario 1" bar="piano superiore"/>\n'
        xml += '</station_info>'
        
        return xml
