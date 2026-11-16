"""Turn saved local SHAP contributions into grounded Gemini explanations."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
import time

import pandas as pd
from google import genai
from google.genai import types

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SHAP_CSV = Path(__file__).resolve().parent / "shap_local_explanations.csv"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "gemini_insights.json"

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "explanation": {
            "type": "STRING",
            "description": "Plain-language summary of this model prediction, grounded only in supplied features.",
        },
        "evidence_features": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Exact feature names from the provided SHAP evidence that support the explanation.",
        },
        "service_improvement_suggestions": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "evidence_feature": {"type": "STRING"},
                    "recommendation": {"type": "STRING"},
                    "reason": {"type": "STRING"},
                },
                "required": ["evidence_feature", "recommendation", "reason"],
            },
        },
        "uncertainty_note": {
            "type": "STRING",
            "description": "State that SHAP describes this model prediction and does not establish causation.",
        },
    },
    "required": [
        "explanation",
        "evidence_features",
        "service_improvement_suggestions",
        "uncertainty_note",
    ],
}


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE entries without overwriting already-set environment values."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value and not os.environ.get(key):
            os.environ[key] = value


def json_safe(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def clean_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Gemini returned an empty or invalid {field}.")
    return value.strip()


def validate_generated_content(content: dict, allowed_features: set[str]) -> dict:
    """Reject claims that cite features absent from the exact input SHAP evidence."""
    explanation = clean_text(content.get("explanation"), "explanation")
    uncertainty = clean_text(content.get("uncertainty_note"), "uncertainty_note")
    evidence = content.get("evidence_features")
    suggestions = content.get("service_improvement_suggestions")
    if not isinstance(evidence, list) or not isinstance(suggestions, list):
        raise ValueError("Gemini response is missing evidence_features or suggestions arrays.")
    if not set(evidence).issubset(allowed_features):
        unknown = sorted(set(evidence) - allowed_features)
        raise ValueError(f"Gemini cited features absent from the supplied SHAP data: {unknown}")

    validated_suggestions = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict):
            raise ValueError("Gemini returned a malformed service suggestion.")
        feature = suggestion.get("evidence_feature")
        if feature not in allowed_features:
            raise ValueError(f"Suggestion cites a feature absent from the supplied SHAP data: {feature}")
        validated_suggestions.append(
            {
                "evidence_feature": feature,
                "recommendation": clean_text(suggestion.get("recommendation"), "recommendation"),
                "reason": clean_text(suggestion.get("reason"), "suggestion reason"),
            }
        )

    # Do not accept newly generated numeric importance/probability values in prose.
    # The source numbers are copied into the final JSON directly from the CSV below.
    generated_text = " ".join([explanation, uncertainty] + [
        f"{s['recommendation']} {s['reason']}" for s in validated_suggestions
    ])
    if re.search(r"(?<![A-Za-z])\d+(?:\.\d+)?\s*%|\b\d+\.\d{2,}\b", generated_text):
        raise ValueError("Gemini returned an unsupported numeric claim; refusing to export it.")
    return {
        "explanation": explanation,
        "evidence_features": list(dict.fromkeys(evidence)),
        "service_improvement_suggestions": validated_suggestions,
        "uncertainty_note": uncertainty,
    }


def prompt_for_passenger(passenger: dict, contributions: list[dict]) -> str:
    evidence_json = json.dumps(contributions, ensure_ascii=False, indent=2)
    return f"""Write a concise, student-friendly explanation of this one classifier prediction.

The model predicts the original binary airline Satisfaction target. The supplied SHAP
values are the only evidence you may use. Positive SHAP values push the model output
P(Satisfied) upward; negative values push it downward. SHAP describes the model, not
causation or what would happen if a service were changed.

Prediction metadata (already computed; do not recalculate or alter it):
{json.dumps(passenger, ensure_ascii=False, indent=2)}

Top local SHAP contributions (exact source values):
{evidence_json}

Requirements:
- Explain the predicted class and its probability in ordinary language. Do not restate
  or invent numeric values; the application will attach the exact class and probability.
- Refer only to exact feature names in the supplied evidence.
- Explain direction using the signed SHAP values, without calling it a cause.
- Suggest one or two practical areas the airline could review. Phrase them as review
  suggestions, not as proven fixes or causal interventions.
- Every evidence_features item and every suggestion evidence_feature must exactly match
  one of the supplied feature names.
