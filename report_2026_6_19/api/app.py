# # api/app.py
# """
# FastAPI app — nhận input → (nếu cần) aggregate → load Pipeline từ MLflow → predict.

# Kiến trúc:
#   - aggregate.py  : chạy LOCAL trên máy này (join bảng CSV)
#   - sklearn Pipeline (feature_builder + preprocessor + classifier): load từ MLflow Registry
#   - Không proxy qua mlflow serving /invocations — load trực tiếp bằng mlflow.sklearn.load_model()

# 3 loại input của /predict:
#   1. {"input_type": "data_dir", "data_dir": "data/"}
#      → gọi aggregate() → master DataFrame → pipeline.predict()

#   2. {"input_type": "joined_table", "records": [...]}
#      → chuyển thẳng thành DataFrame → pipeline.predict()

#   3. {"input_type": "single_record", "record": {...}}
#      → chuyển thành DataFrame 1 dòng → pipeline.predict()

# Chạy server:
#   uvicorn api.app:app --reload --port 8000

# Swagger UI:
#   http://localhost:8000/docs
# """

# import logging
# import os
# import sys
# from contextlib import asynccontextmanager
# from pathlib import Path
# from typing import Any

# import mlflow.sklearn
# import numpy as np
# import pandas as pd
# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Field

# if __package__ in (None, ""):
#     sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# from scripts.aggregate import aggregate
# from scripts.inference_pipeline import (
#     LOCKED_THRESHOLD,
#     FeatureBuilder,
# )

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s  %(levelname)s  %(message)s",
#     datefmt="%H:%M:%S",
# )
# logger = logging.getLogger(__name__)


# # ─────────────────────────────────────────────────────────────────────────────
# #  CẤU HÌNH
# # ─────────────────────────────────────────────────────────────────────────────

# MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
# MLFLOW_MODEL_URI    = os.getenv(
#     "MLFLOW_MODEL_URI",
#     "models:/customer-return-champion@champion",
# )

# mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


# # ─────────────────────────────────────────────────────────────────────────────
# #  GLOBAL PIPELINE — load 1 lần khi khởi động, tái dùng cho mọi request
# # ─────────────────────────────────────────────────────────────────────────────

# _pipeline = None   # sklearn Pipeline (feature_builder → preprocessor → classifier)


# def _load_pipeline():
#     """
#     Load sklearn Pipeline từ MLflow Registry.

#     Pipeline bao gồm đầy đủ 3 bước:
#       _PipelineInputAdapter (FeatureBuilder) → ColumnTransformer → ThresholdedClassifierWrapper

#     Gọi pipeline.predict(master_df)    → nhãn 0/1
#     Gọi pipeline.predict_proba(master_df) → xác suất [[p0, p1], ...]

#     Raises:
#         RuntimeError nếu load thất bại
#     """
#     global _pipeline
#     try:
#         logger.info(f"Đang load Pipeline từ MLflow: {MLFLOW_MODEL_URI}")
#         _pipeline = mlflow.sklearn.load_model(MLFLOW_MODEL_URI)
#         logger.info("✓ Pipeline loaded thành công từ MLflow")
#     except Exception as e:
#         logger.error(f"✗ Load Pipeline thất bại: {e}")
#         _pipeline = None
#         raise RuntimeError(
#             f"Không thể load Pipeline từ MLflow URI: '{MLFLOW_MODEL_URI}'\n"
#             f"Lỗi: {e}\n"
#             f"Kiểm tra: MLflow server đang chạy tại {MLFLOW_TRACKING_URI}? "
#             f"Model đã register chưa? Chạy register_pipeline.py trước."
#         ) from e


