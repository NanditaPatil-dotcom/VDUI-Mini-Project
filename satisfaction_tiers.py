"""
Beyond the Boarding Pass - satisfaction tiers, feature importance & SHAP
Team 11 - VDUI Mini Project

Run airline_satisfaction_eda.py first - this reads its output file.
Requires: pip install pandas scikit-learn shap
"""

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
import shap

df = pd.read_csv("airline_satisfaction_cleaned.csv")

service_cols = [
    "In-flight Wifi Service", "Online Boarding", "Seat Comfort",
    "Food and Drink", "In-flight Entertainment", "Cleanliness",
]
service_cols = [c for c in service_cols if c in df.columns]

# ---- Low / Average / High satisfaction tiers ----
df["avg_service_rating"] = df[service_cols].mean(axis=1)
df["satisfaction_tier"] = pd.qcut(df["avg_service_rating"], q=3, labels=["Low", "Average", "High"])

print("Passengers per tier:")
print(df["satisfaction_tier"].value_counts(), "\n")

tier_means = df.groupby("satisfaction_tier", observed=True)[service_cols].mean()
spread = (tier_means.loc["High"] - tier_means.loc["Low"]).sort_values(ascending=False)
print("Features that differ most between Low and High tiers:")
print(spread, "\n")

# ---- Feature importance & SHAP ----
X = df[service_cols]
y = df["satisfaction"]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = DecisionTreeClassifier(max_depth=5, random_state=42)
model.fit(X_train, y_train)
print(f"Model accuracy: {model.score(X_test, y_test):.2f}\n")

explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
if shap_values.ndim == 3:  # (n_samples, n_features, n_classes) - newer shap versions
    shap_values = shap_values[:, :, 1]  # contribution toward the "satisfied" class
mean_abs_shap = pd.Series(abs(shap_values).mean(axis=0), index=service_cols)
mean_abs_shap = mean_abs_shap.sort_values(ascending=False)

print("Top features by SHAP importance:")
print(mean_abs_shap)

df.to_csv("airline_satisfaction_tiered.csv", index=False)
print("\nSaved airline_satisfaction_tiered.csv - ready for Power BI.")
