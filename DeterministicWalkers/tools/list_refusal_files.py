import os

base_dir = r"c:\Users\gcucino\Desktop\data_generator\FS_dataset_builder\parsing\_synth_refuse\_datasets"
output_file = "refusal_files.txt"

if os.path.exists(base_dir):
    files = [f for f in os.listdir(base_dir) if f.endswith('.jsonl')]
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Found {len(files)} files in {base_dir}:\n")
        for file in sorted(files):
            f.write(f"- {file}\n")
else:
    with open(output_file, "w") as f:
        f.write(f"Directory not found: {base_dir}")