- Do not invent feature-importance values, passenger details, metrics, or business facts.
- Return only the required JSON object.
"""


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        temporary_path = Path(tmp.name)
    temporary_path.replace(path)


def generate_with_fallback(client, primary_model: str, fallback_model: str, prompt: str):
    """Retry transient capacity errors, then try a second stable Flash model."""
    candidates = list(dict.fromkeys([primary_model, fallback_model]))
    transient_statuses = {429, 500, 503, 504}
    last_error = None
    for model_name in candidates:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                    ),
                )
                return response, model_name
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                if status_code not in transient_statuses:
                    raise
                last_error = exc
                if attempt == 0:
                    delay_seconds = 3 if status_code == 503 else 2
                    print(
                        f"Gemini {model_name} returned {status_code}; "
                        f"retrying in {delay_seconds}s.",
                        flush=True,
                    )
                    time.sleep(delay_seconds)
                else:
                    print(
                        f"Gemini {model_name} remained unavailable after retry.",
                        flush=True,
                    )
    raise RuntimeError(
        "Gemini generation failed on the primary and fallback models after retries. "
        "Wait a few minutes and rerun the command."
    ) from last_error


def generate_single_insight(
    client,
    passenger_rows: pd.DataFrame,
    primary_model: str,
    fallback_model: str,
) -> dict:
    """Generate and validate one passenger explanation from local SHAP rows."""
    passenger_rows = passenger_rows.sort_values("rank_by_absolute_contribution")
    metadata_row = passenger_rows.iloc[0]
    contribution_rows = passenger_rows.head(5)
    contributions = [
        {
            "feature": str(row["feature"]),
            "feature_value": json_safe(row["feature_value"]),
            "shap_value": float(row["shap_value"]),
            "direction": str(row["direction"]),
        }
        for _, row in contribution_rows.iterrows()
    ]
    allowed_features = {item["feature"] for item in contributions}
    passenger = {
        "row_index": int(metadata_row["row_index"]),
        "actual_class": str(metadata_row["actual_class"]),
        "predicted_class": str(metadata_row["predicted_class"]),
        "predicted_class_probability": float(metadata_row["predicted_class_probability"]),
        "probability_satisfied": float(metadata_row["probability_satisfied"]),
        "correct_prediction": bool(metadata_row["correct_prediction"]),
    }
    response, model_used = generate_with_fallback(
        client,
        primary_model,
        fallback_model,
        prompt_for_passenger(passenger, contributions),
    )
    if not response.text:
        raise ValueError(f"Gemini returned an empty response for passenger row {passenger['row_index']}.")
    generated = json.loads(response.text)
    validated = validate_generated_content(generated, allowed_features)
    return {
        **passenger,
        "model_used": model_used,
        "top_shap_contributions": contributions,
        **validated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_SHAP_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--env-file", type=Path, default=PROJECT_DIR / ".env")
    parser.add_argument("--model", default=None, help="Override GEMINI_MODEL from the environment.")
    parser.add_argument(
        "--fallback-model",
        default=None,
        help="Override GEMINI_FALLBACK_MODEL (default: gemini-3.7-flash).",
    )
    args = parser.parse_args()

    load_env_file(args.env_file)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            f"GEMINI_API_KEY is empty. Add your key to {args.env_file} and rerun this script."
        )
    model_name = args.model or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash").strip()
    if not model_name:
        model_name = "gemini-3.8-flash"
    fallback_model = args.fallback_model or os.environ.get(
        "GEMINI_FALLBACK_MODEL", "gemini-3.7-flash"
    ).strip()
    if not fallback_model:
        fallback_model = "gemini-3.7-flash"

    df = pd.read_csv(args.input)
    required = {
        "row_index", "actual_class", "predicted_class", "predicted_class_probability",
        "probability_satisfied", "correct_prediction", "feature", "feature_value",
        "shap_value", "direction", "rank_by_absolute_contribution",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Local SHAP CSV is missing required columns: {sorted(missing)}")

    # JSON-mode response schemas on the Gemini GenerateContent API are served by
    # v1beta. Set this explicitly so SDK defaults or local config cannot select v1.
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(api_version="v1beta"),
    )
    explanations = []
    for _, passenger_rows in df.groupby("row_index", sort=True):
        explanations.append(
            generate_single_insight(client, passenger_rows, model_name, fallback_model)
        )

    result = {
        "status": "complete",
        "target": {
            "name": "Satisfaction",
            "class_0": "Neutral or Dissatisfied",
            "class_1": "Satisfied",
            "probability_output": "P(Satisfied)",
        },
        "primary_model": model_name,
        "fallback_model": fallback_model,
        "source": str(args.input.resolve()),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "explanations": explanations,
    }
    atomic_write_json(args.output, result)
    print(f"Saved {len(explanations)} grounded explanations to {args.output}")


if __name__ == "__main__":
    main()
