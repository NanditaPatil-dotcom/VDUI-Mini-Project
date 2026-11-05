import pandas as pd

df = pd.read_csv("airline_satisfaction.csv")

# clean
df = df.drop(columns=[c for c in ["ID", "Unnamed: 0"] if c in df.columns])
df = df.dropna(subset=["Arrival Delay"])
df["satisfaction"] = df["Satisfaction"].map({"Satisfied": 1, "Neutral or Dissatisfied": 0})

# correlate service ratings & delay against satisfaction
feature_cols = [
    "In-flight Wifi Service", "Online Boarding", "Seat Comfort",
    "Food and Drink", "Class", "Arrival Delay",
]
feature_cols = [c for c in feature_cols if c in df.columns]
corr = df[feature_cols + ["satisfaction"]].corr(numeric_only=True)["satisfaction"].drop("satisfaction")
corr = corr.sort_values(key=abs, ascending=False)

print("Correlation with satisfaction:")
print(corr)

df.to_csv("airline_satisfaction_cleaned.csv", index=False)
print("\nCleaned data saved to airline_satisfaction_cleaned.csv")
