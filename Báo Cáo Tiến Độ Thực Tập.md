# BÁO CÁO TIẾN ĐỘ THỰC TẬP
## Dự án: Dự đoán Đơn hàng Bị Trả lại (Customer Return Prediction)

---

**Người thực hiện:** Nguyễn Bá Hào.
**Thời gian báo cáo:** Tháng 6/2026.
**Tech stack:** Python, Pandas, Scikit-learn, LightGBM, MLflow, FastAPI.

---

## Mục tiêu tổng quát

Xây dựng một hệ thống dự đoán end-to-end có khả năng phân loại đơn hàng thương mại điện tử theo hai nhãn: **trả hàng (returned = 1)** và **giao thành công (delivered = 0)**.

## QUY TRÌNH 

## 1. Kiểm tra Chất lượng Dữ liệu (Data Quality Check)

**Mục tiêu:** Kiểm tra các bảng dữ liệu thô trước khi bước vào phân tích và chọn model dự đoán, ghi nhận mọi vấn đề và lập action plan rõ ràng cho các bước tiếp theo.

### 1.1 Cấu trúc và phạm vi dữ liệu

- Xác định và load 6 bảng nguồn: `orders`, `order_items`, `customers`, `products`, `returns`, `payments`.
- Kiểm tra sự tồn tại của file, tính đầy đủ của cột theo schema kỳ vọng, và kiểu dữ liệu thực tế của từng cột.
- Ghi nhận shape và dtype toàn bộ hệ thống trước khi xử lý.

| Bảng | Số dòng | Số cột | Trạng thái |
|---|---|---|---|
| orders | 646,945 | 8 | Loaded OK |
| order_items | 714,669 | 7 | Loaded OK |
| customers | (theo orders) | 7 | Loaded OK |
| products | (theo items) | 8 | Loaded OK |
| returns | (theo orders) | 7 | Loaded OK |
| payments | 646,945 | 4 | Loaded OK |

**Kết quả:** Tất cả 6 file tồn tại, load thành công, và đủ cột kỳ vọng — không có lỗi cấu trúc nào.

### 1.2 Missing value và Duplicate

- Tính tỷ lệ missing theo từng cột, phân loại thành 4 mức: `none / low / medium / high`.
- Kiểm tra duplicate toàn dòng và duplicate theo key chính hoặc key tổ hợp của từng bảng.

**Kết quả missing đáng chú ý:**

| Cột | Bảng | Missing Rate | Mức | Hướng xử lý |
|---|---|---|---|---|
| promo_id | order_items | ~61.34% | high | Loại bỏ — missing có nghĩa (không dùng khuyến mãi) |
| promo_id_2 | order_items | ~99.97% | high | Loại bỏ hoàn toàn — gần như rỗng |

**Kết quả duplicate:**
- Không có duplicate toàn dòng trong cả 6 bảng.
- Key chính của `orders`, `customers`, `products`, `returns`, `payments` đều duy nhất hoàn toàn.
- `order_items` phát hiện **16 tổ hợp key `(order_id, product_id)` bị trùng**, ảnh hưởng **32 dòng** — đây là vấn đề ngầm có thể gây sai số khi aggregate feature.

### 1.3 Giá trị bất thường và Datetime

- Kiểm tra giá trị âm, bằng 0, khoảng min-max các cột số: `quantity`, `unit_price`, `discount_amount`, `payment_value`, `refund_amount`.
- Kiểm tra các cột danh mục về số lượng giá trị duy nhất.
- Parse và validate các cột ngày: `order_date`, `signup_date`, `return_date`.

**Kết quả:**
- Không có giá trị âm ở bất kỳ cột số nào.
- `discount_amount` có nhiều giá trị 0 — hoàn toàn hợp lý (đơn không giảm giá).
- `order_date`, `signup_date`, `return_date` đều parse được 100%, không có lỗi định dạng.
- Dữ liệu trải dài từ **2012-07-04 đến 2022-12-31** (10 năm lịch sử).
- Không có trường hợp `return_date` xảy ra trước `order_date`.

### 1.4 Quan hệ giữa các bảng và vòng đời đơn hàng

