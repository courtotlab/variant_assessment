import json
from pathlib import Path
from collections import defaultdict

def flatten_once(x):
    if isinstance(x, list) and len(x) == 1 and isinstance(x[0], list):
        return flatten_once(x[0])
    return x

def combine_json_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    combined = defaultdict(list)
    combined["explanation"] = defaultdict(list)

    for section_data in data.values():
        for key, value in section_data.items():
            if key == "explanation":
                explanation_dict = flatten_once(flatten_once(value))
                if isinstance(explanation_dict, list):
                    explanation_dict = explanation_dict[0]
                for subkey, subval in explanation_dict.items():
                    combined["explanation"][subkey].append(flatten_once(subval))
            else:
                combined[key].append(flatten_once(value))

    combined["explanation"] = dict(combined["explanation"])
    combined = dict(combined)

    key_order = [
        "num_tested_probands",
        "num_positive_het_probands",
        "positive_phenotypes",
        "num_compound_or_double_hets",
        "explanation",
        "gene_symbol",
        "genomic_hgvs"
    ]
    ordered_combined = {key: combined[key] for key in key_order if key in combined}

    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(ordered_combined, out_file, indent=2)

    print(f"✔ Combined output written to: {output_path}")

def process_directory(directory):
    directory = Path(directory)
    for json_file in directory.glob("*.json"):
        combine_json_file(json_file, json_file)

# Run for all JSON files in the specified directory
process_directory("output_lei_COT")
