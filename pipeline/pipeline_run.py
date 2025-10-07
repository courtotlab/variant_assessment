import os
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

def run_for_all_gene_variants(genes_dir:str, output_path:str, passes:str, prompt_technique:str, model:str):
    # Start execution for all gene directories
    genes_dir_list = os.listdir(genes_dir)
    results_path = create_output_folder_structure(output_path, passes, prompt_technique, model)

    for gene in genes_dir_list:
        current_gene_dir = os.path.join(genes_dir,gene)
        if os.path.isdir(current_gene_dir):
            #Create gene folder in results
            gene_results_dir = os.path.join(results_path, gene)
            if not os.path.exists(gene_results_dir):
                os.mkdir(gene_results_dir)
            #Get the variant dirs list and access them
            variant_list = os.listdir(current_gene_dir)
            for variant in variant_list:
                current_variant_dir = os.path.join(current_gene_dir, variant)
                if os.path.isdir(current_variant_dir):
                    # Reached a variant folder
                    # Create variant folder in results
                    variant_results_dir = os.path.join(gene_results_dir, variant)
                    if not os.path.exists(variant_results_dir):
                        os.mkdir(variant_results_dir)

                    files_list = os.listdir(current_variant_dir)
                    # Create folder for highlighted PDFs
                    hl_docs_path = os.path.join(current_variant_dir, "highlighted_docs")
                    if not os.path.exists(hl_docs_path):
                        os.mkdir(hl_docs_path)
                    # Create folder for outputs
                    for file in files_list:
                        if file.endswith('pdf'):
                            # It is a PDF article
                            file_path = os.path.join(current_variant_dir, file)

                            # First get the prompts tuple
                            prompt = find_prompt_path(passes, prompt_technique, model)
                            # Create path JSON results
                            json_file_path = os.path.join(variant_results_dir, passes+"_"+prompt_technique+"_"+model+".json")

                            if passes == constants.PASSES_OPTS[1]:
                                print("#"*4,"RUNNING 2 PASS EXTRACTION", "#"*4)
                                # Two pass extraction
                                # Create paths for intermediate text extraction
                                txt_file_path = os.path.join(variant_results_dir, passes+"_"+prompt_technique+"_"+model+".txt")
                                # Call passes to get results
                                run_two_pass.pass_one_extract_to_txt(file_path, prompt[0], txt_file_path, model)
                                run_two_pass.pass_two_structure_txt_to_json(txt_file_path, prompt[1], json_file_path, model)
                            else:
                                print("#"*4,"RUNNING 1 PASS EXTRACTION", "#"*4)
                                #Run extraction on 1 pass only
                                if model == "LEI":
                                    print("#"*8,"MODEL: LEI", "#"*8)
                                    run_lei.process_pdfs_lei(file_path, prompt, variant_results_dir)
                                else:
                                    print("#"*8,"MODEL: Llama", "#"*8)
                                    run_llama.test_pdf_by_two_pages(file_path, prompt, json_file_path)


genes_dir = "../test_data"
out_path = "../out_data/"
passes = "1_pass"
prompt_technique = "few_shot_COT"
model = "Llama"
run_for_all_gene_variants(genes_dir, out_path, passes, prompt_technique, model)





