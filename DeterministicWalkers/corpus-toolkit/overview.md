# Corpus Categorization Toolkit - Overview

## 📦 Contenuto del Toolkit

Questo toolkit ti fornisce tutto il necessario per **ri-categorizzare** il tuo corpus di conversazioni in modo strutturato per il tuo sistema modulare di customer care/vendita biglietti.

### File Principali

1. **corpus_categorizer.py** (19KB)
   - Script completo con ML e clustering semantico
   - Richiede: sentence-transformers, scikit-learn, pandas
   - Usa quando: corpus >5K frasi, necessità clustering

2. **simple_categorizer.py** (14KB)
   - Versione semplificata senza dipendenze ML
   - Zero installazioni richieste
   - Usa quando: inizi, corpus <10K frasi, quick test

3. **corpus_analysis.ipynb** (14KB)
   - Notebook Jupyter per analisi interattiva
   - Grafici, statistiche, validazione manuale
   - Usa quando: vuoi esplorare i risultati visualmente

### File di Supporto

4. **README.md** (5.5KB)
   - Documentazione tecnica completa
   - API reference, personalizzazione avanzata

5. **QUICKSTART.md** (7.5KB)
   - Guida rapida per iniziare in 5 minuti
   - Workflow consigliati, FAQ, troubleshooting

6. **config_categories.yaml** (9.5KB)
   - Configurazione dettagliata delle categorie
   - Esempi, pattern, descrizioni
   - Usalo come riferimento per personalizzare

### Esempi

7. **example_corpus.txt** (1.5KB)
   - 31 frasi di esempio
   - Test immediato dello script

