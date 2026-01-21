import os

base_dir = r"c:\Users\gcucino\Desktop\data_generator\FS_dataset_builder\parsing"
target_files = [
    "refusal_conversations_500x_proc_BATCH04_with_keep_turns.jsonl",
    "mixed_rude_ticket_378x_conversations_production_B3.jsonl",
    "search_fail_conversations_production_500_1748640337_fixed.jsonl",
    "search_fail_conversations_production_250x_1748691290.jsonl",
    "complete_qa_pairs_with_emojis.jsonl",
    "search_trains_messages.jsonl",
    "ticket_purchase_messages.jsonl",
    "navigation_commands.jsonl"
]

found_paths = []
print(f"Scanning {base_dir} for targets...")

for root, dirs, files in os.walk(base_dir):
    for f in files:
        if f in target_files:
            full_path = os.path.join(root, f)
            print(f"Found: {full_path}")
            found_paths.append(full_path)

with open("fs_paths.txt", "w", encoding="utf-8") as f:
    for p in found_paths:
        f.write(p + "\n")
