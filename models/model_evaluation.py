
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
    ConfusionMatrixDisplay
)


project_dir = Path(__file__).resolve().parent.parent
models_dir = Path(__file__).resolve().parent
confusion_dir = models_dir / "confusion_matrices"

confusion_dir.mkdir(parents=True, exist_ok=True)

data_path = project_dir / "airline_satisfaction_cleaned.csv"
test_indices_path = models_dir / "test_indices.csv"

model_files = {
    "Logistic Regression": {
        "predictions": models_dir / "logistic_regression_predictions.csv",
        "cv": models_dir / "logistic_regression_5fold_cv_scores.csv"
    },
    "Random Forest": {
        "predictions": models_dir / "random_forest_predictions.csv",
        "cv": models_dir / "random_forest_5fold_cv_scores.csv"
    },
    "XGBoost": {
        "predictions": models_dir / "boosting_predictions.csv",
        "cv": models_dir / "boosting_5fold_cv_scores.csv"
    }
}

subgroup_columns = [
    "Gender",
    "Class",
    "Customer Type",
    "Type of Travel"
]

class_names = ["Neutral or Dissatisfied", "Satisfied"]


def encode_binary(values):
    mapping = {
        "neutral or dissatisfied": 0,
        "neutral/dissatisfied": 0,
        "dissatisfied": 0,
        "neutral": 0,
        "not satisfied": 0,
        "satisfied": 1
    }

    text_values = values.astype(str).str.strip().str.lower()
    result = text_values.map(mapping)

    numeric_values = pd.to_numeric(values, errors="coerce")
    result = result.fillna(numeric_values)

    if result.isna().any() or not result.isin([0, 1]).all():
        raise ValueError("Unexpected or missing satisfaction labels.")

    return result.astype(int)


def get_column(df, possible_names):
    for name in possible_names:
        if name in df.columns:
            return name

    raise ValueError(f"Could not find any of these columns: {possible_names}")


def load_predictions(path, model_name):
    if not path.exists():
        raise FileNotFoundError(f"Missing prediction file: {path}")

    df = pd.read_csv(path)

    row_col = get_column(df, ["row_index"])
    actual_col = get_column(
        df, ["Actual_Satisfaction", "actual", "actual_satisfaction"]
    )
    predicted_col = get_column(
        df, ["Predicted_Satisfaction", "predicted", "predicted_satisfaction"]
    )
    probability_col = get_column(
        df, ["Probability_Satisfied", "probability_satisfied"]
    )

    result = pd.DataFrame({
        "row_index": df[row_col],
        "actual": encode_binary(df[actual_col]),
        "predicted": encode_binary(df[predicted_col]),
        "probability_satisfied": pd.to_numeric(
            df[probability_col], errors="coerce"
        )
    })

    if result["row_index"].duplicated().any():
        raise ValueError(f"Duplicate test row indices in {model_name}.")

    probabilities = result["probability_satisfied"]

    if probabilities.isna().any() or not probabilities.between(0, 1).all():
        raise ValueError(f"Invalid prediction probabilities in {model_name}.")

    return result


def calculate_metrics(y_true, y_pred, y_probability):
    return {
        "Accuracy": accuracy_score(y_true, y_pred),
        "Macro Precision": precision_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "Macro Recall": recall_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "Macro F1": f1_score(
            y_true, y_pred, average="macro", zero_division=0
        ),
        "ROC-AUC": roc_auc_score(y_true, y_probability)
    }


required_files = [data_path, test_indices_path]

for paths in model_files.values():
    required_files.extend([paths["predictions"], paths["cv"]])

missing_files = [path for path in required_files if not path.exists()]

if missing_files:
    print("Missing required files:")

    for path in missing_files:
        print(path)

    raise FileNotFoundError("Please check the missing files.")


# Load the dataset and common test indices

cleaned_df = pd.read_csv(data_path)