# # ─────────────────────────────────────────────────────────────────────────────
# #  LIFESPAN — startup/shutdown
# # ─────────────────────────────────────────────────────────────────────────────

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Load Pipeline từ MLflow khi server khởi động."""
#     try:
#         _load_pipeline()
#     except RuntimeError as e:
#         # Warning thay vì crash — cho phép server khởi động dù Pipeline chưa có
#         # /health sẽ báo pipeline_loaded = false để biết trạng thái
#         logger.warning(f"⚠ Server khởi động với Pipeline chưa load được:\n{e}")
#     yield
#     # Shutdown: không cần cleanup gì đặc biệt


# # ─────────────────────────────────────────────────────────────────────────────
# #  APP
# # ─────────────────────────────────────────────────────────────────────────────

# app = FastAPI(
#     title="Customer Return Prediction API",
#     description=(
#         "Nhận input (data_dir / joined_table / single_record) "
#         "→ aggregate nếu cần → load Pipeline từ MLflow → predict."
#     ),
#     version="4.0",
#     lifespan=lifespan,
#     swagger_ui_parameters={"requestTimeout": 300_000},
# )


# # ─────────────────────────────────────────────────────────────────────────────
# #  PYDANTIC SCHEMAS
# # ─────────────────────────────────────────────────────────────────────────────

# class PredictRequest(BaseModel):
#     input_type: str = Field(
#         ...,
#         description=(
#             "Loại input:\n"
#             "  'data_dir'      : thư mục chứa 5 file CSV chưa join\n"
#             "  'joined_table'  : danh sách records đã join sẵn (list[dict])\n"
#             "  'single_record' : 1 record đã join sẵn (dict)"
#         ),
#         examples=["data_dir", "joined_table", "single_record"],
#     )

#     # Dùng cho input_type = "data_dir"
#     data_dir: str | None = Field(
#         default=None,
#         description="Đường dẫn thư mục CSV (chỉ dùng khi input_type='data_dir')",
#         examples=["data/"],
#     )

#     # Dùng cho input_type = "joined_table"
#     records: list[dict[str, Any]] | None = Field(
#         default=None,
#         description=(
#             "Danh sách records đã join sẵn "
#             "(chỉ dùng khi input_type='joined_table')"
#         ),
#     )

#     # Dùng cho input_type = "single_record"
#     record: dict[str, Any] | None = Field(
#         default=None,
#         description=(
#             "1 record đã join sẵn "
#             "(chỉ dùng khi input_type='single_record')"
#         ),
#     )


# class PredictionItem(BaseModel):
#     order_id:           str
#     return_probability: float
#     prediction:         int
#     threshold:          float


# class PredictResponse(BaseModel):
#     n_predictions: int
#     positive_rate: float
#     predictions:   list[PredictionItem]


# # ─────────────────────────────────────────────────────────────────────────────
# #  HELPER: chuẩn bị master DataFrame từ request
# # ─────────────────────────────────────────────────────────────────────────────

# def _prepare_master_df(request: PredictRequest) -> pd.DataFrame:
#     """
#     Chuyển request thành master DataFrame sẵn sàng đưa vào Pipeline.

#     - data_dir      → gọi aggregate() từ local → master DataFrame
#     - joined_table  → chuyển records list thành DataFrame trực tiếp
#     - single_record → chuyển 1 dict thành DataFrame 1 dòng
#     """
#     if request.input_type == "data_dir":
#         if not request.data_dir:
#             raise ValueError(
#                 "input_type='data_dir' nhưng thiếu trường 'data_dir'."
#             )
#         logger.info(f"Aggregate từ data_dir: '{request.data_dir}'")
#         return aggregate(request.data_dir)

#     if request.input_type == "joined_table":
#         if not request.records:
#             raise ValueError(
#                 "input_type='joined_table' nhưng thiếu trường 'records'."
#             )
#         logger.info(f"Input là joined_table: {len(request.records)} records")
#         return pd.DataFrame(request.records)

#     if request.input_type == "single_record":
#         if not request.record:
#             raise ValueError(
#                 "input_type='single_record' nhưng thiếu trường 'record'."
#             )
#         logger.info("Input là single_record")
#         return pd.DataFrame([request.record])

#     raise ValueError(
#         f"input_type '{request.input_type}' không hợp lệ. "
#         f"Chỉ chấp nhận: 'data_dir', 'joined_table', 'single_record'."
#     )

# # ─────────────────────────────────────────────────────────────────────────────
# #  HELPER: chạy predict qua Pipeline từ MLflow
# # ─────────────────────────────────────────────────────────────────────────────

# def _run_pipeline(master_df: pd.DataFrame) -> tuple[list, np.ndarray, float]:
#     """
#     Đưa master_df qua Pipeline từ MLflow.
#     Returns:
#         (labels, probabilities, actual_threshold)
#     """
#     if _pipeline is None:
#         raise RuntimeError(
#             "Pipeline chưa được load từ MLflow.\n"
#             "Kiểm tra /health để xem chi tiết. "
#             "Chạy register_pipeline.py nếu chưa register model."
#         )

