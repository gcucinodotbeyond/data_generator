import random
import json
from .base import DialogueStep

class SelectionPurchaseStep(DialogueStep):
    def execute(self, ctx, meta_contexts, **kwargs):
        try_interruption = kwargs.get("try_interruption")
        if not ctx.get("current_trains"):
            return

        # 1. INITIALIZATION & RANDOMIZATION
        target_index = random.choice(range(len(ctx['current_trains']))) if len(ctx["current_trains"]) > 1 else 0
        target_train = ctx["current_trains"][target_index]
        pos_map = ["primo", "secondo", "terzo"]
        pos_word = pos_map[target_index] if target_index < 3 else "questo"
        
        ctx["target_train"] = target_train
        ctx["position_word"] = pos_word

        # Deterministic class choice based on train prices
        available_classes = [p["class_denomination"] for p in target_train.get("classes", [])]
        chosen_class = random.choice(available_classes) if available_classes else "Standard"
        ctx["class"] = chosen_class
        
        cls_map = {"STANDARD": "std", "PREMIUM": "prm", "BUSINESS": "bus", "EXECUTIVE": "exe", "2ª CLASSE": "std", "1ª CLASSE": "prm", "ORDINARIA": "ord"}
        ctx["session_class"] = cls_map.get(chosen_class.upper(), "std")

        # --- PHASE 1: TRAIN & CLASS SELECTION ---
        provide_class_initially = random.random() < 0.5
        
        if provide_class_initially:
            # Case A: User provides both at once
            u_sel = self.turn_gen.render_utterance("refinement", ctx, train=target_train, aspect="train_plus_class", 
                                           position_word=pos_word, class_name=chosen_class)
            self.turn_gen.add_turn(ctx, "user", u_sel)
            
            call_id = self.turn_gen.get_next_call_id(ctx)
            args = {"train_id": target_train["id"], "class": chosen_class}
            tool_call = {
                "id": call_id, "type": "function",
                "function": {"name": "purchase_ticket", "arguments": json.dumps(args)}
            }
            resp_json = self.backend.purchase_ticket(json.dumps(args))
            resp_data_fin = json.loads(resp_json)
            self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call], tool_output=resp_json)
        else:
            # Case B: Two-step selection (Train then Class)
            u_sel = self.turn_gen.render_utterance("refinement", ctx, train=target_train, aspect="train", position_word=pos_word)
            self.turn_gen.add_turn(ctx, "user", u_sel)
            
            call_id = self.turn_gen.get_next_call_id(ctx)
            args_init = {"train_id": target_train["id"]}
            tool_call_init = {
                "id": call_id, "type": "function",
                "function": {"name": "purchase_ticket", "arguments": json.dumps(args_init)}
            }
            resp_json_init = self.backend.purchase_ticket(json.dumps(args_init))
            self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call_init], tool_output=resp_json_init)
            
            self.turn_gen.inject_system_context(ctx, meta_contexts)
            
            resp_ask_class = self.turn_gen.render_utterance("assistant_responses", ctx, category="class_prompt")
            self.turn_gen.add_turn(ctx, "assistant", resp_ask_class)
            
            if try_interruption: try_interruption(ctx)
            
            u_class = self.turn_gen.render_utterance("refinement", ctx, aspect="class", class_name=chosen_class)
            self.turn_gen.add_turn(ctx, "user", u_class)
            
            call_id_fin = self.turn_gen.get_next_call_id(ctx)
            args_fin = {"train_id": target_train["id"], "class": chosen_class}
            tool_call_fin = {
                "id": call_id_fin, "type": "function",
                "function": {"name": "purchase_ticket", "arguments": json.dumps(args_fin)}
            }
            resp_json_fin = self.backend.purchase_ticket(json.dumps(args_fin))
            resp_data_fin = json.loads(resp_json_fin)
            self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call_fin], tool_output=resp_json_fin)

        # --- PHASE 2: SEAT SELECTION ---
        ctx["ui_state"] = {"state": "customize", "phase": "select_seats", "actions": "next,back,confirm,change_class,change_seat,show_info", "page": "1/2"}

        auto_assigned = False
        if "resp_data_fin" in locals() and resp_data_fin.get("auto_assigned_seats"):
            auto_assigned = True
            assigned_seats = resp_data_fin.get("auto_assigned_seats")
            ctx["assigned_seats"] = assigned_seats
            ctx["assigned_carriage"] = resp_data_fin.get("auto_assigned_carriage", "5") 

        self.turn_gen.inject_system_context(ctx, meta_contexts) 
            
        if auto_assigned:
            if len(assigned_seats) > 1:
                seats_str = ", ".join(assigned_seats)
                resp_ask_seats = f"Posti {seats_str} in carrozza 5.\nConfermi? 😊"
            else:
                resp_ask_seats = f"Posto {assigned_seats[0]} in carrozza 5.\nConfermi? 😊"
        else:
            resp_ask_seats = self.turn_gen.render_utterance("assistant_responses", ctx, category="seat_prompt")
            
        self.turn_gen.add_turn(ctx, "assistant", resp_ask_seats)
        if try_interruption: try_interruption(ctx)
        
        if auto_assigned:
            u_seats = "Sì va bene." 
            chosen_seats = ",".join(assigned_seats)
        else:
            n_pax = ctx.get("passengers", 1)
            sel_seats = []
            letters = ["A", "B", "C", "D"]
            start = random.randint(1, 10)
            for i in range(n_pax):
                 sel_seats.append(f"{start}{letters[i%4]}")
            chosen_seats = ",".join(sel_seats)
            u_seats = self.turn_gen.render_utterance("refinement", ctx, aspect="seat_multiselect") 
            if not u_seats or "posto" not in u_seats.lower(): 
                 if n_pax > 1:
                     u_seats = f"Ho selezionato i posti {', '.join(sel_seats)} in carrozza 4"
                 else:
                     u_seats = f"Ho selezionato il posto {sel_seats[0]} in carrozza 4"
            
        self.turn_gen.add_turn(ctx, "user", u_seats)
        
        call_id_seats = self.turn_gen.get_next_call_id(ctx)
        args_seats = {"train_id": target_train["id"], "class": chosen_class, "seats": chosen_seats}
        args_seats["carriage"] = ctx.get("assigned_carriage", 4) if auto_assigned else 4
             
        tool_call_seats = {
            "id": call_id_seats, "type": "function",
            "function": {"name": "purchase_ticket", "arguments": json.dumps(args_seats)}
        }
        resp_json_seats = self.backend.purchase_ticket(json.dumps(args_seats))
        self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call_seats], tool_output=resp_json_seats)

        # --- PHASE 3: CONTACT DATA ---
        ctx["ui_state"] = {"state": "confirm", "phase": "input_contact", "actions": "back,show_info", "page": "1/2"}
        self.turn_gen.inject_system_context(ctx, meta_contexts)
        
        resp_ask_data = self.turn_gen.render_utterance("assistant_responses", ctx, category="ask_data")
        self.turn_gen.add_turn(ctx, "assistant", resp_ask_data)
        if try_interruption: try_interruption(ctx)
        
        u_confirm = self.turn_gen.render_utterance("confirmation", ctx)
        self.turn_gen.add_turn(ctx, "user", u_confirm)

        call_id_final = self.turn_gen.get_next_call_id(ctx)
        tool_call_final = {
            "id": call_id_final, "type": "function",
            "function": {"name": "purchase_ticket", "arguments": json.dumps(args_seats)}
        }
        resp_json_final = self.backend.purchase_ticket(json.dumps(args_seats))
        self.turn_gen.add_turn(ctx, "assistant", None, tool_calls=[tool_call_final], tool_output=resp_json_final)
        
        # --- PHASE 4: COMPLETION ---
        ctx["ticket_info"] = json.loads(resp_json_final)
        ctx["ui_state"] = {"state": "purchased", "phase": "delivery", "actions": "show_info,print,sms,email,new", "page": "1/2"}
        self.turn_gen.inject_system_context(ctx, meta_contexts)
        
        resp_handover = self.turn_gen.render_utterance("assistant_responses", ctx, category="ticket_handover")
        self.turn_gen.add_turn(ctx, "assistant", resp_handover)
