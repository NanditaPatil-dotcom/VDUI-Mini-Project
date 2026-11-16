"""Create local, probability-scale SHAP explanations for representative passengers."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from PIL import Image
from scipy import sparse

from shap_analysis import PROJECT_DIR, dense, model_features, original_feature_name


def choose_representatives(
    y_true: np.ndarray, probabilities: np.ndarray, row_indices: np.ndarray
) -> list[tuple[int, int]]:
    """Choose the correctly classified example nearest each predicted class median."""
    predicted = (probabilities >= 0.5).astype(int)
    selected: list[tuple[int, int]] = []
    for class_id in (0, 1):
        candidates = np.flatnonzero((predicted == class_id) & (y_true == class_id))
        if len(candidates) == 0:
            raise ValueError(f"No correctly classified held-out examples for class {class_id}.")
        class_probabilities = probabilities[candidates]
        median_probability = float(np.median(class_probabilities))
        local_position = int(np.argmin(np.abs(class_probabilities - median_probability)))
        selected.append((int(row_indices[candidates[local_position]]), class_id))
    return selected


def render_waterfall(explanation: shap.Explanation, title: str) -> Image.Image:
    plt.figure(figsize=(11, 6))
    shap.plots.waterfall(explanation, max_display=12, show=False)
    fig = plt.gcf()
    fig.suptitle(title, fontsize=12, y=1.01)
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=PROJECT_DIR / "airline_satisfaction_cleaned.csv")
    parser.add_argument("--model", type=Path, default=PROJECT_DIR / "models" / "boosting_model.joblib")
    parser.add_argument("--train-indices", type=Path, default=PROJECT_DIR / "models" / "train_indices.csv")
    parser.add_argument("--test-indices", type=Path, default=PROJECT_DIR / "models" / "test_indices.csv")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--background-size", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    pipeline = joblib.load(args.model)
    if not hasattr(pipeline, "named_steps") or not {"preprocessing", "model"}.issubset(pipeline.named_steps):
        raise ValueError("Expected the saved complete preprocessing + model pipeline.")
    classifier = pipeline.named_steps["model"]
    if list(classifier.classes_) != [0, 1]:
        raise ValueError(f"Expected classes [0, 1], got {classifier.classes_}.")

    frame = pd.read_csv(args.data)
    X, y = model_features(frame)
    train_rows = pd.read_csv(args.train_indices)["row_index"].astype(int).to_numpy()
    test_rows = pd.read_csv(args.test_indices)["row_index"].astype(int).to_numpy()
    if set(train_rows).intersection(test_rows) or len(train_rows) + len(test_rows) != len(frame):
        raise ValueError("Train/test indices do not form a disjoint split of the dataset.")

    test_probabilities = pipeline.predict_proba(X.iloc[test_rows])[:, 1]
    actual_test = y.iloc[test_rows].to_numpy()
    selected = choose_representatives(actual_test, test_probabilities, test_rows)
    selected_rows = np.array([row for row, _ in selected], dtype=int)
    selected_class = np.array([class_id for _, class_id in selected], dtype=int)
    selected_probability = pipeline.predict_proba(X.iloc[selected_rows])[:, 1]
    selected_prediction = (selected_probability >= 0.5).astype(int)

    rng = np.random.default_rng(args.seed)
    background_rows = rng.choice(train_rows, size=min(args.background_size, len(train_rows)), replace=False)
    preprocessing = pipeline.named_steps["preprocessing"]
    background = dense(preprocessing.transform(X.iloc[background_rows]))
    transformed = dense(preprocessing.transform(X.iloc[selected_rows]))
    transformed_names = preprocessing.get_feature_names_out().astype(str)
    source_names = np.array([original_feature_name(name) for name in transformed_names])
    original_names = list(dict.fromkeys(source_names.tolist()))

    explainer = shap.TreeExplainer(
        classifier,
        data=background,
        feature_perturbation="interventional",
        model_output="probability",
    )
    explanation = explainer(transformed, check_additivity=True)
    encoded_values = np.asarray(explanation.values)
    if encoded_values.ndim == 3:
        encoded_values = encoded_values[:, :, 1]
    if encoded_values.shape != transformed.shape:
        raise ValueError(f"Unexpected local SHAP array shape: {encoded_values.shape}.")

    grouped_values = np.zeros((len(selected_rows), len(original_names)), dtype=float)
    for encoded_index, source_name in enumerate(source_names):
        grouped_values[:, original_names.index(source_name)] += encoded_values[:, encoded_index]

    base_values = np.asarray(explanation.base_values).reshape(-1)
    max_error = 0.0
    if len(base_values) == 1 and len(selected_rows) > 1:
        base_values = np.repeat(base_values, len(selected_rows))
    records: list[dict[str, object]] = []
    raw_features = frame.drop(columns=["Satisfaction", "satisfaction"])
    for passenger_position, row_index in enumerate(selected_rows):
        prediction = int(selected_prediction[passenger_position])
        predicted_label = "Satisfied" if prediction == 1 else "Neutral or Dissatisfied"
        actual_label = "Satisfied" if int(y.iloc[row_index]) == 1 else "Neutral or Dissatisfied"
        probability_satisfied = float(selected_probability[passenger_position])
        predicted_class_probability = probability_satisfied if prediction == 1 else 1.0 - probability_satisfied
        row_values = grouped_values[passenger_position]
        reconstruction_error = abs(float(base_values[passenger_position] + row_values.sum()) - probability_satisfied)
        max_error = max(max_error, reconstruction_error)
        order = np.argsort(-np.abs(row_values))
        for rank, feature_index in enumerate(order, start=1):
            value = float(row_values[feature_index])
            feature = original_names[feature_index]
            records.append(
                {
                    "row_index": int(row_index),
                    "actual_class": actual_label,
                    "predicted_class": predicted_label,
                    "predicted_class_probability": predicted_class_probability,
                    "probability_satisfied": probability_satisfied,
                    "correct_prediction": bool(prediction == int(y.iloc[row_index])),
                    "feature": feature,
                    "feature_value": raw_features.iloc[row_index][feature],
                    "shap_value": value,
                    "direction": (
                        "toward Satisfied" if value > 0 else
                        "toward Neutral or Dissatisfied" if value < 0 else "no contribution"
                    ),
                    "rank_by_absolute_contribution": rank,
                }
            )

    local = pd.DataFrame(records)
    local.to_csv(args.output_dir / "shap_local_explanations.csv", index=False)
    if max_error > 1e-4:
        raise ValueError(f"Local SHAP additivity check failed: max error={max_error:.3g}")

    waterfall_images: list[Image.Image] = []
    for position, row_index in enumerate(selected_rows):
        prediction = int(selected_prediction[position])
        label = "Satisfied" if prediction == 1 else "Neutral or Dissatisfied"
        probability = float(selected_probability[position])
        feature_values = raw_features.iloc[row_index][original_names].to_numpy(dtype=object)
        grouped_explanation = shap.Explanation(
            values=grouped_values[position],
            base_values=float(base_values[position]),
            data=feature_values,
            feature_names=original_names,
        )
        title = (
            f"Passenger row {row_index}: predicted {label} "
            f"(P(Satisfied)={probability:.3f})"
        )
        waterfall_images.append(render_waterfall(grouped_explanation, title))

    width = max(image.width for image in waterfall_images)
    gap = 30
    height = sum(image.height for image in waterfall_images) + gap * (len(waterfall_images) - 1)
    combined = Image.new("RGB", (width, height), "white")
    y_offset = 0
    for image in waterfall_images:
        combined.paste(image, ((width - image.width) // 2, y_offset))
        y_offset += image.height + gap
    combined.save(args.output_dir / "shap_waterfall.png")

    print("Selected representative held-out passengers:")
    for position, row_index in enumerate(selected_rows):
        print(
            f"  row {row_index}: predicted={'Satisfied' if selected_prediction[position] else 'Neutral or Dissatisfied'}, "
            f"P(Satisfied)={selected_probability[position]:.6f}, "
            f"P(predicted class)={selected_probability[position] if selected_prediction[position] else 1-selected_probability[position]:.6f}, "
            f"actual={'Satisfied' if y.iloc[row_index] else 'Neutral or Dissatisfied'}"
        )
    print(f"Local SHAP additivity max error: {max_error:.8g}")
    print(f"Saved {len(local)} feature-level explanations to {args.output_dir / 'shap_local_explanations.csv'}")
    print(f"Saved combined waterfall plot to {args.output_dir / 'shap_waterfall.png'}")


if __name__ == "__main__":
    main()
