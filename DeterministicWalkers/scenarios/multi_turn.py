import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from core.scenario import Scenario
from core.random import SeededRandom

# --- Constants & Data ---
CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"

try:
    with open(RESOURCE_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
    STATIONS_ALL = sorted(list(set(STATIONS_ALL)))
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])
except FileNotFoundError:
    STATIONS_ALL = ["Roma Termini", "Milano Centrale", "Napoli Centrale", "Torino Porta Nuova", "Firenze SMN"]
    STATIONS_MAJOR = STATIONS_ALL

# Topics & Content (Golden Samples adapted)
TOPICS = {
    "luggage": {
        "weight": 0.10,
        "qa": [
            ("Quanti bagagli posso portare?", "😊 Puoi portare gratuitamente un bagaglio a mano e uno di dimensioni standard (max 80x50x25 cm). 🙂 Se hai trolley e zaino sei tranquillo!"),
            ("E se ho più bagagli?", "🙂 Per bagagli extra puoi usare il servizio Bagaglio Facile di Trenitalia o cercare spazi a fine carrozza."),
            ("Ci sono limiti di peso?", "😊 Non ci sono limiti rigidi di peso, ma devi essere in grado di movimentare i tuoi bagagli da solo.")
        ]
    },
    "accessibility": {
        "weight": 0.05,
        "qa": [
            ("Viaggio in sedia a rotelle, ci sono posti?", "😊 Certamente! Tutti i Frecciarossa hanno aree dedicate. 🙂 Puoi prenotare l'assistenza gratuita tramite Sala Blu."),
            ("Come prenoto l'assistenza?", "😊 Chiama la Sala Blu 12 ore prima o usa l'app Trenitalia. 🙂 L'assistenza salita/discesa è gratuita!"),
            ("Il bagno è accessibile?", "😊 Sì, tutte le carrozze con posti disabili hanno toilette attrezzate e accessibili.")
        ]
    },
    "pets": {
        "weight": 0.05,
        "qa": [
            ("Posso portare il mio cane?", "😊 Certo! Cani piccoli gratis nel trasportino, grandi con biglietto al 50%. 🙂 Devono avere guinzaglio e museruola."),
            ("Devo comprare un biglietto per il cane?", "😄 Sì, se è medio/grande paghi la metà del biglietto base. 🙂 Se piccolo e nel trasportino è gratis!"),
            ("Dove faccio il biglietto cane?", "😊 Puoi aggiungerlo qui o online prima del pagamento selezionando l'opzione 'Animali'.")
        ]
    },
    "services": {
        "weight": 0.20,
        "qa": [
            ("C'è il WiFi a bordo?", "😊 Sì, WiFi gratuito su tutti i Frecciarossa! 🙂 In Prima Classe è ancora più veloce."),
            ("C'è la carrozza ristorante?", "😄 Sì, trovi il Bar/Bistrot nella carrozza centrale con snack e bevande. 🙂"),
            ("Ci sono prese per caricare il telefono?", "😊 Assolutamente! Ogni sedile ha la sua presa di corrente o USB.")
        ]
    },
    "discounts": {
        "weight": 0.10,
        "qa": [
            ("Ci sono sconti per bambini?", "😊 Sì! Sotto i 4 anni gratis, dai 4 ai 14 anni sconto 50% con 'Bimbi Gratis'."),
            ("Come funziona CartaFRECCIA?", "😊 Accumuli punti per viaggi gratis e hai sconti dedicati. 🙂 L'iscrizione è gratuita!"),
            ("Sconti per giovani?", "😄 Certo, offerta Young per under 30 con sconti fino al 70%! 🙂")
        ]
    },
    "modifications": {
        "weight": 0.10,
        "qa": [
            ("Posso cambiare il biglietto se cambio idea?", "😊 Dipende dalla tariffa! Base modificabile sempre, Economy una volta sola. 🙂 Super Economy non è modificabile."),
            ("Se perdo il treno?", "😔 Se hai tariffa Base hai 1 ora di tempo per prendere il successivo (pagando sovrapprezzo). Altrimenti perdi il biglietto."),
            ("Posso chiedere il rimborso?", "🙂 Sì, per tariffa Base con trattenuta del 20% prima della partenza.")
        ]
    },
    "general": {
        "weight": 0.40,
        "qa": [
            ("Quanto tempo prima devo arrivare?", "😊 Consigliamo almeno 15-20 minuti prima per trovare il binario con calma. 🙂"),
            ("Dove trovo il mio binario?", "🤔 Controlla i tabelloni blu in stazione o l'app Trenitalia. Il binario esce 10 min prima."),
            ("Il biglietto va convalidato?", "🙂 Per i Frecciarossa con posto prenotato no. Per i Regionali cartacei sì, alle macchinette verdi!")
        ]
    }
}

TRANSITIONS_TO_SEARCH = [
    "Perfetto, grazie! Allora cerchiamo treni per {dest}",
    "Ottimo! Cerco un treno per {dest}",
    "Capito. Mi serve un biglietto per {dest}",
    "Grazie delle info. Ora vediamo i treni per {dest}",
    "Chiaro. Andiamo a {dest}"
]

TRANSITIONS_TO_QA = [
    "Un'altra cosa... {question}",
    "A proposito, {question}",
    "Già che ci sono, {question}",
    "Aspetta, {question}",
    "Ah, {question}"
]

