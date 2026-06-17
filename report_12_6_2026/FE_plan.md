# Kế Hoạch Feature Engineering
## Dự đoán đơn hàng bị trả lại tại thời điểm đặt hàng

## 1. Modeling Contract

- Grain: **1 dòng = 1 `order_id` = 1 label**.
- Target lấy duy nhất từ `orders.order_status`:
  - `returned` → `returned_label = 1`.
  - `delivered` → `returned_label = 0`.
  - Trạng thái khác không dùng để huấn luyện.
- Feature chỉ được sử dụng nếu tồn tại tại hoặc trước `order_date`.
- Outcome tương lai được phép dùng làm target, không được dùng làm feature.
- `returns.csv` không được load, join hoặc audit từ FE trở đi.
- EDA và Data Quality trước FE không nằm trong phạm vi thay đổi.

## Phase 0 - Setup & Config

- Import pandas, scipy, scikit-learn, LightGBM và thư viện báo cáo.
- Khai báo output directories, `RANDOM_STATE`, target và primary selection metric.
- PR-AUC là metric chính cho feature wrapper vì positive class mất cân bằng.

## Phase 1 - Load & Audit

Chỉ load:

- `orders`
- `order_items`
- `customers`
- `products`
- `payments`

Audit:

- Shape, dtype, missing.
- Unique key.
- Duplicate `order_id + product_id`.
- Không tạo bất kỳ dependency nào tới `returns.csv`.

## Phase 2 - Clean, Label & Lock Temporal Cutoffs

### 2.1. Chuẩn hóa

- Parse `order_date` và `signup_date`.
- Aggregate duplicate item key, bảo toàn quantity, discount và gross value.
- Loại `promo_id`, `promo_id_2`.

### 2.2. Tạo label

- Map trực tiếp `orders.order_status`.
- Kiểm tra target binary và `order_id` duy nhất.
- Kiểm tra labeled orders có payment.

### 2.3. Khóa outer holdout

- Sắp xếp theo `order_date`, sau đó `order_id`.
- Khóa cutoff 70/15/15:
  - Outer train: 70% đầu.
  - Outer validation: 15% tiếp theo.
  - Test: 15% cuối.
- `data_split` chỉ là internal holdout mask cho tới Phase 6.
- Outer validation và test không được dùng trong feature selection.

## Phase 3 - Candidate Feature Engineering

### 3.1. Point-in-time-safe candidates

- Customer: tenure, tenure group, age group, gender.
- Product/order item: quantity, product count, discount, category, segment, size, color.
- Payment/order: payment method, device, source, COD, value, log value và quantile bucket candidate.
- Calendar: month, quarter, weekday, weekend, Q4.

### 3.2. Research-only target-history candidates

Vẫn tạo để pipeline chứng minh leakage gate hoạt động:

- `mean_product_return_rate`
- `max_product_return_rate`
- `high_risk_product_count`

Ba feature này dùng historical `returned_label`, nhưng dữ liệu không có timestamp chứng minh outcome đã được quan sát tại thời điểm order mới được đặt. Vì vậy chúng chỉ là candidate nghiên cứu và phải bị ban ở Phase 4.

### 3.3. Candidate table

- `phase3_features` chứa toàn bộ candidate, target và metadata.
- Đây chưa phải bảng Modeling an toàn.
- Mỗi order vẫn chỉ có một dòng.

## Phase 4 - Leakage Gate, Screening & Selection

### 4.1. Availability catalog và leakage gate

Mỗi cột được ghi:

- Role.
- Source group.
- Formula/origin.
- Có sử dụng target không.
- Có sẵn tại thời điểm đặt hàng không.
- Action và reason.

Actions:

- `EXCLUDE_ID`
- `EXCLUDE_METADATA`
- `EXCLUDE_TARGET`
- `EXCLUDE_REPRESENTATION`
- `BAN_LEAKAGE`
- `PASS_LEAKAGE_GATE`

Ba target-history feature nhận:

```text
action = BAN_LEAKAGE
reason = Historical target outcome availability is not guaranteed at order time
```

Feature bị ban vẫn có trong audit nhưng không được tham gia bất kỳ bước selection tiếp theo.

`payment_value_quantile_bucket` nhận `EXCLUDE_REPRESENTATION`: bucket vẫn có trong
candidate audit, nhưng không đi vào Modeling vì edges đã được học trước inner CV.
Modeling giữ `payment_value` và `log_payment_value`, rồi fit preprocessing lại trong
từng fold. Representation quantile vẫn được tạo bằng `KBinsDiscretizer` từ raw
`payment_value` bên trong pipeline, nên edges của bốn bin chỉ học từ train của fold.

### 4.2. Quality filter

