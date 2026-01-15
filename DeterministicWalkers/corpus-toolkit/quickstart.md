# Quick Start Guide - Corpus Categorizer

## 🚀 Avvio Rapido (5 minuti)

### Opzione 1: Versione Semplificata (senza ML)

```bash
# Usa subito lo script senza installare nulla
python simple_categorizer.py tuo_corpus.txt output_dir
```

**Vantaggi**: 
- Nessuna installazione richiesta
- Veloce e leggero
- Perfetto per corpus piccoli-medi (<10K frasi)

**Limitazioni**: 
- Solo pattern matching (no clustering semantico)
- Potrebbe avere confidence più bassa su frasi ambigue

### Opzione 2: Versione Completa (con ML)

```bash
# 1. Installa dipendenze (prima volta)
pip install sentence-transformers scikit-learn pandas --break-system-packages

# 2. Esegui con clustering semantico
python corpus_categorizer.py tuo_corpus.txt -c 20
```

**Vantaggi**:
- Clustering semantico automatico
- Migliore gestione di frasi ambigue
- Analisi più profonda

**Quando usarla**: Corpus grandi (>5K frasi), necessità di identificare pattern nascosti

---

## 📁 Preparazione Corpus

Il tuo file deve essere in uno di questi formati:

### Formato TXT (consigliato per semplicità)
```
Buongiorno, vorrei un biglietto
Quanto costa per Milano?
Ci sono treni disponibili?
...
```

### Formato JSON (consigliato se hai già metadata)
```json
[
  "Buongiorno, vorrei un biglietto",
  "Quanto costa per Milano?",
  ...
]
```

oppure:

```json
[
  {"text": "Buongiorno, vorrei un biglietto", "source": "call_001"},
  {"text": "Quanto costa per Milano?", "source": "chat_042"},
  ...
]
```

---

## 📊 Cosa Ottieni

```
categorized_corpus/
├── full_corpus.json              # ← TUTTO il corpus annotato
├── statistics.txt                # ← Statistiche rapide
│
├── opening/                      # Categorie organizzate
│   ├── formal.json
│   ├── informal.json
│   └── direct.json
│
├── information_request/
│   ├── availability.json
│   ├── price.json
│   ├── schedule.json
│   └── options.json
│
└── ... altre categorie
```

**Esempio di frase annotata**:
```json
{
  "id": "utt_0001",
  "text": "Cerco un treno per Milano domani mattina, possibilmente diretto",
  "primary_category": "INFORMATION_REQUEST",
  "sub_category": "availability",
  "confidence": 0.85,
  "attributes": {
    "register": "neutral",
    "completeness": "complete",
    "tone": "neutral",
    "complexity": "compound"
  },
  "extracted_slots": {
    "destination": "Milano",
    "date": "domani",
    "time": "mattina"
  }
}
```

---

## ✅ Test con Esempio

```bash
# Prova subito con il corpus di esempio incluso
python simple_categorizer.py example_corpus.txt my_test

# Guarda i risultati
cat my_test/statistics.txt
cat my_test/full_corpus.json | head -30
```

---

## 🔧 Personalizzazione Rapida

### Aggiungere una nuova categoria

Modifica `simple_categorizer.py` (o `corpus_categorizer.py`):

```python
self.categories['MIA_CATEGORIA'] = {
    'keywords': ['parola1', 'parola2'],
    'patterns': [r'\bpattern_regex\b'],
    'subcategories': ['subcat1', 'subcat2']
}
```

### Aggiungere un nuovo slot

```python
self.slot_patterns['mio_slot'] = r'pattern_regex_con_(gruppo_cattura)'
```

### Modificare gli attributi

Cerca il metodo `analyze_attributes()` e modifica la logica.

---

## 📈 Workflow Consigliato

1. **Prima esecuzione**: Usa `simple_categorizer.py` per vedere com'è il tuo corpus
   ```bash
   python simple_categorizer.py corpus.txt first_run
   ```

2. **Valida risultati**: Guarda `statistics.txt` e campioni casuali
   ```bash
   cat first_run/statistics.txt
   head -100 first_run/full_corpus.json
   ```

