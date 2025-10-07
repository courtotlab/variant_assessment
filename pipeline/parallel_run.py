import os
import pathlib
from concurrent.futures import ProcessPoolExecutor
import run_two_pass
import constants
import run_lei
import run_llama

def create_output_folder_structure(output_path:str, passes:str, prompt_technique:str, model:str):
    """
    Create the folders to save the output. 
    """
    try:
        output_dir = os.path.abspath(output_path)
        results_path = os.path.join(output_dir, passes, prompt_technique, model) 
        os.makedirs(results_path)
    except FileExistsError:
        print("Output folder already exists, existing output files will be overwritten")
    
    return results_path

def find_prompt_path(passes:str, prompt_technique:str, model:str):
    try:
        prompt_path = constants.LEI_PROMPTS_PATH[passes][prompt_technique]
        if model == "LLAMA":
            prompt_path = constants.LLAMA_PROMPTS_PATH[passes][prompt_technique]
        return prompt_path
    except KeyError:
        print("There is no prompt defined in config for: ")
        print("Model:",model)
        print("Technique:",prompt_technique)
        print("# of passes:", passes)

def process_variant(variant_dir: pathlib.Path, results_dir: pathlib.Path, passes: str, prompt_technique: str, model: str):
    """Handles the processing logic for a single variant directory."""
    
    # 1. Efficiently Create Variant Result Folder
    variant_results_dir = results_dir / variant_dir.name
    # os.makedirs is more efficient than checking with os.path.exists() then calling os.mkdir()
    os.makedirs(variant_results_dir, exist_ok=True)

    # 2. Create highlighted_docs folder (using pathlib)
    hl_docs_path = variant_dir / "highlighted_docs"
    os.makedirs(hl_docs_path, exist_ok=True)
    
    # 3. Process PDF files
    for file_path in variant_dir.glob('*.pdf'):
        
        # Determine prompt and output paths
        prompt = find_prompt_path(passes, prompt_technique, model)
        json_file_path = variant_results_dir / f"{passes}_{prompt_technique}_{model}.json"

        # --- Extraction Logic (This is the most time-consuming part) ---
        if passes == constants.PASSES_OPTS[1]:
            print(f"#### RUNNING 2 PASS EXTRACTION for {file_path.name} ####")
            txt_file_path = variant_results_dir / f"{passes}_{prompt_technique}_{model}.txt"
            
            # These calls (likely involving LLMs/Heavy I/O) should ideally be concurrent
            run_two_pass.pass_one_extract_to_txt(str(file_path), prompt[0], str(txt_file_path), model)
            run_two_pass.pass_two_structure_txt_to_json(str(txt_file_path), prompt[1], str(json_file_path), model)
            
        else:
            print(f"#### RUNNING 1 PASS EXTRACTION for {file_path.name} ####")
            if model == "LEI":
                print("######## MODEL: LEI ########")
                # Note: Assuming run_lei.process_pdfs_lei handles output path internally
                run_lei.process_pdfs_lei(str(file_path), prompt, str(variant_results_dir))
            else:
                print("######## MODEL: Llama ########")
                run_llama.test_pdf_by_two_pages(str(file_path), prompt, str(json_file_path))


def run_for_all_gene_variants_efficient(genes_dir: str, output_path: str, passes: str, prompt_technique: str, model: str, max_workers=4):
    """
    Start execution for all gene directories using parallel processing.
    """
    genes_path = pathlib.Path(genes_dir)
    results_path_str = create_output_folder_structure(output_path, passes, prompt_technique, model)
    results_path = pathlib.Path(results_path_str)
    
    tasks = []
    
    # Use glob to efficiently find all variant directories
    # Assuming the structure is genes_dir / gene / variant
    
    # Iterate through gene directories
    for gene_dir in genes_path.iterdir():
        if gene_dir.is_dir():
            # 1. Create Gene Result Folder
            gene_results_dir = results_path / gene_dir.name
            os.makedirs(gene_results_dir, exist_ok=True)
            
            # Iterate through variant directories
            for variant_dir in gene_dir.iterdir():
                if variant_dir.is_dir():
                    # Collect the arguments for parallel processing
                    tasks.append((variant_dir, gene_results_dir, passes, prompt_technique, model))
    
    # 2. Parallel Processing
    # Use ProcessPoolExecutor to utilize multiple CPU cores for concurrent tasks.
    print(f"\nStarting parallel processing with {max_workers} workers...")
    
    # Use ProcessPoolExecutor to bypass the Global Interpreter Lock (GIL).
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = [executor.submit(process_variant, *task_args) for task_args in tasks]
        
        # Wait for all futures to complete (optional, for error handling/progress)
        for future in futures:
            try:
                future.result()
            except Exception as e:
                print(f"An error occurred during processing: {e}")
                
    print("\nAll gene variants processed.")