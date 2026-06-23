# Kế Hoạch Inference Pipeline — Customer Return Prediction

> **Mục tiêu:** Nhận 5 file CSV thô → dự đoán xác suất mỗi đơn hàng bị hoàn trả (return) → trả về nhãn 0/1 kèm xác suất.

---

## Mục lục

1. [Bức tranh toàn cảnh](#1-bức-tranh-toàn-cảnh)
2. [Các khái niệm cần nắm](#2-các-khái-niệm-cần-nắm)
3. [Dữ liệu đầu vào](#3-dữ-liệu-đầu-vào)
4. [Cấu trúc thư mục](#4-cấu-trúc-thư-mục)
5. [Luồng dữ liệu — từ CSV đến predictions](#5-luồng-dữ-liệu--từ-csv-đến-predictions)
6. [File 1 — clean_data.py](#6-file-1--clean_datapy)
7. [File 2 — inference_pipeline.py](#7-file-2--inference_pipelinepy)
8. [File 3 — predict_model.py](#8-file-3--predict_modelpy)
9. [File 4 — app.py](#9-file-4--apppy)
10. [Mối liên kết giữa các file](#10-mối-liên-kết-giữa-các-file)
11. [Artifacts cần có trước khi chạy](#11-artifacts-cần-có-trước-khi-chạy)
12. [Checklist thực hiện](#12-checklist-thực-hiện)
13. [Lỗi phổ biến và cách tránh](#13-lỗi-phổ-biến-và-cách-tránh)

---

## 1. Bức tranh toàn cảnh

### Chúng ta đang ở đâu trong dự án?

Ở các report trước, team đã:
- **Report 12:** Xây `ColumnTransformer` (preprocessor) và fit trên outer train set → lưu thành `preprocessor_v1_outer_train.joblib`
- **Report 14:** Train model LightGBM, chọn champion, đăng ký lên MLflow Registry với alias `@champion`, xác định threshold tối ưu = **0.063357**

Bây giờ cần xây **inference pipeline** — tức là hệ thống chạy thực tế khi có data mới đến. Pipeline **không train lại model**, chỉ tái hiện đúng các bước xử lý đã làm lúc train rồi đưa qua model.

### Tại sao phải tái hiện chính xác?

Nếu xử lý data khác một chút so với lúc train (ví dụ: dùng `log()` thay vì `log1p()`, hoặc quên clip giá trị âm), model sẽ nhận input không khớp với thứ nó đã học → **kết quả dự đoán sai hoàn toàn nhưng không có error**. Đây gọi là **training-serving skew** và là lỗi nguy hiểm nhất khi deploy ML vì không phát hiện được ngay.

### Pipeline sẽ có 2 cách sử dụng

**CLI (`predict_model.py`)** — Batch inference, ví dụ chạy mỗi đêm để predict cho tất cả đơn trong ngày. Kết quả được log lên MLflow để audit và lưu ra file CSV.

**HTTP API (`app.py`)** — Real-time inference, các hệ thống khác gọi qua HTTP khi cần dự đoán ngay lập tức cho 1 batch đơn hàng.

---

## 2. Các khái niệm cần nắm

### sklearn.Pipeline là gì?

Là một object gộp nhiều bước xử lý thành một chuỗi tuần tự. Gọi `.transform(X)` → nó tự động chạy từng bước theo thứ tự, output của bước này là input của bước tiếp theo.

Dùng Pipeline thay vì gọi thủ công vì: đảm bảo thứ tự không bị đảo lộn, có thể save/load cả chuỗi bằng joblib, và MLflow có thể log toàn bộ như một artifact duy nhất.

### ColumnTransformer là gì?

Áp dụng transformer khác nhau cho từng nhóm cột trong cùng một bước. Ví dụ: numeric dùng StandardScaler, categorical dùng OneHotEncoder, binary giữ nguyên (passthrough). Output là numpy array đã được xử lý song song và ghép lại.

Preprocessor trong project này đã được **fit trên outer train set** và lưu thành file `.joblib`. Khi inference, chỉ được dùng `.transform()` — tuyệt đối không được `.fit()` lại vì sẽ làm mất thông tin học được từ lúc train.

### MLflow có 2 phần hoàn toàn riêng biệt

**Model Registry** — Nơi lưu model đã train. Champion model được đăng ký với tên `customer-return-champion` và alias `@champion`. Khi load, dùng URI `models:/customer-return-champion@champion`.

**Experiment Tracking** — Ghi lại mỗi lần chạy inference: params (config), metrics (kết quả), artifacts (file output), và bản thân sklearn Pipeline. Dùng để audit sau này — ai chạy lúc nào, với data nào, ra kết quả gì.

### Grain của DataFrame

"Grain" = mỗi hàng đại diện cho cái gì. Pipeline yêu cầu **grain = order_id** ở mọi bước sau clean. Nếu bị duplicate → model predict cùng 1 đơn nhiều lần → kết quả sai.

### Data Leakage

Là dùng thông tin mà trong thực tế sẽ không có lúc predict. File `returns.csv` chứa thông tin đơn đã bị return — tức là chính cái chúng ta đang cố dự đoán. Không được load, không được join, không được reference bất kỳ cột nào từ file này.

---

## 3. Dữ liệu đầu vào

### Sơ đồ quan hệ

```
customers.csv ──────────────► orders.csv ◄──────────── order_items.csv
(customer_id, signup_date,    (order_id,               (order_id, product_id,
 age_group, gender)            customer_id,             quantity, unit_price,
                               order_date,              discount_amount)
                               payment_method,               │
                               device_type,                  ▼
                               order_source)           products.csv
                                    │                  (product_id, category,
                                    ▼                   segment, size)
                              payments.csv
                              (order_id, payment_value)
```

### Chi tiết từng bảng

**orders.csv** — Bảng trung tâm, grain = order_id

| Cột | Ghi chú |
|-----|---------|
| `order_id` | PK, không null |
| `customer_id` | FK → customers |
| `order_date` | String, phải parse datetime trước khi dùng |
| `payment_method` | Feature categorical |
| `device_type` | Feature categorical |
| `order_source` | Feature categorical |
| `order_status` | ⛔ Không được dùng khi inference — đây chính là label |

**order_items.csv** — Grain = (order_id, product_id) trước khi aggregate

| Cột | Ghi chú |
|-----|---------|
| `quantity` | Có 16 duplicate pairs → phải sum |
| `unit_price` | Dùng để tính `line_gross_value` **trước** khi aggregate |
| `discount_amount` | Sum khi aggregate |
| `promo_id` | ⛔ DROP — 61% missing |
| `promo_id_2` | ⛔ DROP — 99.97% missing |

**customers.csv** — Grain = customer_id

| Cột | Ghi chú |
|-----|---------|
| `signup_date` | String, phải parse datetime để tính tenure |
| `age_group` | Feature categorical |
| `gender` | Feature categorical |

**products.csv** — Grain = product_id

| Cột | Ghi chú |
|-----|---------|
| `category` | 4 giá trị: Casual / GenZ / Outdoor / Streetwear → multi-hot |
| `segment` | 6 giá trị: Activewear / Balanced / Everyday / Performance / Premium / Standard → multi-hot |
| `size` | 4 giá trị: L / M / S / XL → multi-hot |

**payments.csv** — Grain = order_id

| Cột | Ghi chú |
|-----|---------|
| `payment_value` | Giá trị thanh toán thực tế |

> ⛔ **returns.csv** — Không được load. Toàn bộ file này là leakage.

---

## 4. Cấu trúc thư mục

```
report_2026_6_19/
│
├── plan_inference_pipeline.md          ← File này
│
├── artifacts/                          ← Artifacts từ các report trước, KHÔNG tạo lại
│   ├── preprocessor_v1_outer_train.joblib  ← ColumnTransformer đã fit (từ Report 12)
│   └── final_model.joblib              ← Local fallback nếu MLflow không available
│
├── scripts/
│   ├── __init__.py                     ← File rỗng (bắt buộc)
│   ├── clean_data.py                   ← Bước 1: load + clean + validate
│   ├── inference_pipeline.py           ← Bước 2: FeatureBuilder + Pipeline + Model
│   └── predict_model.py               ← Bước 3: CLI runner với MLflow tracking
│
├── api/
│   ├── __init__.py                     ← File rỗng (bắt buộc)
│   └── app.py                          ← FastAPI, 5 endpoints
│
├── data/                               ← 5 file CSV input
│   ├── orders.csv
│   ├── order_items.csv
│   ├── customers.csv
│   ├── products.csv
│   └── payments.csv
│
├── outputs/                            ← Kết quả được tạo ra lúc chạy
│   ├── cleaned_sample.csv
│   ├── features_sample.csv
│   └── predictions_<run_id>.csv
│
├── dockerfile
└── docker-compose.yml
```

---

## 5. Luồng dữ liệu — từ CSV đến predictions

```
5 file CSV
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  clean_data.py                                              │
│                                                             │
│  Load → Parse datetime → Xử lý order_items → Aggregate     │
│  → Multi-hot products → Merge tất cả → Validate schema     │
│                                                             │
│  OUTPUT: cleaned_df  (grain = order_id, ~35 cột)           │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  inference_pipeline.py — sklearn.Pipeline (2 steps)         │
│                                                             │
│  Step A: FeatureBuilder (stateless Transformer)             │
│    • Tính log_payment_value = log1p(payment_value)          │
│    • Tính tenure_group từ customer_tenure_days              │
│    • Kiểm tra leakage gate (banned features)                │
│    • Chọn đúng 30 cột input                                 │
│                                                             │
│  Step B: ColumnTransformer (load từ .joblib đã fit)         │
│    • numeric  (5 cột) → Imputer(median) → StandardScaler    │
│    • categorical (6 cột) → Imputer(freq) → OneHotEncoder    │
│    • binary  (16 cột) → Imputer(freq) → passthrough         │
│    • quantile (1 cột) → Imputer(median) → KBins(4) → OHE   │
│                                                             │
│  OUTPUT: X_preprocessed (numpy array ~70+ chiều)           │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────┐
│  ThresholdedClassifierWrapper                               │
│                                                             │
│  Load champion từ MLflow Registry                           │
│    • Thử sklearn flavor trước → giữ được predict_proba()   │
│    • Thử lightgbm flavor nếu sklearn thất bại              │
│    • Fallback local bundle nếu MLflow không available       │
│                                                             │
│  predict_proba(X)[:, 1] → proba (float 0→1)                │
│  (proba >= 0.063357).astype(int) → label (0 hoặc 1)        │
│                                                             │
│  OUTPUT: predictions DataFrame (4 cột)                     │
└─────────────────────────────────┬───────────────────────────┘
                                  │
                      ┌───────────┴──────────┐
                      ▼                      ▼
             predict_model.py            app.py
             (CLI + MLflow)           (FastAPI HTTP)
```

### 30 cột input cho ColumnTransformer

| Nhóm | Số cột | Các cột |
|------|--------|---------|
| Numeric | 5 | `customer_tenure_days`, `total_quantity`, `unique_product_count`, `discount_ratio`, `log_payment_value` |
| Categorical | 6 | `payment_method`, `device_type`, `order_source`, `tenure_group`, `age_group`, `gender` |
| Binary | 16 | `is_cod`, `is_discounted`, 4 category_, 6 segment_, 4 size_ |
| Quantile | 1 | `payment_value` |

### Features bị cấm (leakage)

| Feature | Lý do |
|---------|-------|
| `order_status` | Chính là label của model |
| `mean_product_return_rate` | Tính từ returns.csv |
| `max_product_return_rate` | Tính từ returns.csv |
| `high_risk_product_count` | Tính từ returns.csv |
| `has_return_record` | Tính từ returns.csv |

---

## 6. File 1 — `clean_data.py`

### Nhiệm vụ

Nhận đường dẫn thư mục chứa 5 CSV → trả về `cleaned_df` chuẩn hóa đủ cột để bước tiếp theo xây feature.

File này chỉ làm đúng một việc: làm sạch và merge data. Không tạo feature, không preprocess, không load returns.csv.

### Kết quả mong đợi

`cleaned_df` với grain = order_id (mỗi hàng là 1 đơn hàng duy nhất), khoảng 35 cột bao gồm IDs, các cột raw cần thiết, và 14 cột multi-hot từ products.

Kèm theo `summary` dict gồm: số đơn, số cột, null counts — để caller biết data trông như thế nào.

### Ý tưởng triển khai từng bước

**Bước 1 — Load 5 bảng**
Đọc từng file CSV, raise `FileNotFoundError` rõ ràng nếu thiếu file nào. order_items cần `low_memory=False` vì có cột mixed type.

**Bước 2 — Parse datetime**
Parse `order_date` và `signup_date` trước tất cả phép tính liên quan đến ngày. Dùng `errors="coerce"` để chuyển giá trị lỗi thành NaT thay vì crash.

**Bước 3 — Xử lý order_items (thứ tự bắt buộc)**
Phải làm theo đúng thứ tự này, không được hoán đổi:
1. Drop `promo_id` và `promo_id_2`
2. Tính `line_gross_value = quantity × unit_price` — phải làm **trước** khi aggregate vì `unit_price` sẽ mất sau khi sum
3. Aggregate theo `(order_id, product_id)` để xử lý 16 duplicate pairs, dùng `.sum()` cho quantity, discount_amount, line_gross_value

**Bước 4 — Aggregate lên grain order_id**
Từ `(order_id, product_id)` lên `order_id`, tính: `total_quantity`, `unique_product_count`, `total_discount_amount`, `total_gross_value`.

**Bước 5 — Multi-hot encode products**
Join order_items với products để biết mỗi sản phẩm thuộc category/segment/size nào. Tạo binary flag cho từng giá trị, rồi aggregate về order_id bằng `.max()` — nếu bất kỳ sản phẩm nào trong đơn có category_Casual = 1 thì đơn đó = 1. Kết quả: 14 cột multi-hot.

**Bước 6 — Tính derived cols từ orders + customers**
Join customers vào orders, tính `customer_tenure_days = (order_date - signup_date).dt.days`, tính `is_cod = 1 nếu payment_method == "COD"`.

**Bước 7 — Merge tất cả về grain order_id**
Merge theo thứ tự: orders (đã có customers) → order_level → product_multihot → payments. Dùng `how="left"` để giữ tất cả orders.

**Bước 8 — Tính discount features**
`discount_ratio = total_discount_amount / total_gross_value` (= 0 nếu gross = 0 để tránh chia 0), `is_discounted = 1 nếu discount_ratio > 0`.

**Bước 9 — Validate schema**
Kiểm tra đủ cột theo `REQUIRED_OUTPUT_COLS`, kiểm tra grain không bị duplicate. Fail-fast ở đây để lỗi xuất hiện đúng chỗ với message rõ ràng.

---

## 7. File 2 — `inference_pipeline.py`

### Nhiệm vụ

Chứa toàn bộ logic biến `cleaned_df` thành predictions. Có 3 class và 2 helper function.

### Kết quả mong đợi

`InferencePipeline` là class chính — khởi tạo một lần, gọi `.predict(cleaned_df)` nhiều lần. Trả về DataFrame 4 cột: `order_id`, `return_probability`, `prediction`, `threshold`.

Ngoài ra có `build_full_pipeline_for_logging()` để lấy sklearn Pipeline đầy đủ 3 bước phục vụ việc log lên MLflow.

### Class 1 — FeatureBuilder (sklearn Transformer)

**Nhiệm vụ:** Nhận `cleaned_df` → trả về DataFrame 30 cột sẵn sàng cho ColumnTransformer.

**Kế thừa `BaseEstimator` và `TransformerMixin`** để có thể đặt vào sklearn.Pipeline như một step bình thường.

**Stateless** — không học gì từ data vì tất cả công thức đều cố định (bins tenure_group là hằng số, log là công thức toán học).

Hai việc cần làm:
- Tính `log_payment_value = log1p(payment_value.clip(lower=0))` — dùng `log1p` để xử lý giá trị 0, dùng `clip` để xử lý giá trị âm nếu có
- Tính `tenure_group` bằng `pd.cut` với bins cố định `[0, 30, 180, 365, ∞)` → 4 label: `new_lt_30d`, `30_179d`, `180_364d`, `loyal_365d_plus`. Chuyển sang string để SimpleImputer xử lý được.

Trước khi làm bất cứ gì: kiểm tra leakage gate — nếu bất kỳ banned feature nào xuất hiện trong columns → raise ValueError ngay lập tức.

### Class 2 — ThresholdedClassifierWrapper (sklearn Estimator)

**Nhiệm vụ:** Bọc champion model + threshold thành một sklearn-compatible final step để Pipeline hoàn chỉnh có thể log lên MLflow.

sklearn.Pipeline yêu cầu final step phải có `.fit()` và `.predict()`. Champion model có thể là sklearn object hoặc LightGBM native — wrapper chuẩn hóa interface cho cả hai.

**Method `_predict_proba_positive_class(X)`** — logic cốt lõi dùng chung cho cả `predict_proba` lẫn `predict`:
- Nếu flavor = `"sklearn"` hoặc `"joblib"`: gọi `model.predict_proba(X)[:, 1]`
- Nếu flavor = `"lightgbm"`: gọi `model.predict(X)` (LightGBM native trả về proba trực tiếp, không cần `[:, 1]`)

`predict_proba(X)` → trả về `(n, 2)` array theo sklearn convention: cột 0 là prob class 0, cột 1 là prob class 1.

`predict(X)` → áp dụng threshold → binary label.

### Class 3 — InferencePipeline

**Nhiệm vụ:** Orchestrate toàn bộ: load artifacts → predict → cung cấp pipeline để log MLflow.

**Load order ưu tiên MLflow trước** — đây là điểm quan trọng nhất. MLflow Registry là source of truth cho champion model. Local fallback chỉ được dùng khi MLflow thực sự không available. Không bao giờ load local trước chỉ vì file tồn tại.

Khi load model từ MLflow, thử sklearn flavor trước (giữ được `predict_proba()`), nếu thất bại mới thử lightgbm flavor. Tuyệt đối không dùng `mlflow.pyfunc.load_model()` vì pyfunc không có `predict_proba()` → crash.

Sau khi load, `_transform_pipeline` chứa đúng 2 step: `FeatureBuilder → ColumnTransformer`. Classifier được xử lý riêng khi predict để linh hoạt với nhiều flavor.

**`.predict(cleaned_df)`** → lưu order_ids trước → transform → tính proba → áp threshold → ghép kết quả thành DataFrame.

**`.build_full_pipeline_for_logging()`** → trả về sklearn.Pipeline 3 bước đầy đủ: `FeatureBuilder → ColumnTransformer → ThresholdedClassifierWrapper`. Pipeline này log được lên MLflow và load lại được bằng `mlflow.sklearn.load_model()`.

### Helper: `_patch_legacy_sklearn_object()`

Patch backward-compatibility của sklearn pickle cũ. `SimpleImputer` từ sklearn version cũ thiếu attribute `_fill_dtype` → gây crash khi load `.joblib`. Hàm này duyệt đệ quy artifact và backfill attribute thiếu. Phải chạy ngay sau `joblib.load()`.

---

## 8. File 3 — `predict_model.py`

### Nhiệm vụ

CLI runner — orchestrate toàn bộ inference batch, log đầy đủ lên MLflow Tracking.

File này không chứa business logic, chỉ gọi các module khác theo đúng thứ tự và ghi kết quả.

### Kết quả mong đợi

Sau khi chạy:
- 1 MLflow run mới trong experiment `customer-return-inference`
- File `outputs/predictions_<run_id[:8]>.csv` chứa kết quả predict
- Full sklearn Pipeline (3 bước) đã được log lên MLflow artifact `sk_pipeline` và registered vào model `customer-return-sk-pipeline`
- MLflow run có đủ params, metrics, tags để audit

### Ý tưởng triển khai

**Khởi tạo MLflow run** với tên có timestamp để phân biệt các lần chạy.

**Bước 1: Clean data** — gọi `clean_data(data_dir)`. Nếu fail → set tag `status=FAILED_clean_data` và raise.

**Bước 2: Load pipeline** — khởi tạo `InferencePipeline` với `fallback_model_path=None`. Truyền `None` để buộc load từ MLflow, không cho phép dùng local fallback khi chạy batch inference chính thức.

**Log params ngay sau khi pipeline load** — lấy `threshold` từ `pipeline.threshold`, không hardcode. Nếu threshold thay đổi trong tương lai, params vẫn được log đúng.

**Bước 3: Predict** — gọi `pipeline.predict(cleaned_df)`.

**Log metrics** — `positive_rate`, `mean/max/min_probability`, `n_predictions`.

**Bước 4: Log full sklearn Pipeline** — gọi `pipeline.build_full_pipeline_for_logging()` rồi `mlflow.sklearn.log_model()`. Bước này đảm bảo MLflow có đủ pipeline để reproduce kết quả sau này.

**Lưu CSV** — tên file gồm `run_id[:8]` để dễ tìm lại trên MLflow UI.

---

## 9. File 4 — `app.py`

### Nhiệm vụ

FastAPI server — HTTP interface cho InferencePipeline. Cho phép các hệ thống khác gọi predict qua REST API.

### Kết quả mong đợi

Server chạy ở port 8000 với 5 endpoints, Swagger UI tự động ở `/docs`.

### Singleton pattern

Pipeline được load một lần lúc server khởi động (`lifespan` context manager), không load lại cho mỗi request. Load model mất vài giây — nếu load mỗi request sẽ không thể dùng được.

Dùng `lifespan` thay vì `@app.on_event("startup")` vì `on_event` đã deprecated từ FastAPI v0.93.

### 5 Endpoints

| Endpoint | Method | Mục đích |
|----------|--------|---------|
| `/health` | GET | Kiểm tra server và pipeline có sẵn sàng không |
| `/model-info` | GET | Thông tin chi tiết: threshold, features, flavor |
| `/clean` | POST | Debug — xem output sau bước clean_data |
| `/features` | POST | Debug — xem output sau bước FeatureBuilder |
| `/predict` | POST | Endpoint chính — chạy full pipeline, trả về predictions |

### Request / Response

`/predict` nhận `{"data_dir": "data/"}` → trả về JSON gồm `n_predictions`, `positive_rate`, và mảng `predictions` mỗi phần tử có `order_id`, `return_probability`, `prediction`, `threshold`.

### Error handling

- `FileNotFoundError` → 400 (caller cung cấp đường dẫn sai)
- `ValueError` (leakage gate hoặc schema) → 422
- `RuntimeError` (model predict lỗi) → 500
- Pipeline chưa load → 503

---

## 10. Mối liên kết giữa các file

```
data/ (5 CSV)
    │
    │  import clean_data()
    ▼
clean_data.py ──────────────────────────────────────────────────────────────┐
    │  trả về cleaned_df                                                     │
    │                                                                        │
    │  import InferencePipeline, FeatureBuilder                              │
    ▼                                                                        │
inference_pipeline.py                                                        │
    │  load artifacts/preprocessor_v1_outer_train.joblib                    │
    │  load models:/customer-return-champion@champion từ MLflow             │
    │  trả về predictions DataFrame                                          │
    │  trả về full Pipeline để log MLflow                                   │
    │                                                                        │
    ├──────────────────────────────────────────────────────────────────┐     │
    │                                                                  │     │
    │  sử dụng bởi                                                     │  sử dụng bởi
    ▼                                                                  ▼
predict_model.py                                                    app.py
(CLI: python scripts/predict_model.py)                         (API: uvicorn api.app:app)
    │                                                                  │
    │  log lên                                                         │  trả về HTTP response
    ▼                                                                  │
MLflow Tracking                                                        │
    │  params, metrics, artifacts                                      │
    │  full sklearn Pipeline                                           │
    ▼                                                                  │
outputs/predictions_<run_id>.csv ◄────────────────────────────────────┘
```

### Quy tắc import

`predict_model.py` và `app.py` import từ `scripts.clean_data` và `scripts.inference_pipeline`. Không import theo chiều ngược lại. `clean_data.py` và `inference_pipeline.py` không biết gì về nhau — mỗi file làm đúng một việc.

---

## 11. Artifacts cần có trước khi chạy

| Artifact | Nguồn | Bắt buộc? |
|----------|-------|-----------|
| `artifacts/preprocessor_v1_outer_train.joblib` | Report 12 fe_outputs | Bắt buộc |
| Champion model trong MLflow Registry với alias `@champion` | Report 14 | Bắt buộc |
| `artifacts/final_model.joblib` | Report 14 modeling_outputs | Chỉ cần khi MLflow offline |

**Script bootstrap** (`bootstrap_report_assets.py`) tự động copy các file này từ các report trước. Chạy trước khi làm bất cứ gì.

**Xác nhận MLflow và model trước khi chạy:**
```
curl http://localhost:5000/health
```
Rồi verify model tồn tại và xác định flavor (sklearn hay lightgbm) bằng Python:
```
mlflow.models.get_model_info("models:/customer-return-champion@champion").flavors
```

---

## 12. Checklist thực hiện

### Phase 0 — Chuẩn bị

- [ ] Chạy bootstrap script để copy data và artifacts
- [ ] Verify `artifacts/preprocessor_v1_outer_train.joblib` tồn tại
- [ ] Verify MLflow server đang chạy và model `@champion` đã được register
- [ ] Xác định flavor của champion model (sklearn hay lightgbm)

### Phase 1 — Test từng file độc lập

- [ ] Test `clean_data()` độc lập: in `summary` và `df.shape` → phải ra đúng số orders, đúng số cột
- [ ] Test `FeatureBuilder.transform()` độc lập: in `features.shape` → phải ra `(n, 30)`
- [ ] Test `InferencePipeline.predict()`: in `results.head()` và `results["prediction"].value_counts()`
- [ ] Test leakage gate: tạo DataFrame có cột `order_status` → phải raise ValueError

### Phase 2 — Test CLI

- [ ] Chạy: `python scripts/predict_model.py --data-dir data/ --output-dir outputs/`
- [ ] Kiểm tra file `outputs/predictions_*.csv` được tạo
- [ ] Kiểm tra MLflow UI có run mới với params, metrics, artifacts đầy đủ
- [ ] Kiểm tra `customer-return-sk-pipeline` xuất hiện trong MLflow Registry

### Phase 3 — Test API

- [ ] Chạy: `uvicorn api.app:app --reload --port 8000`
- [ ] `GET /health` → `{"status": "ok", "pipeline_ready": true}`
- [ ] `POST /predict` với `{"data_dir": "data/"}` → trả về predictions
- [ ] Mở `http://localhost:8000/docs` → test từng endpoint

### Phase 4 — Docker

- [ ] Build: `docker-compose up --build`
- [ ] Verify MLflow container healthy trước khi pipeline_runner bắt đầu
- [ ] Kiểm tra predictions CSV trong `outputs/`

---

## 13. Lỗi phổ biến và cách tránh

### Local bundle load thay vì MLflow

**Triệu chứng:** Pipeline chạy được nhưng MLflow Registry không có model mới. Log MLflow thiếu `sk_pipeline` artifact.

**Nguyên nhân:** `InferencePipeline` load `final_model.joblib` local vì file tồn tại, bỏ qua MLflow hoàn toàn.

**Cách tránh:** Trong `predict_model.py`, luôn truyền `fallback_model_path=None`. Chỉ dùng local fallback khi debug hoặc khi MLflow thực sự không available.

---

### `AttributeError: 'PyFuncModel' has no attribute 'predict_proba'`

**Nguyên nhân:** Dùng `mlflow.pyfunc.load_model()` rồi gọi `predict_proba()`. pyfunc wrapper không expose method này.

**Cách tránh:** Luôn dùng `mlflow.sklearn.load_model()` hoặc `mlflow.lightgbm.load_model()`.

---

### Grain violation — predictions bị duplicate

**Triệu chứng:** `ValueError: Grain violation — cleaned_df có N rows nhưng chỉ có M unique order_id`.

**Nguyên nhân:** Một bảng có nhiều rows cho cùng order_id (ví dụ: payments có 2 dòng cho 1 đơn) → merge tạo ra many-to-many join.

**Cách tránh:** Aggregate payments về grain order_id trước khi merge nếu cần.

---

### Training-serving skew (nguy hiểm nhất — không có error)

**Triệu chứng:** Positive rate bất thường (0% hoặc 100%), phân phối probability lạ.

**Nguyên nhân phổ biến:**
- `line_gross_value` được tính **sau** khi aggregate (sai thứ tự)
- `tenure_group` dùng bins khác lúc train
- `log_payment_value` dùng `log()` thay vì `log1p()`
- ColumnTransformer được `.fit()` lại thay vì chỉ `.transform()`

**Cách debug:** In `results["return_probability"].describe()` — nếu median rất gần 0 hoặc 1, hoặc variance gần 0 → có skew.

---

### Threshold hardcode sai

**Triệu chứng:** params trong MLflow log threshold = 0.063357 nhưng pipeline dùng threshold khác.

**Cách tránh:** Không bao giờ hardcode threshold trong `predict_model.py`. Luôn lấy từ `pipeline.threshold` sau khi load.

---

### sklearn pickle cũ crash khi load

**Triệu chứng:** `AttributeError: 'SimpleImputer' object has no attribute '_fill_dtype'` khi load `preprocessor_v1_outer_train.joblib`.

**Cách tránh:** Luôn dùng `_load_joblib_with_patch()` thay vì `joblib.load()` trực tiếp. Hàm này tự động patch backward-compatibility.