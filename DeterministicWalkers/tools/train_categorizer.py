
import sys
import os

# Add toolkit to path
toolkit_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'corpus-toolkit'))
sys.path.append(toolkit_path)

from corpus_categorizer import DialogueCorpusCategorizer
import re

class TrainAssistantCategorizer(DialogueCorpusCategorizer):
    def __init__(self):
        super().__init__()
        
        # --- Add New Categories ---
        
        self.categories['QA'] = {
            'keywords': ['rimborso', 'bagagli', 'animali', 'bici', 'sciopero', 'ritardo', 'cambio', 'regole', 'posso portare', 'dove trovo', 'come faccio'],
            'patterns': [
                r'\b(rimborso|bagagli|animali|bici|bicicletta|cane|gatto|sciopero|ritardo|cambio biglietto|regole)\b',
                r'posso portare .*',
                r'quanto costa .* (cane|bici|bagaglio)'
            ],
            'subcategories': ['policy', 'luggage', 'animals', 'disruption']
        }
        
        self.categories['NAVIGATION'] = {
            'keywords': ['menu', 'indietro', 'ricomincia', 'stop', 'aiuto', 'esci', 'home', 'inizio'],
            'patterns': [
                r'^(menu|indietro|ricomincia|stop|aiuto|esci|home|inizio)$',
                r'torna (indietro|al menu)',
                r'voglio ricominciare'
            ],
            'subcategories': ['navigation', 'help', 'exit']
        }
        
        self.categories['FEEDBACK'] = {
            'keywords': ['utile', 'inutile', 'bravo', 'ottimo', 'pessimo', 'grazie mille', 'non capisci', 'stupido'],
            'patterns': [
                r'\b(sei|stato) (utile|inutile|bravo|ottimo|pessimo)\b',
                r'non (capisci|funziona|serve a niente)',
                r'(ottimo|buon) lavoro'
            ],
            'subcategories': ['positive', 'negative']
        }

        self.categories['OOD'] = {
            'keywords': [
                'chi sei', 'come ti chiami', 'calcio', 'politica', 'scherzo', 'barzelletta',
                'finanza', 'investimenti', 'borsa', 'risparmi', 'azioni', 'economia',
                'medicine', 'dottore', 'mal di', 'curare', 'salute', 'rimedio', 'dieta',
                'storia', 'arte', 'chi è', 'capitale', 'nobel', 'vinto', 'squadra',
                'iphone', 'telefono', 'excel', 'computer', 'tecnologia',
                'elezioni', 'partito', 'governo', 'immigrazione', 'meteo'
            ],
            'patterns': [
                r'chi (sei|ha vinto|gioca|è|era|preferisci)',
                r'raccontami (una barzelletta|frase|storia)',
                r'parliamo di (altro|calcio|politica|arte|finanza|sport)',
                r'cosa (pensi|ne pensi) (di|del|della|degli)',
                r'come (funziona|si fa) (un|il|la) (mutuo|borsa|iphone|excel)',
                r'(consigli|consiglio) (per|su) (investire|dimagrire|curare)',
                r'(chi|quale) (vincerà|ha vinto)',
                r'problema (con|al) (telefono|ginocchio|schiena)'
            ],
            'subcategories': ['chitchat', 'irrelevant', 'rude_or_toxic'] # Grouping rude/chitchat here implicitly
        }
        
        # --- Refine Existing Categories ---
        
        # Make SEARCH_INTENT (INFO REQUEST) stricter about being an INITIAL request
        self.categories['INFORMATION_REQUEST']['patterns'] = [
            r'^(cerco|vorrei|voglio) (un )?treno',
            r'devo andare a \w+',
            r'orari(o)? per \w+',
            r'bigliett(o|i) per \w+'
        ]
        
    def get_subcategory(self, text: str, category: str) -> str:
        # Custom subcategory logic for new types
        text_lower = text.lower()
        
        if category == 'QA':
            if any(k in text_lower for k in ['bagagli', 'valigia']): return 'luggage'
            if any(k in text_lower for k in ['animali', 'cane', 'gatto']): return 'animals'
            if any(k in text_lower for k in ['sciopero', 'ritardo']): return 'disruption'
            return 'policy'
            
        elif category == 'NAVIGATION':
            if any(k in text_lower for k in ['aiuto']): return 'help'
            if any(k in text_lower for k in ['esci', 'stop']): return 'exit'
            return 'navigation'
            
        elif category == 'FEEDBACK':
            if any(k in text_lower for k in ['inutile', 'pessimo', 'stupido', 'non capisci']): return 'negative'
            return 'positive'
            
        elif category == 'OOD':
            # Basic heuristics
            if any(w in text_lower for w in ['stupido', 'idiota', 'cazzo', 'stronzo']): return 'rude_or_toxic'
            if any(w in text_lower for w in ['meteo', 'tempo', 'chiami', 'sei']): return 'chitchat'
            return 'irrelevant'
            
        return super().get_subcategory(text, category)

if __name__ == "__main__":
    # Quick Test
    cat = TrainAssistantCategorizer()
    test_sentences = [
        "Vorrei un treno per milano",
        "Quanto costa portare il cane?",
        "Tornare indietro",
        "Sei inutile",
        "Che tempo fa a Roma?"
    ]
    
    print("Test Categorization:")
    for s in test_sentences:
        res, conf = cat.categorize_by_patterns(s)
        sub = cat.get_subcategory(s, res) if res else None
        print(f"'{s}' -> {res} ({sub}) [{conf:.2f}]")
