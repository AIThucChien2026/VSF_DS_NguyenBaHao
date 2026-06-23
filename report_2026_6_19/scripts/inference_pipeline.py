# scripts/inference_pipeline.py
"""
File này làm 3 việc chính:

  1. FeatureBuilder
     Nhận cleaned_df từ clean_data.py
     → tạo thêm 2 feature mới (log_payment_value, tenure_group)
     → chọn đúng 28 cột cần thiết

  2. ThresholdedClassifierWrapper
     Bọc champion model lại thành sklearn-compatible object
     → dùng để đặt vào sklearn Pipeline
     → áp dụng threshold 0.063357 để ra label 0/1

  3. InferencePipeline
     Class chính — gộp tất cả lại
     → load preprocessor + model
     → chạy predict
     → trả về DataFrame kết quả

Ngoài ra có hàm build_full_sklearn_pipeline() để đóng gói
toàn bộ Pipeline 3 bước sẵn sàng đẩy lên MLflow.
"""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline as SKPipeline

# mlflow là optional — nếu không cài thì chỉ không load được từ Registry
# các chức năng khác vẫn hoạt động bình thường
try:
    import mlflow
    import mlflow.lightgbm
    import mlflow.sklearn
except ModuleNotFoundError:
    mlflow = None

logger = logging.getLogger(__name__)


# =============================================================
#  PHẦN 1 — CÁC HẰNG SỐ (constants)
#  Đặt ở đây để dễ tìm và sửa khi cần, không nằm rải rác trong code
# =============================================================

# Threshold được chọn từ Report 14, tối ưu cho bài toán này
# KHÔNG thay đổi giá trị này trừ khi có report mới
LOCKED_THRESHOLD = 0.063357

# Đường dẫn model dự phòng — chỉ dùng khi MLflow server không chạy được
DEFAULT_FALLBACK_MODEL_PATH = "artifacts/final_model.joblib"

# Các cột TUYỆT ĐỐI KHÔNG được xuất hiện trong data khi inference
# Lý do: những cột này được tính từ returns.csv — tức là chính thứ ta đang dự đoán
# Nếu có → model sẽ "nhìn thấy đáp án" → kết quả vô nghĩa
BANNED_FEATURES = [
    "mean_product_return_rate",   # tính từ returns.csv
    "max_product_return_rate",    # tính từ returns.csv
    "high_risk_product_count",    # tính từ returns.csv
    "order_status",               # chính là label (đã return hay chưa)
    "has_return_record",          # tính từ returns.csv
]

# 28 cột input — phải khớp CHÍNH XÁC với lúc fit preprocessor ở Report 12
# Thêm/bớt/đổi tên bất kỳ cột nào → preprocessor báo lỗi ngay
NUMERIC_COLS = [
    "customer_tenure_days",   # số ngày từ lúc đăng ký đến lúc đặt hàng
    "total_quantity",         # tổng số lượng sản phẩm trong đơn
    "unique_product_count",   # số loại sản phẩm khác nhau
    "discount_ratio",         # tỷ lệ giảm giá (0.0 → 1.0)
    "log_payment_value",      # log của giá trị thanh toán — tạo trong FeatureBuilder
]

CATEGORICAL_COLS = [
    "payment_method",   # COD, banking, ...
    "device_type",      # mobile, desktop, ...
    "order_source",     # app, web, ...
    "tenure_group",     # nhóm tenure — tạo trong FeatureBuilder
    "age_group",        # nhóm tuổi khách hàng
    "gender",           # giới tính
]

BINARY_COLS = [
    "is_cod",          # 1 nếu thanh toán khi nhận hàng
    "is_discounted",   # 1 nếu đơn có giảm giá
    # 14 cột multi-hot từ products (1 đơn có thể thuộc nhiều nhóm cùng lúc)
    "category_Casual", "category_GenZ", "category_Outdoor", "category_Streetwear",
    "segment_Activewear", "segment_Balanced", "segment_Everyday",
    "segment_Performance", "segment_Premium", "segment_Standard",
    "size_L", "size_M", "size_S", "size_XL",
]

QUANTILE_COLS = [
    "payment_value",   # giá trị thanh toán gốc — preprocessor dùng KBins để chia nhóm
]