#     labels       = _pipeline.predict(master_df)
#     proba_matrix = _pipeline.predict_proba(master_df)  # shape (n, 2)
#     probabilities = proba_matrix[:, 1]                 # lấy cột P(return)

#     # ── TRÍCH XUẤT THRESHOLD TỰ ĐỘNG TỪ MLFLOW MÔ HÌNH ────────────────────────
#     # Bước cuối cùng trong Pipeline là ThresholdedClassifierWrapper
#     try:
#         actual_threshold = _pipeline.steps[-1][1].threshold
#     except Exception:
#         # Phòng hờ nếu cấu trúc pipeline thay đổi thì lấy default từ config
#         actual_threshold = getattr(_pipeline, "threshold", 0.5)

#     return labels.tolist(), probabilities, float(actual_threshold)


# # ─────────────────────────────────────────────────────────────────────────────
# #  ENDPOINTS
# # ─────────────────────────────────────────────────────────────────────────────

# @app.get("/health", summary="Kiểm tra trạng thái app và Pipeline")
# async def health():
#     # Lấy threshold động từ model nếu đã load thành công
#     current_thresh = 0.5
#     if _pipeline is not None:
#         try:
#             current_thresh = _pipeline.steps[-1][1].threshold
#         except Exception:
#             pass

#     return {
#         "status":          "ok" if _pipeline is not None else "pipeline_not_loaded",
#         "pipeline_loaded": _pipeline is not None,
#         "mlflow_uri":      MLFLOW_MODEL_URI,
#         "mlflow_tracking": MLFLOW_TRACKING_URI,
#         "threshold":       current_thresh, # Lấy chuẩn từ MLflow mô hình
#     }


# @app.post(
#     "/predict",
#     response_model=PredictResponse,
#     summary="Predict customer return — nhận 3 loại input",
# )
# def predict_endpoint(request: PredictRequest):
#     try:
#         # ── Bước 1: Chuẩn bị master DataFrame ────────────────────────────────
#         master_df = _prepare_master_df(request)

#         if master_df.empty:
#             raise ValueError("Input không có dòng dữ liệu nào.")

#         # ── Bước 2: Lấy order_ids trước khi Pipeline transform ────────────────
#         if "order_id" not in master_df.columns:
#             raise ValueError(
#                 "Master DataFrame thiếu cột 'order_id'.\n"
#                 "Kiểm tra lại input."
#             )
#         order_ids = master_df["order_id"].astype(str).tolist()

#         # ── Bước 3: Chạy Pipeline từ MLflow & Lấy ngưỡng thực tế ──────────────
#         labels, probabilities, actual_threshold = _run_pipeline(master_df)

#         # ── Bước 4: Ghép kết quả dùng chính xác actual_threshold ──────────────
#         results = [
#             PredictionItem(
#                 order_id=          str(order_id),
#                 return_probability=float(prob),
#                 prediction=        int(label),
#                 threshold=         actual_threshold, # <-- Chuẩn xác 100% từ MLflow mang xuống
#             )
#             for order_id, prob, label in zip(order_ids, probabilities, labels)
#         ]

#         positive_rate = (
#             sum(r.prediction for r in results) / len(results)
#             if results else 0.0
#         )

#         logger.info(
#             f"Predict xong: {len(results)} orders, "
#             f"positive_rate={positive_rate:.3f} (Dùng ngưỡng: {actual_threshold})"
#         )

#         return PredictResponse(
#             n_predictions=len(results),
#             positive_rate=positive_rate,
#             predictions=results,
#         )

#     except (FileNotFoundError, KeyError) as e:
#         raise HTTPException(status_code=400, detail=str(e))
#     except ValueError as e:
#         raise HTTPException(status_code=422, detail=str(e))
#     except RuntimeError as e:
#         raise HTTPException(status_code=503, detail=str(e))
#     except Exception as e:
#         logger.exception(f"Lỗi không xác định: {e}")
#         raise HTTPException(status_code=500, detail=f"Lỗi server: {e}")

# # ─────────────────────────────────────────────────────────────────────────────
# #  KHỞI CHẠY SERVER DIRECTLY (CHẠY BẰNG LỆNH PYTHON)
# # ─────────────────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     import uvicorn

#     logger.info("Chạy FastAPI server bằng uvicorn.run...")
    
