import json
from pathlib import Path
from typing import Any, Dict, List
from core.scenario import Scenario
from core.random import SeededRandom

# --- Data Constants ---
CURRENT_DIR = Path(__file__).parent
RESOURCE_PATH = CURRENT_DIR.parent / "resources" / "stations.json"

try:
    with open(RESOURCE_PATH, 'r', encoding='utf-8') as f:
        STATIONS_DATA = json.load(f)
    STATIONS_ALL = []
    for category in STATIONS_DATA.values():
        STATIONS_ALL.extend(category)
    STATIONS_MAJOR = STATIONS_DATA.get("major", STATIONS_ALL[:20])
except FileNotFoundError:
    STATIONS_ALL = ["Roma Termini", "Milano Centrale"]
    STATIONS_MAJOR = STATIONS_ALL

QA_PAIRS = [
    # CartaFRECCIA
    ("Quali sono i livelli CartaFRECCIA e cosa offrono?", "😊 Ci sono 4 livelli CartaFRECCIA! 🙂 Base (gratuito): accumuli 1 punto/euro. Argento: accesso FRECCIAClub 4h prima, 10% sconto servizi. Oro: 2 accessi FRECCIAClub, upgrade gratuiti. Platino: lounge illimitata, fast track sicurezza, 2 accompagnatori gratis!"),
    ("Come funziona CartaFRECCIA? Quanti punti accumulo?", "😊 Con CartaFRECCIA accumuli 1 punto ogni euro speso sui treni Frecce! 🙂 Con 1000 punti hai un biglietto omaggio. Il livello base è gratuito, poi sali a Argento, Oro e Platino."),
    ("Ho il livello Argento, ci sono vantaggi extra?", "😄 Con Argento hai accesso alle sale FRECCIAClub 4 ore prima della partenza e sconti del 10% sui servizi di bordo. 🙂 Inoltre priorità nelle modifiche biglietto!"),

    # FRECCIAClub
    ("Che cos'è il FRECCIAClub e dove si trovano le sale?", "😊 Il FRECCIAClub è un circuito di sale esclusive che Trenitalia mette a disposizione dei propri clienti fidelizzati! 🙂 Le sale si trovano nelle principali stazioni AV come Milano Centrale e Roma Termini. Gli orari di apertura li trovi sul sito."),
    ("Come posso accedere alla FRECCIALounge? Devo pagare?", "😊 L'accesso è incluso con biglietto Executive o con CartaFRECCIA Oro/Platino! 🙂 Puoi anche acquistare un singolo accesso a 20€. 😄 Trovi WiFi, snack, bevande, quotidiani e un ambiente tranquillo."),
    
    # Rimborsi
    ("Se il treno è in ritardo, ho diritto al rimborso?", "😊 Sì! Per ritardi oltre 60 minuti hai diritto a un indennizzo. 🙂 25% del prezzo del biglietto per ritardi tra 60 e 119 minuti, 50% per ritardi superiori a 120 minuti. 😔 Per i regionali le condizioni sono diverse, verifica sul sito."),
    ("Se il mio treno arriva in ritardo, quanto mi rimborsano?", "😊 Per i treni Frecce e Intercity: 25% del biglietto per ritardi tra 60-119 minuti, 50% oltre i 120 minuti. 🙂 Puoi richiedere l'indennizzo online, via app o in biglietteria entro 12 mesi."),
    
    # Modifiche
    ("Posso cedere il mio biglietto a un'altra persona?", "😔 No, i biglietti nominativi Trenitalia non sono cedibili. 🙂 Puoi però cambiare il nome dell'intestatario una sola volta, pagando una piccola commissione, se fatto prima della partenza. 🤔 Solo per biglietti Base la modifica è gratuita!"),
    ("Qual è la differenza tra biglietto Base, Economy e Super Economy?", "😊 Base: il più flessibile, cambio e rimborso fino alla partenza. 🙂 Economy: prezzo ridotto, cambio con 10€ di penale, no rimborso. 😔 Super Economy: il più economico ma non modificabile né rimborsabile. 🤔 Scegli in base a quanto sei sicuro del viaggio!"),
    
    # Animali
    ("Posso portare il mio gatto sul Frecciarossa?", "😊 Certo! I gatti e i cani piccoli (max 10kg) viaggiano gratis se tenuti nel trasportino. 🙂 Per cani più grandi serve un biglietto a metà prezzo della seconda classe e devono avere guinzaglio e museruola. 😄 I cani guida viaggiano sempre gratis!"),
    ("Ho un labrador, posso portarlo sul Frecciarossa?", "😊 Certo che sì! Per i cani di taglia grande serve un biglietto dedicato al 50% del prezzo base seconda classe. 🙂 Deve stare al guinzaglio e con museruola, ma viaggia comodamente con te!"),
    
    # Bagagli
    ("Quanti bagagli posso portare a bordo gratuitamente?", "😊 Puoi portare gratuitamente un bagaglio a mano più uno di dimensioni standard (max 80x50x25 cm, 20 kg). 🙂 In pratica: trolley, zaino e borsetta vanno benissimo! 🤔 Per bagagli extra o fuori misura c'è il servizio Bagaglio Facile con spedizione separata."),
    ("C'è spazio per i bagagli grandi?", "😊 Sì, sulle carrozze Frecciarossa ci sono spazi appositi a inizio e fine carrozza per i bagagli voluminosi. 🙂 Inoltre c'è spazio nelle cappelliere per i trolley standard."),
    
    # Accessibilità
    ("Cosa sono le Sale Blu e come funzionano?", "😊 Le Sale Blu sono i centri di assistenza per viaggiatori con disabilità e mobilità ridotta. 🙂 Offrono aiuto all'imbarco/sbarco, accompagnamento in stazione e prenotazione posti riservati. 😄 Il servizio è gratuito! Prenota almeno 12 ore prima chiamando 800.90.60.60."),
    ("Viaggio in sedia a rotelle. Ci sono posti riservati sui treni?", "😊 Buongiorno! Certamente, tutti i treni Frecciarossa e Intercity hanno aree dedicate per passeggeri in carrozzina. 🙂 I posti sono prenotabili gratuitamente tramite le Sale Blu."),
    
    # Servizi Bordo
    ("C'è il WiFi gratuito sui treni Freccia?", "😊 Sì! Tutti i Frecciarossa, Frecciargento e Frecciabianca hanno WiFi gratuito. 🙂 In Prima Classe e Executive la connessione è potenziata per streaming e videochiamate. 😄 Ogni posto ha anche una presa elettrica per ricaricare i dispositivi!"),
    ("C'è il WiFi sui Frecciarossa? Devo lavorare durante il viaggio", "😊 Sì! Tutti i Frecciarossa hanno WiFi gratuito. 🙂 In Prima Classe la connessione è più veloce e stabile, ideale per lavorare."),
    
    # Bambini
    ("Ci sono sconti per bambini sui treni Freccia?", "😊 Sì, c'è lo sconto Bimbi Gratis! 🙂 Bambini da 0 a 14 anni viaggiano gratis sui treni Frecce se accompagnati da almeno un adulto pagante tariffa Base. 😄 Sotto i 4 anni se non occupano posto viaggiano sempre gratis."),
    ("Viaggio con i miei figli, 6 e 3 anni. Ci sono sconti per bambini?", "😊 Sì! I bambini sotto i 4 anni viaggiano gratis se non occupano un posto. 🙂 Dai 4 ai 14 anni c'è lo sconto Bimbi Gratis: viaggiano gratis con almeno un adulto pagante!")
]

class QA(Scenario):
    @property
    def name(self) -> str:
        return "qa"

    def generate(self, rng: SeededRandom, run_id: int, **kwargs) -> Dict[str, Any]:
        # 1. Setup Context
        origin = rng.choice(STATIONS_MAJOR)
        ctx_time = f"{rng.randint(6, 22):02d}:{rng.randint(0, 59):02d}"
        
        # 2. Pick Q&A Pair
        q, a = rng.choice(QA_PAIRS)
        
        # 3. Construct Messages
        system_content = "{{SYSTEM_PROMPT}}"
        
        # 4. Define Context (Only one, predicting the answer)
        # Length = 2 (System + User)
        ctx_qa = {
            "slice_length": 2,
            "params": {
                "origin": origin,
                "ctx_time": ctx_time,
                "date": "2025-12-23",
                "ui_state": '{"state":"idle","can":{"next":false,"prev":false,"back":false}}',
                "trains_array": "[]"
            }
        }
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]

        return {
            "tools": "{{TOOL_DEFINITION}}",
            "messages": messages,
            "_meta": {
                "scenario": self.name,
                "run_id": run_id,
                "contexts": [ctx_qa]
            }
        }
