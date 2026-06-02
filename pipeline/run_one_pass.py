import pdf_to_text
from pathlib import Path
from Ollama_struct_out import call_ollama_struct_out
import json

def read_pdf_pages(pdf_path):
    return pdf_to_text.convert_pdf_to_str_list(pdf_path)

def read_txt_prompt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()
    
def structure_txt_to_json(input_txt_path:Path, prompt_path:str, output_json_path:str, variant:str, model:str):
    print(f"START EXTRACTION FOR {input_txt_path.name}")
    system_msg = read_txt_prompt(prompt_path)
    pages = read_pdf_pages(input_txt_path)

    raw_text = "\n\n".join(pages)

    try:
        variant = "Target variant: "+variant
        queries = [variant, raw_text]
        result = call_ollama_struct_out(system_msg, queries, model)
        
        with open(output_json_path, "w", encoding="utf-8") as out_json:
            json.dump(result, out_json, indent=2)
        print(f"EXTRACTION done: {output_json_path}")
    except Exception as e:
        print(f"Error during EXTRACTION: {e}")