#     # Sử dụng dạng chuỗi "api.app:app" để Uvicorn hỗ trợ tính năng --reload chuẩn xác
#     uvicorn.run(
#         "api.app:app",
#         host="0.0.0.0",
#         port=8000,
#         reload=True,
#         log_level="info",
#     )
# api/app.py
"""
FastAPI app — Nhận thẳng dữ liệu phẳng (Single Record hoặc Batch chứa sẵn 28 features)
→ Không join, không aggregate → Đưa trực tiếp vào Pipeline của MLflow → Predict.

2 loại input mới:
  1. {"input_type": "batch", "records": [{"order_id": "...", "customer_id": "...", "age_group": "..."}, ...]}
  2. {"input_type": "single_record", "record": {"order_id": "...", "customer_id": "...", "age_group": "..."}}
"""

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import mlflow.sklearn
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ĐÃ XÓA: Bỏ hoàn toàn import aggregate từ scripts.aggregate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  CẤU HÌNH MLFLOW
# ─────────────────────────────────────────────────────────────────────────────

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_MODEL_URI    = os.getenv(
    "MLFLOW_MODEL_URI",
    "models:/customer-return-champion@champion",
)

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


# ─────────────────────────────────────────────────────────────────────────────
#  GLOBAL PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

_pipeline = None 


def _load_pipeline():
    global _pipeline
    try:
        logger.info(f"Đang load Pipeline từ MLflow: {MLFLOW_MODEL_URI}")
        _pipeline = mlflow.sklearn.load_model(MLFLOW_MODEL_URI)
        logger.info("✓ Pipeline loaded thành công từ MLflow")
    except Exception as e:
        logger.error(f"✗ Load Pipeline thất bại: {e}")
        _pipeline = None
        raise RuntimeError(f"Không thể load Pipeline từ MLflow. Lỗi: {e}") from e


# ─────────────────────────────────────────────────────────────────────────────
#  LIFESPAN
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        _load_pipeline()
    except RuntimeError as e:
        logger.warning(f"⚠ Server khởi động với Pipeline chưa load được:\n{e}")
    yield


# ─────────────────────────────────────────────────────────────────────────────
#  APP INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Customer Return Prediction API",
    description="Nhận trực tiếp 1 bản ghi phẳng hoặc 1 batch dữ liệu phẳng gồm 28 features để dự đoán.",
    version="6.0",
    lifespan=lifespan,
    swagger_ui_parameters={"requestTimeout": 300_000},
)


# ─────────────────────────────────────────────────────────────────────────────
#  PYDANTIC SCHEMAS (Đã cập nhật theo JSON phẳng của bạn)
# ─────────────────────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    input_type: str = Field(
        ...,
        description=(
            "Loại input:\n"
            "  'batch'         : Danh sách nhiều record phẳng gom lại\n"
            "  'single_record' : Đúng 1 record phẳng duy nhất"
        ),
        examples=["batch", "single_record"],
    )

    # Dạng Batch: Danh sách các JSON phẳng (Mỗi JSON có 28 features)
    records: list[dict[str, Any]] | None = Field(
        default=None,
        description="Mảng các record phẳng chứa sẵn đầy đủ thông tin (Dùng cho input_type='batch')",
        examples=[[
            {
                "order_id": "ORD-TEST-001", "customer_id": "CUST-001", "order_date": "2024-03-15",
                "order_status": "delivered", "order_source": "app", "device_type": "mobile",
                "signup_date": "2023-06-01", "gender": "Male", "age_group": "25-34",
                "product_id": "PROD-001", "quantity": 2, "unit_price": 350000,
                "discount_amount": 35000, "category": "Casual", "segment": "Everyday",
                "size": "M", "payment_method": "MOMO", "payment_value": 665000
            }
        ]],
    )

    # Dạng Single Record: Đúng 1 JSON phẳng có 28 features như bạn mô tả
    record: dict[str, Any] | None = Field(
        default=None,
        description="Một record phẳng duy nhất (Dùng cho input_type='single_record')",
        examples=[{
            "order_id": "ORD-TEST-001", "customer_id": "CUST-001", "order_date": "2024-03-15",
            "order_status": "delivered", "order_source": "app", "device_type": "mobile",
            "signup_date": "2023-06-01", "gender": "Male", "age_group": "25-34",
            "product_id": "PROD-001", "quantity": 2, "unit_price": 350000,
            "discount_amount": 35000, "category": "Casual", "segment": "Everyday",
            "size": "M", "payment_method": "MOMO", "payment_value": 665000
        }],
    )