- Kiểm tra toàn bộ foreign key: `order_items.order_id`, `returns.order_id`, `payments.order_id` đối chiếu với `orders.order_id`; `order_items.product_id` và `returns.product_id` đối chiếu với `products.product_id`.
- Kiểm tra logic vòng đời đơn hàng (lifecycle): xác nhận trạng thái `returned` phải có bằng chứng trong bảng `returns`.

**Phân bố `order_status`:** `delivered`, `returned`, `cancelled`, `shipped`, `paid`, `created` — 6 trạng thái.

**Kết quả vòng đời:**
- 36,142 orders mang trạng thái `returned`; trong đó 36,062 có record tương ứng trong `returns`, còn **80 orders bị thiếu record** — được ghi nhận là lifecycle conflict mức medium.
- Không phát hiện `return_quantity > ordered_quantity` hay sản phẩm trả không thuộc đơn ban đầu.

### 1.5 Gắn nhãn và kiểm tra cân bằng lớp

- Gắn nhãn binary ở cấp order sau khi xác minh lifecycle: `returned_label = 1` nếu `order_status == returned` và có record returns; `returned_label = 0` nếu `order_status == delivered`.
- Các trạng thái khác giữ `returned_label = NaN` — không dùng làm nhãn model.

**Phân bố nhãn trên tập hợp lệ (552,778 orders):**

| Nhãn | Số lượng | Tỷ lệ |
|---|---|---|
| Delivered (0) | 516,716 | ~93.48% |
| Returned (1) | 36,062 | ~6.52% |
| NaN (loại khỏi tập binary) | 94,167 | — |

**Kết quả leakage risk:** Xác định các cột từ bảng `returns` (`return_date`, `return_reason`, `refund_amount`, `return_quantity`) và `order_status`, `has_return_record` là cột không được dùng làm feature vì chỉ biết sau khi đơn đã hoàn/trả.

---

## 2. Phân tích Khám phá Dữ liệu (EDA)

**Mục tiêu:** Kiểm chứng 5 nhóm giả thuyết nghiệp vụ về yếu tố ảnh hưởng đến tỷ lệ trả hàng, xây dựng feature map ưu tiên có căn cứ thực nghiệm cho bước Feature Engineering.

### 2.1 Tích hợp dữ liệu và thiết lập nền phân tích

- Join tạm 5 bảng trong RAM (không dùng `returns.csv`) để phục vụ vẽ biểu đồ.
- Loại bỏ duplicate trong `order_items` theo tổ hợp `(order_id, product_id)` trước khi join.
- Tạo nhãn `returned_label`, ép kiểu datetime, tính `customer_tenure_days`.
- Baseline return rate trên toàn tập phân tích: **~6.52%**.

### 2.2 Kết quả kiểm chứng các giả thuyết

**Giả thuyết 1 — Chân dung khách hàng (Customer Profile):**
- `customer_tenure_days` và `tenure_group`: các nhóm thâm niên có return rate dao động nhẹ quanh baseline, không có nhóm nào vượt trội rõ rệt.
- `age_group` và `gender`: return rate giữa các nhóm gần như không phân tách.
- **Kết luận:** giả thuyết "khách hàng mới trả hàng nhiều hơn" không được xác nhận mạnh. Các biến này giữ ở mức supporting.

**Giả thuyết 2 — Đặc trưng sản phẩm (Product Features):**
- `category`, `segment`, `size`, `color`: tín hiệu đơn lẻ yếu, chênh lệch return rate giữa các nhóm không đáng kể.
- Tín hiệu mạnh nhất là lịch sử trả hàng theo SKU (`product_historical_return_rate`) — nhưng phải tính bằng dữ liệu quá khứ để tránh leakage.
- **Kết luận:** thuộc tính sản phẩm là supporting feature; dữ liệu lịch sử sản phẩm cần xử lý cẩn thận leakage.

