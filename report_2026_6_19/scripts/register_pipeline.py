# scripts/register_pipeline.py
"""
Script chạy 1 lần khi setup — đóng gói và đẩy full sklearn Pipeline lên MLflow Registry.

Luồng:
  1. Load preprocessor đã fit từ artifacts/
  2. Load model đã train từ artifacts/
  3. Build sklearn Pipeline 3 bước (feature_builder → preprocessor → classifier)
  4. Log lên MLflow và register với tên + alias

Chạy:
  python scripts/register_pipeline.py --uri http://localhost:5000
"""

import logging
import os
import sys
import argparse  # BỔ SUNG: Thư viện đọc tham số dòng lệnh
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
#  CẤU HÌNH MẶC ĐỊNH
# ─────────────────────────────────────────────────────────────────────────────
MLFLOW_REGISTERED_MODEL = "customer-return-champion"
MLFLOW_ALIAS             = "champion"

PREPROCESSOR_PATH = "artifacts/preprocessor_v1_outer_train.joblib"
LOCAL_MODEL_PATH  = "artifacts/final_model.joblib"


# ─────────────────────────────────────────────────────────────────────────────
#  HÀM CHÍNH
# ─────────────────────────────────────────────────────────────────────────────

def register_pipeline(tracking_uri: str) -> str:
    """
    Build và đẩy full sklearn Pipeline lên MLflow Registry.
    """
    # Ép MLflow set đúng địa chỉ URI nhận vào từ tham số
    mlflow.set_tracking_uri(tracking_uri)
    logger.info(f"MLflow tracking URI được thiết lập: {tracking_uri}")

    # ── Bước 1: Load preprocessor ─────────────────────────────────────────────
    if not Path(PREPROCESSOR_PATH).exists():
        raise FileNotFoundError(
            f"Không tìm thấy preprocessor: {PREPROCESSOR_PATH}\n"
            f"Chạy bootstrap_report_assets.py trước."
        )
    preprocessor = load_joblib_artifact(PREPROCESSOR_PATH)
    logger.info(f"✓ Preprocessor loaded: {PREPROCESSOR_PATH}")

    # ── Bước 2: Load model từ local bundle ────────────────────────────────────
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
        f"  • MLflow UI  : {tracking_uri}/#/models/{MLFLOW_REGISTERED_MODEL}\n"
        f"\n"
        f"  Load trong app.py:\n"
        f"    import mlflow.sklearn\n"
        f"    pipeline = mlflow.sklearn.load_model(\"{model_uri}\")\n"
        f"    predictions = pipeline.predict(master_df)\n"
        f"{'='*60}"
    )

    return model_uri


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đăng ký Sklearn Pipeline lên MLflow Server.")
    
    parser.add_argument(
        "--uri",
        type=str,
        # Nếu gõ lệnh không truyền --uri, script tự tìm biến môi trường, không thấy nữa sẽ lấy localhost mặc định
        default=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"),
        help="Địa chỉ Tracking URI của MLflow Server"
    )
    
    args = parser.parse_args()

    try:
        # Truyền chính xác URI đã phân tách vào hàm xử lý
        register_pipeline(tracking_uri=args.uri)
    except Exception as e:
        logger.error(f"Register thất bại: {e}")
        sys.exit(1)