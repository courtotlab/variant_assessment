import os

def run_for_all_gene_variants(genes_dir:str):
    genes_dir_list = os.listdir(genes_dir)
    for gene in genes_dir_list:
        current_gene_dir = os.path.join(genes_dir,gene)
        if os.path.isdir(current_gene_dir):
            print("--",gene)
            variant_list = os.listdir(current_gene_dir)
            for variant in variant_list:
                current_variant_dir = os.path.join(current_gene_dir, variant)
                if os.path.isdir(current_variant_dir):
                    # Reached a variant folder
                    print("--"*3, variant)
                    files_list = os.listdir(os.path.join(current_gene_dir, variant))
                    for file in files_list:
                        print("--"*6,file)
                        if file.endswith('pdf'):
                            # It is a PDF article
                            # TODO - run the pipeline for the file
                            pass


run_for_all_gene_variants("../test_data/")