**Giả thuyết 3 — Phương thức thanh toán & Thiết bị:**
- `payment_method = COD`: return rate ~**11.37%**, cao gần gấp đôi so với các phương thức khác (~5.8%). Đây là tín hiệu rõ nhất trong toàn bộ EDA.
- `device_type` (`desktop` ~6.58%, `mobile` ~6.57%, `tablet` ~6.42%): gần như không phân tách.
- `order_source`: dao động từ ~6.50% đến ~6.61%, không có nguồn nào nổi bật.
- **Kết luận:** giả thuyết về COD được xác nhận rõ; giả thuyết về mobile và social media không được ủng hộ.

**Giả thuyết 4 — Giá trị & Quy mô đơn hàng:**
- `payment_value` theo quantile: Q1 (6.69%), Q2 (6.63%), Q3 (6.44%), Q4 (6.45%) — chênh lệch nhỏ.
- `quantity` và `discount_ratio`: tín hiệu yếu tương tự.
- **Kết luận:** giả thuyết không được xác nhận rõ. Các biến này giữ ở mức supporting.

**Giả thuyết 5 — Yếu tố Thời gian & Mùa vụ:**
- Return rate theo tháng dao động từ ~6.28% (tháng 6) đến ~6.79% (tháng 10) — không có mùa vụ nổi bật.
- Q4 không phải quý cao nhất (Q3 ~6.67% > Q4 ~6.57%).
- Cuối tuần vs ngày thường: gần như giống nhau.
- **Kết luận:** giả thuyết về mùa vụ và Q4 không được xác nhận.

### 2.3 Feature map ưu tiên từ EDA

| Mức ưu tiên | Feature |
|---|---|
| **High** | `is_cod`, `payment_method` |
| **Medium** | `customer_tenure_days`, `tenure_group`, `category`, `segment`, `size`, `device_type`, `order_source`, `payment_value`, `log_payment_value`, `quantity`, `discount_ratio`, `is_discounted` |
| **Low / Experimental** | `age_group`, `gender`, các biến thời gian (`order_month`, `order_quarter`, `is_weekend`...), các interaction feature |

---

## 3. Feature Engineering

**Mục tiêu:** Tạo bộ feature sạch, an toàn khỏi leakage, sẵn sàng cho Modeling. Toàn bộ quá trình chọn feature chỉ được thực hiện trên outer train; validation và test không được nhìn thấy ở bước này.

### 3.1 Làm sạch và tạo nhãn

- Loại bỏ duplicate trong `order_items` theo `(order_id, product_id)` trước khi aggregate.
- Loại bỏ `promo_id` và `promo_id_2` do tỷ lệ missing quá cao.
- `returns.csv` không được load hay sử dụng từ bước FE trở đi để loại trừ hoàn toàn rủi ro leakage từ nguồn.
- Khóa phân chia tập theo thời gian (temporal cutoff) **70/15/15** trước khi bắt đầu tạo feature.

### 3.2 Tạo candidate feature

Tổng hợp các feature ở cấp order-grain từ nhiều nhóm:

- **Customer features:** `customer_tenure_days`, `tenure_group` (4 bucket: new_lt_30d / 30_179d / 180_364d / loyal_365d_plus).
- **Product descriptor features:** multi-hot encoding cho `category` (4 nhóm), `segment` (6 nhóm), `size` (4 kích cỡ) — lấy max() khi aggregate về cấp order.
- **Payment features:** `payment_method`, `is_cod`, `log_payment_value`, `payment_value`, `payment_device_interaction`.
- **Order value features:** `total_quantity`, `unique_product_count`, `discount_ratio`, `is_discounted`.
- **Time features:** `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend`, `is_q4`.
- **Product target-history candidates:** tạo để audit nhưng đánh dấu chờ Leakage Gate quyết định.

### 3.3 Leakage Gate và lựa chọn feature

- Chạy Leakage Gate tự động: phân loại toàn bộ cột theo tiêu chí "có sẵn tại thời điểm đặt hàng hay không".
- Ba product target-history feature (`mean_product_return_rate`, `max_product_return_rate`, `high_risk_product_count`) đều nhận quyết định **BAN_LEAKAGE**.
- Các feature còn lại qua Quality Filter: loại bỏ cột hằng số và cột trùng lặp chữ ký.
- Wrapper selection dùng đồng thời Logistic Regression và LightGBM, metric chính là PR-AUC.

