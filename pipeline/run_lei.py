import subprocess
from pathlib import Path

# === CONFIGURATION ===
"""
pdf_dir = Path("literature")
prompt_path = Path("prompts/lei_prompt_COT.txt")
output_dir = Path("output_lei_COT")
output_dir.mkdir(parents=True, exist_ok=True)

# === SPECIAL FILENAMES ===
special_cases = {
    "Gatke_2001_11575530_392.pdf": "Gatke2001.json",
    "Gatke_2007_18075469_658.pdf": "Gatke2007.json",
}
"""

# === PROCESS ALL PDFS ===
def process_pdfs_lei(pdf_path:str, prompt_path:str, output_dir:str):
    pdf_name = pdf_path.name[:-4]

    out_json_name = f"{pdf_name}.json"

    out_path = output_dir / out_json_name

    # Build command: backslash must be part of the same argument string
    task_arg = f"lei\\ {prompt_path}"

    command = [
        str(Path("~/.local/bin/ohcrn-lei").expanduser()),
        str(pdf_path),
        "--task", task_arg,
        "--outfile", str(out_path)
    ]

    print(f"Running: {' '.join(command)}")
    result = subprocess.run(" ".join(command), shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Success: {out_path.name}")
    else:
        print(f"Failed on {pdf_name}\n{result.stderr}")
