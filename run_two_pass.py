import fitz  # PyMuPDF
from pathlib import Path
# from Ollama_struct_out import call_ollama_struct_out
from openai_struct_out import call_openai_struct_out as call_ollama_struct_out
import json

def read_pdf_pages(pdf_path):
    doc = fitz.open(pdf_path)
    return [page.get_text().strip() for page in doc]

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

# === Output filename generator ===
def get_output_filename(pdf_path: Path):
    name = pdf_path.stem
    if name.startswith("Gatke_2001"):
        return "Gatke2001"
    elif name.startswith("Gatke_2007"):
        return "Gatke2007"
    else:
        return name.split("_")[0]

# === PASS 1: Extract raw text and save to .txt ===
def pass_one_extract_to_txt(pdf_path, prompt_path, output_txt_path, model="llama3.2:latest"):
    print(f"\nStarting PASS 1 for {pdf_path.name}")
    system_msg = read_txt_prompt(prompt_path)
    pages = read_pdf_pages(pdf_path)

    all_text_outputs = []
    all_quotes_context = ""

    for i in range(0, len(pages), 2):
        page_start = i + 1
        page_end = min(i + 2, len(pages))
        page_range = f"{page_start}-{page_end}" if page_end > page_start else f"{page_start}"
        print(f"Processing pages {page_range}...")

        current_text = "\n".join(pages[i:page_end])
        context_section = f"\n\nPreviously extracted quotes:\n{all_quotes_context.strip()}\n" if all_quotes_context.strip() else ""
        query = current_text + context_section

        try:
            result = call_ollama_struct_out(system_msg, query, model, use_structured_output=False)
            result_text = result if isinstance(result, str) else json.dumps(result, indent=2)
            all_text_outputs.append(f"## Pages {page_range} ##\n{result_text}\n")
            all_quotes_context += f"\n\n## From pages {page_range} ##\n{result_text}"
        except Exception as e:
            print(f"Error on pages {page_range}: {e}")

    Path(output_txt_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as out_txt:
        out_txt.write("\n".join(all_text_outputs))

    print(f"PASS 1 done: {output_txt_path}")

# === PASS 2: Structure the text into JSON ===
def pass_two_structure_txt_to_json(input_txt_path, prompt_path, output_json_path, model="llama3.2:latest"):
    print(f"Starting PASS 2 for {input_txt_path.name}")
    system_msg = read_txt_prompt(prompt_path)

    with open(input_txt_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    try:
        result = call_ollama_struct_out(system_msg, raw_text, model, use_structured_output=True)
        Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as out_json:
            json.dump(result, out_json, indent=2)
        print(f"PASS 2 done: {output_json_path}")
    except Exception as e:
        print(f"Error during PASS 2: {e}")

# === Batch Runner for All PDFs ===
def run_all_passes_on_literature_folder(
    literature_dir="literature",
    prompt_pass1="llama prompts first pass/few_shot_COT.txt",
    prompt_pass2="llama prompts two pass/few_shot_COT.txt",
    intermediate_txt_dir="output_llama_2pass_few_shot_COT",
    final_json_dir="output_llama_2pass_few_shot_COT",
    model="llama3.2:latest"
):
    pdf_dir = Path(literature_dir)
    txt_dir = Path(intermediate_txt_dir)
    json_dir = Path(final_json_dir)

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        base_name = get_output_filename(pdf_path)
        txt_output = txt_dir / f"pass1_{base_name}.txt"
        json_output = json_dir / f"{base_name}.json"

        pass_one_extract_to_txt(pdf_path, prompt_pass1, txt_output, model)
        pass_two_structure_txt_to_json(txt_output, prompt_pass2, json_output, model)

# === Run it ===
if __name__ == "__main__":
    run_all_passes_on_literature_folder()
