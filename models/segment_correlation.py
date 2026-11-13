from pathlib import Path

import numpy as np
import pandas as pd

from scipy.stats import pointbiserialr, spearmanr


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

service_cols = [
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

segment_cols = [
    "Class",
    "Type of Travel",
    "Customer Type"
]

target_col = "satisfaction"


# load data

df = pd.read_csv(data_path)

required_cols = (
    numerical_cols + service_cols + segment_cols + [target_col]
)

missing_cols = [
    col for col in required_cols
    if col not in df.columns
]

if missing_cols:
    raise ValueError(f"Missing columns: {missing_cols}")

df[target_col] = pd.to_numeric(
    df[target_col], errors="coerce"
)

if df[target_col].isna().any():
    raise ValueError("Invalid satisfaction values found.")

analysis_df = df.copy()

for col in numerical_cols + service_cols:
    analysis_df[col] = pd.to_numeric(
        analysis_df[col], errors="coerce"
    )

for col in service_cols:
    analysis_df[col] = analysis_df[col].replace(0, np.nan)


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


# segment-wise correlation

results = []

for segment_col in segment_cols:

    for category, group in analysis_df.groupby(
        segment_col, dropna=False
    ):

        category_name = (
            "Missing" if pd.isna(category) else str(category)
        )

        for col in numerical_cols:

            valid = group[[col, target_col]].dropna()

            if (
                len(valid) < 3
                or valid[col].nunique() < 2
                or valid[target_col].nunique() != 2
            ):
                continue

            coefficient, pvalue = pointbiserialr(
                valid[target_col],
                valid[col]
            )

            results.append({
                "Segment": segment_col,
                "Category": category_name,
                "Feature": col,
                "Method": "Point-Biserial",
                "EffectValue": coefficient,
                "AbsoluteEffect": abs(coefficient),
                "PValue": pvalue,
                "SampleCount": len(valid)
            })

        for col in service_cols:

            valid = group[[col, target_col]].dropna()

            if (
                len(valid) < 3
                or valid[col].nunique() < 2
                or valid[target_col].nunique() != 2
            ):
                continue

            coefficient, pvalue = spearmanr(
                valid[col],
                valid[target_col]
            )

            results.append({
                "Segment": segment_col,
                "Category": category_name,
                "Feature": col,
                "Method": "Spearman",
                "EffectValue": coefficient,
                "AbsoluteEffect": abs(coefficient),
                "PValue": pvalue,
                "SampleCount": len(valid)
            })


# save results

results_df = pd.DataFrame(results)

if results_df.empty:
    raise ValueError("No segment correlation results generated.")

results_df["AdjustedPValue"] = (
    results_df.groupby(
        ["Segment", "Category", "Method"]
    )["PValue"]
    .transform(lambda values: adjust_pvalues(values.to_numpy()))
)

results_df = results_df.sort_values(
    ["Segment", "Category", "Method", "AbsoluteEffect"],
    ascending=[True, True, True, False]
)

output_path = output_dir / "segment_correlation_ranking.csv"

results_df.to_csv(
    output_path,
    index=False
)


# display top features

for (segment, category, method), group in results_df.groupby(
    ["Segment", "Category", "Method"],
    sort=False
):

    print(f"\n{segment}: {category} | {method}")

    print(
        group.nlargest(5, "AbsoluteEffect")[
            [
                "Feature",
                "EffectValue",
                "AdjustedPValue",
                "SampleCount"
            ]
        ].to_string(index=False)
    )

print("\nSegment correlation analysis completed.")
print("Results saved in:", output_path)
