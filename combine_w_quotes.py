import json
from pathlib import Path

def initialize_combined_structure(keys, explanation_keys):
    combined = {key: [] for key in keys}
    combined["explanation"] = {key: [] for key in explanation_keys}
    return combined

def combine_json_structured(input_path, output_dir, output_filename="combined.json"):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Use the first section to get keys
    sample_section = next(iter(data.values()))
    top_level_keys = [k for k in sample_section.keys() if k != "explanation"]
    explanation_keys = sample_section.get("explanation", {}).keys()

    combined = initialize_combined_structure(top_level_keys, explanation_keys)

    for section in data.values():
        for key in top_level_keys:
            combined[key].append(section.get(key, []))  # Preserve structure (lists or values)
        for ex_key in explanation_keys:
            combined["explanation"][ex_key].append(section.get("explanation", {}).get(ex_key, ""))

    # Save combined output
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / output_filename
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(combined, out_file, indent=2)
    print(f"Structured combined output written to: {output_path}")

# Run it
combine_json_structured(
    "output_lei_with_quotes/Vantroys.json",                # Input file path
    "output_lei_with_quotes",    # Output directory
    "Vantroys_lei_quotes.json"      # Output filename
)

