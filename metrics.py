import os
import json
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

# === CONFIGURATION ===
ground_truth_csv = "ground.csv"
json_folder = "output_llama"
output_csv = "llama_metrics_output.csv"

# === Load ground truth ===
ground_df = pd.read_csv(ground_truth_csv)
for col in ["num_tested_probands", "num_positive_het_probands", "num_compound_or_double_hets"]:
    ground_df[col] = ground_df[col].apply(eval)

# === Store results ===
all_results = []
overall = {
    "num_tested_probands": {"y_true": [], "y_pred": []},
    "num_positive_het_probands": {"y_true": [], "y_pred": []},
    "num_compound_or_double_hets": {"y_true": [], "y_pred": []}
}

# === Loop through JSON files ===
for fname in os.listdir(json_folder):
    if not fname.endswith(".json") or "PrimoParmo" in fname:
        continue

    fpath = os.path.join(json_folder, fname)
    with open(fpath, "r") as f:
        pred = json.load(f)

    base_name = fname.replace(".json", "")
    row = ground_df[ground_df["filename"] == base_name]
    if row.empty:
        continue
    row = row.iloc[0]

    for field in ["num_tested_probands", "num_positive_het_probands", "num_compound_or_double_hets"]:
        y_true = [1 if v > 0 else 0 for v in row[field]]
        y_pred = [1 if v > 0 else 0 for v in pred[field]]
        if len(y_true) != len(y_pred):
            raise ValueError(
                f"\n❌ Length mismatch detected!\n"
                f"File: {base_name}\n"
                f"Field: {field}\n"
                f"GT length: {len(y_true)}\n"
                f"Pred length: {len(y_pred)}"
            )

        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        all_results.append({
            "file": base_name,
            "field": field,
            "precision": precision,
            "recall": recall,
            "f1_score": f1
        })

        overall[field]["y_true"].extend(y_true)
        overall[field]["y_pred"].extend(y_pred)

# === Compute Overall Scores ===
for field in overall:
    y_true_all = overall[field]["y_true"]
    y_pred_all = overall[field]["y_pred"]

    precision = precision_score(y_true_all, y_pred_all, zero_division=0)
    recall = recall_score(y_true_all, y_pred_all, zero_division=0)
    f1 = f1_score(y_true_all, y_pred_all, zero_division=0)

    all_results.append({
        "file": "OVERALL",
        "field": field,
        "precision": precision,
        "recall": recall,
        "f1_score": f1
    })

# === Save to CSV ===
df = pd.DataFrame(all_results)
df.to_csv(output_csv, index=False)
print(f"Saved to {output_csv}")
