# scripts/register_pipeline.py
"""
Script chạy 1 lần khi setup — đóng gói và đẩy full sklearn Pipeline lên MLflow Registry.

Luồng:
  1. Load preprocessor đã fit từ artifacts/
  2. Load model đã train từ artifacts/
  3. Build sklearn Pipeline 3 bước (feature_builder → preprocessor → classifier)
  4. Log lên MLflow và register với tên + alias

Sau khi chạy xong, app.py có thể load Pipeline bằng:
  mlflow.sklearn.load_model("models:/customer-return-champion@champion")

Chạy:
  python scripts/register_pipeline.py
"""

import logging
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mlflow
import mlflow.sklearn

from scripts.inference_pipeline import (
    LOCKED_THRESHOLD,
    load_joblib_artifact,
    build_full_sklearn_pipeline,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  CẤU HÌNH
# ─────────────────────────────────────────────────────────────────────────────

MLFLOW_TRACKING_URI     = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_REGISTERED_MODEL = "customer-return-champion"
MLFLOW_ALIAS            = "champion"

PREPROCESSOR_PATH = "artifacts/preprocessor_v1_outer_train.joblib"
LOCAL_MODEL_PATH  = "artifacts/final_model.joblib"


# ─────────────────────────────────────────────────────────────────────────────
#  HÀM CHÍNH
# ─────────────────────────────────────────────────────────────────────────────

def register_pipeline() -> str:
    """
    Build và đẩy full sklearn Pipeline lên MLflow Registry.

    Pipeline được đăng ký bao gồm đầy đủ:
      _PipelineInputAdapter (FeatureBuilder) → preprocessor → ThresholdedClassifierWrapper

    Sau khi register, chỉ cần load bằng URI cố định:
      mlflow.sklearn.load_model("models:/customer-return-champion@champion")
    rồi gọi pipeline.predict(master_df) là cho ra nhãn 0/1.

    Returns:
        model_uri: URI của model vừa register
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    logger.info(f"MLflow tracking URI: {MLFLOW_TRACKING_URI}")

    # ── Bước 1: Load preprocessor ─────────────────────────────────────────────
    if not Path(PREPROCESSOR_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy preprocessor: {PREPROCESSOR_PATH}\n"
            f"Chạy bootstrap_report_assets.py trước."
        )
    preprocessor = load_joblib_artifact(PREPROCESSOR_PATH)
    logger.info(f"✓ Preprocessor loaded: {PREPROCESSOR_PATH}")

    # ── Bước 2: Load model từ local bundle ────────────────────────────────────
    # Đây là lần duy nhất load từ local — sau khi register xong thì mọi thứ
    # đều load từ MLflow Registry, không dùng local nữa
    if not Path(LOCAL_MODEL_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy model bundle: {LOCAL_MODEL_PATH}\n"
            f"Chạy bootstrap_report_assets.py trước."
        )
    bundle = load_joblib_artifact(LOCAL_MODEL_PATH)

    if isinstance(bundle, dict) and "model" in bundle:
        model  = bundle["model"]
        flavor = "joblib"
        logger.info(f"✓ Model loaded từ bundle dict: {LOCAL_MODEL_PATH}")
    else:
        model  = bundle
        flavor = "sklearn"
        logger.info(f"✓ Model loaded trực tiếp: {LOCAL_MODEL_PATH}")

    # Nếu model là Pipeline lồng (preprocessor bên trong) → chỉ lấy classifier
    if hasattr(model, "steps"):
        logger.info(
            f"✓ Trích xuất classifier từ Pipeline lồng: '{model.steps[-1][0]}'"
        )
        model = model.steps[-1][1]

    # ── Bước 3: Build sklearn Pipeline hoàn chỉnh ────────────────────────────
    pipeline = build_full_sklearn_pipeline(
        preprocessor=preprocessor,
        model=model,
        flavor=flavor,
        threshold=LOCKED_THRESHOLD,
    )
    logger.info(
        f"✓ Pipeline built — steps: "
        f"feature_builder (adapter) → preprocessor → "
        f"classifier (threshold={LOCKED_THRESHOLD})"
    )

    # ── Bước 4: Log lên MLflow và register ───────────────────────────────────
    # Đóng gói scripts/ cùng với model để MLflow serving có thể tái tạo
    # FeatureBuilder, _PipelineInputAdapter, ThresholdedClassifierWrapper
    with mlflow.start_run(run_name="register_pipeline") as run:
        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="sk_pipeline",
            registered_model_name=MLFLOW_REGISTERED_MODEL,
            serialization_format="cloudpickle",
            code_paths=["scripts/"],
        )
        run_id = run.info.run_id
        logger.info(f"✓ Pipeline logged — run_id: {run_id}")

    # ── Bước 5: Set alias @champion ──────────────────────────────────────────
    # Alias cho phép load bằng URI cố định không phụ thuộc version number:
    #   models:/customer-return-champion@champion
    client = mlflow.MlflowClient()
    latest_version = (
        client
        .get_registered_model(MLFLOW_REGISTERED_MODEL)
        .latest_versions[0]
        .version
    )
    client.set_registered_model_alias(
        name=MLFLOW_REGISTERED_MODEL,
        alias=MLFLOW_ALIAS,
        version=latest_version,
    )

    model_uri = f"models:/{MLFLOW_REGISTERED_MODEL}@{MLFLOW_ALIAS}"
    logger.info(
        f"\n{'='*60}\n"
        f"  ✓ Pipeline đã được register thành công!\n"
        f"  • Model name : {MLFLOW_REGISTERED_MODEL}\n"
        f"  • Version    : {latest_version}\n"
        f"  • Alias      : @{MLFLOW_ALIAS}\n"
        f"  • URI        : {model_uri}\n"
        f"  • MLflow UI  : {MLFLOW_TRACKING_URI}/#/models/{MLFLOW_REGISTERED_MODEL}\n"
        f"\n"
        f"  Load trong app.py:\n"
        f"    import mlflow.sklearn\n"
        f"    pipeline = mlflow.sklearn.load_model(\"{model_uri}\")\n"
        f"    predictions = pipeline.predict(master_df)\n"
        f"{'='*60}"
    )

    return model_uri


if __name__ == "__main__":
    try:
        register_pipeline()
    except Exception as e:
        logger.error(f"Register thất bại: {e}")
        sys.exit(1)