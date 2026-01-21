import json

with open("resources/corpus/harvested_from_fs.json", "r", encoding="utf-8") as f:
    data = json.load(f)

sources = sorted(list(set(item.get("source", "Unknown") for item in data)))
with open("final_sources.txt", "w", encoding="utf-8") as out:
    out.write("AVAILABLE SOURCES:\n")
    for s in sources:
        count = sum(1 for item in data if item.get("source") == s)
        out.write(f"- {s} ({count} items)\n")
        print(f"- {s} ({count} items)")
