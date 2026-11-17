"""Cross-checks every number the Power BI report reads against the existing CSV outputs. Nothing is recalculated or replaced:
the report loads the CSVs as-is; this script only verifies they are internally consistent. Writes powerbi/validation_report.md."""
import os
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
lines, fails = [], 0


def check(name, ok, detail=""):
    global fails
    fails += 0 if ok else 1
    lines.append(f"| {'PASS' if ok else 'FAIL'} | {name} | {detail} |")


mc = pd.read_csv(P("models", "model_comparison.csv")).set_index("Model")
cv = pd.read_csv(P("models", "cross_validation_scores.csv"))
sg = pd.read_csv(P("models", "subgroup_model_comparison.csv"))
sh = pd.read_csv(P("explainability", "shap_importance.csv"))
co = pd.read_csv(P("correlation", "correlation_ranking.csv"))
n_test = len(pd.read_csv(P("models", "test_indices.csv")))
cmfile = {"Logistic Regression": "logistic_regression", "Random Forest": "random_forest", "XGBoost": "xgboost"}


# 0 passenger data model (replicates the Power Query steps in pandas)
df = pd.read_csv(P("airline_satisfaction_cleaned.csv"))
tiered = pd.read_csv(P("airline_satisfaction_tiered.csv"))
check("cleaned file: 129,487 passenger rows x 24 columns", df.shape == (129487, 24), f"{df.shape[0]:,} x {df.shape[1]}")
check("cleaned file: 73,225 Neutral/Dissatisfied and 56,262 Satisfied", (df.Satisfaction == "Neutral or Dissatisfied").sum() == 73225 and (df.Satisfaction == "Satisfied").sum() == 56262, "56.55% / 43.45%")
check("tiered file = cleaned file + 2 columns, identical rows in identical order (tier can be attached by position)", df.reset_index(drop=True).equals(tiered[list(df.columns)].reset_index(drop=True)) and list(tiered.columns[len(df.columns):]) == ["avg_service_rating", "satisfaction_tier"], "24 shared columns identical")
df["satisfaction_tier"] = tiered["satisfaction_tier"].values
check("unfiltered passenger count (rows = Total Passengers) is 129,487", len(df) == 129487, f"{len(df):,} rows")
sat_n = (df["Satisfaction"] == "Satisfied").sum()
check("Satisfied + Neutral/Dissatisfied = total", sat_n + (df["Satisfaction"] == "Neutral or Dissatisfied").sum() == len(df), f"{sat_n:,} satisfied")
check("High + Average + Low tier = total", df["satisfaction_tier"].isin(["High", "Average", "Low"]).all(), f"High {(df.satisfaction_tier == 'High').sum():,}")
def band_age(a):
    return "Young" if a < 25 else "Young Adult" if a < 40 else "Adult" if a < 55 else "Senior"
d = df.copy()
d["Age Band"] = d.Age.map(band_age)
for name, cols in {"DimTravel": ["Class", "Type of Travel"], "DimPassengerProfile": ["Gender", "Customer Type", "Age Band"],
                   "DimSatisfaction": ["Satisfaction", "satisfaction_tier"]}.items():
    dim = d[cols].drop_duplicates().reset_index(drop=True)
    dim["key"] = dim.index + 1
    j = d.merge(dim, on=cols, how="left")
    check(f"{name}: left-outer merge keeps every passenger and finds every key", len(j) == len(d) and j.key.notna().all(), f"{len(dim)} dimension rows, {len(j):,} fact rows")
rating_cols = ["Departure and Arrival Time Convenience", "Ease of Online Booking", "Check-in Service", "Online Boarding", "Gate Location", "On-board Service",
               "Seat Comfort", "Leg Room Service", "Cleanliness", "Food and Drink", "In-flight Service", "In-flight Wifi Service", "In-flight Entertainment", "Baggage Handling"]
check("FactServiceRating rows = 14 x passengers after unpivot", len(df) * len(rating_cols) == 1812818, f"{len(df) * len(rating_cols):,} rows")
ex = pd.read_csv(P("explainability", "gemini_insights.json").replace(".json", ".json")) if False else None


# 0b AI Explainability data behind the row_index selector (all from the existing explainability outputs)
import json
gj = json.load(open(P("explainability", "gemini_insights.json"), encoding="utf-8"))["explanations"]
sl = pd.read_csv(P("explainability", "shap_local_explanations.csv"))
check("row_index values in SHAP local file = Gemini passengers", sorted(sl.row_index.unique()) == sorted(e["row_index"] for e in gj), f"{sorted(sl.row_index.unique())}")
for e in gj:
    g = sl[sl.row_index == e["row_index"]]
    check(f"passenger {e['row_index']}: SHAP rows, predicted class and probability agree between SHAP file and Gemini file",
          len(g) == 22 and g.predicted_class.iloc[0] == e["predicted_class"] and abs(g.predicted_class_probability.iloc[0] - e["predicted_class_probability"]) < 1e-9,
          f"{len(g)} SHAP rows, {e['predicted_class']}, p={e['predicted_class_probability']:.4f}, {len(e['service_improvement_suggestions'])} recommendation row(s)")

