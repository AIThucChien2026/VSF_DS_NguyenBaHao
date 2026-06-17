from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from .predict import model_info, predict_payload
    from .transform import transform_payload
except ImportError:  # pragma: no cover - supports running app.py directly
    from predict import model_info, predict_payload
    from transform import transform_payload


app = FastAPI(
    title="Customer Return Prediction API",
    description="Inference API for cleaning raw order data, creating 28 selected features, and predicting return risk.",
    version="1.0.0",
)


class InferenceRequest(BaseModel):
    orders: list[dict[str, Any]] = Field(..., description="Raw order records to transform or predict.")


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        info = model_info()
    except Exception as exc:  # noqa: BLE001 - API should return readable health status
        return {"status": "error", "model_loaded": False, "detail": str(exc)}
    return {
        "status": "ok",
        "model_loaded": True,
        "feature_count": info["feature_count"],
        "threshold": info["threshold"],
    }


@app.get("/model-info")
def get_model_info() -> dict[str, Any]:
    try:
        return model_info()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/transform")
def transform(request: InferenceRequest) -> dict[str, Any]:
    try:
        return transform_payload(request.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/predict")
def predict(request: InferenceRequest) -> dict[str, Any]:
    try:
        return predict_payload(request.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