3. **Identifica problemi**: 
   - Categorie con poche frasi → aggiungi esempi al corpus
   - Bassa confidence → aggiungi pattern/keyword
   - Molte frasi non categorizzate → serve nuova categoria

4. **Itera**: Modifica pattern, riprocessa, valida

5. **Validazione finale**: Usa il notebook Jupyter per analisi approfondita
   ```bash
   jupyter notebook corpus_analysis.ipynb
   ```

---

## 🎯 Casi d'Uso

### Caso 1: Dataset di Training per Chatbot
**Obiettivo**: 10K frasi bilanciate per categoria

```bash
# Step 1: Categorizza
python simple_categorizer.py raw_corpus.txt categorized

# Step 2: Analizza bilanciamento (in Python)
import json
with open('categorized/full_corpus.json') as f:
    data = json.load(f)
    
from collections import Counter
counts = Counter(item['primary_category'] for item in data)
print(counts)  # Vedi se è bilanciato

# Step 3: Campiona per bilanciare
# (usa il notebook o scrivi script custom)
```

### Caso 2: Sistema Modulare con Template
**Obiettivo**: Usare frasi come template per generazione

```python
# Carica categoria specifica
import json
with open('categorized/opening/formal.json') as f:
    formal_openings = json.load(f)

# Usa per generare varianti
import random
template = random.choice(formal_openings)
print(f"Template: {template['text']}")
print(f"Slot disponibili: {template['extracted_slots']}")
```

### Caso 3: Analisi Pattern Conversazionali
**Obiettivo**: Capire come le persone interagiscono

```bash
# Usa versione completa con clustering
python corpus_categorizer.py corpus.txt analysis -c 25

# Analizza cluster nel notebook
jupyter notebook corpus_analysis.ipynb
# → Sezione 7: Analisi Cluster Semantici
```

---

## 💡 Tips & Tricks

- **Corpus sporco?** Pulisci prima: rimuovi duplicati, correggi typos evidenti
- **Troppi uncategorized?** Aggiungi categorie, non forzare tutto nelle esistenti
- **Confidence bassa?** Pattern troppo generici, raffina con regex più specifiche
- **Slot non trovati?** Verifica che i pattern regex matchino le tue frasi
- **Performance lenta?** Usa `simple_categorizer.py` o processa in batch

---

## 📚 File Inclusi

| File | Scopo |
|------|-------|
| `corpus_categorizer.py` | Script completo con ML (richiede dipendenze) |
| `simple_categorizer.py` | Script semplificato senza dipendenze |
| `config_categories.yaml` | Configurazione categorie (documentazione) |
| `README.md` | Documentazione completa |
| `corpus_analysis.ipynb` | Notebook per analisi interattiva |
| `example_corpus.txt` | Corpus di esempio (30 frasi) |
| `example_output/` | Output di esempio già processato |

---

## ❓ FAQ

**Q: Quale versione dello script devo usare?**  
A: Inizia con `simple_categorizer.py`. Se hai >5K frasi o vuoi clustering semantico, passa a `corpus_categorizer.py`.

**Q: Come valido che le categorie siano corrette?**  
A: Controlla manualmente un campione (10-20 frasi) per categoria. Se accuracy >80%, va bene.

**Q: Posso aggiungere le mie categorie?**  
A: Assolutamente! Modifica il dizionario `self.categories` nello script.

**Q: E se il mio corpus è in un'altra lingua?**  
A: Cambia keywords/pattern nel codice. Il modello ML (`corpus_categorizer.py`) supporta già 50+ lingue.

**Q: Quanto è accurato?**  
A: Con pattern ben definiti: 85-95%. Il clustering aiuta a identificare pattern mancanti.

---

## 🆘 Troubleshooting

| Problema | Soluzione |
|----------|-----------|
| `ModuleNotFoundError: sentence_transformers` | Usa `simple_categorizer.py` oppure installa con pip |
| "Molte frasi non categorizzate" | Aggiungi keywords/pattern o crea nuove categorie |
| "Confidence troppo bassa" | Pattern troppo generici, raffina regex |
| "Slot non estratti" | Verifica pattern regex con esempi del tuo corpus |
| Script lento su corpus grande | Processa in batch o usa `simple_categorizer.py` |

---

**Hai domande? Guarda il README.md completo per dettagli approfonditi!**