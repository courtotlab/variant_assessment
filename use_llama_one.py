import fitz  # PyMuPDF
from pathlib import Path
from Ollama_struct_out import call_ollama_struct_out
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
        if isinstance(value, dict):  # e.g., "explanation"
            if key not in cumulative:
                cumulative[key] = {}
            for sub_key, sub_value in value.items():
                flattened = recursive_flatten(sub_value)
                cumulative[key].setdefault(sub_key, []).append(flattened)
        else:
            flattened = recursive_flatten(value)
            cumulative.setdefault(key, []).append(flattened)
    return cumulative

def test_pdf_by_two_pages(pdf_path, prompt_path, output_path, model="llama3.2:latest"):
    print("Reading Prompt...\n")
    system_msg = read_txt_prompt(prompt_path)

    print("Reading PDF pages...\n")
    pages = read_pdf_pages(pdf_path)

    final_result = {}
    for i in range(0, len(pages), 2):
        page_start = i + 1
        page_end = min(i + 2, len(pages))
        page_range = f"{page_start}-{page_end}" if page_end > page_start else f"{page_start}"
        print(f"Processing pages {page_range}...")

        two_page_text = "\n".join(pages[i:page_end])
        try:
            result = call_ollama_struct_out(system_msg, two_page_text, model)
            print(f"Structured Output from {page_range}:\n{json.dumps(result, indent=2)}\n")
            final_result = merge_structured_output(final_result, result)
        except Exception as e:
            print(f"⚠️ Error processing pages {page_range}: {e}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(final_result, out_file, indent=2)

    print(f"\n✅ Final structured output written to: {output_path}")

# === Run it ===
test_pdf_by_two_pages(
    "literature/Burke_2018_29120065_522.pdf",
    "llama prompts/llama_prompt_one_shot.txt",
    "output_llama_one_shot/Burke.json"
)