**Bộ feature cuối cùng: 28 feature**, được phân nhóm như sau:

| Nhóm | Feature | Số lượng |
|---|---|---|
| Numeric | `customer_tenure_days`, `total_quantity`, `unique_product_count`, `discount_ratio`, `log_payment_value` | 5 |
| Categorical | `payment_method`, `device_type`, `order_source`, `tenure_group`, `age_group`, `gender` | 6 |
| Binary (multi-hot) | `is_cod`, `is_discounted`, `category_*` (4), `segment_*` (6), `size_*` (4) | 16 |
| Quantile | `payment_value` | 1 |

### 3.4 Phân chia tập dữ liệu

Phân chia theo thứ tự thời gian (temporal split):

| Tập | Số orders | Tỷ lệ | Ghi chú |
|---|---|---|---|
| Train | ~386,768 | ~70% | Outer train — dùng để fit model và chọn feature |
| Validation | ~83,045 | ~15% | Outer validation — chọn threshold, so sánh model |
| Test | ~83,045 | ~15% | Chỉ dùng đúng 1 lần sau khi khóa champion |

---

## 4. Mô hình hóa (Modeling)

**Mục tiêu:** Huấn luyện, so sánh, tinh chỉnh và chọn model champion trên tập train/validation, đánh giá final test một lần duy nhất, sau đó lưu trữ toàn bộ artifact để chuẩn bị cho deployment.

### 4.1 Thiết lập bài toán và baseline

- Grain: 1 dòng / 1 `order_id`.
- Metric chính: **PR-AUC (average precision)** — phù hợp với bài toán mất cân bằng lớp mạnh (~6.52% positive).
- Preprocessing: `ColumnTransformer` với impute + scale (numeric), impute + OneHot (categorical), impute constant=0 (binary), impute + StandardScaler (quantile). Toàn bộ transformer **fit lại bên trong mỗi CV fold** để tránh leakage.
- Cross-validation: **3 expanding temporal folds** trên outer train.

**Baseline kết quả:**

| Model | PR-AUC | ROC-AUC | Ghi chú |
|---|---|---|---|
| Dummy (prior) | 0.063723 | 0.500000 | Mốc tham chiếu tối thiểu |
| Core Logistic (2 feature: is_cod, payment_method) | 0.076408 | 0.553883 | Mốc baseline nghiệp vụ |

### 4.2 Huấn luyện model ban đầu (3 model, 28 feature V1)

| Model | PR-AUC | ROC-AUC |
|---|---|---|
| Logistic Regression | 0.080873 | 0.550431 |
| Random Forest | 0.080320 | 0.547571 |
| LightGBM | 0.078067 | 0.538708 |

### 4.3 Phân tích threshold

- Tính threshold tối đa F1 và threshold đảm bảo Recall ≥ 70% cho từng model.
- Vẽ Precision-Recall và ROC curves trên outer validation để hỗ trợ quyết định vận hành.

### 4.4 Tinh chỉnh siêu tham số (Hyperparameter Tuning)

| Model | Phương pháp | Số cấu hình thử | Best CV PR-AUC |
|---|---|---|---|
| Logistic Regression | GridSearchCV | 2 configs | 0.086350 (C=0.1, balanced, l2) |
| Random Forest | RandomizedSearchCV | 5 configs | 0.084661 (250 trees, depth=8, balanced_subsample) |
| LightGBM | Bayesian (Optuna) | 15 trials | ~0.086532 |

### 4.5 Chọn model Champion

So sánh 3 model đã tuned trên outer validation, kết hợp đánh giá temporal stability qua 3 fold thời gian:

| Model | PR-AUC (validation) | ROC-AUC | Mean Fold PR-AUC | Std Fold PR-AUC |
|---|---|---|---|---|
| **LightGBM Tuned** | **0.082374** | **0.552626** | **0.086250** | **0.002915** |
| Logistic Regression Tuned | — | — | — | — |
| Random Forest Tuned | — | — | — | — |

**Champion: LightGBM Tuned** — được chọn theo validation PR-AUC và temporal stability.

