from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

try:
    from .transform import FEATURE_COLS, transform_orders
except ImportError:  # pragma: no cover - supports direct script imports
    from transform import FEATURE_COLS, transform_orders


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = PROJECT_ROOT / "report_14_6_2026" / "modeling_outputs" / "models" / "final_model.joblib"
DEFAULT_THRESHOLD = 0.06335713951173381


@lru_cache(maxsize=1)
def load_model_bundle() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

    artifact = joblib.load(MODEL_PATH)
    if isinstance(artifact, dict):
        model = artifact.get("model")
        feature_cols = artifact.get("feature_cols") or FEATURE_COLS
        threshold = float(artifact.get("threshold", DEFAULT_THRESHOLD))
        champion_summary = artifact.get("champion_summary", {})
    else:
        model = artifact
        feature_cols = FEATURE_COLS
        threshold = DEFAULT_THRESHOLD
        champion_summary = {}

    if model is None:
        raise ValueError("Model artifact does not contain a usable model.")

    return {
        "model": model,
        "feature_cols": list(feature_cols),
        "threshold": threshold,
        "champion_summary": champion_summary,
        "model_source": str(MODEL_PATH),
    }


def model_info() -> dict[str, Any]:
    bundle = load_model_bundle()
    return {
        "model_source": bundle["model_source"],
        "threshold": bundle["threshold"],
        "feature_count": len(bundle["feature_cols"]),
        "feature_columns": bundle["feature_cols"],
        "champion_summary": bundle["champion_summary"],
    }


def predict_features(features: pd.DataFrame) -> list[dict[str, Any]]:
    bundle = load_model_bundle()
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    threshold = bundle["threshold"]

    aligned = features.reindex(columns=feature_cols, fill_value=0)
    probabilities = model.predict_proba(aligned)[:, 1]

    return [
        {
            "return_probability": float(probability),
            "prediction": int(probability >= threshold),
            "threshold": threshold,
            "model_source": bundle["model_source"],
        }
        for probability in probabilities
    ]


def predict_payload(payload: Any) -> dict[str, Any]:
    records = payload if isinstance(payload, list) else None
    if records is None and isinstance(payload, dict):
        for key in ("orders", "records", "data"):
            if isinstance(payload.get(key), list):
                records = payload[key]
                break
        if records is None:
            records = [payload]
    if records is None:
        raise ValueError("Payload must be an object or a list of objects.")

    features = transform_orders(records)
    predictions = predict_features(features)
    feature_records = features.to_dict(orient="records")

    results = []
    for raw_record, feature_record, prediction in zip(records, feature_records, predictions):
        results.append(
            {
                "order_id": raw_record.get("order_id") if isinstance(raw_record, dict) else None,
                **prediction,
                "features_used": feature_record,
            }
        )

    return {"count": len(results), "results": results}