# Ghép lại thành danh sách đầy đủ 28 cột theo đúng thứ tự
ALL_FEATURE_COLS = NUMERIC_COLS + CATEGORICAL_COLS + BINARY_COLS + QUANTILE_COLS

# Bins để chia tenure thành 4 nhóm — phải giống hệt lúc fit ở Report 12
# [0, 30)   → new_lt_30d       : khách mới dưới 30 ngày
# [30, 180) → 30_179d          : khách 1-6 tháng
# [180, 365)→ 180_364d         : khách 6-12 tháng
# [365, ∞)  → loyal_365d_plus  : khách trên 1 năm
TENURE_BINS   = [0, 30, 180, 365, float("inf")]
TENURE_LABELS = ["new_lt_30d", "30_179d", "180_364d", "loyal_365d_plus"]


# =============================================================
#  PHẦN 2 — XỬ LÝ TƯƠNG THÍCH SKLEARN VERSION CŨ
#
#  Vấn đề: preprocessor_v1_outer_train.joblib được tạo từ sklearn version cũ.
#  Khi load lên sklearn version mới, SimpleImputer bị thiếu attribute "_fill_dtype"
#  → crash ngay khi gọi .transform()
#
#  Giải pháp: duyệt toàn bộ artifact sau khi load, tìm SimpleImputer nào
#  bị thiếu thì tự thêm attribute đó vào.
# =============================================================

def _fix_one_imputer(imputer: SimpleImputer) -> None:
    """
    Thêm attribute _fill_dtype bị thiếu vào 1 SimpleImputer cụ thể.

    Cách hoạt động:
    - Nếu đã có _fill_dtype rồi → bỏ qua, không làm gì
    - Nếu chưa có → tự suy luận dtype từ statistics_ (dữ liệu đã học của imputer)
    - Nếu không suy luận được → dùng float64 làm mặc định an toàn
    """
    if hasattr(imputer, "_fill_dtype"):
        return  # Đã có rồi, không cần làm gì

    existing_statistics = getattr(imputer, "statistics_", None)
    try:
        inferred_dtype = (
            np.asarray(existing_statistics).dtype
            if existing_statistics is not None
            else np.dtype("float64")
        )
    except Exception:
        inferred_dtype = np.dtype("float64")

    imputer._fill_dtype = inferred_dtype


def _fix_all_imputers_in_artifact(obj, _visited: set | None = None) -> None:
    """
    Duyệt đệ quy toàn bộ artifact và fix tất cả SimpleImputer bên trong.

    Tại sao cần đệ quy?
    ColumnTransformer chứa nhiều Pipeline con, mỗi Pipeline lại chứa SimpleImputer.
    Phải đi sâu vào từng tầng mới tìm hết được.

    _visited: tránh xử lý cùng 1 object 2 lần (tránh vòng lặp vô tận)
    """
    if _visited is None:
        _visited = set()

    # Dùng id() vì muốn theo dõi object thực tế trong memory, không phải giá trị
    obj_id = id(obj)
    if obj_id in _visited:
        return  # Đã xử lý rồi, bỏ qua
    _visited.add(obj_id)

    # Các kiểu dữ liệu đơn giản — không chứa sklearn object bên trong, bỏ qua
    primitive_types = (str, bytes, bytearray, int, float, complex, bool, type(None), np.generic)
    if isinstance(obj, primitive_types):
        return

    # numpy array — chỉ đi vào nếu là object array (có thể chứa sklearn objects)
    if isinstance(obj, np.ndarray):
        if obj.dtype == object:
            for item in obj.flat:
                _fix_all_imputers_in_artifact(item, _visited)
        return

    # Nếu chính object này là SimpleImputer → fix luôn
    if isinstance(obj, SimpleImputer):
        _fix_one_imputer(obj)

    # Container types — đi vào từng phần tử
    if isinstance(obj, dict):
        for value in obj.values():
            _fix_all_imputers_in_artifact(value, _visited)
        return

    if isinstance(obj, (list, tuple, set)):
        for item in obj:
            _fix_all_imputers_in_artifact(item, _visited)
        return

    # sklearn objects (Pipeline, ColumnTransformer, ...) — đi vào các attribute chứa sub-objects
    sklearn_child_attributes = (
        "steps",            # sklearn.Pipeline
        "transformers",     # ColumnTransformer (trước khi fit)
        "transformers_",    # ColumnTransformer (sau khi fit)
        "named_steps",      # Pipeline.named_steps
        "named_transformers_",
        "estimators_",      # VotingClassifier
        "best_estimator_",  # GridSearchCV
    )
    for attr_name in sklearn_child_attributes:
        child = getattr(obj, attr_name, None)
        if child is not None:
            _fix_all_imputers_in_artifact(child, _visited)

    # Các attribute còn lại trong __dict__ — bắt những trường hợp không có tên chuẩn
    if hasattr(obj, "__dict__"):
        for value in obj.__dict__.values():
            if isinstance(value, primitive_types):
                continue
            if isinstance(value, np.ndarray) and value.dtype != object:
                continue
            _fix_all_imputers_in_artifact(value, _visited)


