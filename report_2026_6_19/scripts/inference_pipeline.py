# scripts/inference_pipeline.py
"""
Build sklearn Pipeline gồm 3 bước:
  1. FeatureBuilder        : nhận master table → tạo 28 feature + label
  2. ColumnTransformer     : tiền xử lý (impute, encode, scale)
  3. ThresholdedClassifier : load model đã train + áp threshold → predict

Ngoài ra có:
  - build_full_sklearn_pipeline() : đóng gói Pipeline để đẩy lên MLflow
  - load_joblib_artifact()        : load .joblib + fix sklearn version cũ
"""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline as SKPipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    import mlflow
    import mlflow.lightgbm
    import mlflow.sklearn
except ModuleNotFoundError:
    mlflow = None

logger = logging.getLogger(__name__)


# =============================================================================
#  PHẦN 1 — CONSTANTS
# =============================================================================

LOCKED_THRESHOLD = 0.063357

DEFAULT_FALLBACK_MODEL_PATH = "artifacts/final_model.joblib"

# Cột bị cấm — tuyệt đối không được xuất hiện khi inference (data leakage)
BANNED_FEATURES = [
    "mean_product_return_rate",
    "max_product_return_rate",
    "high_risk_product_count",
    "has_return_record",
]

# 28 cột feature theo đúng thứ tự preprocessor đã fit
NUMERIC_COLS = [
    "customer_tenure_days",
    "total_quantity",
    "unique_product_count",
    "discount_ratio",
    "log_payment_value",
]

CATEGORICAL_COLS = [
    "payment_method",
    "device_type",
    "order_source",
    "tenure_group",
    "age_group",
    "gender",
]

BINARY_COLS = [
    "is_cod",
    "is_discounted",
    "category_Casual", "category_GenZ", "category_Outdoor", "category_Streetwear",
    "segment_Activewear", "segment_Balanced", "segment_Everyday",
    "segment_Performance", "segment_Premium", "segment_Standard",
    "size_L", "size_M", "size_S", "size_XL",
]

QUANTILE_COLS = [
    "payment_value",
]

ALL_FEATURE_COLS = NUMERIC_COLS + CATEGORICAL_COLS + BINARY_COLS + QUANTILE_COLS

# Bins để phân nhóm tenure — phải khớp với lúc fit preprocessor
TENURE_BINS   = [0, 30, 180, 365, float("inf")]
TENURE_LABELS = ["new_lt_30d", "30_179d", "180_364d", "loyal_365d_plus"]

# Tên cột label
LABEL_COL = "label"


# =============================================================================
#  PHẦN 2 — FIX SKLEARN VERSION CŨ
#  SimpleImputer bị thiếu attribute _fill_dtype khi load từ sklearn version cũ
# =============================================================================

def _fix_one_imputer(imputer: SimpleImputer) -> None:
    if hasattr(imputer, "_fill_dtype"):
        return
    existing = getattr(imputer, "statistics_", None)
    try:
        dtype = (
            np.asarray(existing).dtype
            if existing is not None
            else np.dtype("float64")
        )
    except Exception:
        dtype = np.dtype("float64")
    imputer._fill_dtype = dtype


def _fix_all_imputers_in_artifact(obj, _visited: set | None = None) -> None:
    if _visited is None:
        _visited = set()

    obj_id = id(obj)
    if obj_id in _visited:
        return
    _visited.add(obj_id)

    primitive_types = (str, bytes, bytearray, int, float, complex, bool, type(None), np.generic)
    if isinstance(obj, primitive_types):
        return

    if isinstance(obj, np.ndarray):
        if obj.dtype == object:
            for item in obj.flat:
                _fix_all_imputers_in_artifact(item, _visited)
        return

    if isinstance(obj, SimpleImputer):
        _fix_one_imputer(obj)

    if isinstance(obj, dict):
        for v in obj.values():
            _fix_all_imputers_in_artifact(v, _visited)
        return

    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            _fix_all_imputers_in_artifact(item, _visited)
        return

    for attr in ("steps", "transformers", "transformers_", "named_steps",
                 "named_transformers_", "estimators_", "best_estimator_"):
        child = getattr(obj, attr, None)
        if child is not None:
            _fix_all_imputers_in_artifact(child, _visited)

    if hasattr(obj, "__dict__"):
        for v in obj.__dict__.values():
            if isinstance(v, primitive_types):
                continue
            if isinstance(v, np.ndarray) and v.dtype != object:
                continue
            _fix_all_imputers_in_artifact(v, _visited)


def load_joblib_artifact(path: str | Path):
    """Load .joblib và tự động fix compatibility sklearn version cũ."""
    artifact = joblib.load(path)
    _fix_all_imputers_in_artifact(artifact)
    return artifact


