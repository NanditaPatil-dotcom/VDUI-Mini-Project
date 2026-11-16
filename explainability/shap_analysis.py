"""Global SHAP analysis for the selected XGBoost satisfaction pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from scipy import sparse


PROJECT_DIR = Path(__file__).resolve().parents[1]
RATING_COLUMNS = [
    "Departure and Arrival Time Convenience",
    "Ease of Online Booking",
    "Check-in Service",
    "Online Boarding",
    "Gate Location",
    "On-board Service",
    "Seat Comfort",
    "Leg Room Service",
    "Cleanliness",
    "Food and Drink",
    "In-flight Service",
    "In-flight Wifi Service",
    "In-flight Entertainment",
    "Baggage Handling",
]
CATEGORICAL_COLUMNS = ["Gender", "Customer Type", "Type of Travel", "Class"]
TARGET_MAP = {"Neutral or Dissatisfied": 0, "Satisfied": 1}


def model_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Reproduce the feature and binary-target definitions used to train XGBoost."""
    if "Satisfaction" not in frame or "satisfaction" not in frame:
        raise ValueError("Dataset must contain Satisfaction and satisfaction columns.")

    target = frame["Satisfaction"].astype(str).str.strip().map(TARGET_MAP)
    if target.isna().any():
        raise ValueError("Unexpected labels found in Satisfaction target.")
    stored_target = pd.to_numeric(frame["satisfaction"], errors="coerce")
    if stored_target.isna().any() or not np.array_equal(target.to_numpy(), stored_target.to_numpy()):
        raise ValueError("The text and binary satisfaction targets do not match.")

    features = frame.drop(columns=["Satisfaction", "satisfaction"]).copy()
    missing = set(RATING_COLUMNS + CATEGORICAL_COLUMNS) - set(features.columns)
    if missing:
        raise ValueError(f"Dataset is missing expected feature columns: {sorted(missing)}")
    for column in RATING_COLUMNS:
        features[f"{column}_not_applicable"] = (features[column] == 0).astype("int8")
        features[column] = features[column].replace(0, np.nan)
    return features, target.astype(int)


def original_feature_name(transformed_name: str) -> str:
    """Map ColumnTransformer/OneHotEncoder output names to source columns."""
    name = transformed_name.split("__", 1)[-1]
    if name.endswith("_not_applicable"):
        return name[: -len("_not_applicable")]
    for column in CATEGORICAL_COLUMNS:
        if name == column or name.startswith(f"{column}_"):
            return column
    return name


