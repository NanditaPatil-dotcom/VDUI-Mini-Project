"""Interactive Streamlit dashboard for Gemini explanations grounded in local SHAP."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

from generate_insights import (
    DEFAULT_OUTPUT,
    DEFAULT_SHAP_CSV,
    PROJECT_DIR,
    atomic_write_json,
    generate_single_insight,
    load_env_file,
)


st.set_page_config(
    page_title="Passenger Insight Studio",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { max-width: 1280px; padding-top: 2rem; padding-bottom: 3rem; }
      .hero { margin-top: 1.5rem; padding: 1.35rem 1.6rem; border-radius: 18px; color: white;
              background: linear-gradient(115deg, #173D75 0%, #2389ED 100%);
              margin-bottom: 1.25rem; }
      .hero-kicker { letter-spacing: .12em; text-transform: uppercase; font-size: .75rem;
                     opacity: .82; font-weight: 700; }
      .hero h1 { color: white; margin: .35rem 0 .25rem; font-size: 2rem; }
      .hero p { color: #e8f2ff; margin: 0; font-size: 1rem; }
      .section-label { color: #55708f; text-transform: uppercase; letter-spacing: .1em;
                       font-size: .75rem; font-weight: 700; margin-bottom: .35rem; }
      div[data-testid="stMetric"] { background: white; border: 1px solid #e1e8f0;
          border-radius: 14px; padding: .85rem 1rem; }
      div[data-testid="stMetricLabel"] { color: #55708f; }
      .stButton > button[kind="primary"] { border-radius: 10px; font-weight: 700; }
    </style>
    <div class="hero">
      <div class="hero-kicker">Airline passenger satisfaction · explainable AI</div>
      <h1>Passenger Insight Studio</h1>
      <p>Explore a model prediction, inspect its SHAP evidence, and generate a grounded Gemini explanation.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_shap_rows(path_string: str) -> pd.DataFrame:
    return pd.read_csv(path_string)


def read_insights(path: Path) -> dict:
    if not path.exists():
        return {"status": "pending", "explanations": []}
    with path.open(encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("Gemini insights JSON must contain a top-level object.")
    return value


def safe_model_name(value: str | None, fallback: str) -> str:
    name = value or fallback
    return name.strip() or fallback


def render_suggestions(insight: dict) -> None:
    suggestions = insight.get("service_improvement_suggestions", [])
    if not suggestions:
        st.info("Gemini did not return a service review suggestion for this passenger.")
        return
    for item in suggestions:
        with st.container(border=True):
            st.markdown(f"**Review area:** {item.get('evidence_feature', 'SHAP feature')}")
            st.write(item.get("recommendation", ""))
            if item.get("reason"):
                st.caption(item["reason"])


def main() -> None:
    # Read model choices for display and generation; the API key remains hidden.
    load_env_file(PROJECT_DIR / ".env")
    st.markdown('<div class="section-label">Prediction workspace</div>', unsafe_allow_html=True)
    try:
        shap_rows = load_shap_rows(str(DEFAULT_SHAP_CSV))
        insight_file = read_insights(DEFAULT_OUTPUT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        st.error(f"Could not load the SHAP or Gemini data: {exc}")
        st.stop()

    required_columns = {
        "row_index", "actual_class", "predicted_class", "predicted_class_probability",
        "probability_satisfied", "correct_prediction", "feature", "feature_value",
        "shap_value", "direction", "rank_by_absolute_contribution",
    }
    missing = required_columns - set(shap_rows.columns)
    if missing:
        st.error(f"The SHAP CSV is missing required fields: {', '.join(sorted(missing))}")
        st.stop()
    if shap_rows.empty:
        st.warning("No local SHAP explanations are available yet. Run the individual explanation step first.")
        st.stop()

    existing_insights = {
        int(item["row_index"]): item
        for item in insight_file.get("explanations", [])
        if isinstance(item, dict) and "row_index" in item
    }
    passenger_ids = sorted(shap_rows["row_index"].astype(int).unique().tolist())
    metadata = shap_rows.drop_duplicates("row_index").set_index("row_index")

    def passenger_label(row_index: int) -> str:
        row = metadata.loc[row_index]
        prediction = str(row["predicted_class"])
        confidence = float(row["predicted_class_probability"])
        return f"Passenger {row_index} · {prediction} · {confidence:.1%} confidence"

    with st.sidebar:
        st.markdown("### Select a passenger")
        selected_row = st.selectbox(
            "Passenger example",
            passenger_ids,
            format_func=passenger_label,
            label_visibility="collapsed",
        )
        st.caption("Examples come from the held-out test split and are selected from the local SHAP CSV.")
        st.divider()
        model_primary = safe_model_name(os.environ.get("GEMINI_MODEL"), "gemini-3.8-flash")
        model_fallback = safe_model_name(os.environ.get("GEMINI_FALLBACK_MODEL"), "gemini-3.7-flash")
        st.caption(f"Primary: `{model_primary}`")
        st.caption(f"Fallback: `{model_fallback}`")
        st.caption("The Gemini API key is read locally from `.env` when you click generate.")

    passenger_rows = shap_rows[shap_rows["row_index"].astype(int) == int(selected_row)].copy()
    passenger_rows = passenger_rows.sort_values("rank_by_absolute_contribution")
    row = passenger_rows.iloc[0]
    saved_insight = existing_insights.get(int(selected_row))

    st.markdown('<div class="section-label">Model result</div>', unsafe_allow_html=True)
    metric_cols = st.columns(2)
    metric_cols[0].metric("Predicted class", str(row["predicted_class"]))
    metric_cols[1].metric("Confidence in prediction", f"{float(row['predicted_class_probability']):.1%}")
    metric_cols = st.columns(2)
    metric_cols[0].metric("Actual class", str(row["actual_class"]))
    metric_cols[1].metric("Prediction check", "Correct" if bool(row["correct_prediction"]) else "Incorrect")

    probability_satisfied = float(row["probability_satisfied"])
    st.write(f"**Probability of Satisfied:** {probability_satisfied:.1%}")
    st.progress(max(0, min(100, round(probability_satisfied * 100))))

    action_label = "Regenerate Gemini insight" if saved_insight else "Generate Gemini insight"
    if st.button(action_label, type="primary", use_container_width=False):
        load_env_file(PROJECT_DIR / ".env")
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            st.error("GEMINI_API_KEY is empty. Add it to the project `.env` file and try again.")
        else:
            with st.spinner("Generating a SHAP-grounded explanation with Gemini…"):
                try:
                    client = genai.Client(
                        api_key=api_key,
                        http_options=types.HttpOptions(api_version="v1beta"),
                    )
                    generated = generate_single_insight(
                        client,
                        passenger_rows,
                        model_primary,
                        model_fallback,
                    )
                    insight_file.update(
                        {
                            "status": "complete",
                            "target": {
                                "name": "Satisfaction",
                                "class_0": "Neutral or Dissatisfied",
                                "class_1": "Satisfied",
                                "probability_output": "P(Satisfied)",
                            },
                            "primary_model": model_primary,
                            "fallback_model": model_fallback,
                            "source": str(DEFAULT_SHAP_CSV.resolve()),
                            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    previous = [
                        item for item in insight_file.get("explanations", [])
                        if int(item.get("row_index", -1)) != int(selected_row)
                    ]
                    insight_file["explanations"] = sorted(
                        previous + [generated], key=lambda item: int(item["row_index"])
                    )
                    atomic_write_json(DEFAULT_OUTPUT, insight_file)
                    st.success("Gemini insight generated and saved.")
                    st.rerun()
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None)
                    detail = getattr(exc, "message", None) or str(exc)
                    if api_key:
                        detail = detail.replace(api_key, "[redacted]")
                    st.error(f"Gemini request failed{f' ({status_code})' if status_code else ''}: {detail}")

    if saved_insight:
        st.markdown('<div class="section-label">Gemini explanation</div>', unsafe_allow_html=True)
        st.write(saved_insight.get("explanation", "No explanation text was saved."))
        st.caption(f"Generated with `{saved_insight.get('model_used', insight_file.get('model', insight_file.get('primary_model', 'Gemini')))}`")
    else:
        st.info("No Gemini insight is saved for this passenger yet. Click **Generate Gemini insight** to create one.")

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.markdown('<div class="section-label">Why the model predicted this</div>', unsafe_allow_html=True)
        st.subheader("Top SHAP contributions")
        contribution_view = passenger_rows.head(5).copy()
        contribution_view["feature"] = contribution_view["feature"].astype(str)
        chart_data = contribution_view.set_index("feature")["shap_value"]
        st.bar_chart(chart_data, horizontal=True, color="#2389ED")
        display = contribution_view[["feature", "feature_value", "shap_value", "direction"]].rename(
            columns={
                "feature": "Feature",
                "feature_value": "Passenger value",
                "shap_value": "SHAP impact on P(Satisfied)",
                "direction": "Contribution direction",
            }
        )
        st.dataframe(
            display,
            hide_index=True,
            use_container_width=True,
            column_config={"SHAP impact on P(Satisfied)": st.column_config.NumberColumn(format="%+.3f")},
        )

    with right:
        st.markdown('<div class="section-label">Potential service follow-up</div>', unsafe_allow_html=True)
        st.subheader("Gemini suggestions")
        if saved_insight:
            render_suggestions(saved_insight)
            if saved_insight.get("uncertainty_note"):
                st.caption(saved_insight["uncertainty_note"])
        else:
            st.write("Suggestions appear here after you generate an insight.")

    with st.expander("View exact SHAP evidence sent to Gemini"):
        st.json(
            [
                {
                    "feature": str(item["feature"]),
                    "feature_value": item["feature_value"],
                    "shap_value": float(item["shap_value"]),
                    "direction": str(item["direction"]),
                }
                for _, item in passenger_rows.head(5).iterrows()
            ]
        )

    st.divider()
    generated_at = insight_file.get("generated_at_utc")
    source_status = "Saved insights loaded from gemini_insights.json"
    if generated_at:
        source_status += f" · Last saved {generated_at}"
    st.caption(f"{source_status} · SHAP describes the model’s associations; it does not prove causation.")


if __name__ == "__main__":
    main()