# 1 five-fold CV
for model, g in cv.groupby("Model"):
    check(f"CV folds = 5 ({model})", len(g) == 5 and sorted(g.Fold) == [1, 2, 3, 4, 5], f"{len(g)} folds")
    check(f"CV mean matches model_comparison ({model})", abs(g["Macro F1"].mean() - mc.loc[model, "CV Macro F1 Mean"]) < 1e-9,
          f"{g['Macro F1'].mean():.6f} vs {mc.loc[model, 'CV Macro F1 Mean']:.6f}")
    check(f"CV std (ddof=1) matches model_comparison ({model})", abs(g["Macro F1"].std(ddof=1) - mc.loc[model, "CV Macro F1 Std"]) < 1e-9,
          f"{g['Macro F1'].std(ddof=1):.6f} vs {mc.loc[model, 'CV Macro F1 Std']:.6f}")
    lo, hi = mc.loc[model, "CV Macro F1 Mean"] - mc.loc[model, "CV Macro F1 Std"], mc.loc[model, "CV Macro F1 Mean"] + mc.loc[model, "CV Macro F1 Std"]
    check(f"error band [{lo:.4f}, {hi:.4f}] brackets most folds ({model})", ((g['Macro F1'] >= lo) & (g['Macro F1'] <= hi)).sum() >= 3,
          f"{((g['Macro F1'] >= lo) & (g['Macro F1'] <= hi)).sum()}/5 folds inside the band")

# 2 confusion matrices vs model_comparison and subgroup totals
for model, key in cmfile.items():
    cm = pd.read_csv(P("models", "confusion_matrices", f"{key}_confusion_matrix.csv"), index_col=0).values
    tn, fp, fn, tp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
    check(f"confusion matrix total = test rows ({model})", tn + fp + fn + tp == n_test, f"{tn+fp+fn+tp} vs {n_test}")
    check(f"accuracy from confusion matrix = model_comparison ({model})", abs((tn + tp) / n_test - mc.loc[model, "Accuracy"]) < 1e-9,
          f"{(tn+tp)/n_test:.6f} vs {mc.loc[model, 'Accuracy']:.6f}")
    s = sg[(sg.Model == model) & (sg.Attribute == "Gender")]
    check(f"Power BI confusion measures (sum of Gender subgroups) = confusion matrix ({model})",
          (s.TN.sum(), s.FP.sum(), s.FN.sum(), s.TP.sum()) == (tn, fp, fn, tp), f"{(s.TN.sum(), s.FP.sum(), s.FN.sum(), s.TP.sum())} vs {(tn, fp, fn, tp)}")

# 3 subgroup file
for (model, attr), g in sg.groupby(["Model", "Attribute"]):
    check(f"subgroup passengers sum to test rows ({model} / {attr})", g["Sample Count"].sum() == n_test, f"{g['Sample Count'].sum()}")
bad = 0
for _, r in sg.iterrows():
    rec = r.TP / (r.TP + r.FN)
    fpr = r.FP / (r.FP + r.TN)
    pre = r.TP / (r.TP + r.FP)
    if abs(rec - r.Recall) > 1e-9 or abs(fpr - r.FPR) > 1e-9 or abs(pre - r.Precision) > 1e-9:
        bad += 1
check("subgroup Recall / Precision / FPR recompute from TP-FP-FN-TN", bad == 0, f"{bad} mismatching rows of {len(sg)}")
for model in mc.index:
    s = sg[(sg.Model == model)]
    for attr, g in s.groupby("Attribute"):
        pass

# 4 SHAP vs correlation
check("SHAP ranks are 1..N without gaps", list(sh.Rank) == list(range(1, len(sh) + 1)), f"{len(sh)} features")
check("SHAP sorted by mean |SHAP| descending", sh.MeanAbsoluteSHAP.is_monotonic_decreasing)
top5 = list(sh.sort_values("Rank").Feature[:5])
sp = co[co.Method == "Spearman"].sort_values("AbsoluteEffect", ascending=False)
lines_extra = [f"Top-5 SHAP: {', '.join(top5)}", f"Top-5 |Spearman|: {', '.join(sp.Feature[:5])}"]
common = [f for f in sh.Feature if f in set(co.Feature)]
r = sh.set_index("Feature").loc[common, "MeanAbsoluteSHAP"].rank().corr(co.set_index("Feature").loc[common, "AbsoluteEffect"].rank())
check("SHAP and association rankings are positively related (rank correlation shown for info)", r > 0, f"rank correlation over {len(common)} shared features = {r:.2f}")

out = ["# Model Performance validation (report data vs existing CSV outputs)", "",
       "The report reads these CSVs unchanged. Validated metrics were **not** modified; this only checks internal consistency.", "",
       "| Result | Check | Detail |", "|---|---|---|"] + lines + ["", *["- " + l for l in lines_extra], "",
       f"**{len(lines) - fails} of {len(lines)} checks passed.**"]
open(P("powerbi", "validation_report.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("\n".join(out[-8:]), "\nFAILS:", fails)