def dense(matrix) -> np.ndarray:
    return matrix.toarray() if sparse.issparse(matrix) else np.asarray(matrix)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT_DIR / "airline_satisfaction_cleaned.csv")
    parser.add_argument("--model", type=Path, default=PROJECT_DIR / "models" / "boosting_model.joblib")
    parser.add_argument("--train-indices", type=Path, default=PROJECT_DIR / "models" / "train_indices.csv")
    parser.add_argument("--test-indices", type=Path, default=PROJECT_DIR / "models" / "test_indices.csv")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--background-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = joblib.load(args.model)
    if not hasattr(pipeline, "named_steps") or not {"preprocessing", "model"}.issubset(pipeline.named_steps):
        raise ValueError("Expected the saved complete preprocessing + model pipeline.")
    classifier = pipeline.named_steps["model"]
    if list(classifier.classes_) != [0, 1]:
        raise ValueError(f"Expected classes [0, 1] (0=dissatisfied, 1=satisfied), got {classifier.classes_}.")

    raw = pd.read_csv(args.data)
    X, y = model_features(raw)
    train_idx = pd.read_csv(args.train_indices)["row_index"].astype(int).to_numpy()
    test_idx = pd.read_csv(args.test_indices)["row_index"].astype(int).to_numpy()
    if set(train_idx).intersection(test_idx) or len(train_idx) + len(test_idx) != len(raw):
        raise ValueError("Train/test indices do not form a disjoint split of the dataset.")

    rng = np.random.default_rng(args.seed)
    background_rows = rng.choice(train_idx, size=min(args.background_size, len(train_idx)), replace=False)
    sample_rows = rng.choice(test_idx, size=min(args.sample_size, len(test_idx)), replace=False)
    preprocessing = pipeline.named_steps["preprocessing"]
    background_encoded = dense(preprocessing.transform(X.iloc[background_rows]))
    sample_encoded = dense(preprocessing.transform(X.iloc[sample_rows]))
    transformed_names = preprocessing.get_feature_names_out().astype(str)
    if sample_encoded.shape[1] != len(transformed_names):
        raise ValueError("Transformed feature names do not match the transformed data.")

    # Explain class 1 (Satisfied) probabilities. Using the fitted tree model directly
    # avoids wrapping the entire pipeline in a slow model-agnostic explainer.
    explainer = shap.TreeExplainer(
        classifier,
        data=background_encoded,
        feature_perturbation="interventional",
        model_output="probability",
    )
    explanation = explainer(sample_encoded, check_additivity=True)
    shap_values = np.asarray(explanation.values)
    if shap_values.ndim == 3:
        # Some SHAP/XGBoost combinations return a final class axis.
        shap_values = shap_values[:, :, 1]
    if shap_values.shape != sample_encoded.shape:
        raise ValueError(f"Unexpected SHAP array shape {shap_values.shape}; expected {sample_encoded.shape}.")

    # Recombine one-hot levels and the applicability indicator with their source
    # service-rating column. Summing signed attributions preserves each row's total.
    source_names = np.array([original_feature_name(n) for n in transformed_names])
    original_names = list(dict.fromkeys(source_names.tolist()))
    grouped = np.zeros((len(sample_rows), len(original_names)), dtype=float)
    for column_index, source_name in enumerate(source_names):
        grouped[:, original_names.index(source_name)] += shap_values[:, column_index]

    importance = pd.DataFrame(
        {
            "Feature": original_names,
            "MeanAbsoluteSHAP": np.mean(np.abs(grouped), axis=0),
            "MeanSHAP": np.mean(grouped, axis=0),
        }
    ).sort_values("MeanAbsoluteSHAP", ascending=False, ignore_index=True)
    importance.insert(0, "Rank", np.arange(1, len(importance) + 1))
    importance["ExplainedOutput"] = "P(Satisfied)"
    importance["SampleSize"] = len(sample_rows)
    importance.to_csv(args.output_dir / "shap_importance.csv", index=False)

    mapping = pd.DataFrame(
        {"TransformedFeature": transformed_names, "OriginalFeature": source_names}
    )
    mapping.to_csv(args.output_dir / "shap_feature_mapping.csv", index=False)

    top = importance.head(5).sort_values("MeanAbsoluteSHAP")
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    ax.barh(top["Feature"], top["MeanAbsoluteSHAP"], color="#2389ED")
    ax.set_xlabel("Mean absolute SHAP value (satisfaction probability scale)")
    ax.set_title("Top 5 Features Influencing Satisfaction Predictions")
    ax.grid(axis="x", alpha=0.2)
    fig.savefig(args.output_dir / "shap_importance.png", dpi=200)
    plt.close(fig)

    # Beeswarm is shown at the transformed-feature level so one-hot categories remain
    # visible; each transformed label has an explicit source-column mapping CSV.
    transformed_explanation = shap.Explanation(
        values=shap_values,
        base_values=np.asarray(explanation.base_values),
        data=sample_encoded,
        feature_names=transformed_names.tolist(),
    )
    plt.figure(figsize=(10, 8))
    shap.plots.beeswarm(transformed_explanation, max_display=20, show=False)
    plt.title("SHAP Beeswarm: Transformed Model Features")
    plt.tight_layout()
    plt.savefig(args.output_dir / "shap_beeswarm.png", dpi=200, bbox_inches="tight")
    plt.close()

    # Confirm that the SHAP values reconstruct the model's class-1 probabilities.
    class1_probabilities = pipeline.predict_proba(X.iloc[sample_rows])[:, 1]
    base_values = np.asarray(explanation.base_values)
    reconstructed = base_values.reshape(-1) + shap_values.sum(axis=1)
    max_error = float(np.max(np.abs(reconstructed - class1_probabilities)))
    if max_error > 1e-4:
        raise ValueError(f"SHAP additivity check failed for P(Satisfied): max error={max_error:.3g}")

    print(f"Model: {args.model}")
    print("Explained class: 1 = Satisfied; 0 = Neutral or Dissatisfied")
    print(f"Explained output: P(Satisfied), interventional TreeSHAP")
    print(f"Representative held-out rows: {len(sample_rows)}; background training rows: {len(background_rows)}")
    print(f"SHAP additivity max error: {max_error:.8g}")
    print("Top five original features:")
    print(importance[["Rank", "Feature", "MeanAbsoluteSHAP"]].head(5).to_string(index=False))
    print(f"Outputs saved in {args.output_dir}")


if __name__ == "__main__":
    main()
