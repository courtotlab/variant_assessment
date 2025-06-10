import fitz  # PyMuPDF
from pathlib import Path

from Ollama_struct_out import call_ollama_struct_out

def read_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text.strip()

def read_txt_prompt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def test_with_pdf_and_prompt(pdf_path, prompt_path, model="llama3.2:latest"):
    # Read files
    print("Reading PDF\n")
    query = read_pdf_text(pdf_path)

    print("=== PDF Text ===")
    print(query[:1000])  # print first 1000 chars

    print("Reading Prompt\n")
    system_msg = read_txt_prompt(prompt_path)

    print("Calling LLM\n")

    # Call structured output function
    result = call_ollama_struct_out(system_msg, query, model)
    
    print("Structured Output:\n", result)

# Example usage
test_with_pdf_and_prompt("Burke_2018_29120065_522.pdf", "test_prompt.txt")
