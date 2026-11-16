
from pathlib import Path

import joblib
import pandas as pd


project_dir = Path(__file__).resolve().parent.parent
models_dir = Path(__file__).resolve().parent

model_path = models_dir / "logistic_regression_pipeline.joblib"
output_path = models_dir / "logistic_regression_coefficients.csv"

if not model_path.exists():
    raise FileNotFoundError(f"Model not found: {model_path}")

pipeline = joblib.load(model_path)

preprocessor = pipeline.named_steps["preprocessor"]
classifier = pipeline.named_steps["classifier"]

if list(classifier.classes_) != [0, 1]:
    raise ValueError("Expected classes [0, 1].")

feature_names = preprocessor.get_feature_names_out()
coefficients = classifier.coef_[0]

if len(feature_names) != len(coefficients):
    raise ValueError("Feature names and coefficients do not match.")

coefficient_df = pd.DataFrame({
    "Feature": feature_names,
    "Coefficient": coefficients,
    "Absolute Coefficient": abs(coefficients),
    "Direction": [
        "Positive association with Satisfied"
        if value > 0 else "Negative association with Satisfied"
        for value in coefficients
    ]
})

coefficient_df = coefficient_df.sort_values(
    "Absolute Coefficient",
    ascending=False
)

coefficient_df.to_csv(output_path, index=False)

print("Logistic Regression coefficients extracted successfully.")

print("\nTop 10 positive coefficients:")
print(
    coefficient_df[coefficient_df["Coefficient"] > 0]
    .head(10)[["Feature", "Coefficient"]]
    .to_string(index=False)
)

print("\nTop 10 negative coefficients:")
print(
    coefficient_df[coefficient_df["Coefficient"] < 0]
    .sort_values("Coefficient")
    .head(10)[["Feature", "Coefficient"]]
    .to_string(index=False)
)

print("\nSaved:", output_path)