**Locked threshold: 0.063357** (policy: max F1 trên outer validation).

### 4.6 Phân tích lỗi và khả năng giải thích

- Phân loại toàn bộ validation orders thành TP/TN/FP/FN.
- Vẽ Confusion Matrix và Calibration Curve.
- Trích xuất feature importance theo tree importance từ LightGBM.
- Chạy SHAP values trên mẫu 2,000 orders từ validation.

**Validation metrics của Champion (tại threshold 0.063357):**

| Metric | Giá trị |
|---|---|
| PR-AUC | 0.082374 |
| ROC-AUC | 0.552626 |
| Precision | 0.108733 |
| Recall | 0.240394 |
| F1 | 0.149738 |
| Balanced Accuracy | 0.553142 |

### 4.7 Đánh giá Final Test (chạy đúng 1 lần)

- Refit champion trên **train + validation (469,813 dòng)**, đánh giá trên **83,045 dòng test**.
- Kiểm tra reload audit: prediction sau khi load lại model khớp trên 100 sample rows.

**Test metrics cuối cùng:**

| Metric | Giá trị |
|---|---|
| PR-AUC | 0.084922 |
| ROC-AUC | 0.548519 |
| Precision | 0.115128 |
| Recall | 0.235675 |
| F1 | 0.154690 |
| Balanced Accuracy | 0.552761 |

**Decile lift (test set):**
- Decile 10 (nhóm rủi ro cao nhất): return rate **11.46%**, lift **1.71x** so với base rate.
- Decile 9: return rate **8.53%**, lift **1.27x**.

---

## 5. Xây dựng Inference Pipeline và Triển khai API

**Mục tiêu:** Đóng gói toàn bộ logic xử lý thành một sklearn Pipeline hoàn chỉnh, đăng ký lên MLflow Registry, và phơi bày qua FastAPI để phục vụ dự đoán theo thời gian thực.

### 5.1 Xây dựng Inference Pipeline

Thiết kế `inference_pipeline.py` với kiến trúc 3 bước trong một sklearn Pipeline:

- **Bước 1 — `_PipelineInputAdapter` (feature_builder):** Nhận master DataFrame thô → chạy `FeatureBuilder` → trả về đúng 28 feature cột theo thứ tự đã fit.
- **Bước 2 — `ColumnTransformer` (preprocessor):** Tiền xử lý đã fit từ training (impute, scale, encode) — load từ `artifacts/preprocessor_v1_outer_train.joblib`.
- **Bước 3 — `ThresholdedClassifierWrapper` (classifier):** Bọc model đã train, tích hợp threshold cố định (`LOCKED_THRESHOLD = 0.063357`) vào phương thức `predict()`.

`FeatureBuilder` xử lý các tác vụ chính:
- Leakage gate: từ chối inference nếu phát hiện các cột bị cấm (`mean_product_return_rate`, `max_product_return_rate`, `high_risk_product_count`, `has_return_record`).
- Multi-hot encoding cho `category`, `segment`, `size` ở cấp item trước khi aggregate.
- Aggregate về grain `order_id` (sum quantity, nunique product, max multi-hot).
- Tính các derived feature: `customer_tenure_days`, `log_payment_value`, `tenure_group`, `is_cod`, `discount_ratio`, `is_discounted`.

Ngoài ra, xây dựng hàm `load_joblib_artifact()` tự động vá lỗi tương thích khi load preprocessor từ phiên bản scikit-learn cũ (`SimpleImputer` thiếu attribute `_fill_dtype`).

### 5.2 Đăng ký Pipeline lên MLflow Registry (`register_pipeline.py`)

Quy trình đăng ký chạy một lần khi setup:
- Load preprocessor đã fit từ `artifacts/preprocessor_v1_outer_train.joblib`.
- Load model đã train từ `artifacts/final_model.joblib`; trích xuất classifier từ Pipeline lồng nếu cần.
- Build sklearn Pipeline 3 bước hoàn chỉnh.
- Log lên MLflow với `mlflow.sklearn.log_model()` và đăng ký tên `customer-return-champion`.
- Gắn alias `@champion` cho phiên bản mới nhất.

