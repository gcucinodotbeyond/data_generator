# Corpus Categorizer - Guida Rapida

## Installazione Dipendenze

```bash
pip install sentence-transformers scikit-learn pandas --break-system-packages
```

## Uso Base

### 1. Preparazione Corpus

Il tuo corpus può essere in due formati:

**Formato TXT** (una frase per riga):
```
Buongiorno, vorrei un biglietto
Quanto costa per Milano?
...
```

**Formato JSON** (lista di stringhe o oggetti):
```json
[
  "Buongiorno, vorrei un biglietto",
  {"text": "Quanto costa per Milano?", "metadata": "..."},
  ...
]
```

### 2. Esecuzione Script

```bash
# Uso base
python corpus_categorizer.py tuo_corpus.txt

# Con opzioni personalizzate
python corpus_categorizer.py tuo_corpus.txt -o output_directory -c 20
```

**Parametri:**
- `input_file`: File del corpus (.txt o .json) - OBBLIGATORIO
- `-o, --output`: Directory di output (default: categorized_corpus)
- `-c, --clusters`: Numero di cluster semantici (default: 15, 0 per disabilitare)

### 3. Test con Esempio

```bash
python corpus_categorizer.py example_corpus.txt
```

## Output

Lo script genera:

```
categorized_corpus/
├── full_corpus.json              # Corpus completo annotato
├── statistics.txt                # Statistiche dettagliate
├── opening/                      # Categoria OPENING
│   ├── formal.json
│   ├── informal.json
│   └── direct.json
├── information_request/          # Categoria INFORMATION_REQUEST
│   ├── availability.json
│   ├── price.json
│   ├── schedule.json
│   └── options.json
├── specification/
│   ├── time_constraint.json
│   ├── price_constraint.json
│   └── preferences.json
└── ...
```

## Struttura JSON Output

Ogni frase nel `full_corpus.json` ha questa struttura:

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
  },
  "semantic_cluster": 3
}
```

## Categorie Disponibili

### Categorie Primarie
1. **OPENING** - Saluti e aperture
   - formal, informal, direct

2. **INFORMATION_REQUEST** - Richieste di informazioni
   - availability, price, schedule, options

3. **SPECIFICATION** - Raffinamento requisiti
   - time_constraint, price_constraint, preferences, conditions

4. **NEGOTIATION** - Negoziazione e obiezioni
   - price_objection, time_objection, alternatives, compromise

5. **CONFIRMATION** - Conferme
   - positive, conditional, verification_request

6. **TRANSACTION** - Transazioni
   - purchase, payment, personal_data

7. **PROBLEM_HANDLING** - Gestione problemi
   - clarification, technical_issue, frustration

8. **CLOSING** - Chiusure
   - thanks, farewell, aborted

### Attributi Linguistici
- **register**: formal, neutral, informal, colloquial
- **completeness**: complete, partial, vague
- **tone**: neutral, urgent, frustrated, uncertain, satisfied
- **complexity**: simple, compound, complex

### Slot Estratti
- destination (città destinazione)
- date (data viaggio)
- time (orario/fascia oraria)
- ticket_type (andata/ritorno)
- passengers (numero passeggeri)
- class (prima/seconda classe)
- price (prezzo)

## Personalizzazione

### Aggiungere Nuove Categorie

Modifica il dizionario `self.categories` in `DialogueCorpusCategorizer.__init__()`:

```python
self.categories['TUA_CATEGORIA'] = {
    'keywords': ['parola1', 'parola2'],
    'patterns': [r'regex_pattern'],
    'subcategories': ['subcat1', 'subcat2']
}
```

### Aggiungere Nuovi Slot

Modifica `self.slot_patterns`:

```python
self.slot_patterns['nuovo_slot'] = r'pattern_regex'
```

### Modificare Logica Sottocategorie

Estendi il metodo `get_subcategory()` con la tua logica.

## Uso Programmatico

```python
from corpus_categorizer import DialogueCorpusCategorizer

# Inizializza
categorizer = DialogueCorpusCategorizer()

# Carica corpus
sentences = categorizer.load_corpus('tuo_corpus.txt')

# Categorizza
results = categorizer.categorize_corpus(sentences)

# Export
categorizer.export_categorized_corpus(results, 'output_dir')

# Oppure usa i risultati direttamente
for item in results:
    print(f"{item['text']} -> {item['primary_category']}")
```

## Suggerimenti per Risultati Migliori

1. **Pulisci il corpus**: Rimuovi duplicati, frasi incomplete, errori di battitura
2. **Valida manualmente**: Controlla un campione di risultati per ogni categoria
3. **Itera**: Aggiungi pattern/keyword per categorie con bassa confidence
4. **Bilancia**: Se una categoria ha troppi pochi esempi, aggiungi frasi al corpus originale
5. **Clustering semantico**: Usa i cluster per identificare pattern non catturati dalle regole

## Troubleshooting

**Problema**: Molte frasi "uncategorized"
- Soluzione: Aggiungi più keyword/pattern alle categorie esistenti o crea nuove categorie

**Problema**: Bassa confidence
- Soluzione: Pattern troppo generici, raffina con regex più specifiche

**Problema**: Slot non estratti correttamente
- Soluzione: Verifica e adatta i pattern regex per il tuo dominio specifico

**Problema**: Out of memory durante clustering
- Soluzione: Riduci il numero di cluster o processa il corpus in batch