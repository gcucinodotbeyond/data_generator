import json
import re
from collections import Counter

def analyze_keywords(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    all_words = []
    # Parole comuni da escludere (stop words semplici in italiano)
    stop_words = {
        'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'il', 'lo', 'la', 'i', 'gli', 'le',
        'un', 'uno', 'una', 'ed', 'ed', 'e', 'o', 'che', 'chi', 'cui', 'non', 'si', 'ho', 'ha', 'hai',
        'abbiamo', 'hanno', 'posso', 'può', 'possono', 'come', 'quale', 'quali', 'cosa', 'dove', 'quando',
        'perché', 'mio', 'tua', 'suo', 'sono', 'essere', 'stata', 'questo', 'questa', 'quelli', 'quelle',
        'anche', 'solo', 'sempre', 'molto', 'troppo', 'bene', 'male', 'già', 'ancora', 'mai', 'forse',
        'però', 'tuttavia', 'quindi', 'del', 'sui', 'devo', 'succede', 'quanto', 'cos', 'funziona', 'sul',
        'fare', 'usare', 'della', 'dopo', 'dei', 'delle', 'più', 'mia', 'nel', 'senza', 'avere', 'qual',
        'tempo', 'viene', 'costa', 'durante', 'persone', 'dell', 'fino', 'all', 'tutto', 'era', 'nelle', 'salgo',
        'tutti', 'quello', 'dal', 'acquistato', 'quanti', 'nella', 'chiedere', 'altre', 'negli', 'utilizzare',
        'alle', 'vengono', 'ricevo', 'erano', 'quante', 'deve', 'direttamente', 'funzionano', 'perdo', 'voglio', 'furono', 'trovo',
        'iii', 'compro', 'nell', 'oltre', 'viii', 'dello', 'miei', 'comprato', 'presentare', 'qualcosa', 'prendere',
        'vale', 'italiana', 'tipi', 'nei', 'casi', 'aver', 'sapere', 'averlo', 'degli', 'significa', 'altro',  'tutte', 'offre', 'servono', 'esiste', 'salire'
    }

    for item in data:
        if isinstance(item, list) and len(item) > 0:
            question = item[0].lower()
            # Rimuovere punteggiatura e tokenizzare
            words = re.findall(r'\b\w+\b', question)
            # Filtrare parole brevi e stop words
            filtered_words = [w for w in words if len(w) > 2 and w not in stop_words]
            all_words.extend(filtered_words)
    
    counter = Counter(all_words)
    print(len(counter))
    return counter.most_common(500)

if __name__ == "__main__":
    file_path = r"qa/qa_pairs.json"
    keywords = analyze_keywords(file_path)
    
    output_path = r"qa/keywords_analysis.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("TOP 500 PAROLE PIÙ UTILIZZATE NELLE DOMANDE\n")
        f.write("=========================================\n\n")
        for word, count in keywords:
            f.write(f"{word}: {count}\n")
    
    print(f"Analisi completata. Risultati salvati in {output_path}")