Model URI sau khi đăng ký: `models:/customer-return-champion@champion`.

### 5.3 FastAPI Serving (`app.py`)

Xây dựng REST API với các thành phần chính:

- **Lifecycle startup:** Load Pipeline từ MLflow khi server khởi động; server cho phép khởi động dù Pipeline chưa load được — `/health` sẽ phản ánh trạng thái.
- **Endpoint `GET /health`:** Trả về trạng thái Pipeline, URI MLflow và threshold hiện tại.
- **Endpoint `POST /predict`:** Nhận 2 loại input và trả về kết quả dự đoán:

| `input_type` | Mô tả |
|---|---|
| `batch` | Danh sách nhiều record phẳng (28 field) |
| `single_record` | Đúng 1 record phẳng |

**Cấu trúc response:**

```
{
  "n_predictions": int,
  "positive_rate": float,
  "predictions": [
    {
      "order_id": str,
      "return_probability": float,
      "prediction": 0 hoặc 1,
      "threshold": float
    }
  ]
}
```

- **Xử lý lỗi phân tầng:** HTTP 400 (file/key lỗi), 422 (dữ liệu không hợp lệ), 503 (Pipeline chưa load), 500 (lỗi server).
- **Threshold:** Lấy động từ bước cuối cùng của Pipeline (`pipeline.steps[-1][1].threshold`) thay vì hardcode trong API.

---

## 6. Đánh giá tổng thể và Hướng phát triển

### 6.1 Đánh giá tổng thể

**Điểm mạnh của dự án:**
- Tuân thủ nghiêm ngặt nguyên tắc chống data leakage ở mọi bước, từ việc loại `returns.csv` khỏi FE cho đến Leakage Gate tự động kiểm tra từng cột candidate.
- Temporal split và temporal CV đảm bảo đánh giá model phản ánh đúng điều kiện vận hành thực tế (dự đoán đơn hàng tương lai từ dữ liệu quá khứ).

**Giới hạn hiện tại:**
- PR-AUC trên test (**0.085**) và ROC-AUC (**0.549**) ở mức vừa phải; khoảng cách lift giữa 3 model sau tuning còn khá sát nhau, cho thấy giới hạn đến từ signal của feature hơn là từ thuật toán.
- Model phù hợp làm **risk ranking và triage** (ưu tiên đơn hàng cần kiểm tra), nhưng chưa đủ mạnh cho tác vụ **auto-block** hoặc quyết định tự động không cần duyệt người.
- Decile 10 đạt lift 1.71x — có ích trong vận hành nhưng còn thấp so với các bài toán tương tự có feature phong phú hơn.
- Chưa tích hợp feature lịch sử trả hàng theo sản phẩm (product historical return rate) do rủi ro leakage khi tính trên toàn bộ lịch sử.

### 6.2 Hướng phát triển

- **Feature phong phú hơn:** Tính feature lịch sử sản phẩm theo dạng point-in-time (chỉ dùng dữ liệu trước `order_date` của từng đơn), bao gồm `product_historical_return_rate` và `is_high_return_product`. Đây là feature được EDA đánh giá là tín hiệu mạnh nhất nhưng bị loại ở FE vì chưa có cơ chế tính an toàn.
- **Feature lịch sử khách hàng:** Tỷ lệ trả hàng theo khách hàng trong quá khứ, số đơn đã đặt, tần suất mua — tương tự cần xử lý point-in-time.
- **Cải thiện xử lý mất cân bằng lớp:** Thử nghiệm các kỹ thuật resampling (SMOTE, oversampling) kết hợp với threshold tuning tinh hơn.
- **Monitoring và retraining:** Xây dựng pipeline theo dõi drift của feature và label distribution theo thời gian; thiết lập chu kỳ retrain định kỳ khi phát hiện model degradation.
- **Mở rộng API:** Thêm endpoint `/explain` trả về SHAP values cho từng dự đoán, hỗ trợ đội vận hành hiểu lý do model đưa ra cảnh báo rủi ro.
- **Bảo mật và xác thực:** Bổ sung authentication/authorization cho API trước khi đưa vào production thực.