if "satisfaction" in cleaned_df.columns:
    full_target = encode_binary(cleaned_df["satisfaction"])
elif "Satisfaction" in cleaned_df.columns:
    full_target = encode_binary(cleaned_df["Satisfaction"])
else:
    raise ValueError("Satisfaction target column not found.")

test_index_df = pd.read_csv(test_indices_path)
test_index_col = get_column(test_index_df, ["row_index"])

expected_test_indices = test_index_df[test_index_col].to_numpy()

if len(np.unique(expected_test_indices)) != len(expected_test_indices):
    raise ValueError("Duplicate indices found in test_indices.csv.")


# Load and align predictions from all three models

predictions = {}

for model_name, paths in model_files.items():
    model_predictions = load_predictions(
        paths["predictions"], model_name
    )

    if set(model_predictions["row_index"]) != set(expected_test_indices):
        raise ValueError(
            f"{model_name} does not use the same test records."
        )

    model_predictions = (
        model_predictions
        .set_index("row_index")
        .loc[expected_test_indices]
        .reset_index()
    )

    predictions[model_name] = model_predictions

    print(
        f"{model_name}: verified {len(model_predictions)} predictions."
    )


y_true = predictions["Logistic Regression"]["actual"].to_numpy()

for model_name, model_predictions in predictions.items():
    if not np.array_equal(
        y_true,
        model_predictions["actual"].to_numpy()
    ):
        raise ValueError(f"Actual labels do not match for {model_name}.")


dataset_actual = full_target.loc[expected_test_indices].to_numpy()

if not np.array_equal(y_true, dataset_actual):
    raise ValueError("Test labels do not match the cleaned dataset.")

print("\nAll models use the same test records and actual labels.")


# Calculate model performance and save reports

comparison_records = []
cv_records = []
classification_records = []

for model_name, paths in model_files.items():
    model_predictions = predictions[model_name]

    y_pred = model_predictions["predicted"].to_numpy()
    y_probability = model_predictions["probability_satisfied"].to_numpy()

    metrics = calculate_metrics(y_true, y_pred, y_probability)

    cv_df = pd.read_csv(paths["cv"])

    if "macro_f1" not in cv_df.columns:
        raise ValueError(f"macro_f1 column missing in {paths['cv'].name}.")

    cv_scores = pd.to_numeric(
        cv_df["macro_f1"], errors="coerce"
    ).dropna()

    if len(cv_scores) != 5:
        raise ValueError(f"{model_name} must have five valid CV scores.")

    metrics["CV Macro F1 Mean"] = cv_scores.mean()
    metrics["CV Macro F1 Std"] = cv_scores.std(ddof=1)

    comparison_records.append({
        "Model": model_name,
        **metrics
    })

    for fold, score in enumerate(cv_scores, start=1):
        cv_records.append({
            "Model": model_name,
            "Fold": fold,
            "Macro F1": score
        })

    report = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=class_names,
        output_dict=True,
        zero_division=0
    )

    for class_name, values in report.items():
        if isinstance(values, dict):
            classification_records.append({
                "Model": model_name,
                "Class": class_name,
                **values
            })
        else:
            classification_records.append({
                "Model": model_name,
                "Class": class_name,
                "Value": values
            })

    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    cm_df = pd.DataFrame(
        cm,
        index=["Actual 0", "Actual 1"],
        columns=["Predicted 0", "Predicted 1"]
    )

    file_prefix = model_name.lower().replace(" ", "_")

    cm_df.to_csv(
        confusion_dir / f"{file_prefix}_confusion_matrix.csv"
    )

    fig, ax = plt.subplots(figsize=(6, 5))

    display = ConfusionMatrixDisplay(
        confusion_matrix=cm,
        display_labels=class_names
    )

    display.plot(
        ax=ax,
        cmap="Blues",
        values_format="d",
        colorbar=False
    )

    ax.set_title(f"{model_name} - Confusion Matrix")
    plt.xticks(rotation=15, ha="right")
    plt.tight_layout()

    fig.savefig(
        confusion_dir / f"{file_prefix}_confusion_matrix.png",
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)


