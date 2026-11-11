
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.stats import pointbiserialr, spearmanr, chi2_contingency


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

required_cols = (
    numerical_cols + ordinal_cols + categorical_cols
)

missing_cols = [
    col for col in required_cols
    if col not in df.columns
]

if missing_cols:
    raise ValueError(f"Missing columns: {missing_cols}")

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

    if target_col in df.columns:
        existing_target = pd.to_numeric(
            df[target_col], errors="coerce"
        )

        if not np.array_equal(
            mapped_target.to_numpy(),
            existing_target.to_numpy()
        ):
            raise ValueError("Satisfaction columns do not match.")

    df[target_col] = mapped_target

elif target_col not in df.columns:
    raise ValueError("Satisfaction target column not found.")

analysis_df = df.copy()

for col in numerical_cols:
    analysis_df[col] = pd.to_numeric(
        analysis_df[col], errors="coerce"
    )

for col in ordinal_cols:
    analysis_df[col] = pd.to_numeric(
        analysis_df[col], errors="coerce"
    )
    analysis_df[col] = analysis_df[col].replace(0, np.nan)

analysis_df[target_col] = pd.to_numeric(
    analysis_df[target_col], errors="coerce"
)

if (
    analysis_df[target_col].isna().any()
    or analysis_df[target_col].nunique() != 2
):
    raise ValueError("Target must contain two valid classes.")


# correlation

results = []


# point-biserial correlation

for col in numerical_cols:
    valid = analysis_df[[col, target_col]].dropna()

    if len(valid) < 3 or valid[col].nunique() < 2:
        continue

    coefficient, pvalue = pointbiserialr(
        valid[target_col],
        valid[col]
    )

    results.append({
        "Feature": col,
        "Method": "Point-Biserial",
        "EffectValue": coefficient,
        "AbsoluteEffect": abs(coefficient),
        "PValue": pvalue,
        "SampleCount": len(valid)
    })


# spearman correlation

for col in ordinal_cols:
    valid = analysis_df[[col, target_col]].dropna()

    if len(valid) < 3 or valid[col].nunique() < 2:
        continue

    coefficient, pvalue = spearmanr(
        valid[col],
        valid[target_col]
    )

    results.append({
        "Feature": col,
        "Method": "Spearman",
        "EffectValue": coefficient,
        "AbsoluteEffect": abs(coefficient),
        "PValue": pvalue,
        "SampleCount": len(valid)
    })


# cramer's v

def calculate_cramers_v(table):
    chi2, pvalue, _, _ = chi2_contingency(
        table,
        correction=False
    )

    n = table.to_numpy().sum()
    rows, cols = table.shape

    if n <= 1 or min(rows, cols) < 2:
        return np.nan, pvalue

    phi2 = chi2 / n

    phi2_corrected = max(
        0,
        phi2 - ((cols - 1) * (rows - 1)) / (n - 1)
    )

    rows_corrected = rows - ((rows - 1) ** 2) / (n - 1)
    cols_corrected = cols - ((cols - 1) ** 2) / (n - 1)

    denominator = min(
        rows_corrected - 1,
        cols_corrected - 1
    )

    if denominator <= 0:
        return np.nan, pvalue

    coefficient = np.sqrt(phi2_corrected / denominator)

    return coefficient, pvalue


for col in categorical_cols:
    valid = analysis_df[[col, target_col]].dropna()

    table = pd.crosstab(
        valid[col],
        valid[target_col]
    )

    if min(table.shape) < 2:
        continue

    coefficient, pvalue = calculate_cramers_v(table)

    results.append({
        "Feature": col,
        "Method": "Cramer's V",
        "EffectValue": coefficient,
        "AbsoluteEffect": abs(coefficient),
        "PValue": pvalue,
        "SampleCount": len(valid)
    })


# adjust p-values

def adjust_pvalues(pvalues):
    pvalues = np.asarray(pvalues, dtype=float)
    adjusted = np.full(len(pvalues), np.nan)

    valid_indices = np.where(np.isfinite(pvalues))[0]

    if len(valid_indices) == 0:
        return adjusted

    valid_pvalues = pvalues[valid_indices]
    order = np.argsort(valid_pvalues)
    sorted_pvalues = valid_pvalues[order]

    total = len(sorted_pvalues)
    ranks = np.arange(1, total + 1)

    sorted_adjusted = sorted_pvalues * total / ranks
    sorted_adjusted = np.minimum.accumulate(
        sorted_adjusted[::-1]
    )[::-1]

    sorted_adjusted = np.clip(sorted_adjusted, 0, 1)

    adjusted_valid = np.empty(total)
    adjusted_valid[order] = sorted_adjusted

    adjusted[valid_indices] = adjusted_valid

    return adjusted


results_df = pd.DataFrame(results)

if results_df.empty:
    raise ValueError("No correlation results were generated.")

results_df["AdjustedPValue"] = adjust_pvalues(
    results_df["PValue"].to_numpy()
)

results_df = results_df.sort_values(
    ["Method", "AbsoluteEffect"],
    ascending=[True, False]
)

results_df.to_csv(
    output_dir / "correlation_ranking.csv",
    index=False
)

print("\nCorrelation results:\n")

for method in results_df["Method"].unique():
    print(f"\n{method}")

    method_results = results_df[
        results_df["Method"] == method
    ].sort_values(
        "AbsoluteEffect",
        ascending=False
    )

    print(
        method_results[
            [
                "Feature",
                "EffectValue",
                "PValue",
                "AdjustedPValue",
                "SampleCount"
            ]
        ].to_string(index=False)
    )


# heatmap

heatmap_cols = numerical_cols + ordinal_cols + [target_col]

heatmap_data = analysis_df[heatmap_cols].corr(
    method="spearman"
)

plt.figure(figsize=(17, 13))

sns.heatmap(
    heatmap_data,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    center=0,
    linewidths=0.5,
    vmin=-1,
    vmax=1
)

plt.title("Correlation Heatmap")
plt.xticks(rotation=45, ha="right")
plt.yticks(rotation=0)
plt.tight_layout()

plt.savefig(
    output_dir / "correlation_heatmap.png",
    dpi=300,
    bbox_inches="tight"
)

plt.close()

print("\nCorrelation analysis completed.")
print("Files saved in:", output_dir)
