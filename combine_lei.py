import json
from pathlib import Path
from collections import defaultdict

def flatten_once(x):
    """Flattens a list by one level if it's a list of one item that is a list."""
    if isinstance(x, list) and len(x) == 1 and isinstance(x[0], list):
        return flatten_once(x[0])
    return x

def combine_json_file(input_path, output_dir, output_filename="combined.json"):
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

    # Convert back defaultdict to normal dict
    combined["explanation"] = dict(combined["explanation"])
    combined = dict(combined)
    # Reorder keys
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

    # Write to output file
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / output_filename
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(ordered_combined, out_file, indent=2)

    print(f"Combined output written to: {output_path}")
   



combine_json_file(
    "output_lei_one_shot/Vantroys.json",
    "output_lei_one_shot",
    "Vantroys.json"
)