Chỉ chạy trên leakage-safe features và outer train:

- Drop constant.
- Drop missing rate trên 60%.
- Drop infinite numeric values.
- Drop exact duplicate columns.
- Ghi dtype, missing, cardinality và duplicate owner.

### 4.3. Relevance ranking

Chỉ dùng outer train:

- Numeric: point-biserial correlation.
- Categorical: Chi-square và bias-corrected Cramér’s V.
- Relevance chỉ dùng ranking và giải thích, không hard-drop feature yếu.

### 4.4. Redundancy

- Numeric absolute Pearson correlation trên outer train.
- Hard-drop khi `|corr| > 0.98`.
- Khi phải chọn, giữ representation có univariate effect size lớn hơn.
- Các family như COD/payment method, raw/log value và tenure numeric/group chỉ được ghi audit; không tự động loại bằng rule thủ công.

### 4.5. Dual-model wrapper

- Chỉ dùng outer train.
- Tạo ba expanding inner temporal folds.
- Baseline: `is_cod`.
- Thử từng candidate bằng `is_cod + candidate`.
- Model:
  - Balanced Logistic Regression.
  - LightGBM với `scale_pos_weight` tính riêng từng fold.
- Preprocessing nằm trong pipeline và fit lại ở từng fold.
- Metric chính: PR-AUC.
- ROC-AUC là metric phụ.

Chỉ hard-drop feature khi cả hai model đồng thuận:

```text
mean delta PR-AUC <= -0.001
negative PR-AUC folds == 3
```

### 4.6. Chốt feature set

- `core`: point-in-time safe và có bằng chứng wrapper dương ổn định.
- `v1`: safe, qua quality/redundancy và không bị hai model đồng thuận loại.
- `experimental`: safe nhưng thuộc interaction, color hoặc calendar chưa ổn định.
- Banned feature không được xuất hiện trong bất kỳ feature set nào.

Selection funnel:

```text
CANDIDATE
→ BAN_LEAKAGE
→ EXCLUDE_REPRESENTATION
→ DROP_QUALITY
→ DROP_REDUNDANT
→ DROP_CONSISTENT_HARM
→ CORE / V1 / EXPERIMENTAL
```

## Phase 5 - Format & Preprocessing

### 5.1. Modeling schema

Chỉ giữ:

- `order_id`
- `order_date`
- `data_split`
- `returned_label`
- Feature V1 đã pass leakage gate

Pipeline dừng nếu banned feature xuất hiện trong bảng này.

### 5.2. Outer preprocessing artifact

- Numeric: median → StandardScaler.
- Categorical: most frequent → OneHotEncoder, unknown ignored.
- Binary/multi-hot: most frequent → passthrough.
- `payment_value`: đồng thời tạo bốn quantile bins bằng `KBinsDiscretizer`; edges
  được fit từ train của pipeline.
- Fit bằng internal outer-train mask.
- Transform outer validation và test.
- Lưu policy, fitted preprocessor và transformed feature names.

Artifact này phục vụ audit/final transform. Modeling vẫn phải fit lại cùng policy trong từng temporal CV fold.

## Phase 6 - Materialize Splits

Chính thức xuất:

- `train_features_raw.csv`
- `valid_features_raw.csv`
- `test_features_raw.csv`
- `X_*_preprocessed.npz`
- `y_*.npy`

Audit:

- Row count và unique order.
- Date range và return rate.
- Không overlap.
- Train trước validation, validation trước test.
- Raw schema và transformed column count giống nhau.

## Phase 7 - Readiness & Report

Pipeline chỉ pass khi:

- Grain và target hợp lệ.
- `returns.csv` không được load.
- Ba target-history candidate có decision `BAN_LEAKAGE`.
- Banned feature không có trong feature list hoặc raw split.
- Selection chỉ dùng outer train.
- Wrapper có đủ Logistic và LightGBM.
- Split integrity pass.
- Item aggregation bảo toàn dữ liệu.
- Preprocessing tạo schema nhất quán.

Output chính:

- `phase4_feature_availability_catalog.csv`
- `phase4_leakage_gate.csv`
- `phase4_quality_filter.csv`
- `phase4_relevance_report.csv`
- `phase4_redundancy_pairs.csv`
- `phase4_wrapper_logistic.csv`
- `phase4_wrapper_lightgbm.csv`
- `phase4_wrapper_consensus.csv`
- `phase4_feature_selection_report.csv`
- `feature_cols_core.csv`
- `feature_cols_v1.csv`
- `feature_cols_experimental.csv`
- `phase5_preprocessing_policy.csv`
- `phase6_split_audit.csv`
- `fe_readiness_checklist.csv`
- `FE_final_report.md`