class PredictionItem(BaseModel):
    order_id:           str
    return_probability: float
    prediction:         int
    threshold:          float


class PredictResponse(BaseModel):
    n_predictions: int
    positive_rate: float
    predictions:   list[PredictionItem]


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: CHUYỂN REQUEST THẲNG THÀNH DATAFRAME (KHÔNG CÒN AGGREGATE)
# ─────────────────────────────────────────────────────────────────────────────

def _prepare_master_df(request: PredictRequest) -> pd.DataFrame:
    """
    Chuyển đổi dữ liệu phẳng nhận được thành DataFrame trực tiếp, bỏ qua hoàn toàn bước join.
    """
    if request.input_type == "batch":
        if not request.records:
            raise ValueError("input_type='batch' nhưng thiếu trường 'records'.")
        logger.info(f"Nhận dạng Batch: Chuyển trực tiếp {len(request.records)} records sang DataFrame.")
        return pd.DataFrame(request.records)

    if request.input_type == "single_record":
        if not request.record:
            raise ValueError("input_type='single_record' nhưng thiếu trường 'record'.")
        logger.info("Nhận dạng Single Record: Tạo DataFrame 1 dòng từ record phẳng.")
        return pd.DataFrame([request.record])

    raise ValueError(f"input_type '{request.input_type}' không hợp lệ.")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: CHẠY PREDICT QUA PIPELINE MLFLOW
# ─────────────────────────────────────────────────────────────────────────────

def _run_pipeline(master_df: pd.DataFrame) -> tuple[list, np.ndarray, float]:
    if _pipeline is None:
        raise RuntimeError("Pipeline chưa được load thành công từ MLflow.")

    labels       = _pipeline.predict(master_df)
    proba_matrix = _pipeline.predict_proba(master_df)
    probabilities = proba_matrix[:, 1]

    try:
        actual_threshold = _pipeline.steps[-1][1].threshold
    except Exception:
        actual_threshold = getattr(_pipeline, "threshold", 0.5)

    return labels.tolist(), probabilities, float(actual_threshold)


# ─────────────────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", summary="Kiểm tra trạng thái app và Pipeline")
async def health():
    current_thresh = 0.5
    if _pipeline is not None:
        try:
            current_thresh = _pipeline.steps[-1][1].threshold
        except Exception:
            pass

    return {
        "status":          "ok" if _pipeline is not None else "pipeline_not_loaded",
        "pipeline_loaded": _pipeline is not None,
        "mlflow_uri":      MLFLOW_MODEL_URI,
        "mlflow_tracking": MLFLOW_TRACKING_URI,
        "threshold":       current_thresh,
    }


@app.post(
    "/predict",
    response_model=PredictResponse,
    summary="Predict customer return trực tiếp từ dữ liệu phẳng",
)
def predict_endpoint(request: PredictRequest):
    try:
        # Bước 1: Parse trực tiếp dữ liệu phẳng thành DataFrame (Không gọi hàm aggregate nữa!)
        master_df = _prepare_master_df(request)

        if master_df.empty:
            raise ValueError("Dữ liệu đầu vào trống.")

        # Bước 2: Kiểm tra cột định danh order_id có trong cục JSON phẳng kia không
        if "order_id" not in master_df.columns:
            raise ValueError("Dữ liệu thiếu trường định danh 'order_id'.")
        order_ids = master_df["order_id"].astype(str).tolist()

        # Bước 3: Đẩy trực tiếp vào Pipeline để xử lý feature builder + predict
        labels, probabilities, actual_threshold = _run_pipeline(master_df)

        # Bước 4: Đóng gói kết quả trả về
        results = [
            PredictionItem(
                order_id=          str(order_id),
                return_probability=float(prob),
                prediction=        int(label),
                threshold=         actual_threshold,
            )
            for order_id, prob, label in zip(order_ids, probabilities, labels)
        ]

        positive_rate = (
            sum(r.prediction for r in results) / len(results)
            if results else 0.0
        )

        logger.info(f"Predict xong {len(results)} records phẳng thành công.")

        return PredictResponse(
            n_predictions=len(results),
            positive_rate=positive_rate,
            predictions=results,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Lỗi hệ thống: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi server: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )