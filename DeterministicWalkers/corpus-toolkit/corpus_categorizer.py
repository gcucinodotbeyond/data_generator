#!/usr/bin/env python3
"""
Script per la categorizzazione automatica di un corpus di frasi conversazionali
per un sistema di dialogo modulare (customer care / vendita biglietti)

Autore: Claude
Data: 2026-01-15
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np

# Installare con: pip install sentence-transformers scikit-learn pandas --break-system-packages
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.metrics.pairwise import cosine_similarity
    import pandas as pd
except ImportError:
    print("ATTENZIONE: Installa le dipendenze con:")
    print("pip install sentence-transformers scikit-learn pandas --break-system-packages")
    exit(1)


class DialogueCorpusCategorizer:
    """Categorizza automaticamente frasi di dialogo per un sistema modulare"""
    
    def __init__(self, model_name: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'):
        """
        Inizializza il categorizzatore
        
        Args:
            model_name: Modello di sentence transformers (multilingua per italiano)
        """
        print(f"Caricamento modello {model_name}...")
        self.model = SentenceTransformer(model_name)
        
        # Definizione tassonomia categorie
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
        """
        Carica il corpus da file
        
        Args:
            filepath: Path al file (txt con una frase per riga, o json)
        
        Returns:
            Lista di frasi
        """
        path = Path(filepath)
        
        if path.suffix == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        elif path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Assume lista di stringhe o oggetti con campo 'text'
                    return [item if isinstance(item, str) else item.get('text', '') 
                           for item in data]
        else:
            raise ValueError(f"Formato file non supportato: {path.suffix}")
    
    def categorize_by_patterns(self, text: str) -> Tuple[Optional[str], float]:
        """
        Categorizza una frase usando pattern e keyword matching
        
        Returns:
            (categoria, confidence_score)
        """
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
                    score += 2.0  # Pattern matching più affidabile
            
            if score > 0:
                scores[category] = score
        
        if not scores:
            return None, 0.0
        
        best_category = max(scores, key=scores.get)
        max_score = scores[best_category]
        confidence = min(max_score / 3.0, 1.0)  # Normalizza
        
        return best_category, confidence
    
    def get_subcategory(self, text: str, category: str) -> Optional[str]:
        """Determina la sottocategoria basandosi sul contenuto"""
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
        
        # Aggiungi logica per altre categorie se necessario
        return None
    
    def extract_slots(self, text: str) -> Dict[str, str]:
        """Estrae slot dalla frase"""
        slots = {}
        
        for slot_name, pattern in self.slot_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Prendi il gruppo catturato (di solito il secondo gruppo)
                if len(match.groups()) > 1:
                    slots[slot_name] = match.group(2).strip()
                else:
                    slots[slot_name] = match.group(1).strip()
        
        return slots
    
    def analyze_attributes(self, text: str) -> Dict[str, str]:
        """Analizza attributi linguistici della frase"""
        attributes = {}
        
        # Registro linguistico
        formal_markers = ['vorrei', 'cortesemente', 'gentilmente', 'desidererei']
        informal_markers = ['voglio', 'mi serve', 'devo']
        
        text_lower = text.lower()
        
        if any(marker in text_lower for marker in formal_markers):
            attributes['register'] = 'formal'
        elif any(marker in text_lower for marker in informal_markers):
            attributes['register'] = 'informal'
        else:
            attributes['register'] = 'neutral'
        
        # Completezza (numero di slot estratti)
        slots = self.extract_slots(text)
        if len(slots) >= 3:
            attributes['completeness'] = 'complete'
        elif len(slots) >= 1:
            attributes['completeness'] = 'partial'
        else:
            attributes['completeness'] = 'vague'
        
        # Tono emotivo (semplificato)
        urgent_markers = ['subito', 'urgente', 'immediatamente', 'ora']
        frustrated_markers = ['ennesima volta', 'ancora', 'sempre', 'ma è possibile']
        
        if any(marker in text_lower for marker in urgent_markers):
            attributes['tone'] = 'urgent'
        elif any(marker in text_lower for marker in frustrated_markers):
            attributes['tone'] = 'frustrated'
        else:
            attributes['tone'] = 'neutral'
        
        # Complessità sintattica (conta congiunzioni)
        conjunctions = len(re.findall(r'\b(e|ma|però|se|quindi|possibilmente)\b', text_lower))
        if conjunctions >= 2:
            attributes['complexity'] = 'complex'
        elif conjunctions == 1:
            attributes['complexity'] = 'compound'
        else:
            attributes['complexity'] = 'simple'
        
        return attributes
    
    def semantic_clustering(self, sentences: List[str], n_clusters: int = 15) -> np.ndarray:
        """
        Clustering semantico usando embeddings
        
        Args:
            sentences: Lista di frasi
            n_clusters: Numero di cluster desiderati
        
        Returns:
            Array con label dei cluster per ogni frase
        """
        print("Generazione embeddings...")
        embeddings = self.model.encode(sentences, show_progress_bar=True)
        
        print(f"Clustering in {n_clusters} gruppi...")
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        
        return labels
    
    def categorize_corpus(self, sentences: List[str]) -> List[Dict]:
        """
        Categorizza l'intero corpus
        
        Returns:
            Lista di dizionari con informazioni complete per ogni frase
        """
        results = []
        
        print(f"Categorizzazione di {len(sentences)} frasi...")
        
        for i, sentence in enumerate(sentences):
            # Categorizzazione rule-based
            category, confidence = self.categorize_by_patterns(sentence)
            subcategory = self.get_subcategory(sentence, category) if category else None
            
            # Estrazione slot
            slots = self.extract_slots(sentence)
            
            # Analisi attributi
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
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"  Processate {i + 1}/{len(sentences)} frasi...")
        
        return results
    
    def export_categorized_corpus(self, results: List[Dict], output_dir: str = 'categorized_corpus'):
        """
        Esporta il corpus categorizzato in struttura modulare
        
        Args:
            results: Lista di frasi categorizzate
            output_dir: Directory di output
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # Export completo in JSON
        with open(output_path / 'full_corpus.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # Organizza per categoria
        by_category = defaultdict(list)
        for item in results:
            if item['primary_category']:
                by_category[item['primary_category']].append(item)
        
        # Export per categoria
        for category, items in by_category.items():
            category_dir = output_path / category.lower()
            category_dir.mkdir(exist_ok=True)
            
            # Raggruppa per sottocategoria
            by_subcat = defaultdict(list)
            for item in items:
                subcat = item.get('sub_category', 'other')
                if subcat:
                    by_subcat[subcat].append(item)
            
            # Salva ogni sottocategoria
            for subcat, subitems in by_subcat.items():
                filepath = category_dir / f'{subcat}.json'
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(subitems, f, ensure_ascii=False, indent=2)
        
        # Export statistiche
        self._export_statistics(results, output_path)
        
        print(f"\n✓ Corpus esportato in: {output_path}")
        print(f"  - File completo: full_corpus.json")
        print(f"  - Categorie: {len(by_category)}")
        print(f"  - Statistiche: statistics.txt")
    
    def _export_statistics(self, results: List[Dict], output_path: Path):
        """Genera e salva statistiche del corpus"""
        stats = {
            'total_sentences': len(results),
            'by_category': defaultdict(int),
            'by_subcategory': defaultdict(int),
            'by_register': defaultdict(int),
            'by_tone': defaultdict(int),
            'by_complexity': defaultdict(int),
            'uncategorized': 0,
            'avg_confidence': 0.0
        }
        
        confidences = []
        
        for item in results:
            cat = item.get('primary_category')
            if cat:
                stats['by_category'][cat] += 1
                subcat = item.get('sub_category')
                if subcat:
                    stats['by_subcategory'][f"{cat}/{subcat}"] += 1
                confidences.append(item.get('confidence', 0))
            else:
                stats['uncategorized'] += 1
            
            attrs = item.get('attributes', {})
            stats['by_register'][attrs.get('register', 'unknown')] += 1
            stats['by_tone'][attrs.get('tone', 'unknown')] += 1
            stats['by_complexity'][attrs.get('complexity', 'unknown')] += 1
        
        if confidences:
            stats['avg_confidence'] = sum(confidences) / len(confidences)
        
        # Scrivi file statistiche
        with open(output_path / 'statistics.txt', 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("STATISTICHE CORPUS CATEGORIZZATO\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Totale frasi: {stats['total_sentences']}\n")
            f.write(f"Frasi non categorizzate: {stats['uncategorized']}\n")
            f.write(f"Confidence media: {stats['avg_confidence']:.2f}\n\n")
            
            f.write("DISTRIBUZIONE PER CATEGORIA:\n")
            f.write("-" * 40 + "\n")
            for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
                pct = (count / stats['total_sentences']) * 100
                f.write(f"  {cat:25s}: {count:4d} ({pct:5.1f}%)\n")
            
            f.write("\nDISTRIBUZIONE PER SOTTOCATEGORIA:\n")
            f.write("-" * 40 + "\n")
            for subcat, count in sorted(stats['by_subcategory'].items(), key=lambda x: -x[1]):
                f.write(f"  {subcat:35s}: {count:4d}\n")
            
            f.write("\nATTRIBUTI LINGUISTICI:\n")
            f.write("-" * 40 + "\n")
            f.write("Registro:\n")
            for reg, count in stats['by_register'].items():
                f.write(f"  {reg:15s}: {count:4d}\n")
            
            f.write("\nTono:\n")
            for tone, count in stats['by_tone'].items():
                f.write(f"  {tone:15s}: {count:4d}\n")
            
            f.write("\nComplessità:\n")
            for comp, count in stats['by_complexity'].items():
                f.write(f"  {comp:15s}: {count:4d}\n")
        
        print(f"\n--- STATISTICHE RAPIDE ---")
        print(f"Totale: {stats['total_sentences']} frasi")
        print(f"Non categorizzate: {stats['uncategorized']}")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1])[:5]:
            print(f"  {cat}: {count}")


def main():
    """Funzione principale per test dello script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Categorizza corpus di dialoghi')
    parser.add_argument('input_file', help='File corpus (.txt o .json)')
    parser.add_argument('-o', '--output', default='categorized_corpus', 
                       help='Directory output (default: categorized_corpus)')
    parser.add_argument('-c', '--clusters', type=int, default=15,
                       help='Numero di cluster semantici (default: 15)')
    
    args = parser.parse_args()
    
    # Inizializza categorizzatore
    categorizer = DialogueCorpusCategorizer()
    
    # Carica corpus
    print(f"Caricamento corpus da: {args.input_file}")
    sentences = categorizer.load_corpus(args.input_file)
    print(f"Caricate {len(sentences)} frasi\n")
    
    # Categorizza
    results = categorizer.categorize_corpus(sentences)
    
    # Clustering semantico opzionale
    if args.clusters > 0:
        print(f"\nClustering semantico...")
        labels = categorizer.semantic_clustering(sentences, n_clusters=args.clusters)
        for i, result in enumerate(results):
            result['semantic_cluster'] = int(labels[i])
    
    # Export
    categorizer.export_categorized_corpus(results, args.output)
    
    print("\n✓ Processo completato!")


if __name__ == '__main__':
    main()