import fitz  # PyMuPDF
from pathlib import Path
from Ollama_struct_out import call_ollama_struct_out

def read_pdf_pages(pdf_path):
    doc = fitz.open(pdf_path)
    return [page.get_text().strip() for page in doc]

def read_txt_prompt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def test_pdf_by_page(pdf_path, prompt_path, model="llama3.2:latest"):
    print("Reading Prompt...\n")
    system_msg = read_txt_prompt(prompt_path)

    print("Reading PDF Pages...\n")
    pages = read_pdf_pages(pdf_path)

    for i, page_text in enumerate(pages):
        print(f"\n=== Page {i + 1} ===")
        print(page_text[:500])  # preview first 500 chars

        print(f"\nSending Page {i + 1} to LLM...\n")
        result = call_ollama_struct_out(system_msg, page_text, model)

        print(f"Structured Output from Page {i + 1}:\n{result}")

# Example usage
test_pdf_by_page("Burke_2018_29120065_522.pdf", "test_prompt.txt")
