#!/usr/bin/env python3
"""
Versione semplificata del categorizzatore (senza dipendenze di ML)
Usa solo pattern matching e regole per la categorizzazione
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


class SimpleCategorizer:
    """Categorizzatore basato su pattern senza dipendenze ML"""
    
    def __init__(self):
        # Definizione tassonomia categorie (stesso dello script principale)
        self.categories = {
            'OPENING': {
                'keywords': ['buongiorno', 'salve', 'ciao', 'buonasera', 'saluti'],
                'patterns': [r'^(buongiorno|salve|ciao|buonasera|saluti)', r'vorrei informazioni'],
                'subcategories': ['formal', 'informal', 'direct']
            },
            'INFORMATION_REQUEST': {
                'keywords': ['quanto costa', 'che orari', 'ci sono', 'disponibilità', 'quando parte', 'a che ora'],
                'patterns': [r'\b(quanto|che|quali|ci sono|disponibilità|orari?)\b', r'\?$'],
                'subcategories': ['availability', 'price', 'schedule', 'options']
            },
            'SPECIFICATION': {
                'keywords': ['preferibilmente', 'possibilmente', 'se possibile', 'meglio', 'vorrei'],
                'patterns': [r'\b(preferi[a-z]+|possibilmente|se possibile|meglio|vorrei)\b'],
                'subcategories': ['time_constraint', 'price_constraint', 'preferences', 'conditions']
            },
            'NEGOTIATION': {
                'keywords': ['troppo', 'caro', 'altro', 'alternativa', 'sconto', 'meno'],
                'patterns': [r'\b(troppo|caro|costoso|altro|alternativa|sconto|meno)\b'],
                'subcategories': ['price_objection', 'time_objection', 'alternatives', 'compromise']
            },
            'CONFIRMATION': {
                'keywords': ['sì', 'va bene', 'ok', 'perfetto', 'd\'accordo', 'confermo'],
                'patterns': [r'\b(sì|si|va bene|ok|okay|perfetto|d\'accordo|confermo)\b'],
                'subcategories': ['positive', 'conditional', 'verification_request']
            },
            'TRANSACTION': {
                'keywords': ['prenoto', 'acquisto', 'compro', 'prendo', 'pagamento', 'carta'],
                'patterns': [r'\b(prenot[ao]|acquist[ao]|compr[ao]|prend[ao]|pagamento|carta)\b'],
                'subcategories': ['purchase', 'payment', 'personal_data']
            },
            'PROBLEM_HANDLING': {
                'keywords': ['problema', 'errore', 'non funziona', 'non capisco', 'aiuto'],
                'patterns': [r'\b(problema|errore|non funziona|non capisco|aiuto|difficoltà)\b'],
                'subcategories': ['clarification', 'technical_issue', 'frustration']
            },
            'CLOSING': {
                'keywords': ['grazie', 'arrivederci', 'buona giornata', 'ciao', 'perfetto'],
                'patterns': [r'\b(grazie|arrivederci|buona giornata|saluti|ciao)\b.*$'],
                'subcategories': ['thanks', 'farewell', 'aborted']
            }
        }
        
        # Pattern per estrazione slot
        self.slot_patterns = {
            'destination': r'\b(per|a|verso)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            'date': r'\b(oggi|domani|dopodomani|lunedì|martedì|mercoledì|giovedì|venerdì|sabato|domenica|\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b',
            'time': r'\b(mattina|pomeriggio|sera|notte|\d{1,2}:\d{2}|alle\s+\d{1,2})\b',
            'ticket_type': r'\b(andata|ritorno|andata-ritorno|solo andata)\b',
            'passengers': r'\b(\d+)\s+(persone|passeggeri|biglietti?)\b',
            'class': r'\b(prima|seconda)\s+classe\b',
            'price': r'\b(\d+)\s*€\b'
        }
    
    def load_corpus(self, filepath: str) -> List[str]:
        """Carica il corpus da file"""
        path = Path(filepath)
        
        if path.suffix == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        elif path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [item if isinstance(item, str) else item.get('text', '') 
                           for item in data]
        else:
            raise ValueError(f"Formato file non supportato: {path.suffix}")
    
    def categorize_by_patterns(self, text: str) -> Tuple[Optional[str], float]:
        """Categorizza una frase usando pattern e keyword matching"""
        text_lower = text.lower()
        scores = {}
        
        for category, info in self.categories.items():
            score = 0.0
            
            # Check keywords
            for keyword in info['keywords']:
                if keyword in text_lower:
                    score += 1.0
            
            # Check patterns
            for pattern in info['patterns']:
                if re.search(pattern, text_lower):
                    score += 2.0
            
            if score > 0:
                scores[category] = score
        
        if not scores:
            return None, 0.0
        
        best_category = max(scores, key=scores.get)
        max_score = scores[best_category]
        confidence = min(max_score / 3.0, 1.0)
        
        return best_category, confidence
    
    def get_subcategory(self, text: str, category: str) -> Optional[str]:
        """Determina la sottocategoria"""
        text_lower = text.lower()
        
        if category == 'OPENING':
            if any(word in text_lower for word in ['buongiorno', 'buonasera', 'salve', 'vorrei']):
                return 'formal'
            elif 'ciao' in text_lower:
                return 'informal'
            else:
                return 'direct'
        
        elif category == 'INFORMATION_REQUEST':
            if any(word in text_lower for word in ['quanto', 'prezzo', 'costa']):
                return 'price'
            elif any(word in text_lower for word in ['orari', 'ora', 'quando']):
                return 'schedule'
            elif any(word in text_lower for word in ['disponibilità', 'ci sono', 'c\'è']):
                return 'availability'
            else:
                return 'options'
        
        elif category == 'SPECIFICATION':
            if any(word in text_lower for word in ['mattina', 'pomeriggio', 'prima', 'dopo']):
                return 'time_constraint'
            elif any(word in text_lower for word in ['meno di', 'massimo', 'economico']):
                return 'price_constraint'
            else:
                return 'preferences'
        
        return None
    
    def extract_slots(self, text: str) -> Dict[str, str]:
        """Estrae slot dalla frase"""
        slots = {}
        
        for slot_name, pattern in self.slot_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) > 1:
                    slots[slot_name] = match.group(2).strip()
                else:
                    slots[slot_name] = match.group(1).strip()
        
        return slots
    
    def analyze_attributes(self, text: str) -> Dict[str, str]:
        """Analizza attributi linguistici della frase"""
        attributes = {}
        text_lower = text.lower()
        
        # Registro linguistico
        formal_markers = ['vorrei', 'cortesemente', 'gentilmente', 'desidererei']
        informal_markers = ['voglio', 'mi serve', 'devo']
        
        if any(marker in text_lower for marker in formal_markers):
            attributes['register'] = 'formal'
        elif any(marker in text_lower for marker in informal_markers):
            attributes['register'] = 'informal'
        else:
            attributes['register'] = 'neutral'
        
        # Completezza
        slots = self.extract_slots(text)
        if len(slots) >= 3:
            attributes['completeness'] = 'complete'
        elif len(slots) >= 1:
            attributes['completeness'] = 'partial'
        else:
            attributes['completeness'] = 'vague'
        
        # Tono emotivo
        urgent_markers = ['subito', 'urgente', 'immediatamente', 'ora']
        frustrated_markers = ['ennesima volta', 'ancora', 'sempre', 'ma è possibile']
        
        if any(marker in text_lower for marker in urgent_markers):
            attributes['tone'] = 'urgent'
        elif any(marker in text_lower for marker in frustrated_markers):
            attributes['tone'] = 'frustrated'
        else:
            attributes['tone'] = 'neutral'
        
        # Complessità
        conjunctions = len(re.findall(r'\b(e|ma|però|se|quindi|possibilmente)\b', text_lower))
        if conjunctions >= 2:
            attributes['complexity'] = 'complex'
        elif conjunctions == 1:
            attributes['complexity'] = 'compound'
        else:
            attributes['complexity'] = 'simple'
        
        return attributes
    
    def categorize_corpus(self, sentences: List[str]) -> List[Dict]:
        """Categorizza l'intero corpus"""
        results = []
        
        print(f"Categorizzazione di {len(sentences)} frasi...")
        
        for i, sentence in enumerate(sentences):
            category, confidence = self.categorize_by_patterns(sentence)
            subcategory = self.get_subcategory(sentence, category) if category else None
            slots = self.extract_slots(sentence)
            attributes = self.analyze_attributes(sentence)
            
            result = {
                'id': f'utt_{i:04d}',
                'text': sentence,
                'primary_category': category,
                'sub_category': subcategory,
                'confidence': round(confidence, 2),
                'attributes': attributes,
                'extracted_slots': slots
            }
            
            results.append(result)
            
            if (i + 1) % 10 == 0:
                print(f"  Processate {i + 1}/{len(sentences)} frasi...")
        
        return results
    
    def export_results(self, results: List[Dict], output_dir: str = 'categorized_corpus'):
        """Esporta risultati"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # Export completo
        with open(output_path / 'full_corpus.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Organizza per categoria
        by_category = defaultdict(list)
        for item in results:
            if item['primary_category']:
                by_category[item['primary_category']].append(item)
        
        for category, items in by_category.items():
            category_dir = output_path / category.lower()
            category_dir.mkdir(exist_ok=True)
            
            by_subcat = defaultdict(list)
            for item in items:
                subcat = item.get('sub_category', 'other')
                if subcat:
                    by_subcat[subcat].append(item)
            
            for subcat, subitems in by_subcat.items():
                filepath = category_dir / f'{subcat}.json'
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(subitems, f, ensure_ascii=False, indent=2)
        
        # Statistiche
        self._export_statistics(results, output_path)
        
        print(f"\n✓ Corpus esportato in: {output_path}")
    
    def _export_statistics(self, results: List[Dict], output_path: Path):
        """Genera statistiche"""
        stats = {
            'total': len(results),
            'by_category': defaultdict(int),
            'uncategorized': 0,
            'avg_confidence': 0.0
        }
        
        confidences = []
        
        for item in results:
            cat = item.get('primary_category')
            if cat:
                stats['by_category'][cat] += 1
                confidences.append(item.get('confidence', 0))
            else:
                stats['uncategorized'] += 1
        
        if confidences:
            stats['avg_confidence'] = sum(confidences) / len(confidences)
        
        with open(output_path / 'statistics.txt', 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("STATISTICHE CORPUS\n")
            f.write("="*60 + "\n\n")
            f.write(f"Totale: {stats['total']}\n")
            f.write(f"Non categorizzate: {stats['uncategorized']}\n")
            f.write(f"Confidence media: {stats['avg_confidence']:.2f}\n\n")
            f.write("Per categoria:\n")
            for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
                pct = (count / stats['total']) * 100
                f.write(f"  {cat:25s}: {count:4d} ({pct:5.1f}%)\n")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python simple_categorizer.py <input_file> [output_dir]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else 'categorized_corpus'
    
    categorizer = SimpleCategorizer()
    sentences = categorizer.load_corpus(input_file)
    results = categorizer.categorize_corpus(sentences)
    categorizer.export_results(results, output_dir)
    
    print("\n✓ Fatto!")