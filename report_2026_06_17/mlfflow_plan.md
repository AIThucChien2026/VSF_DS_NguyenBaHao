# Kế Hoạch Triển Khai MLflow Tracking & Model Registry

Tài liệu này vạch ra kế hoạch từng bước để thiết lập, ghi nhận thử nghiệm (experiment tracking) và đăng ký mô hình (model registry) bằng MLflow cho dự án dự đoán trả hàng. 

**Bối cảnh hiện tại:**
* Đã hoàn thành huấn luyện mô hình ở pha Modeling (`report_14_6_2026/modeling_outputs`).
* MLflow Server đã được cài đặt và đang chạy trên Docker (lắng nghe ở cổng 5000).
* Chưa thực hiện bất kỳ hoạt động tracking nào trước đây. Mọi hoạt động lưu trữ database local hoặc log dự phòng (nếu có) sẽ sử dụng thư mục hiện tại: **`report_17_6_2026`**.

---

## BƯỚC 1: Chuẩn bị môi trường & Thư viện
1. Tạo file chứa danh sách thư viện bổ sung cho MLflow nếu chưa có (ví dụ: `requirements-mlflow.txt`):
   ```text
   mlflow>=2.10.0
   protobuf>=3.20.0
   sqlite
   ```
2. Cài đặt các thư viện vào môi trường ảo `venv` của dự án:
   ```powershell
   .\venv\Scripts\python.exe -m pip install -r requirements-mlflow.txt
   ```

---

## BƯỚC 2: Cấu hình và Thiết lập MLflow Server

### Phương án A: Sử dụng Docker Container đang chạy (Khuyên dùng)
* MLflow server đang chạy tại Docker ở cổng `5000`.
* Tracking URI sẽ là: `http://localhost:5000`

### Phương án B: Chạy local MLflow Server (Dự phòng độc lập)
* Nếu cần chạy một server cục bộ hoàn toàn độc lập, lưu trữ dữ liệu tại thư mục báo cáo mới (`report_17_6_2026`), sử dụng lệnh:
  ```powershell
  .\venv\Scripts\mlflow.exe server `
    --backend-store-uri sqlite:///B:/DA_VSF/customer_churn_PL/report_17_6_2026/mlflow/mlflow.db `
    --default-artifact-root file:///B:/DA_VSF/customer_churn_PL/report_17_6_2026/mlflow/artifacts `
    --port 5000
  ```

---

## BƯỚC 3: Thiết lập Script Đẩy Dữ Liệu (`scripts/mlflow_track_and_register.py`)
Viết script Python để tự động hóa việc đọc dữ liệu huấn luyện từ `report_14_6_2026` và đẩy lên server MLflow. Script sẽ thực hiện các nhiệm vụ sau:

1. **Khởi tạo kết nối**: Kết nối tới server qua Tracking URI được chỉ định.
2. **Khởi tạo Experiment**: Tạo mới một experiment tên là `customer-return-prediction`.
3. **Đọc Artifacts từ Modeling (`report_14_6_2026`)**:
   * Đọc file so sánh `model_comparison.csv` để lấy danh sách mô hình và các chỉ số validation ban đầu và sau khi tuned.
   * Đọc file parameters json để lấy cấu hình tốt nhất của từng thuật toán.
4. **Log Run Cha (Parent Run - Model Comparison)**:
   * Ghi nhận tổng số ứng viên mô hình.
   * Lưu các file cấu trúc chung của dự án làm Artifacts (`4_Modeling.ipynb`, `feature_cols_v1.csv`, `Modeling_final_report.md`).
5. **Log Run Con (Nested Runs - Individual Models)**:
   * Tạo các run con cho từng mô hình: **LightGBM Tuned**, **Random Forest Tuned**, **Logistic Regression Tuned**.
   * Log các tham số (`params`), các chỉ số (`metrics` gồm PR-AUC, ROC-AUC, Precision, Recall, F1).
6. **Đóng gói và Đăng ký Champion Model**:
   * Đóng gói mô hình LightGBM kèm class wrapper `ThresholdedClassifier` chứa logic áp dụng threshold tối ưu đã khóa (`0.063357`).
   * Đăng ký mô hình vào Registry dưới tên `customer-return-champion`.
   * Gán nhãn alias `@champion` cho phiên bản này.

---

## BƯỚC 4: Thực thi và Đăng ký mô hình

Chạy script tracking trỏ về địa chỉ server để thực hiện kế hoạch:
```powershell
.\venv\Scripts\python.exe scripts/mlflow_track_and_register.py `
  --tracking-uri http://localhost:5000 `
  --experiment-name customer-return-prediction `
  --registered-model-name customer-return-champion
```

---

## BƯỚC 5: Đánh giá và Kiểm tra trên MLflow UI
1. Truy cập giao diện tại **`http://localhost:5000`**.
2. Kiểm tra tab **Experiments**:
   * Xác nhận sự tồn tại của experiment `customer-return-prediction`.
   * Kiểm tra các run con và so sánh biểu đồ PR-AUC giữa các mô hình trực tiếp trên UI.
3. Kiểm tra tab **Models**:
   * Xác nhận mô hình `customer-return-champion` đã xuất hiện trong Model Registry.
   * Đảm bảo tag `decision_threshold = 0.063357` và alias `champion` được map đúng vào Model Version 1.

---

## BƯỚC 6: Sử dụng mô hình từ Registry phục vụ Inference
Sau khi hoàn tất đăng ký, mô hình Champion có thể được tải từ bất kỳ script nào để đưa vào sử dụng:
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
model = mlflow.pyfunc.load_model("models:/customer-return-champion@champion")

# Dự đoán dữ liệu mới (tự động áp dụng threshold 0.063357)
# y_pred = model.predict(df_new_features)
```
