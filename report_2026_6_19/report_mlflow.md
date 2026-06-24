# Báo Cáo Quy Trình Thực Hiện MLflow Pipeline & REST API

**Dự án:** Customer Return Prediction  
**Ngày:** 19/06/2026

---

## Mục Tiêu

Xây dựng hệ thống dự đoán khả năng hoàn trả đơn hàng của khách hàng, bao gồm ba thành phần chính: đóng gói ML Pipeline lên MLflow Registry, triển khai REST API bằng FastAPI, và container hóa toàn bộ hệ thống bằng Docker Compose.

---

## Tóm Tắt Luồng

```
Dữ liệu thô (CSV)
      │
      ▼
  aggregate.py  →  master table
      │
      ▼
  FeatureBuilder  →  28 features
      │
      ▼
  Preprocessor (ColumnTransformer)
      │
      ▼
  LightGBM + Threshold  →  nhãn 0/1
      │
      ▼
  MLflow Registry  ←  register_pipeline.py
      │
      ▼
  FastAPI /predict  →  JSON response
```

---

## Quy Trình Cụ Thể

### Bước 1 — Aggregate dữ liệu (`aggregate.py`)

**Input:** 5 file CSV (orders, order_items, customers, products, payments) (đây là dữ liệu ví dụ sẽ dùng dữ liệu thực tế nếu có)

**Thực hiện:** Join 5 bảng lại với nhau bằng các câu lệnh LEFT JOIN theo khóa ngoại tương ứng thành một master table duy nhất.

**Output:** Master table, mỗi dòng tương ứng một đơn hàng.

---

### Bước 2 — Xây dựng features (`inference_pipeline.py` — FeatureBuilder)

**Input:** Master table từ bước 1

**Thực hiện:** 
- thực hiện các bước tiền xử lý cơ bản
- thực hiện tạo các feature đã biết trong quá trình FE

**Output:** Bảng đặc trưng 28 cột chuẩn hóa, sẵn sàng đưa vào model.

---

### Bước 3 — Tiền xử lý (`inference_pipeline.py` — ColumnTransformer)

**Input:** Bảng đặc trưng 28 cột

**Thực hiện:** Thực hiện tiền xử lý với các cột có kiểu dữ liệu khác nhau. Với cột dữ liệu số thì thực hiện điền khuyết bằng trung bình, sau đó chuẩn hóa StandardScaler. Với cột dữ liệu phân loại thì thực hiện điền khuyết bằng phương pháp most_frequent, sau đó one-hot encode.

**Output:** Ma trận số đã chuẩn hóa, sẵn sàng đưa vào model LightGBM.

---

### Bước 4 — Dự đoán (`inference_pipeline.py` — ThresholdedClassifierWrapper)

**Input:** Ma trận số đã chuẩn hóa và làm sạch

**Thực hiện:** bọc quy trình (model.predict_proba() → so sánh với ngưỡng và trả kết quả dự đoán)

**Output:** Nhãn dự đoán (0 = không hoàn trả, 1 = hoàn trả) kèm xác suất.

---

### Bước 5 — Đăng ký Pipeline lên MLflow (`register_pipeline.py`)

**Input:** sklearn pipeline và model đã huấn luyện từ thư mục `artifacts/`

**Thực hiện:** Load model đã train từ thư mục artifacts/, sau đó thực hiện đóng gói (sklearn pipeline + model pkl) và đưa lên MLflow

**Output:** Pipeline được lưu tại URI `models:/customer-return-champion@champion`, có thể load lại bất cứ lúc nào.

---

### Bước 6 — REST API phục vụ dự đoán (`api/app.py`)

**Input:** thư mục chứa các bảng dữ liệu rời rạc (ví dụ data/), table đã tổng hợp, record đã tổng hợp (JSON)

**Thực hiện:** Load MLflow pipeline đã đóng gói từ MLflow (load_model()) sau đó đưa thực hiện dự đoán   và trả kết quả

**Output:** JSON response gồm nhãn dự đoán, xác suất hoàn trả và ngưỡng đang dùng cho từng đơn hàng.

---

### Hạ tầng Docker Compose

Ba container khởi động theo thứ tự bắt buộc:

```
mlflow_server  →  register_pipeline  →  api
 (port 5000)       (exit sau khi         (port 8000)
                    register xong)
```

`api` chỉ được phép khởi động sau khi `register_pipeline` hoàn thành thành công, đảm bảo model luôn tồn tại trong Registry trước khi API load.

---

## Demo

**Swagger UI:** `http://localhost:8000/docs`

**Input mẫu** (dán vào `/predict`):

```json
{
  "input_type": "single_record",
  "record": {
    "order_id": "ORD-TEST-001",
    "customer_id": "CUST-001",
    "order_date": "2024-03-15",
    "order_status": "delivered",
    "order_source": "app",
    "device_type": "mobile",
    "signup_date": "2023-06-01",
    "gender": "Male",
    "age_group": "25-34",
    "product_id": "PROD-001",
    "quantity": 2,
    "unit_price": 350000,
    "discount_amount": 35000,
    "category": "Casual",
    "segment": "Everyday",
    "size": "M",
    "payment_method": "MOMO",
    "payment_value": 665000
  }
}
```

**Output mong đợi:**

```json
{
  "n_predictions": 1,
  "positive_rate": 0.0,
  "predictions": [
    {
      "order_id": "ORD-TEST-001",
      "return_probability": 0.031,
      "prediction": 0,
      "threshold": 0.063357
    }
  ]
}
```