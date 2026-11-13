
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder


# paths

project_dir = Path(__file__).resolve().parent.parent
output_dir = Path(__file__).resolve().parent
data_path = project_dir / "airline_satisfaction_cleaned.csv"

output_dir.mkdir(parents=True, exist_ok=True)


# columns

numerical_cols = [
    "Age",
    "Flight Distance",
    "Departure Delay",
    "Arrival Delay"
]

ordinal_cols = [
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
    "Baggage Handling"
]

categorical_cols = [
    "Gender",
    "Customer Type",
    "Type of Travel",
    "Class"
]

target_col = "satisfaction"


# load data

df = pd.read_csv(data_path)

if target_col not in df.columns:
    raise ValueError("Satisfaction target column not found.")

if "Satisfaction" in df.columns:
    mapped_target = (
        df["Satisfaction"]
        .astype(str)
        .str.strip()
        .map({
            "Satisfied": 1,
            "Neutral or Dissatisfied": 0
        })
    )

    if mapped_target.isna().any():
        raise ValueError("Unexpected values in Satisfaction column.")

    if not np.array_equal(
        mapped_target.to_numpy(),
        df[target_col].to_numpy()
    ):
        raise ValueError("Satisfaction columns do not match.")

y = df[target_col].astype(int)

feature_cols = numerical_cols + ordinal_cols + categorical_cols

missing_cols = [
    col for col in feature_cols
    if col not in df.columns
]

if missing_cols:
    raise ValueError(f"Missing columns: {missing_cols}")

X = df[feature_cols].copy()


# handle service rating zeros

indicator_cols = []

for col in ordinal_cols:
    indicator_col = f"{col}_not_applicable"

    rating_values = pd.to_numeric(
        X[col], errors="coerce"
    )

    X[indicator_col] = (
        rating_values == 0
    ).astype(int)

    X[col] = rating_values.replace(0, np.nan)

    indicator_cols.append(indicator_col)

for col in numerical_cols:
    X[col] = pd.to_numeric(
        X[col], errors="coerce"
    )


# train/test split

train_idx, test_idx = train_test_split(
    df.index.to_numpy(),
    test_size=0.20,
    random_state=42,
    stratify=y
)

X_train = X.loc[train_idx]
X_test = X.loc[test_idx]

y_train = y.loc[train_idx]
y_test = y.loc[test_idx]

pd.Series(train_idx, name="row_index").to_csv(
    output_dir / "train_indices.csv",
    index=False
)

pd.Series(test_idx, name="row_index").to_csv(
    output_dir / "test_indices.csv",
    index=False
)

print("Training records:", len(X_train))
print("Testing records:", len(X_test))


# preprocessing

numeric_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("scaler", StandardScaler())
])

categorical_transformer = Pipeline([
    ("imputer", SimpleImputer(strategy="most_frequent")),
    ("encoder", OneHotEncoder(handle_unknown="ignore"))
])

preprocessor = ColumnTransformer([
    ("numeric", numeric_transformer, numerical_cols + ordinal_cols),
    ("categorical", categorical_transformer, categorical_cols),
    ("not_applicable", "passthrough", indicator_cols)
])


# logistic regression

model = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", LogisticRegression(
        max_iter=3000,
        random_state=42
    ))
])


# cross-validation

cv = StratifiedKFold(
    n_splits=5,
    shuffle=True,
    random_state=42
)

cv_scores = cross_val_score(
    model,
    X_train,
    y_train,
    cv=cv,
    scoring="f1_macro",
    n_jobs=-1
)


# train model

model.fit(X_train, y_train)

y_pred = model.predict(X_test)

satisfied_index = list(model.classes_).index(1)
y_prob = model.predict_proba(X_test)[:, satisfied_index]


# evaluation

metrics = {
    "Accuracy": accuracy_score(y_test, y_pred),
    "Macro Precision": precision_score(
        y_test, y_pred, average="macro", zero_division=0
    ),
    "Macro Recall": recall_score(
        y_test, y_pred, average="macro", zero_division=0
    ),
    "Macro F1": f1_score(
        y_test, y_pred, average="macro", zero_division=0
    ),
    "ROC-AUC": roc_auc_score(y_test, y_prob),
    "CV Macro F1 Mean": cv_scores.mean(),
    "CV Macro F1 Std": cv_scores.std(ddof=1)
}

metrics_df = pd.DataFrame([metrics])

metrics_df.to_csv(
    output_dir / "logistic_regression_metrics.csv",
    index=False
)

print("\nLogistic Regression Results")

for name, value in metrics.items():
    print(f"{name}: {value:.4f}")

print("\n5-fold CV scores:")
print(np.round(cv_scores, 4))

print("\nClassification Report:\n")

report = classification_report(
    y_test,
    y_pred,
    labels=[0, 1],
    target_names=["Neutral or Dissatisfied", "Satisfied"],
    output_dict=True,
    zero_division=0
)

print(classification_report(
    y_test,
    y_pred,
    labels=[0, 1],
    target_names=["Neutral or Dissatisfied", "Satisfied"],
    zero_division=0
))

pd.DataFrame(report).transpose().to_csv(
    output_dir / "logistic_regression_classification_report.csv"
)


# confusion matrix

cm = confusion_matrix(
    y_test,
    y_pred,
    labels=[0, 1]
)

cm_df = pd.DataFrame(
    cm,
    index=["Actual 0", "Actual 1"],
    columns=["Predicted 0", "Predicted 1"]
)

cm_df.to_csv(
    output_dir / "logistic_regression_confusion_matrix.csv"
)

print("\nConfusion Matrix:")
print(cm_df)


# save predictions

predictions = pd.DataFrame({
    "row_index": test_idx,
    "Actual_Satisfaction": y_test.to_numpy(),
    "Predicted_Satisfaction": y_pred,
    "Probability_Satisfied": y_prob,
    "Correct_Prediction": (
        y_test.to_numpy() == y_pred
    )
})

predictions.to_csv(
    output_dir / "logistic_regression_predictions.csv",
    index=False
)


# save model

joblib.dump(
    model,
    output_dir / "logistic_regression_pipeline.joblib"
)

print("\nLogistic Regression completed.")
print("Results saved in:", output_dir)