comparison_df = pd.DataFrame(comparison_records)

comparison_df.to_csv(
    models_dir / "model_comparison.csv",
    index=False
)

pd.DataFrame(cv_records).to_csv(
    models_dir / "cross_validation_scores.csv",
    index=False
)

pd.DataFrame(classification_records).to_csv(
    models_dir / "classification_reports.csv",
    index=False
)


# Cross-validation error-bar plot

model_names = comparison_df["Model"].tolist()
cv_means = comparison_df["CV Macro F1 Mean"].to_numpy()
cv_stds = comparison_df["CV Macro F1 Std"].to_numpy()

fig, ax = plt.subplots(figsize=(8, 5))

ax.errorbar(
    model_names,
    cv_means,
    yerr=cv_stds,
    fmt="o",
    capsize=6
)

ax.set_title("Five-Fold Cross-Validation Macro F1 Comparison")
ax.set_xlabel("Model")
ax.set_ylabel("Macro F1")
ax.grid(axis="y", alpha=0.3)

plt.tight_layout()

fig.savefig(
    models_dir / "model_error_bands.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close(fig)


# Subgroup performance comparison

missing_columns = [
    col for col in subgroup_columns
    if col not in cleaned_df.columns
]

if missing_columns:
    raise ValueError(f"Missing subgroup columns: {missing_columns}")

subgroup_base = cleaned_df.loc[
    expected_test_indices,
    subgroup_columns
].copy()

subgroup_base["actual"] = y_true

subgroup_records = []

for model_name, model_predictions in predictions.items():
    subgroup_df = subgroup_base.copy()

    subgroup_df["predicted"] = (
        model_predictions["predicted"].to_numpy()
    )

    for attribute in subgroup_columns:
        for group_value, group_df in subgroup_df.groupby(
            attribute, dropna=False, sort=True
        ):
            actual = group_df["actual"].to_numpy()
            predicted = group_df["predicted"].to_numpy()

            tn, fp, fn, tp = confusion_matrix(
                actual, predicted, labels=[0, 1]
            ).ravel()

            subgroup_records.append({
                "Model": model_name,
                "Attribute": attribute,
                "Group": (
                    "<Missing>" if pd.isna(group_value)
                    else str(group_value)
                ),
                "Sample Count": len(group_df),
                "Accuracy": accuracy_score(actual, predicted),
                "Precision": precision_score(
                    actual, predicted, zero_division=0
                ),
                "Recall": recall_score(
                    actual, predicted, zero_division=0
                ),
                "F1": f1_score(
                    actual, predicted, zero_division=0
                ),
                "Macro F1": f1_score(
                    actual, predicted,
                    average="macro",
                    zero_division=0
                ),
                "FPR": fp / (fp + tn) if (fp + tn) > 0 else np.nan,
                "TN": tn,
                "FP": fp,
                "FN": fn,
                "TP": tp
            })


subgroup_comparison_df = pd.DataFrame(subgroup_records)

subgroup_comparison_df.to_csv(
    models_dir / "subgroup_model_comparison.csv",
    index=False
)


# Display results

print("\nThree-Model Performance Comparison")
print(comparison_df.round(4).to_string(index=False))

print("\nSubgroup Performance Comparison")
print(subgroup_comparison_df.round(4).to_string(index=False))

print("\nModel evaluation completed successfully.")
print("\nGenerated files:")

for filename in [
    "model_comparison.csv",
    "cross_validation_scores.csv",
    "classification_reports.csv",
    "model_error_bands.png",
    "subgroup_model_comparison.csv"
]:
    print(models_dir / filename)

print("\nConfusion matrices saved in:")
print(confusion_dir)
