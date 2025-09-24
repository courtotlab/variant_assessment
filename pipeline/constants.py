import os

# Path constants -----------------------------------------------

PROMPTS_PATH = os.path.abspath("../prompts")

# LEI prompts - 1 pass only
LEI_PROMPTS_PATH = {"1_pass":{"COT":os.path.join(PROMPTS_PATH, "1_pass", "lei_prompts", "lei_prompt_COT.txt"),
                              "few_shot_COT":os.path.join(PROMPTS_PATH, "1_pass", "lei_prompts", "lei_prompt_few_shot_COT.txt"),
                              "few_shot":os.path.join(PROMPTS_PATH, "1_pass", "lei_prompts", "lei_prompt_few_shot.txt"),
                              "one_shot":os.path.join(PROMPTS_PATH, "1_pass", "lei_prompts", "lei_prompt_one_shot.txt"),
                              "zero_shot":os.path.join(PROMPTS_PATH, "1_pass", "lei_prompts", "prompt_with_quote.txt")},
                    "2_pass":{}}

# LLAMA prompts - 1 and 2 pass. 2 pass prompts represented by tuples (first pass prompt, second pass prompt)
LLAMA_PROMPTS_PATH = {"1_pass":{"COT":os.path.join(PROMPTS_PATH, "1_pass", "llama_prompts", "llama_prompt_COT.txt"),
                              "few_shot_COT":os.path.join(PROMPTS_PATH, "1_pass", "llama_prompts", "llama_prompt_few_shot_COT.txt"),
                              "few_shot":os.path.join(PROMPTS_PATH, "1_pass", "llama_prompts", "llama_prompt_few_shot.txt"),
                              "one_shot":os.path.join(PROMPTS_PATH, "1_pass", "llama_prompts", "llama_prompt_one_shot.txt"),
                              "zero_shot":os.path.join(PROMPTS_PATH, "1_pass", "llama_prompts", "prompt_with_quote_llama.txt")},
                    "2_pass":{"COT":(os.path.join(PROMPTS_PATH, "llama_prompts_first_pass", "COT.txt"),
                                     os.path.join(PROMPTS_PATH, "llama_prompts_second_pass", "COT.txt")),
                            "few_shot_COT":(os.path.join(PROMPTS_PATH, "llama_prompts_first_pass", "few_shot_COT.txt"),
                                     os.path.join(PROMPTS_PATH, "llama_prompts_second_pass", "few_shot_COT.txt")),
                            "few_shot":(os.path.join(PROMPTS_PATH, "llama_prompts_first_pass", "few_shot.txt"),
                                     os.path.join(PROMPTS_PATH, "llama_prompts_second_pass", "few_shot.txt")),
                            "one_shot":(os.path.join(PROMPTS_PATH, "llama_prompts_first_pass", "one_shot.txt"),
                                     os.path.join(PROMPTS_PATH, "llama_prompts_second_pass", "one_shot.txt")),
                            "zero_shot":(os.path.join(PROMPTS_PATH, "llama_prompts_first_pass", "zero_shot.txt"),
                                     os.path.join(PROMPTS_PATH, "llama_prompts_second_pass", "zero_shot.txt"))}}

OUTPUT_DIR = os.path.abspath("../outputs") 

