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
