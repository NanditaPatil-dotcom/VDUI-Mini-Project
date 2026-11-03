"""
Beyond the Boarding Pass - basic EDA
Team 11 - VDUI Mini Project

Download the dataset first:
https://www.kaggle.com/datasets/mysarahmadbhat/airline-passenger-satisfaction
and place it next to this script as 'airline_satisfaction.csv'
"""

import pandas as pd

df = pd.read_csv("airline_satisfaction.csv")

# clean
df = df.drop(columns=[c for c in ["id", "Unnamed: 0"] if c in df.columns])
df = df.dropna(subset=["Arrival Delay in Minutes"])
df["satisfaction"] = df["satisfaction"].map({"satisfied": 1, "neutral or dissatisfied": 0})

# correlate service ratings & delay against satisfaction
feature_cols = [
    "Inflight wifi service", "Online boarding", "Seat comfort",
    "Food and drink", "Class", "Arrival Delay in Minutes",
]
feature_cols = [c for c in feature_cols if c in df.columns]
corr = df[feature_cols + ["satisfaction"]].corr(numeric_only=True)["satisfaction"].drop("satisfaction")
corr = corr.sort_values(key=abs, ascending=False)

print("Correlation with satisfaction:")
print(corr)

df.to_csv("airline_satisfaction_cleaned.csv", index=False)
print("\nCleaned data saved to airline_satisfaction_cleaned.csv - ready for Power BI.")