class MultiTurn(Scenario):
    @property
    def name(self) -> str:
        return "multi_turn"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # 1. Setup
        origin = rng.choice(STATIONS_MAJOR)
        possible_dests = [s for s in STATIONS_ALL if s != origin]
        destination = rng.choice(possible_dests)
        
        # Select Pattern: 50% QA First, 50% Search First
        pattern = "qa_first" if rng.random() < 0.5 else "search_first"
        
        # Select Topic based on weights
        topic_keys = list(TOPICS.keys())
        topic_weights = [TOPICS[k]["weight"] for k in topic_keys]
        # Weighted choice logic
        r = rng.random()
        cumulative = 0
        selected_topic_key = "general"
        for i, w in enumerate(topic_weights):
            cumulative += w
            if r <= cumulative:
                selected_topic_key = topic_keys[i]
                break
        
        topic_data = TOPICS[selected_topic_key]
        qa_pairs = list(topic_data["qa"]) # Copy to avoid modifying original if we pop
        rng.shuffle(qa_pairs)
        
        messages = []
        contexts = []
        
        # Initial Context (System)
        system_content = "{{SYSTEM_PROMPT}}" # Will be hydrated
        messages.append({"role": "system", "content": system_content})
        
        # --- PREPARE SEARCH DATA ---
        date_str = "2025-12-25" # Mock
        time_str = f"{rng.randint(8, 20):02d}:00"
        
        tool_call_id = "call_search_01"
        search_args = {
            "origin": origin,
            "destination": destination,
            "date": "today",
            "time": "now",
            "passengers": 1
        }
        
        trains = [
            {"train_id": "FR9000", "departure_time": time_str, "arrival_time": "23:59", "train_type": "Frecciarossa", "price": [{"class_denomination": "Standard", "price": "50.00"}]}
        ]
        
        trains_json = json.dumps({"trains": trains})
        
        search_block = {
            "tool_call": {
                "id": tool_call_id,
                "type": "function",
                "function": {
                    "name": "search_trains",
                    "arguments": json.dumps(search_args)
                }
            },
            "tool_result": {
                "role": "tool",
                "content": trains_json,
                "tool_call_id": tool_call_id,
                "name": "search_trains"
            },
            "assistant_reply": f"😊 Ecco i treni per {destination}. Il primo parte alle {time_str}. 🙂"
        }

        # --- GENERATE FLOW ---
        
        if pattern == "qa_first":
            # Flow: QA -> QA -> Search
            # Decide how many QA pairs before search (1 or 2)
            num_qa = rng.randint(1, 2)
            
            # --- QA Phase ---
            for i in range(min(num_qa, len(qa_pairs))):
                q, a = qa_pairs[i]
                
                # Turn 1 context (if i==0)
                if i == 0:
                     contexts.append({
                        "slice_length": len(messages) + 1, # Predict Assistant answer
                        "params": {
                            "origin": origin,
                            "ctx_time": time_str,
                            "date": date_str,
                            "ui_state": '{"state":"idle"}',
                            "trains_array": "[]"
                        }
                    })
                
                messages.append({"role": "user", "content": q})
                messages.append({"role": "assistant", "content": a})
            
            # --- Transition to Search ---
            trans_template = rng.choice(TRANSITIONS_TO_SEARCH)
            user_search_msg = trans_template.format(dest=destination)
            
            contexts.append({
                "slice_length": len(messages) + 1, # Predict Assistant (Tool Call)
                "params": {
                    "origin": origin,
                    "ctx_time": time_str,
                    "ui_state": '{"state":"idle"}',
                    "trains_array": "[]"
                }
            })
            
            messages.append({"role": "user", "content": user_search_msg})
            messages.append({"role": "assistant", "tool_calls": [search_block["tool_call"]], "content": None})
            messages.append(search_block["tool_result"])
            messages.append({"role": "assistant", "content": search_block["assistant_reply"]})
            
        else:
            # Pattern: Search First -> QA
            
            # --- Search Phase ---
            user_search_msg = f"Vorrei andare a {destination}"
            
            contexts.append({
                "slice_length": len(messages) + 1,
                "params": {
                    "origin": origin,
                    "ctx_time": time_str,
                    "date": date_str,
                    "ui_state": '{"state":"idle"}',
                    "trains_array": "[]"
                }
            })
            
            messages.append({"role": "user", "content": user_search_msg})
            messages.append({"role": "assistant", "tool_calls": [search_block["tool_call"]], "content": None})
            messages.append(search_block["tool_result"])
            messages.append({"role": "assistant", "content": search_block["assistant_reply"]})
            
            # --- QA Phase ---
            num_qa = rng.randint(1, 2)
            for i in range(min(num_qa, len(qa_pairs))):
                q, a = qa_pairs[i]
                
                # Transition User Msg
                trans_template = rng.choice(TRANSITIONS_TO_QA)
                # Lowercase first letter of question for better flow integration
                q_text = q[0].lower() + q[1:]
                user_qa_msg = trans_template.format(question=q_text)
                
                contexts.append({
                    "slice_length": len(messages) + 1,
                    "params": {
                        "origin": origin,
                        "ui_state": '{"state":"results"}',
                        "trains_array": json.dumps([{"id":"result1"}]) # Mock visible
                    }
                })
                
                messages.append({"role": "user", "content": user_qa_msg})
                messages.append({"role": "assistant", "content": a})

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": contexts
            }
        }
