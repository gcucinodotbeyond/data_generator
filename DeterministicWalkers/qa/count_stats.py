import json

def print_stats(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Prepara i dati per la tabella
    rows = []
    total_all = 0
    
    # Ordina le macro-categorie per numero totale di elementi
    sorted_macros = sorted(data.items(), key=lambda x: sum(len(v) for v in x[1].values()), reverse=True)
    
    for macro, subs in sorted_macros:
        macro_total = sum(len(items) for items in subs.values())
        total_all += macro_total
        
        # Ordina le sottocategorie per numero di elementi
        sorted_subs = sorted(subs.items(), key=lambda x: len(x[1]), reverse=True)
        
        for i, (sub, items) in enumerate(sorted_subs):
            macro_label = f"**{macro}** ({macro_total})" if i == 0 else ""
            rows.append(f"| {macro_label} | {sub} | {len(items)} |")
            
    print("\n".join(rows))
    print(f"\n**Totale Complessivo: {total_all} QA**")

if __name__ == "__main__":
    print_stats("qa/qa_classified_hierarchical.json")
