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

# === PASS 1: Extract raw summaries or content and save to text ===
def pass_one_extract_to_txt(pdf_path, prompt_path, output_txt_path, model="llama3.2:latest"):
    print("Starting PASS 1 - Extracting Text with Context...\n")
    system_msg = read_txt_prompt(prompt_path)
    pages = read_pdf_pages(pdf_path)

    all_text_outputs = []
    all_quotes_context = ""  # Accumulated context

    for i in range(0, len(pages), 2):
        page_start = i + 1
        page_end = min(i + 2, len(pages))
        page_range = f"{page_start}-{page_end}" if page_end > page_start else f"{page_start}"
        print(f"Processing pages {page_range}...")

        current_text = "\n".join(pages[i:page_end])

        # Add context from previously extracted quotes (if any)
        if all_quotes_context.strip():
            context_section = f"\n\nPreviously extracted quotes:\n{all_quotes_context.strip()}\n"
        else:
            context_section = ""

        query = current_text + context_section

        try:
            result = call_ollama_struct_out(system_msg, query, model, use_structured_output=False)
            result_text = result if isinstance(result, str) else json.dumps(result, indent=2)

            all_text_outputs.append(f"## Pages {page_range} ##\n{result_text}\n")

            # Add this result to the accumulated context
            all_quotes_context += f"\n\n## From pages {page_range} ##\n{result_text}"

        except Exception as e:
            print(f"Error processing pages {page_range}: {e}")

    Path(output_txt_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as out_txt:
        out_txt.write("\n".join(all_text_outputs))

    print(f"\nPASS 1 complete. Output written to: {output_txt_path}\n")


# === PASS 2: Use final prompt and structure the raw text into JSON ===
def pass_two_structure_txt_to_json(input_txt_path, prompt_path, output_json_path, model="llama3.2:latest"):
    print("🔁 Starting PASS 2 - Structuring Data...\n")
    system_msg = read_txt_prompt(prompt_path)

    with open(input_txt_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    try:
        result = call_ollama_struct_out(system_msg, raw_text, model, use_structured_output=True)
        Path(output_json_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as out_json:
            json.dump(result, out_json, indent=2)
        print(f"\nPASS 2 complete. Structured JSON saved to: {output_json_path}")
    except Exception as e:
        print(f"Error during PASS 2: {e}")

# === Run Both Passes ===
if __name__ == "__main__":
    pdf_path = "literature/Musante_2017_28236339_126.pdf"
    prompt_pass1 = "llama prompts first pass/llama_zero_shot.txt"
    prompt_pass2 = "llama prompts two pass/zero_shot.txt"
    intermediate_txt = "one_pass_output/pass1_Musante.txt"
    final_json = "output_llama_2_pass/Musante.json"
    model = "llama3.2:latest"

    pass_one_extract_to_txt(pdf_path, prompt_pass1, intermediate_txt, model)
    pass_two_structure_txt_to_json(intermediate_txt, prompt_pass2, final_json, model)
