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

def merge_structured_output(cumulative, new_result):
    for key, value in new_result.items():
        if isinstance(value, dict):
            if key not in cumulative:
                cumulative[key] = {}
            for sub_key, sub_value in value.items():
                cumulative[key].setdefault(sub_key, []).append(sub_value)
        else:
            cumulative.setdefault(key, []).append(value)
    return cumulative

def test_pdf_by_two_pages(pdf_path, prompt_path, model="llama3.2:latest"):
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
        result = call_ollama_struct_out(system_msg, two_page_text, model)
        print(f"Structured Output from {page_range}:\n{result}\n")
        final_result = merge_structured_output(final_result, result)

    print("Writing final structured output to output.json...\n")
    with open("output/Vantroys_llama.json", "w", encoding="utf-8") as out_file:
        json.dump(final_result, out_file, indent=2)

    print("Done.")


test_pdf_by_two_pages("literature/Vantroys_2018_29783990_371.pdf", "test_prompt.txt")