def load_joblib_artifact(path: str | Path):
    """
    Load file .joblib và tự động fix compatibility với sklearn version mới.

    Dùng hàm này thay vì joblib.load() trực tiếp để tránh lỗi _fill_dtype.

    Args:
        path: đường dẫn đến file .joblib

    Returns:
        artifact đã được load và fix
    """
    artifact = joblib.load(path)
    _fix_all_imputers_in_artifact(artifact)
    return artifact


# =============================================================
#  PHẦN 3 — FEATUREBUILDER
#
#  Nhiệm vụ: nhận cleaned_df → tạo thêm 2 feature → chọn đúng 28 cột
#
#  Kế thừa BaseEstimator + TransformerMixin để có thể đặt vào sklearn.Pipeline
#  như một step bình thường.
#
#  "Stateless" nghĩa là không học gì từ data — fit() không làm gì cả.
#  Lý do: log1p và pd.cut đều dùng công thức cố định, không cần học từ data.
# =============================================================

class FeatureBuilder(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        # Không học gì từ data — trả về self để sklearn Pipeline hoạt động đúng
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Nhận cleaned_df → trả về DataFrame 28 cột sẵn sàng cho ColumnTransformer.

        Bước 1: Kiểm tra leakage — có cột bị cấm thì dừng ngay
        Bước 2: Tạo log_payment_value
        Bước 3: Tạo tenure_group
        Bước 4: Kiểm tra đủ 28 cột chưa
        Bước 5: Trả về đúng 28 cột theo thứ tự chuẩn
        """
        df = X.copy()  # Không thay đổi DataFrame gốc

        # Bước 1: Leakage gate
        # Kiểm tra này phải chạy TRƯỚC mọi thứ khác
        # Nếu có cột bị cấm → dừng ngay, không tiếp tục
        banned_cols_found = [col for col in BANNED_FEATURES if col in df.columns]
        if banned_cols_found:
            raise ValueError(
                f"Phát hiện data leakage — các cột sau KHÔNG được dùng khi inference:\n"
                f"  {banned_cols_found}\n"
                f"Kiểm tra lại clean_data.py — không được load returns.csv."
            )

        # Bước 2: Tạo log_payment_value
        # Tại sao dùng log1p thay vì log?
        #   log(0) = -infinity → crash
        #   log1p(0) = log(1+0) = 0 → an toàn
        # Tại sao clip(lower=0)?
        #   payment_value âm (refund?) → log của số âm = không xác định → crash
        df["log_payment_value"] = np.log1p(df["payment_value"].clip(lower=0))

        # Bước 3: Tạo tenure_group
        # pd.cut chia số liên tục thành bucket theo bins cố định
        # right=False: [0, 30) thay vì (0, 30] — khách đúng 30 ngày vào bucket tiếp theo
        # .astype(str): SimpleImputer cần string, không nhận Categorical
        df["tenure_group"] = pd.cut(
            df["customer_tenure_days"],
            bins=TENURE_BINS,
            labels=TENURE_LABELS,
            right=False,
        ).astype(str)

        # Bước 4: Kiểm tra đủ cột chưa
        missing_cols = [col for col in ALL_FEATURE_COLS if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"FeatureBuilder thiếu {len(missing_cols)} cột:\n"
                f"  {missing_cols}\n"
                f"Kiểm tra REQUIRED_OUTPUT_COLS trong clean_data.py."
            )

        # Bước 5: Trả về đúng 28 cột theo thứ tự ColumnTransformer mong đợi
        return df[ALL_FEATURE_COLS]


# =============================================================
#  PHẦN 4 — THRESHOLDEDCLASSIFIERWRAPPER
#
#  Vấn đề cần giải quyết:
#    sklearn.Pipeline yêu cầu step cuối cùng phải có .fit() và .predict()
#    Nhưng champion model có thể là sklearn object hoặc LightGBM native
#    → 2 loại này có interface khác nhau
#
#  Wrapper này chuẩn hóa interface, đồng thời tích hợp threshold vào predict()
#  để Pipeline hoàn chỉnh từ đầu đến cuối, kể cả bước áp threshold.
# =============================================================

class ThresholdedClassifierWrapper(BaseEstimator):

    def __init__(
        self,
        model=None,
        flavor: str = "sklearn",
        threshold: float = LOCKED_THRESHOLD,
    ):
        """
        Args:
            model    : champion model đã train sẵn
            flavor   : "sklearn" hoặc "lightgbm" — xác định cách gọi predict_proba
            threshold: ngưỡng phân loại, mặc định = LOCKED_THRESHOLD từ Report 14
        """
        self.model     = model
        self.flavor    = flavor
        self.threshold = threshold

    def fit(self, X, y=None):
        # Không train lại — model đã được train sẵn từ Report 14
        return self

    def _get_return_probability(self, X: np.ndarray) -> np.ndarray:
        """
        Tính xác suất return (class 1) cho từng đơn hàng.

        Tại sao cần phân biệt flavor?
          sklearn model: predict_proba() trả về (n, 2) array
                         → cần lấy cột thứ 2 [:, 1] = xác suất class 1
          LightGBM native: predict() trả về thẳng array xác suất
                         → không cần [:, 1]
        """
        if self.flavor in ("sklearn", "joblib"):
            return self.model.predict_proba(X)[:, 1]

        if self.flavor == "lightgbm":
            return self.model.predict(X)

        raise ValueError(
            f"Flavor '{self.flavor}' không hợp lệ. Chỉ chấp nhận: 'sklearn', 'joblib', 'lightgbm'."
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Trả về xác suất cho cả 2 class theo chuẩn sklearn: shape (n, 2)
          cột 0 = xác suất KHÔNG return
          cột 1 = xác suất return
        """
        proba_return     = self._get_return_probability(X)
        proba_not_return = 1 - proba_return
        return np.column_stack([proba_not_return, proba_return])

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Áp threshold → trả về nhãn nhị phân:
          1 = dự đoán sẽ return
          0 = dự đoán không return
        """
        proba = self._get_return_probability(X)
        return (proba >= self.threshold).astype(int)

    # get_params và set_params bắt buộc phải có để sklearn Pipeline hoạt động đúng
    # khi clone hoặc set_params từ bên ngoài
    def get_params(self, deep: bool = True) -> dict:
        return {"model": self.model, "flavor": self.flavor, "threshold": self.threshold}

    def set_params(self, **params):
        for key, value in params.items():
            setattr(self, key, value)
        return self


# =============================================================
#  PHẦN 5 — HÀM BUILD VÀ LOAD
# =============================================================

def build_full_sklearn_pipeline(
    preprocessor,
    model,
    flavor: str = "sklearn",
    threshold: float = LOCKED_THRESHOLD,
) -> SKPipeline:
    """
    Tạo sklearn Pipeline 3 bước hoàn chỉnh để đẩy lên MLflow.

    Thứ tự các bước:
      1. feature_builder → FeatureBuilder (tạo feature mới, chọn 28 cột)
      2. preprocessor    → ColumnTransformer đã fit (scale, encode, ...)
      3. classifier      → ThresholdedClassifierWrapper (predict + threshold)

    Pipeline này có thể load lại bằng mlflow.sklearn.load_model()
    và chạy thẳng: pipeline.predict(cleaned_df)
    """
    return SKPipeline([
        ("feature_builder", FeatureBuilder()),
        ("preprocessor",    preprocessor),
        ("classifier",      ThresholdedClassifierWrapper(
            model=model,
            flavor=flavor,
            threshold=threshold,
        )),
    ])


def _load_model_from_mlflow(mlflow_uri: str) -> tuple:
    """
    Load champion model từ MLflow Registry.

    Thử sklearn flavor trước vì giữ được predict_proba().
    Nếu không được thì thử lightgbm flavor.
    Tuyệt đối không dùng mlflow.pyfunc vì pyfunc không có predict_proba().

    Returns:
        (model_object, flavor_string)

    Raises:
        RuntimeError nếu cả 2 flavor đều thất bại
    """
    # Thử sklearn flavor
    try:
        model = mlflow.sklearn.load_model(mlflow_uri)
        logger.info(f"✓ Model loaded từ MLflow (sklearn flavor): {mlflow_uri}")
        return model, "sklearn"
    except Exception as e:
        logger.warning(f"sklearn flavor thất bại: {e}")

    # Thử lightgbm flavor
    try:
        model = mlflow.lightgbm.load_model(mlflow_uri)
        logger.info(f"✓ Model loaded từ MLflow (lightgbm flavor): {mlflow_uri}")
        return model, "lightgbm"
    except Exception as e:
        logger.warning(f"lightgbm flavor thất bại: {e}")

    raise RuntimeError(
        f"Không thể load model từ MLflow URI: '{mlflow_uri}'\n"
        f"Kiểm tra: MLflow server đang chạy? Model đã được register chưa?"
    )


def _load_model_from_local_file(bundle_path: str) -> tuple:
    """
    Load model từ file .joblib local — chỉ dùng khi MLflow không available.

    File có thể là:
      - dict với key "model" → lấy dict["model"]
      - model trực tiếp      → dùng luôn

    Returns:
        (model_object, "joblib")
    """
    obj = load_joblib_artifact(bundle_path)

    if isinstance(obj, dict) and "model" in obj:
        logger.info(f"✓ Model loaded từ bundle dict: {bundle_path}")
        model = obj["model"]
    else:
        logger.info(f"✓ Model loaded trực tiếp: {bundle_path}")
        model = obj

    # Trích xuất classifier thực tế nếu model là Pipeline (tránh lỗi preprocessor lồng nhau)
    if hasattr(model, "steps"):
        logger.info(f"✓ Trích xuất classifier thực tế từ Pipeline: step '{model.steps[-1][0]}'")
        model = model.steps[-1][1]

    return model, "joblib"


# =============================================================
#  PHẦN 6 — INFERENCEPIPELINE (class chính)
#
#  Class này gộp tất cả lại thành 1 interface đơn giản:
#    pipeline = InferencePipeline(...)
#    results  = pipeline.predict(cleaned_df)
# =============================================================

class InferencePipeline:
    """
    Pipeline inference hoàn chỉnh: cleaned_df → predictions DataFrame.

    Thứ tự ưu tiên khi load model:
      1. MLflow Registry (sklearn flavor)   ← source of truth
      2. MLflow Registry (lightgbm flavor)
      3. Local .joblib file                 ← chỉ dùng khi MLflow offline

    Ví dụ sử dụng:
        pipeline = InferencePipeline(
            preprocessor_path="artifacts/preprocessor_v1_outer_train.joblib",
            mlflow_uri="models:/customer-return-champion@champion",
        )
        results_df = pipeline.predict(cleaned_df)
        # results_df có 4 cột: order_id, return_probability, prediction, threshold
    """

    def __init__(
        self,
        preprocessor_path: str,
        mlflow_uri: str = "models:/customer-return-champion@champion",
        fallback_model_path: str | None = DEFAULT_FALLBACK_MODEL_PATH,
    ):
        # Load preprocessor (ColumnTransformer đã fit từ Report 12)
        self._preprocessor = self._load_preprocessor(preprocessor_path)

        # Load champion model theo thứ tự ưu tiên
        self._model, self._flavor = self._load_model(mlflow_uri, fallback_model_path)

        # Threshold cố định từ Report 14
        self.threshold = LOCKED_THRESHOLD

        # Pipeline nội bộ chỉ gồm 2 bước transform (không có classifier)
        # Dùng khi gọi predict() để tách riêng bước transform và predict
        self._transform_only_pipeline = SKPipeline([
            ("feature_builder", FeatureBuilder()),
            ("preprocessor",    self._preprocessor),
        ])

        logger.info(
            f"✓ InferencePipeline sẵn sàng "
            f"(model flavor: {self._flavor}, threshold: {self.threshold})"
        )

    @staticmethod
    def _load_preprocessor(preprocessor_path: str):
        """Load ColumnTransformer đã fit từ file .joblib."""
        if not Path(preprocessor_path).exists():
            raise FileNotFoundError(
                f"Không tìm thấy preprocessor: {preprocessor_path}\n"
                f"File này từ Report 12 — chạy bootstrap_report_assets.py để copy về."
            )
        preprocessor = load_joblib_artifact(preprocessor_path)
        logger.info(f"✓ Preprocessor loaded: {preprocessor_path}")
        return preprocessor

    @staticmethod
    def _load_model(mlflow_uri: str, fallback_model_path: str | None) -> tuple:
        """
        Load model theo thứ tự ưu tiên: MLflow trước, local sau.

        Tại sao MLflow phải là ưu tiên cao hơn?
        MLflow Registry là nơi lưu champion model chính thức.
        Local file chỉ là bản sao dự phòng — không đảm bảo là phiên bản mới nhất.
        """
        # Thử MLflow trước
        if mlflow is not None:
            try:
                return _load_model_from_mlflow(mlflow_uri)
            except Exception as e:
                logger.warning(f"MLflow load thất bại, thử local fallback: {e}")

        # Fallback sang local nếu MLflow không được
        if fallback_model_path and Path(fallback_model_path).exists():
            logger.warning(f"⚠ Dùng local fallback: {fallback_model_path}")
            return _load_model_from_local_file(fallback_model_path)

        # Cả 2 đều thất bại
        raise RuntimeError(
            f"Không thể load model từ bất kỳ nguồn nào.\n"
            f"  MLflow URI    : {mlflow_uri}\n"
            f"  Local fallback: {fallback_model_path or 'không cung cấp'}\n"
            f"Kiểm tra MLflow server đang chạy hoặc copy model vào thư mục artifacts/."
        )

    def predict(self, cleaned_df: pd.DataFrame) -> pd.DataFrame:
        """
        Chạy toàn bộ pipeline và trả về predictions.

        Luồng bên trong:
          cleaned_df
            → FeatureBuilder (tạo 2 feature, chọn 28 cột)
            → ColumnTransformer (scale numeric, encode categorical, ...)
            → ThresholdedClassifierWrapper (predict_proba → áp threshold → label)

        Returns:
            DataFrame với 4 cột:
              - order_id           : mã đơn hàng
              - return_probability : xác suất return (0.0 → 1.0)
              - prediction         : nhãn nhị phân (0 hoặc 1)
              - threshold          : threshold đã dùng (để audit)
        """
        # Lưu order_ids trước khi transform vì các bước tiếp theo làm mất cột này
        order_ids = cleaned_df["order_id"].values

        # Bước 1+2: FeatureBuilder → ColumnTransformer → numpy array
        X_transformed = self._transform_only_pipeline.transform(cleaned_df)

        # Bước 3: tính xác suất và áp threshold
        classifier = ThresholdedClassifierWrapper(
            model=self._model,
            flavor=self._flavor,
            threshold=self.threshold,
        )
        probabilities = classifier._get_return_probability(X_transformed)
        labels        = (probabilities >= self.threshold).astype(int)

        return pd.DataFrame({
            "order_id":           order_ids,
            "return_probability": probabilities,
            "prediction":         labels,
            "threshold":          self.threshold,
        })

    def build_full_pipeline_for_logging(self) -> SKPipeline:
        """
        Trả về Pipeline 3 bước hoàn chỉnh để log lên MLflow.

        Pipeline này khác _transform_only_pipeline ở chỗ có thêm bước classifier.
        Sau khi log lên MLflow, có thể load lại bằng mlflow.sklearn.load_model()
        và chạy thẳng pipeline.predict(cleaned_df).
        """
        return build_full_sklearn_pipeline(
            preprocessor=self._preprocessor,
            model=self._model,
            flavor=self._flavor,
            threshold=self.threshold,
        )

    def get_info(self) -> dict:
        """Thông tin pipeline — dùng cho /model-info endpoint của FastAPI."""
        return {
            "threshold":    self.threshold,
            "model_flavor": self._flavor,
            "feature_cols": ALL_FEATURE_COLS,
            "n_feature_cols": len(ALL_FEATURE_COLS),
            "feature_groups": {
                "numeric":     NUMERIC_COLS,
                "categorical": CATEGORICAL_COLS,
                "binary":      BINARY_COLS,
                "quantile":    QUANTILE_COLS,
            },
        }