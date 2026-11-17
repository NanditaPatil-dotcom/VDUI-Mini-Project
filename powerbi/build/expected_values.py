"""Independent pandas calculation of the headline numbers, to verify the DAX measures after the first refresh."""
import os, sys
import pandas as pd
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
df = pd.read_csv(f"{ROOT}/airline_satisfaction_tiered.csv")
R = ["Departure and Arrival Time Convenience", "Ease of Online Booking", "Check-in Service", "Online Boarding", "Gate Location", "On-board Service",
     "Seat Comfort", "Leg Room Service", "Cleanliness", "Food and Drink", "In-flight Service", "In-flight Wifi Service", "In-flight Entertainment", "Baggage Handling"]
sat = df["Satisfaction"] == "Satisfied"
long = df[R].stack()
rated = long[long > 0]
avg = {c: df.loc[df[c] > 0, c].mean() for c in R}
late = df["Arrival Delay"] > 15
mc = pd.read_csv(f"{ROOT}/models/model_comparison.csv").set_index("Model")
best = mc["Macro F1"].idxmax()
rows = [
    ("Total Passengers", len(df), "#,0"), ("Satisfied Passengers", int(sat.sum()), "#,0"), ("Satisfaction Rate", sat.mean(), "0.0%"),
    ("Dissatisfaction Rate", 1 - sat.mean(), "0.0%"), ("High Tier Rate", (df.satisfaction_tier == "High").mean(), "0.0%"),
    ("Low Tier Rate", (df.satisfaction_tier == "Low").mean(), "0.0%"), ("Returning Share", (df["Customer Type"] == "Returning").mean(), "0.0%"),
    ("Avg Departure Delay", df["Departure Delay"].mean(), "0.0"), ("Avg Arrival Delay", df["Arrival Delay"].mean(), "0.0"),
    ("Avg Flight Distance", df["Flight Distance"].mean(), "#,0"), ("Average Service Rating (zeros excluded)", rated.mean(), "0.00"),
    ("Good Rating Share", (rated >= 4).mean(), "0.0%"), ("Poor Rating Share", (rated <= 2).mean(), "0.0%"),
    ("Not Rated Share", (long == 0).mean(), "0.0%"), ("Lowest Rated Attribute", min(avg, key=avg.get), ""), ("Lowest Attribute Rating", min(avg.values()), "0.00"),
    ("Highest Rated Attribute", max(avg, key=avg.get), ""), ("Highest Attribute Rating", max(avg.values()), "0.00"),
    ("Delayed Share (>15 min arrival)", late.mean(), "0.0%"), ("Satisfaction Rate - Delayed", sat[late].mean(), "0.0%"),
    ("Satisfaction Rate - On Time", sat[~late].mean(), "0.0%"),
    ("Best Model (Macro F1)", best, ""), ("Best Macro F1", mc.loc[best, "Macro F1"], "0.0%"), ("Best ROC-AUC", mc["ROC-AUC"].max(), "0.000"),
    ("Best Macro Recall", mc["Macro Recall"].max(), "0.0%"), ("Best Accuracy", mc["Accuracy"].max(), "0.0%"),
]
for k, v in df.groupby("Class").apply(lambda g: (g["Satisfaction"] == "Satisfied").mean(), include_groups=False).items():
    rows.append((f"Satisfaction Rate - {k}", v, "0.0%"))
out = pd.DataFrame(rows, columns=["Measure", "Expected value", "Format"])
def fmt(v, f):
    if isinstance(v, str): return v
    return {"#,0": f"{v:,.0f}", "0.0%": f"{v*100:.1f}%", "0.0": f"{v:.1f}", "0.00": f"{v:.2f}", "0.000": f"{v:.3f}"}.get(f, str(v))
out["Expected value"] = [fmt(v, f) for v, f in zip(out["Expected value"], out["Format"])]
out.drop(columns="Format").to_csv(f"{ROOT}/powerbi/expected_values.csv", index=False)
print(out.drop(columns="Format").to_string(index=False))
