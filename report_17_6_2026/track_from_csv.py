import os
import json
from pathlib import Path
import pandas as pd
import joblib
import mlflow
import mlflow.sklearn

# 1. Cấu hình đường dẫn dự án
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = PROJECT_ROOT / "report_14_6_2026" / "modeling_outputs" / "tables" / "model_comparison.csv"
MODEL_DIR = PROJECT_ROOT / "report_14_6_2026" / "modeling_outputs" / "models"

# Ánh xạ tên model trong bảng so sánh sang file joblib tương ứng
MODEL_FILE_MAPPING = {
    "LightGBM Tuned": "final_model.joblib",
    "Random Forest Tuned": "random_forest_tuned.joblib",
    "Logistic Regression Tuned": "logistic_tuned.joblib"
}

# 2. Cấu hình kết nối MLflow Server (lấy từ biến môi trường hoặc mặc định localhost)
tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(tracking_uri)
mlflow.set_experiment("customer-return-prediction")
print(f"MLflow Tracking URI: {tracking_uri}")

def main():
    # Kiểm tra sự tồn tại của file bảng so sánh kết quả
    if not TABLE_PATH.exists():
        print(f"Error: Không tìm thấy file bảng so sánh tại {TABLE_PATH}")
        return

    # 3. Đọc dữ liệu từ file CSV (Report Table)
    print(f"Đang đọc dữ liệu từ bảng so sánh: {TABLE_PATH.name}...")
    df = pd.read_csv(TABLE_PATH)

    # Định nghĩa danh sách cột metric và cột parameter để tách tự động
    metric_cols = ["pr_auc", "roc_auc", "precision", "recall", "f1", "balanced_accuracy", "fit_seconds", "mean_fold_pr_auc", "std_fold_pr_auc"]
    param_cols = ["model", "threshold", "threshold_policy", "n_features"]

    # Duyệt qua từng dòng trong bảng dữ liệu để log lên MLflow một cách động
    for index, row in df.iterrows():
        model_name = row["model"]
        print(f"\n--- Đang xử lý log cho mô hình: {model_name} ---")

        # Tách metrics từ dòng hiện tại (chuyển sang float và bỏ qua giá trị NaN)
        metrics = {
            col: float(row[col]) 
            for col in metric_cols 
            if col in row.index and pd.notna(row[col])
        }

        # Tách parameters từ dòng hiện tại (chuyển thành string/số và bỏ qua NaN)
        params = {
            col: str(row[col]) if not isinstance(row[col], (int, float)) else row[col]
            for col in param_cols 
            if col in row.index and pd.notna(row[col])
        }

        # Tải thêm file cấu hình hyperparameter đã tối ưu (nếu có) từ JSON tương ứng làm parameters bổ sung
        param_file_name = f"phase7_{'lgbm' if 'LightGBM' in model_name else 'rf' if 'Random Forest' in model_name else 'logistic'}_best_params.json"
        param_file_path = PROJECT_ROOT / "report_14_6_2026" / "modeling_outputs" / "tables" / param_file_name
        if param_file_path.exists():
            with open(param_file_path, "r", encoding="utf-8") as f:
                best_params = json.load(f)
                for k, v in best_params.items():
                    params[f"best_{k}"] = v

        # 4. Ghi nhận lên MLflow
        with mlflow.start_run(run_name=model_name):
            # Log tham số tự động từ bảng
            mlflow.log_params(params)
            print(f"-> Đã log parameters: {list(params.keys())}")

            # Log metric tự động từ bảng
            mlflow.log_metrics(metrics)
            print(f"-> Đã log metrics: {metrics}")

            # 5. Load model joblib và log lên MLflow làm Model Registry Candidate
            file_name = MODEL_FILE_MAPPING.get(model_name)
            if file_name:
                model_path = MODEL_DIR / file_name
                if model_path.exists():
                    # Load model object từ joblib
                    model_artifact = joblib.load(model_path)
                    # Nếu file lưu dạng dict, lấy model chính ra
                    if isinstance(model_artifact, dict) and "model" in model_artifact:
                        model = model_artifact["model"]
                    else:
                        model = model_artifact
                    
                    # Log model lên MLflow (sử dụng thư viện tương thích)
                    mlflow.sklearn.log_model(
                        sk_model=model, 
                        artifact_path="model",
                        registered_model_name=None # Đăng ký tự động nếu muốn
                    )
                    print(f"-> Đã log model từ file: {file_name}")
                else:
                    print(f"Warning: Không tìm thấy file model vật lý tại {model_path}")
            else:
                print(f"Warning: Không có ánh xạ file cho model {model_name}")

    print("\nHoàn thành! Hãy kiểm tra giao diện MLflow UI tại http://localhost:5000")

if __name__ == "__main__":
    main()
