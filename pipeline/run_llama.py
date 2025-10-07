import pdf_to_text
from pathlib import Path
from Ollama_struct_out import call_ollama_struct_out
import json

def read_pdf_pages(pdf_path):
    return pdf_to_text.convert_pdf_to_str_list(pdf_path)

def read_txt_prompt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def recursive_flatten(x):
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x

def merge_structured_output(cumulative, new_result):
    for key, value in new_result.items():
        if isinstance(value, dict):
            if key not in cumulative:
                cumulative[key] = {}
            for sub_key, sub_value in value.items():
                flattened = recursive_flatten(sub_value)
                cumulative[key].setdefault(sub_key, []).append(flattened)
        else:
            flattened = recursive_flatten(value)
            cumulative.setdefault(key, []).append(flattened)
    return cumulative

def get_output_filename(pdf_path: Path):
    name = pdf_path.stem
    if name.startswith("Gatke_2001"):
        return "Gatke2001.json"
    elif name.startswith("Gatke_2007"):
        return "Gatke2007.json"
    else:
        return name.split("_")[0] + ".json"

def test_pdf_by_two_pages(pdf_path, prompt_path, output_path, model="llama3.2:latest"):
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    print(f"\n📄 Processing: {pdf_path.name}")
    system_msg = read_txt_prompt(prompt_path)
    pages = read_pdf_pages(pdf_path)

    final_result = {}
    for i in range(0, len(pages), 2):
        page_start = i + 1
        page_end = min(i + 2, len(pages))
        page_range = f"{page_start}-{page_end}" if page_end > page_start else f"{page_start}"
        print(f"  ⏳ Processing pages {page_range}...")

        text = "\n".join(pages[i:page_end])
        try:
            result = call_ollama_struct_out(system_msg, text, model)
            final_result = merge_structured_output(final_result, result)
        except Exception as e:
            print(f"  ⚠️ Error on pages {page_range}: {e}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(final_result, out_file, indent=2)

    print(f"✅ Written to: {output_path}")

# === Main Batch Runner ===
def run_on_literature_folder(
    literature_dir="literature",
    prompt_file="llama prompts/llama_prompt_COT.txt",
    output_dir="output_llama_COT"
):
    pdf_dir = Path(literature_dir)
    out_dir = Path(output_dir)
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        out_filename = get_output_filename(pdf_file)
        out_path = out_dir / out_filename
        test_pdf_by_two_pages(pdf_file, prompt_file, out_path)

# === Run it ===
#run_on_literature_folder()