8. **example_output/** (57KB)
   - Output pre-generato del corpus di esempio
   - Mostra la struttura finale dei risultati

---

## 🎯 Cosa Risolve Questo Toolkit

### Problema
Hai un corpus di conversazioni "scombinato" e vuoi organizzarlo in categorie funzionali per il tuo sistema modulare (saluto, richiesta, compra biglietto, ecc.).

### Soluzione
Il toolkit **categorizza automaticamente** ogni frase secondo:

1. **Categoria primaria** (8 tipi)
   - OPENING, INFORMATION_REQUEST, SPECIFICATION, NEGOTIATION
   - CONFIRMATION, TRANSACTION, PROBLEM_HANDLING, CLOSING

2. **Sottocategoria** (20+ tipi)
   - Es. INFORMATION_REQUEST → price, schedule, availability, options

3. **Attributi linguistici**
   - Register: formal/informal/neutral
   - Tone: neutral/urgent/frustrated
   - Completeness: complete/partial/vague
   - Complexity: simple/compound/complex

4. **Slot estratti** (7 tipi)
   - destination, date, time, ticket_type, passengers, class, price

---

## 📊 Output Strutturato

```
categorized_corpus/
├── full_corpus.json              # Corpus completo annotato
├── statistics.txt                # Report statistiche
│
├── opening/                      # Per ogni categoria primaria
│   ├── formal.json              # Per ogni sottocategoria
│   ├── informal.json
│   └── direct.json
│
├── information_request/
│   ├── availability.json
│   ├── price.json
│   └── ...
└── ...
```

Ogni frase ha questa struttura:
```json
{
  "id": "utt_0001",
  "text": "Cerco un treno per Milano domani",
  "primary_category": "INFORMATION_REQUEST",
  "sub_category": "availability",
  "confidence": 0.85,
  "attributes": {
    "register": "neutral",
    "completeness": "complete",
    "tone": "neutral",
    "complexity": "simple"
  },
  "extracted_slots": {
    "destination": "Milano",
    "date": "domani"
  }
}
```

---

## 🚀 Quick Start (3 Comandi)

```bash
# 1. Prova con l'esempio
python simple_categorizer.py example_corpus.txt test_run

# 2. Guarda i risultati
cat test_run/statistics.txt

# 3. Usa sul tuo corpus
python simple_categorizer.py tuo_corpus.txt output_finale
```

Fatto! Hai il tuo corpus categorizzato.

---

## 🔬 Base Scientifica

Il toolkit si basa sui framework identificati nella ricerca:

### 1. Dialogue Acts (DAMSL, ISO 24617-2)
- Categorie primarie mappano a standard dialogue acts
- INFORMATION_REQUEST → Request
- CONFIRMATION → Accept/Acknowledge
- Ecc.

### 2. Slot-Value Pairs (MultiWOZ)
- Estrazione automatica di informazioni strutturate
- Permette di tracciare lo stato del dialogo

### 3. Dialogue Flow States (TeleSalesCorpus)
- Opening → Need Discovery → Negotiation → Transaction → Closing
- Pattern naturale per vendita/customer care

### 4. Complexity Taxonomy (ChatGPT Studies)
- Attributi linguistici per differenziare livelli di difficoltà
- Utile per training progressivo del modello

---

## 🛠️ Personalizzazione

### Facile (5 minuti)
Modifica keywords/pattern esistenti in `simple_categorizer.py`:
```python
'OPENING': {
    'keywords': ['buongiorno', 'ciao', 'TUA_KEYWORD'],
    ...
}
```

### Media (15 minuti)
Aggiungi nuova categoria:
```python
self.categories['TUA_CATEGORIA'] = {
    'keywords': [...],
    'patterns': [r'regex'],
    'subcategories': [...]
}
```

### Avanzata (30+ minuti)
- Modifica logica sottocategorie (`get_subcategory()`)
- Aggiungi nuovi slot (`slot_patterns`)
- Personalizza attributi linguistici (`analyze_attributes()`)

---

## 📈 Workflow Consigliato

```
1. TEST
   python simple_categorizer.py example_corpus.txt test
   → Familiarizza con l'output

2. PRIMA ESECUZIONE
   python simple_categorizer.py tuo_corpus.txt run1
   → Categorizza il tuo corpus

3. VALIDAZIONE
   cat run1/statistics.txt
   → Controlla distribuzione categorie
   → Identifica problemi (bassa confidence, uncategorized)

4. ITERAZIONE
   → Modifica pattern/keywords per categorie problematiche
   python simple_categorizer.py tuo_corpus.txt run2
   → Ripeti finché soddisfatto

5. ANALISI APPROFONDITA
   jupyter notebook corpus_analysis.ipynb
   → Visualizza, esplora, valida

6. USO NEL SISTEMA
   → Integra i file JSON nel tuo sistema modulare
   → Campiona frasi per categoria quando costruisci scenari
```

---

## 💡 Quando Usare Quale File

| Scenario | File da Usare |
|----------|---------------|
| Prima volta, quick test | `simple_categorizer.py` + `example_corpus.txt` |
| Corpus <10K, produzione | `simple_categorizer.py` + tuo corpus |
| Corpus >10K, analisi profonda | `corpus_categorizer.py` + tuo corpus |
| Validazione risultati | `corpus_analysis.ipynb` |
| Capire le categorie | `config_categories.yaml` |
| Dubbi, troubleshooting | `QUICKSTART.md` |
| Personalizzazione avanzata | `README.md` |

---

## ✅ Vantaggi del Toolkit

1. **Zero Setup** (con simple_categorizer.py)
   - Funziona out-of-the-box, nessuna dipendenza

2. **Basato su Ricerca**
   - Usa framework validati (DAMSL, MultiWOZ, TeleSalesCorpus)
   - Non è "inventato", ma segue best practices

3. **Modulare**
   - Output già organizzato per categoria/sottocategoria
   - Pronto per il tuo sistema modulare

4. **Estensibile**
   - Aggiungi categorie, slot, pattern facilmente
   - Codice chiaro e commentato

5. **Validabile**
   - Confidence scores per ogni categorizzazione
   - Notebook per analisi visuale
   - Statistiche automatiche

---

## 📚 Prossimi Passi

1. ✅ **Inizia**: `python simple_categorizer.py example_corpus.txt test`
2. 📖 **Leggi**: `QUICKSTART.md` per workflow completo
3. 🔧 **Personalizza**: Modifica categorie per il tuo dominio
4. 📊 **Analizza**: Usa notebook per validazione
5. 🚀 **Integra**: Usa i JSON nel tuo sistema

---

## 🆘 Supporto

- **Quick help**: `QUICKSTART.md` → Sezione FAQ
- **Dettagli tecnici**: `README.md`
- **Esempi**: Guarda `example_output/` per capire la struttura
- **Configurazione**: `config_categories.yaml` per dettagli categorie

---

**Ready to go!** 🎉

Hai tutto ciò che serve per ri-categorizzare il tuo corpus e costruire un dataset modulare di alta qualità per il tuo sistema di customer care/vendita biglietti.