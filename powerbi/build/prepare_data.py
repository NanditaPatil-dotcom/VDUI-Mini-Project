"""Flatten explainability/gemini_insights.json into Power BI friendly CSVs (one row per passenger / per suggestion)."""
import json
import os

import pandas as pd

CLASS_SHORT = {"Satisfied": "Satisfied", "Neutral or Dissatisfied": "Neutral/Dissatisfied"}


def _load(root):
    with open(os.path.join(root, "explainability", "gemini_insights.json"), encoding="utf-8") as f:
        return json.load(f)


def _label(e):
    return f"Passenger #{e['row_index']} - predicted {CLASS_SHORT.get(e['predicted_class'], e['predicted_class'])}"


def first_label(root):
    return _label(_load(root)["explanations"][0])


def run(root):
    j = _load(root)
    rows, recs = [], []
    for e in j["explanations"]:
        rows.append({
            "Passenger Index": e["row_index"], "Passenger Label": _label(e), "Actual Class": e["actual_class"],
            "Predicted Class": e["predicted_class"], "Predicted Probability": e["predicted_class_probability"],
            "Probability Satisfied": e["probability_satisfied"], "Correct Prediction": "Yes" if e["correct_prediction"] else "No",
            "Explanation": e["explanation"], "Evidence Features": ", ".join(e.get("evidence_features", [])),
            "Uncertainty Note": e.get("uncertainty_note", ""), "Gemini Model": j.get("model", ""), "Generated At": j.get("generated_at_utc", "")})
        for s in e.get("service_improvement_suggestions", []):
            recs.append({"Passenger Index": e["row_index"], "Evidence Feature": s["evidence_feature"],
                         "Recommendation": s["recommendation"], "Reason": s["reason"]})
    out = os.path.join(root, "powerbi", "data")
    os.makedirs(out, exist_ok=True)
    pd.DataFrame(rows).to_csv(os.path.join(out, "gemini_insights_flat.csv"), index=False, encoding="utf-8")
    pd.DataFrame(recs, columns=["Passenger Index", "Evidence Feature", "Recommendation", "Reason"]).to_csv(
        os.path.join(out, "gemini_recommendations_flat.csv"), index=False, encoding="utf-8")
    return len(rows), len(recs)


if __name__ == "__main__":
    print(run(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))))
