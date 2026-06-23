# api/app.py
"""
FastAPI app — nhận request → clean data → gọi MLflow serving → trả predictions.

App này không load model trực tiếp. Model được serve bởi MLflow ở port 8001.
App chỉ đóng vai trò trung gian: nhận file path → clean → forward → parse kết quả.

Chạy server:
  uvicorn api.app:app --reload --port 8000

Swagger UI:
  http://localhost:8000/docs
"""

import logging
import os
from contextlib import asynccontextmanager

import httpx
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from scripts.clean_data import clean_data
from scripts.inference_pipeline import FeatureBuilder, LOCKED_THRESHOLD

logger = logging.getLogger(__name__)

# MLflow serving endpoint — chạy ở container mlflow_serving port 8001
MLFLOW_SERVING_URL = os.getenv("MLFLOW_SERVING_URL", "http://localhost:8001")
INVOCATIONS_URL    = f"{MLFLOW_SERVING_URL}/invocations"


# ── Startup check ────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Kiểm tra MLflow serving có sẵn sàng không khi server khởi động."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{MLFLOW_SERVING_URL}/health")
            if resp.status_code == 200:
                logger.info(f"✓ MLflow serving sẵn sàng tại {MLFLOW_SERVING_URL}")
            else:
                logger.warning(f"⚠ MLflow serving trả về status {resp.status_code}")
    except Exception as e:
        logger.warning(f"⚠ Không kết nối được MLflow serving: {e}")
    yield


app = FastAPI(
    title="Customer Return Prediction API",
    description=(
        "Nhận đường dẫn thư mục CSV → clean data → "
        "gọi MLflow serving → trả về predictions."
    ),
    version="3.0",
    lifespan=lifespan,
)


# ── Pydantic Schemas ──────────────────────────────────────

class PredictRequest(BaseModel):
    data_dir: str = Field(
        ...,
        description="Đường dẫn thư mục chứa 5 file CSV",
        example="data/",
    )


class PredictionItem(BaseModel):
    order_id: str
    return_probability: float
    prediction: int
    threshold: float


class PredictResponse(BaseModel):
    n_predictions: int
    positive_rate: float
    predictions: list[PredictionItem]


# ── Helper: gọi MLflow /invocations ──────────────────────

def _call_mlflow_serving(cleaned_df: pd.DataFrame) -> list:
    """
    Gửi cleaned_df sang MLflow serving, nhận về predictions.

    MLflow /invocations nhận JSON format dataframe_split:
      {
        "dataframe_split": {
          "columns": [...],
          "data": [[...], [...]]
        }
      }

    MLflow trả về:
      {"predictions": [0, 1, 0, ...]}

    Returns:
        list predictions raw từ MLflow
    """
    payload = {
        "dataframe_split": {
            "columns": cleaned_df.columns.tolist(),
            "data":    cleaned_df.values.tolist(),
        }
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                INVOCATIONS_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        response.raise_for_status()
        return response.json()["predictions"]

    except httpx.ConnectError:
        raise RuntimeError(
            f"Không kết nối được MLflow serving tại {INVOCATIONS_URL}.\n"
            f"Kiểm tra container mlflow_serving đang chạy."
        )
    except httpx.TimeoutException:
        raise RuntimeError("MLflow serving timeout — data quá lớn hoặc serving bị treo.")
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"MLflow serving lỗi {e.response.status_code}: {e.response.text}")


# ── Endpoints ─────────────────────────────────────────────

@app.get("/health", summary="Kiểm tra trạng thái app và MLflow serving")
async def health():
    """Kiểm tra app và kết nối tới MLflow serving."""
    mlflow_ok = False
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{MLFLOW_SERVING_URL}/health")
            mlflow_ok = resp.status_code == 200
    except Exception:
        pass

    return {
        "status":          "ok" if mlflow_ok else "mlflow_serving_unavailable",
        "mlflow_serving":  mlflow_ok,
        "invocations_url": INVOCATIONS_URL,
        "threshold":       LOCKED_THRESHOLD,
    }


@app.post("/clean", summary="Làm sạch dữ liệu")
def clean_endpoint(request: PredictRequest):
    """Chỉ chạy bước clean_data — dùng để debug khi nghi ngờ data có vấn đề."""
    try:
        cleaned_df, summary = clean_data(request.data_dir)
        return {
            "summary":       summary,
            "sample_5_rows": cleaned_df.head(5).to_dict(orient="records"),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/features", summary="Tạo đặc trưng từ dữ liệu đầu vào")
def features_endpoint(request: PredictRequest):
    """Chạy clean_data + FeatureBuilder — verify features trước khi gửi vào MLflow."""
    try:
        cleaned_df, _ = clean_data(request.data_dir)
        features_df   = FeatureBuilder().transform(cleaned_df)
        return {
            "n_rows":        len(features_df),
            "n_cols":        len(features_df.columns),
            "columns":       features_df.columns.tolist(),
            "sample_5_rows": features_df.head(5).to_dict(orient="records"),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post(
    "/predict",
    response_model=PredictResponse,
    summary="Full pipeline: clean → MLflow serving → predictions",
)
def predict_endpoint(request: PredictRequest):
    """
    Endpoint chính.

    Luồng:
      1. clean_data(data_dir)  → cleaned_df
      2. gửi cleaned_df        → MLflow /invocations
      3. MLflow chạy Pipeline  → predictions (0/1)
      4. ghép order_id + label → trả về client

    Request:  {"data_dir": "data/"}
    Response: {"n_predictions": N, "positive_rate": 0.08, "predictions": [...]}
    """
    try:
        cleaned_df, _ = clean_data(request.data_dir)
        order_ids     = cleaned_df["order_id"].tolist()

        # Gọi MLflow serving — trả về list label [0, 1, 0, ...]
        # ThresholdedClassifierWrapper.predict() đã apply threshold bên trong Pipeline
        raw_predictions = _call_mlflow_serving(cleaned_df)

        results = [
            PredictionItem(
                order_id=str(order_id),
                return_probability=float(pred),
                prediction=int(pred),
                threshold=LOCKED_THRESHOLD,
            )
            for order_id, pred in zip(order_ids, raw_predictions)
        ]

        positive_rate = sum(r.prediction for r in results) / len(results) if results else 0.0

        return PredictResponse(
            n_predictions=len(results),
            positive_rate=positive_rate,
            predictions=results,
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))