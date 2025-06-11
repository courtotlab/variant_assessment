import json
from pathlib import Path

def merge_structured_output(cumulative, new_result):
    for key, value in new_result.items():
        if isinstance(value, dict):
            if key not in cumulative:
                cumulative[key] = {}
            for sub_key, sub_value in value.items():
                cumulative[key].setdefault(sub_key, []).append(sub_value)
        else:
            cumulative.setdefault(key, []).append(value)
    return cumulative

def combine_json_file(input_path, output_dir, output_filename="combined.json"):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    combined = {}
    for section in data.values():
        combined = merge_structured_output(combined, section)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / output_filename
    with open(output_path, "w", encoding="utf-8") as out_file:
        json.dump(combined, out_file, indent=2)
    print(f"Combined output written to: {output_path}")


combine_json_file(
    "/Users/aahmed/Downloads/Vantroys.json",
    "/Users/aahmed/variant_assessment/output_lei",
    "Vantroys_lei.json"
)