# =============================================================================
#  PHẦN 3 — FEATUREBUILDER
#  Nhận master table (output của aggregate.py)
#  → tạo label từ order_status
#  → tạo các feature derived
#  → trả về DataFrame 28 feature + order_id + label
# =============================================================================

class FeatureBuilder(BaseEstimator, TransformerMixin):
    """
    Stateless transformer: nhận master table → trả về feature table.

    Tạo label:
      order_status == "returned"  → 1
      order_status == "delivered" → 0
      khác                        → NaN  (sẽ bị lọc ở bước ColumnTransformer)

    Tạo feature derived:
      - log_payment_value  : log1p(payment_value)
      - tenure_group       : phân nhóm customer_tenure_days thành 4 bucket
      - customer_tenure_days: (order_date - min(signup_date, first_order_date)).dt.days
      - is_cod             : 1 nếu payment_method == "COD"
      - discount_ratio     : total_discount_amount / total_gross_value
      - is_discounted      : 1 nếu discount_ratio > 0
    """

    def fit(self, X, y=None):
        return self
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Nhận master DataFrame (đang bị fan-out ở grain order-product) 
        → aggregate về grain order_id → tạo feature → trả về 28 cols.
        """
        df = X.copy()

        # ── 1. Leakage gate ──────────────────────────────────────────────────
        banned = [c for c in BANNED_FEATURES if c in df.columns]
        if banned:
            raise ValueError(
                f"Phát hiện data leakage — các cột sau KHÔNG được dùng khi inference:\n  {banned}"
            )
        # xoa cac cot missing lon 
        df.drop(columns=["promo_id", "promo_id_2"], errors="ignore", inplace=True)
        # ── 2. Tạo Multi-hot Flag cho Product (TRƯỚC KHI AGGREGATE) ──────────
        categories = ["Casual", "GenZ", "Outdoor", "Streetwear"]
        segments = ["Activewear", "Balanced", "Everyday", "Performance", "Premium", "Standard"]
        sizes = ["L", "M", "S", "XL"]

        for val in categories:
            df[f"category_{val}"] = (df["category"] == val).astype(int) if "category" in df.columns else 0
            
        for val in segments:
            df[f"segment_{val}"] = (df["segment"] == val).astype(int) if "segment" in df.columns else 0
            
        for val in sizes:
            df[f"size_{val}"] = (df["size"] == val).astype(int) if "size" in df.columns else 0

        # ── 3. Ép data về grain order_id (Xử lý Fan-out) ─────────────────────
        if "quantity" in df.columns and "unit_price" in df.columns:
            df["line_gross_value"] = df["quantity"] * df["unit_price"]
        else:
            df["line_gross_value"] = 0.0

        multihot_cols = [c for c in ALL_FEATURE_COLS if c.startswith(("category_", "segment_", "size_"))]

        # Định nghĩa phép tính cho từng cột khi gom nhóm
        agg_funcs = {
            "quantity": "sum",
            "product_id": "nunique",
            "discount_amount": "sum",
            "line_gross_value": "sum",
        }
        # Các cột multi-hot thì lấy max() (chỉ cần 1 item có là order đó có)
        for c in multihot_cols:
            agg_funcs[c] = "max"

        # Lọc ra các cột thực sự tồn tại trong df hiện tại để tránh KeyError
        valid_agg_funcs = {k: v for k, v in agg_funcs.items() if k in df.columns}

        order_features = df.groupby("order_id", as_index=False).agg(valid_agg_funcs)
        
        # Đổi tên cho khớp với danh sách features yêu cầu
        rename_map = {
            "quantity": "total_quantity",
            "product_id": "unique_product_count",
            "discount_amount": "total_discount_amount",
            "line_gross_value": "total_gross_value",
        }
        order_features.rename(columns={k: v for k, v in rename_map.items() if k in order_features.columns}, inplace=True)

        # Xóa bỏ các cột không cần thiết 
        cols_to_drop = list(valid_agg_funcs.keys()) + ["unit_price", "category", "segment", "size"]
        order_level_df = df.drop_duplicates(subset=["order_id"]).drop(columns=cols_to_drop, errors="ignore")

        # Merge lại để ra dataframe chuẩn 1 dòng / 1 order
        df = order_level_df.merge(order_features, on="order_id", how="left")

        # ── 4. Tạo label từ order_status ─────────────────────────────────────
        if "order_status" in df.columns:
            df[LABEL_COL] = df["order_status"].map({"returned": 1, "delivered": 0})
        else:
            df[LABEL_COL] = np.nan

        # ── 5. Parse datetime + tính customer_tenure_days ────────────────────
        if "order_date" in df.columns:
            df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")
        if "signup_date" in df.columns:
            df["signup_date"] = pd.to_datetime(df["signup_date"], errors="coerce")

        if "customer_tenure_days" not in df.columns:
            if "order_date" in df.columns and "signup_date" in df.columns:
                if "customer_id" in df.columns:
                    first_order = df.groupby("customer_id")["order_date"].transform("min")
                    actual_start = pd.concat([df["signup_date"], first_order], axis=1).min(axis=1)
                else:
                    actual_start = df["signup_date"]
                df["customer_tenure_days"] = (df["order_date"] - actual_start).dt.days

        # ── 6. Binary flags và ratio ─────────────────────────────────────────
        if "is_cod" not in df.columns and "payment_method" in df.columns:
            df["is_cod"] = (df["payment_method"] == "COD").astype(int)

        if "discount_ratio" not in df.columns:
            if "total_discount_amount" in df.columns and "total_gross_value" in df.columns:
                df["discount_ratio"] = np.where(
                    df["total_gross_value"] > 0,
                    df["total_discount_amount"] / df["total_gross_value"],
                    0.0,
                )

        if "is_discounted" not in df.columns and "discount_ratio" in df.columns:
            df["is_discounted"] = (df["discount_ratio"] > 0).astype(int)

        # ── 7. log_payment_value ─────────────────────────────────────────────
        if "payment_value" in df.columns:
            df["log_payment_value"] = np.log1p(df["payment_value"].clip(lower=0))
        else:
            df["log_payment_value"] = np.nan

        # ── 8. tenure_group ──────────────────────────────────────────────────
        if "customer_tenure_days" in df.columns:
            df["tenure_group"] = pd.cut(
                df["customer_tenure_days"],
                bins=TENURE_BINS,
                labels=TENURE_LABELS,
                right=False,
            ).astype(str)
        else:
            df["tenure_group"] = np.nan

        # ── 9. Kiểm tra đủ 28 cột ────────────────────────────────────────────
        missing = [c for c in ALL_FEATURE_COLS if c not in df.columns]
        if missing:
            raise ValueError(
                f"FeatureBuilder thiếu {len(missing)} cột feature:\n  {missing}\nKiểm tra lại output của aggregate.py."
            )

        keep_cols = ["order_id", LABEL_COL] + ALL_FEATURE_COLS
        return df[keep_cols]

# =============================================================================
#  PHẦN 4 — COLUMN TRANSFORMER (tiền xử lý)
#  Xây dựng ColumnTransformer từ đầu để dùng trong Pipeline
#  Nếu có preprocessor đã fit sẵn (từ artifacts/) thì load thay thế bước này
# =============================================================================

def build_preprocessor() -> ColumnTransformer:
    """
    Xây dựng ColumnTransformer mới (chưa fit) để dùng trong Pipeline.

    Xử lý theo từng nhóm cột:
      - numeric    : impute (median) → StandardScaler
      - categorical: impute (mode)   → OneHotEncoder
      - binary     : impute (0)      → giữ nguyên (passthrough)
      - quantile   : impute (median) → StandardScaler (hoặc KBins nếu cần)

    Lưu ý: nếu load preprocessor đã fit từ artifacts/ thì không cần hàm này.
    """
    numeric_pipe = SKPipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])

    categorical_pipe = SKPipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    binary_pipe = SKPipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value=0)),
    ])

    quantile_pipe = SKPipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
    ])

    return ColumnTransformer(
        transformers=[
            ("numeric",     numeric_pipe,     NUMERIC_COLS),
            ("categorical", categorical_pipe, CATEGORICAL_COLS),
            ("binary",      binary_pipe,      BINARY_COLS),
            ("quantile",    quantile_pipe,    QUANTILE_COLS),
        ],
        remainder="drop",
    )


# =============================================================================
#  PHẦN 5 — THRESHOLDEDCLASSIFIERWRAPPER
# =============================================================================

class ThresholdedClassifierWrapper(BaseEstimator):
    """
    Bọc model đã train, tích hợp threshold vào predict().
    Hỗ trợ cả sklearn và lightgbm flavor.
    """

    def __init__(
        self,
        model=None,
        flavor: str = "sklearn",
        threshold: float = LOCKED_THRESHOLD,
    ):
        self.model     = model
        self.flavor    = flavor
        self.threshold = threshold

    def fit(self, X, y=None):
        # Model đã được train sẵn — không train lại
        return self

    def _get_return_probability(self, X: np.ndarray) -> np.ndarray:
        if self.flavor in ("sklearn", "joblib"):
            return self.model.predict_proba(X)[:, 1]
        if self.flavor == "lightgbm":
            return self.model.predict(X)
        raise ValueError(
            f"Flavor '{self.flavor}' không hợp lệ. "
            f"Chỉ chấp nhận: 'sklearn', 'joblib', 'lightgbm'."
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Trả về shape (n, 2): [P(không return), P(return)]"""
        p = self._get_return_probability(X)
        return np.column_stack([1 - p, p])

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Áp threshold → trả về nhãn 0/1."""
        return (self._get_return_probability(X) >= self.threshold).astype(int)

    def get_params(self, deep: bool = True) -> dict:
        return {"model": self.model, "flavor": self.flavor, "threshold": self.threshold}

    def set_params(self, **params):
        for k, v in params.items():
            setattr(self, k, v)
        return self


# =============================================================================
#  PHẦN 6 — BUILD PIPELINE
# =============================================================================

def build_full_sklearn_pipeline(
    preprocessor,
    model,
    flavor: str = "sklearn",
    threshold: float = LOCKED_THRESHOLD,
) -> SKPipeline:
    """
    Tạo sklearn Pipeline 3 bước để đẩy lên MLflow.

    Bước:
      feature_builder → preprocessor (ColumnTransformer đã fit) → classifier

    Pipeline này nhận master DataFrame (output của aggregate.py)
    và trả về nhãn 0/1 khi gọi .predict().

    Lưu ý: Pipeline này KHÔNG bao gồm bước tạo label — label chỉ được tạo
    bởi FeatureBuilder nhưng KHÔNG được truyền vào preprocessor/classifier.
    FeatureBuilder trả về [order_id, label, ...28 cols...], nhưng Pipeline
    chỉ dùng 28 cols để predict. Xem _PipelineInputAdapter bên dưới.
    """
    return SKPipeline([
        ("feature_builder", _PipelineInputAdapter()),
        ("preprocessor",    preprocessor),
        ("classifier",      ThresholdedClassifierWrapper(
            model=model,
            flavor=flavor,
            threshold=threshold,
        )),
    ])


class _PipelineInputAdapter(BaseEstimator, TransformerMixin):
    """
    Adapter nội bộ: nhận master table → chạy FeatureBuilder → trả về 28 cols.

    Tại sao cần adapter thay vì dùng FeatureBuilder trực tiếp?
    FeatureBuilder trả về [order_id, label, 28 cols] nhưng preprocessor
    chỉ chấp nhận đúng 28 cols. Adapter này tách order_id và label ra.

    Khi dùng trong Pipeline.predict():
      master_df → _PipelineInputAdapter → (28 cols) → preprocessor → classifier
    """

    def __init__(self):
        self._fb = FeatureBuilder()

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        feature_df = self._fb.transform(X)
        # Chỉ giữ 28 feature cols — loại order_id và label
        return feature_df[ALL_FEATURE_COLS]

    def get_params(self, deep=True):
        return {}

    def set_params(self, **params):
        return self


# =============================================================================
#  PHẦN 7 — LOAD MODEL
# =============================================================================

def _load_model_from_mlflow_pipeline(mlflow_uri: str) -> SKPipeline:
    """
    Load toàn bộ sklearn Pipeline từ MLflow Registry.

    Pipeline đã bao gồm đầy đủ:
      feature_builder → preprocessor → classifier

    Sau khi load, gọi thẳng pipeline.predict(master_df) là xong.

    Raises:
        RuntimeError nếu load thất bại
    """
    if mlflow is None:
        raise RuntimeError("mlflow chưa được cài — pip install mlflow")
    try:
        pipeline = mlflow.sklearn.load_model(mlflow_uri)
        logger.info(f"✓ Pipeline loaded từ MLflow: {mlflow_uri}")
        return pipeline
    except Exception as e:
        raise RuntimeError(
            f"Không thể load Pipeline từ MLflow URI: '{mlflow_uri}'\n"
            f"Lỗi: {e}\n"
            f"Kiểm tra: MLflow server đang chạy? Model đã register chưa?"
        ) from e


def _load_model_from_local_bundle(bundle_path: str) -> tuple:
    """
    Load model từ file .joblib local (chỉ dùng khi MLflow không available).

    Returns:
        (model_object, flavor_str)
    """
    obj = load_joblib_artifact(bundle_path)
    if isinstance(obj, dict) and "model" in obj:
        model  = obj["model"]
        flavor = "joblib"
    else:
        model  = obj
        flavor = "sklearn"

    # Nếu model là Pipeline lồng (có preprocessor bên trong) → lấy classifier thôi
    if hasattr(model, "steps"):
        logger.info(f"✓ Trích xuất classifier từ Pipeline: '{model.steps[-1][0]}'")
        model = model.steps[-1][1]

    logger.info(f"✓ Model loaded từ local: {bundle_path}")
    return model, flavor