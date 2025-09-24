import os
import json
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score

# === CONFIGURATION ===
ground_truth_csv = "ground_2.csv"
json_folder = "output_gpt-4-1106-preview_2pass_few_shot"
output_csv = "metrics_2pass/gpt-4-1106-preview_metrics_few_shot.csv"

# === Load ground truth ===
ground_df = pd.read_csv(ground_truth_csv)

# === Fields to evaluate ===
fields = ["num_tested_probands", "num_positive_het_probands", "num_compound_or_double_hets"]

# === Store results ===
all_results = []
per_field_scores = {field: [] for field in fields}

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

    for field in fields:
        try:
            gt_val = int(row[field])
            pred_val = int(pred[field])
        except (KeyError, ValueError, TypeError):
            print(f"Skipping {base_name} - missing or invalid field: {field}")
            continue

        y_true = [1 if gt_val > 0 else 0]
        y_pred = [1 if pred_val > 0 else 0]

        if y_true == [0] and y_pred == [0]:
            precision = recall = f1 = 1.0
        else:
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

        per_field_scores[field].append((precision, recall, f1))

# === Compute Macro-Averaged Overall Scores ===
for field, score_list in per_field_scores.items():
    if score_list:
        avg_precision = sum(x[0] for x in score_list) / len(score_list)
        avg_recall = sum(x[1] for x in score_list) / len(score_list)
        avg_f1 = sum(x[2] for x in score_list) / len(score_list)

        all_results.append({
            "file": "OVERALL",
            "field": field,
            "precision": avg_precision,
            "recall": avg_recall,
            "f1_score": avg_f1
        })

# === Save to CSV ===
df = pd.DataFrame(all_results)
os.makedirs(os.path.dirname(output_csv), exist_ok=True)
df.to_csv(output_csv, index=False)
print(f"Saved to {output_csv}")
