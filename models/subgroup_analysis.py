from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix
)


# paths

project_dir = Path(__file__).resolve().parent.parent
output_dir = Path(__file__).resolve().parent

data_path = project_dir / "airline_satisfaction_cleaned.csv"
predictions_path = output_dir / "logistic_regression_predictions.csv"

output_dir.mkdir(parents=True, exist_ok=True)


# columns

group_cols = [
    "Gender",
    "Class",
    "Customer Type",
    "Type of Travel"
]

target_col = "satisfaction"


# load data

df = pd.read_csv(data_path)
predictions = pd.read_csv(predictions_path)

required_prediction_cols = [
    "row_index",
    "Actual_Satisfaction",
    "Predicted_Satisfaction"
]

for col in required_prediction_cols:
    if col not in predictions.columns:
        raise ValueError(f"Missing prediction column: {col}")

for col in group_cols:
    if col not in df.columns:
        raise ValueError(f"Missing subgroup column: {col}")

if target_col not in df.columns:
    raise ValueError("Satisfaction column not found.")

df["row_index"] = df.index

predictions["row_index"] = pd.to_numeric(
    predictions["row_index"], errors="coerce"
)

if predictions["row_index"].isna().any():
    raise ValueError("Invalid row indices in predictions.")

predictions["row_index"] = predictions["row_index"].astype(int)

if predictions["row_index"].duplicated().any():
    raise ValueError("Duplicate row indices found in predictions.")

test_df = predictions.merge(
    df[["row_index", target_col] + group_cols],
    on="row_index",
    how="left",
    validate="one_to_one"
)

if test_df[group_cols].isna().all(axis=None):
    raise ValueError("Could not match predictions to passenger records.")

if test_df[target_col].isna().any():
    raise ValueError("Some prediction indices were not found in the dataset.")

if not np.array_equal(
    test_df[target_col].astype(int).to_numpy(),
    test_df["Actual_Satisfaction"].astype(int).to_numpy()
):
    raise ValueError("Actual predictions do not match the original dataset.")

print("Test records loaded:", len(test_df))


# calculate subgroup metrics

def calculate_metrics(group):

    y_true = group["Actual_Satisfaction"].astype(int)
    y_pred = group["Predicted_Satisfaction"].astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        y_pred,
        labels=[0, 1]
    ).ravel()

    fpr = fp / (fp + tn) if (fp + tn) > 0 else np.nan

    specificity = (
        tn / (tn + fp) if (tn + fp) > 0 else np.nan
    )

    return {
        "Passengers": len(group),
        "Actual_Not_Satisfied": int((y_true == 0).sum()),
        "Actual_Satisfied": int((y_true == 1).sum()),
        "Accuracy": accuracy_score(y_true, y_pred),
        "Precision": precision_score(
            y_true, y_pred, pos_label=1, zero_division=0
        ),
        "Recall": recall_score(
            y_true, y_pred, pos_label=1, zero_division=0
        ),
        "F1": f1_score(
            y_true, y_pred, pos_label=1, zero_division=0
        ),
        "Macro_F1": f1_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "FPR": fpr,
        "Specificity": specificity,
        "TN": tn,
        "FP": fp,
        "FN": fn,
        "TP": tp
    }


# analyse each subgroup

results = []

for col in group_cols:

    print(f"\n{col} performance")

    for category, group in test_df.groupby(
        col, dropna=False, sort=True
    ):

        metrics = calculate_metrics(group)

        row = {
            "Group": col,
            "Category": (
                "Missing" if pd.isna(category) else str(category)
            )
        }

        row.update(metrics)
        results.append(row)

        print(
            f"\n{row['Category']} "
            f"(n={metrics['Passengers']})"
        )

        for metric in [
            "Accuracy",
            "Precision",
            "Recall",
            "F1",
            "Macro_F1",
            "FPR"
        ]:
            print(f"{metric}: {metrics[metric]:.4f}")


# save results

results_df = pd.DataFrame(results)

results_df.to_csv(
    output_dir / "subgroup_performance.csv",
    index=False
)

print("\nSubgroup analysis completed.")
print("Results saved in:", output_dir / "subgroup_performance.csv")
