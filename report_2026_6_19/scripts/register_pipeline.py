# scripts/register_pipeline.py
"""
Script chạy 1 lần khi setup — đóng gói và đẩy full sklearn Pipeline lên MLflow Registry.

Không predict gì cả. Chỉ:
  1. Load preprocessor từ local artifact
  2. Load model từ local bundle (final_model.joblib)
  3. Build sklearn Pipeline 3 bước
  4. Đẩy lên MLflow Registry với tên và alias

Sau khi script này chạy xong, MLflow serving có thể load và serve Pipeline đó.

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

MLFLOW_TRACKING_URI     = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_REGISTERED_MODEL = "customer-return-champion"
MLFLOW_ALIAS            = "champion"

PREPROCESSOR_PATH  = "artifacts/preprocessor_v1_outer_train.joblib"
LOCAL_MODEL_PATH   = "artifacts/final_model.joblib"


def register_pipeline() -> str:
    """
    Build và đẩy full sklearn Pipeline lên MLflow Registry.

    Luồng:
      load preprocessor → load model → build Pipeline → log lên MLflow → set alias

    Returns:
        model_uri: URI của model vừa register (ví dụ: models:/customer-return-champion/1)
    """
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    # ── Bước 1: Load preprocessor ──────────────────────────
    if not Path(PREPROCESSOR_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy preprocessor: {PREPROCESSOR_PATH}\n"
            f"Chạy bootstrap_report_assets.py trước."
        )
    preprocessor = load_joblib_artifact(PREPROCESSOR_PATH)
    logger.info(f"✓ Preprocessor loaded: {PREPROCESSOR_PATH}")

    # ── Bước 2: Load model từ local bundle ─────────────────
    # Dùng local bundle vì lúc này MLflow Registry chưa có model nào
    # Đây là lần duy nhất dùng local — sau khi register xong, mọi thứ load từ Registry
    if not Path(LOCAL_MODEL_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy model bundle: {LOCAL_MODEL_PATH}\n"
            f"Chạy bootstrap_report_assets.py trước."
        )
    bundle = load_joblib_artifact(LOCAL_MODEL_PATH)
    if isinstance(bundle, dict) and "model" in bundle:
        model  = bundle["model"]
        flavor = "joblib"
        logger.info(f"✓ Model loaded từ bundle: {LOCAL_MODEL_PATH}")
    else:
        model  = bundle
        flavor = "sklearn"
        logger.info(f"✓ Model loaded: {LOCAL_MODEL_PATH}")

    # Trích xuất classifier thực tế nếu model là Pipeline (tránh lỗi preprocessor lồng nhau)
    if hasattr(model, "steps"):
        logger.info(f"✓ Trích xuất classifier thực tế từ Pipeline: step '{model.steps[-1][0]}'")
        model = model.steps[-1][1]


    # ── Bước 3: Build full sklearn Pipeline ────────────────
    pipeline = build_full_sklearn_pipeline(
        preprocessor=preprocessor,
        model=model,
        flavor=flavor,
        threshold=LOCKED_THRESHOLD,
    )
    logger.info(
        f"✓ Pipeline built — steps: "
        f"feature_builder → preprocessor → classifier (threshold={LOCKED_THRESHOLD})"
    )

    # ── Bước 4: Log lên MLflow và register ─────────────────
    # Dùng 1 run ngắn chỉ để log model, không log metrics hay params vì chưa có data
    with mlflow.start_run(run_name="register_pipeline") as run:
        model_info = mlflow.sklearn.log_model(
            sk_model=pipeline,
            artifact_path="sk_pipeline",
            registered_model_name=MLFLOW_REGISTERED_MODEL,
            # code_paths đóng gói inference_pipeline.py kèm theo model.pkl
            # MLflow serving cần file này để tái tạo FeatureBuilder và ThresholdedClassifierWrapper
            code_paths=["scripts/"],
           # code_paths=["scripts/inference_pipeline.py"],
        )
        run_id = run.info.run_id
        logger.info(f"✓ Pipeline logged — run_id: {run_id}")

    # ── Bước 5: Set alias @champion ────────────────────────
    # Alias cho phép load bằng URI cố định: models:/customer-return-champion@champion
    # Không cần biết version number thay đổi sau mỗi lần register
    client = mlflow.MlflowClient()
    latest_version = client.get_registered_model(MLFLOW_REGISTERED_MODEL).latest_versions[0].version
    client.set_registered_model_alias(
        name=MLFLOW_REGISTERED_MODEL,
        alias=MLFLOW_ALIAS,
        version=latest_version,
    )

    model_uri = f"models:/{MLFLOW_REGISTERED_MODEL}@{MLFLOW_ALIAS}"
    logger.info(
        f"\n{'='*55}\n"
        f"  ✓ Pipeline đã được register thành công!\n"
        f"  • Model name  : {MLFLOW_REGISTERED_MODEL}\n"
        f"  • Version     : {latest_version}\n"
        f"  • Alias       : @{MLFLOW_ALIAS}\n"
        f"  • URI         : {model_uri}\n"
        f"  • MLflow UI   : {MLFLOW_TRACKING_URI}/#/models/{MLFLOW_REGISTERED_MODEL}\n"
        f"\n"
        f"  Bước tiếp theo — khởi động MLflow serving:\n"
        f"  mlflow models serve -m \"{model_uri}\" --port 8001 --no-conda\n"
        f"{'='*55}"
    )

    return model_uri


if __name__ == "__main__":
    try:
        register_pipeline()
    except Exception as e:
        logger.error(f"Register thất bại: {e}")
        sys.exit(1)
