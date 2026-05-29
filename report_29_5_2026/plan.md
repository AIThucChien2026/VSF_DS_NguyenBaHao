# Kế hoạch Data Preparation cần làm cho Daily Revenue/COGS Forecasting

> Mục tiêu: viết notebook Data Preparation theo CRISP-DM, dùng kết quả EDA ngày 28/5 làm tiền đề và chỉ làm các bước thật sự cần để tạo dữ liệu model-ready cho bài toán dự báo `Revenue` và `COGS` theo ngày.

---

## 0. Scope & reuse EDA findings

### Mục tiêu

Notebook này **không làm lại EDA**. Các phân tích đã có trong `report_28_5_2026/EDA.ipynb` và `report_28_5_2026/plan.md` được xem là đầu vào:

- Schema overview, semantic type, date coverage.
- Missing overview, duplicate overview, outlier overview.
- Revenue/profit analysis theo product, category, channel, discount, return.
- Relationship/correlation và feature candidates cho forecasting.
- Các cảnh báo leakage liên quan same-period realized features.

Notebook Data Preparation chỉ làm các việc còn thiếu để chuyển dữ liệu sang dạng modeling:

- Select dữ liệu liên quan đến daily forecasting.
- Clean dữ liệu với log quyết định.
- Construct bảng ngày đúng grain.
- Integrate feature sources bằng join an toàn.
- Tạo lag/rolling features không leakage.
- Format feature/target.
- Split theo thời gian.
- Export dữ liệu và report.

### Input tham chiếu

| Tài liệu | Vai trò |
|---|---|
| `report_28_5_2026/EDA.ipynb` | EDA đã thực hiện, dùng để tránh làm lại phân tích khám phá |
| `report_28_5_2026/plan.md` | Tóm tắt mục tiêu EDA, quan hệ bảng, insight và feature candidates |
| `report_29_5_2026/Chapter 4. Data Preparation.txt` | Khung CRISP-DM Data Preparation |

### Nguyên tắc

| Nguyên tắc | Cách thực hiện |
|---|---|
| Không làm lại EDA | Chỉ kiểm tra kỹ thuật tối thiểu phục vụ cleaning/join/model-ready |
| Không sửa dữ liệu gốc | Lưu raw vào `raw_tables`, xử lý trên `clean_tables` |
| Mặc định grain ngày | Base là `daily_level_base` từ `sales.Date` |
| Không dùng `sample_submission` để train | Chỉ dùng `sample_submission.Date` làm horizon/template |
| Không dùng future information | Feature phải có timestamp tại hoặc trước prediction date |
| Không join 1-n trực tiếp | Aggregate về daily grain trước khi join |
| Mọi fill/drop/replace phải có log | Ghi vào `cleaning_decision_log` và report cuối |

---

# 01. Setup/load data

## Mục tiêu

Load 14 CSV, giữ raw data, chuẩn hóa tối thiểu tên bảng/cột và kiểm tra file/cột bắt buộc. Không vẽ lại biểu đồ inventory như EDA.

## Bảng dùng

Toàn bộ 14 bảng:

```python
EXPECTED_FILES = {
    "orders": "orders.csv",
    "order_items": "order_items.csv",
    "customers": "customers.csv",
    "products": "products.csv",
    "payments": "payments.csv",
    "shipments": "shipments.csv",
    "returns": "returns.csv",
    "reviews": "reviews.csv",
    "promotions": "promotions.csv",
    "inventory": "inventory.csv",
    "web_traffic": "web_traffic.csv",
    "sales": "sales.csv",
    "geography": "geography.csv",
    "sample_submission": "sample_submission.csv",
}
```

## Code cần viết

1. Import thư viện chính: `pandas`, `numpy`, `Path`, `display`.
2. Tạo `DATA_DIR`, `OUTPUT_DIR`.
3. Load các file có trong `EXPECTED_FILES` vào `raw_tables`.
4. Tạo `tables = {name: df.copy() for name, df in raw_tables.items()}`.
5. Chuẩn hóa tên cột tối thiểu: strip whitespace; chỉ lowercase nếu không làm mất tương thích với `Date`, `Revenue`, `COGS` thì cần mapping rõ.
6. Parse date columns bắt buộc:
   - `sales.Date`
   - `sample_submission.Date`
   - `web_traffic.date`
   - `orders.order_date`
   - `returns.return_date`
   - `reviews.review_date`
   - `shipments.ship_date`, `shipments.delivery_date`
   - `inventory.snapshot_date`
7. Tạo warning nếu thiếu file/cột, nhưng notebook không crash vì cột phụ.

## Output cần hiển thị

### `load_status_report`

| table_name | file_name | status | rows | columns | missing_required_columns | warning |
|---|---|---|---:|---:|---|---|

### `date_parse_report`

| table_name | date_column | parse_success_pct | min_date | max_date | invalid_count |
|---|---|---:|---|---|---:|

## Output biến

```python
raw_tables
tables
load_status_report
date_parse_report
```

---

# 02. Data selection for modeling

## Mục tiêu

Chọn dữ liệu phục vụ daily forecasting và loại các bảng/cột chỉ thuộc EDA hoặc có leakage mặc định.

## Base modeling grain

| Thành phần | Giá trị mặc định |
|---|---|
| Grain | 1 dòng = 1 ngày |
| Base table | `sales` |
| Date key | `Date` |
| Target candidates | `Revenue`, `COGS` |
| Forecast horizon/template | `sample_submission.Date` |

## Table usage mặc định

| Bảng | Vai trò trong Data Preparation | Trạng thái |
|---|---|---|
| `sales` | Base target table theo ngày | use |
| `sample_submission` | Horizon/template ngày cần dự báo | template_only |
| `web_traffic` | Daily/source traffic, tạo lag/rolling features | use_with_lag |
| `orders` | Aggregate order count/AOV/status/source theo ngày | use_aggregate_daily |
| `order_items` | Aggregate quantity, gross revenue, discount theo ngày | use_aggregate_daily |
| `products` | Bổ sung category/cogs cho item aggregate nếu cần | use_before_aggregate |
| `returns` | Refund/return daily; mặc định chỉ dùng lag/rolling | use_with_lag_or_exclude |
| `shipments` | Fulfillment metrics; mặc định leakage risk | conditional |
| `reviews` | Rating/review sau mua; mặc định leakage risk | conditional |
| `inventory` | Snapshot tồn kho; chỉ dùng snapshot <= prediction date | conditional |
| `customers`, `payments`, `promotions`, `geography` | Không ưu tiên trong v1 daily forecast, chỉ dùng nếu tạo aggregate rõ ràng | optional |

## Code cần viết

1. Tạo `table_usage_plan`.
2. Tạo `modeling_scope_config`.
3. Đánh dấu bảng/cột theo `use`, `optional`, `exclude`, `template_only`.
4. Ghi lý do loại các bảng không dùng ở v1 để tránh mở rộng quá mức.

## Output cần hiển thị

### `table_usage_plan`

| table_name | default_status | allowed_use | leakage_risk | reason |
|---|---|---|---|---|

### `modeling_scope_config`

| config_name | value | note |
|---|---|---|

---

# 03. Minimal validation before cleaning

## Mục tiêu

Chỉ kiểm tra kỹ thuật cần thiết trước khi cleaning/join. Không làm lại full EDA quality audit.

## Validation bắt buộc

| Nhóm kiểm tra | Mục đích |
|---|---|
| Required columns | Đảm bảo đủ cột để dựng daily base và target |
| Key uniqueness | Đảm bảo `sales.Date` và `sample_submission.Date` đúng grain ngày |
| Join keys | Đảm bảo `order_items.order_id`, `orders.order_id`, `products.product_id` tồn tại trước aggregate |
| Numeric sanity | Đảm bảo các cột target/feature số convert được |
| Date sanity | Đảm bảo feature có timestamp để audit leakage |

## Code cần viết

1. Kiểm tra `sales` có `Date`, `Revenue`, `COGS`.
2. Kiểm tra `sample_submission` có `Date`.
3. Kiểm tra duplicate `Date` trong `sales` và `sample_submission`.
4. Kiểm tra cột join tối thiểu:
   - `orders.order_id`, `orders.order_date`
   - `order_items.order_id`, `order_items.product_id`
   - `products.product_id`, `products.cogs` nếu tính cost/profit
   - `web_traffic.date`
5. Convert numeric cần thiết bằng `pd.to_numeric(errors="coerce")` và ghi invalid count.
6. Tạo `validation_status` theo `pass`, `warning`, `fail`.

## Output cần hiển thị

### `minimal_validation_report`

| check_name | table_name | checked_column | status | issue_count | action |
|---|---|---|---|---:|---|

### `blocking_issue_report`

| issue | severity | affected_step | suggested_fix |
|---|---|---|---|

---

# 04. Cleaning rules and decision log

## Mục tiêu

Tạo `clean_tables` và log mọi thay đổi. Cleaning ở đây phục vụ modeling, không nhằm khám phá insight.

## Strategy mặc định

| Vấn đề | Strategy |
|---|---|
| Date parse invalid ở cột bắt buộc | Giữ raw, set parsed value `NaT`, ghi warning; dòng thiếu target date bị loại khỏi training base |
| `sales.Revenue`, `sales.COGS` missing trong train period | Không tự fill target; loại khỏi training rows hoặc đánh dấu không train |
| Numeric feature missing sau aggregate | Fill 0 nếu missing nghĩa là không có event; nếu không chắc, để pending và tạo flag |
| Duplicate ngày trong `sales` | Aggregate theo ngày nếu cùng ngày có nhiều row; ghi log |
| Duplicate row exact trong source | Drop exact duplicate nếu an toàn; ghi log |
| Negative values ở money/count | Không sửa âm thầm; flag vào invalid report |
| `sample_submission.Revenue`, `sample_submission.COGS` blank | Hợp lệ, không fill, không dùng train |

## Code cần viết

1. Tạo `clean_tables` từ `tables`.
2. Tạo helper `log_cleaning_action(table, column, action, rows_affected, reason)`.
3. Apply cleaning tối thiểu cho các bảng dùng trong v1:
   - `sales`
   - `sample_submission`
   - `web_traffic`
   - `orders`
   - `order_items`
   - `products`
   - `returns`
   - `inventory`
4. Chuẩn hóa date key về ngày, không giữ timestamp giờ nếu grain là ngày.
5. Chuẩn hóa numeric columns cần aggregate.
6. Không drop/fill bảng optional nếu không dùng.

## Output cần hiển thị

### `cleaning_decision_log`

| table_name | column_name | action | rows_affected | reason |
|---|---|---|---:|---|

### `cleaning_impact_summary`

| table_name | rows_before | rows_after | columns_before | columns_after | missing_target_before | missing_target_after |
|---|---:|---:|---:|---:|---:|---:|

### `invalid_value_report`

| table_name | column_name | issue | count | default_action |
|---|---|---|---:|---|

---

# 05. Construct daily modeling table

## Mục tiêu

Tạo bảng nền `daily_level_base` ở đúng grain ngày từ `sales`, sau đó tạo các bảng feature daily đã aggregate trước khi join.

## 05A. `daily_level_base`

### Input

- `clean_tables["sales"]`

### Code cần viết

1. Chuẩn hóa `Date` về ngày.
2. Nếu `sales` có nhiều row/ngày, aggregate:
   - `Revenue = sum`
   - `COGS = sum`
3. Tạo calendar features không leakage:
   - `day_of_week`
   - `month`
   - `quarter`
   - `year`
   - `is_weekend`
4. Kiểm tra sau aggregate còn 1 row/ngày.

### Output

```python
daily_level_base
```

## 05B. Daily feature tables

### `traffic_daily_features`

Nguồn: `web_traffic`

Aggregate theo `date`:

| Feature | Logic |
|---|---|
| `sessions_sum` | sum sessions theo ngày |
| `unique_visitors_sum` | sum unique visitors theo ngày |
| `page_views_sum` | sum page views theo ngày |
| `avg_bounce_rate` | weighted/mean nếu có |
| `traffic_source_count` | số source trong ngày |

### `orders_daily_features`

Nguồn: `orders`

Aggregate theo `order_date`:

| Feature | Logic |
|---|---|
| `daily_order_count` | nunique order_id |
| `daily_customer_count` | nunique customer_id nếu có |
| `order_source_count` | nunique order_source nếu có |
| `cancelled_order_count` | count status cancelled nếu có |
| `delivered_order_count` | count status delivered nếu có |

### `items_daily_features`

Nguồn: `order_items` + `orders` + optional `products`

Aggregate theo `order_date`:

| Feature | Logic |
|---|---|
| `daily_total_quantity` | sum quantity |
| `daily_gross_item_revenue` | sum quantity * unit_price |
| `daily_discount_amount` | sum discount_amount |
| `daily_distinct_products` | nunique product_id |
| `daily_estimated_cogs` | sum quantity * products.cogs nếu đủ cột |

### `returns_daily_features`

Nguồn: `returns`

Aggregate theo `return_date`, nhưng **không dùng same-day return làm feature cho cùng ngày sales**. Chỉ dùng lag/rolling ở bước sau.

| Feature | Logic |
|---|---|
| `daily_return_count` | count return records |
| `daily_refund_amount` | sum refund_amount |
| `daily_return_quantity` | sum return_quantity |

### `inventory_daily_features`

Nguồn: `inventory`

Aggregate theo `snapshot_date`; chỉ dùng nếu snapshot date <= prediction date.

| Feature | Logic |
|---|---|
| `daily_stock_on_hand_sum` | sum stock_on_hand |
| `daily_inventory_product_count` | nunique product_id |

## Output cần hiển thị

### `daily_table_build_report`

| output_table | source_tables | date_key | rows | unique_dates | duplicate_dates | status |
|---|---|---|---:|---:|---:|---|

### `aggregation_plan`

| source_table | output_table | source_grain | output_grain | aggregation_logic | leakage_note |
|---|---|---|---|---|---|

---

# 06. Leakage-safe feature engineering

## Mục tiêu

Tạo feature chỉ dùng dữ liệu có sẵn trước thời điểm dự báo. Với daily forecasting, mọi realized signal cùng ngày hoặc sau ngày target phải được lag trước khi dùng.

## Rule leakage mặc định

| Feature source | Rule |
|---|---|
| `sales.Revenue`, `sales.COGS` | Chỉ dùng lag/rolling quá khứ, không dùng same-day target |
| `web_traffic` | Mặc định lag 1 ngày trước khi dùng nếu traffic cùng ngày chưa biết tại prediction time |
| `orders/order_items` | Mặc định lag 1 ngày nếu dự báo đầu ngày; có thể same-day nếu bài toán dự báo cuối ngày |
| `returns` | Luôn lag/rolling, không dùng same-day return cho target cùng ngày |
| `reviews` | Mặc định exclude khỏi v1 vì là post-purchase signal |
| `shipments` | Mặc định exclude khỏi v1 nếu không có cutoff rõ |
| `inventory` | Dùng snapshot gần nhất <= prediction date; không forward từ tương lai |

## Feature cần tạo

### Target lags

| Feature | Logic |
|---|---|
| `revenue_lag_1d` | `Revenue.shift(1)` |
| `revenue_lag_7d` | `Revenue.shift(7)` |
| `revenue_rolling_7d` | rolling mean/sum trên dữ liệu đã shift 1 |
| `revenue_rolling_28d` | rolling mean/sum trên dữ liệu đã shift 1 |
| `cogs_lag_1d` | `COGS.shift(1)` |
| `cogs_lag_7d` | `COGS.shift(7)` |
| `cogs_rolling_7d` | rolling trên `COGS.shift(1)` |
| `cogs_rolling_28d` | rolling trên `COGS.shift(1)` |

### External/source lags

Với các feature từ traffic, orders, items, returns, inventory:

- Tạo `*_lag_1d`.
- Tạo `*_lag_7d` cho numeric quan trọng.
- Tạo `*_rolling_7d` và `*_rolling_28d` trên series đã shift 1.
- Không giữ same-day feature trong `X` trừ khi config `ALLOW_SAME_DAY_FEATURES = True`.

## Code cần viết

1. Join các daily feature tables vào `daily_level_base` theo date.
2. Trước khi đưa vào `X`, tạo lag/rolling features.
3. Drop hoặc exclude same-day realized features theo config mặc định.
4. Tạo `leakage_audit_table`.
5. Tạo `feature_candidate_catalog` chỉ cho feature thật sự tạo trong notebook, không làm catalog EDA rộng.

## Output cần hiển thị

### `daily_model_base`

Một dòng/ngày, gồm target, calendar features, lag/rolling features.

### `leakage_audit_table`

| feature_name | source_table | source_date_column | prediction_date_column | leakage_risk | default_action | reason |
|---|---|---|---|---|---|---|

### `feature_candidate_catalog`

| feature_name | source_tables | feature_type | included_by_default | transform | reason |
|---|---|---|---|---|---|

### `join_quality_report`

| join_step | rows_before | rows_after | duplicate_date_after_join | unmatched_left_count | status |
|---|---:|---:|---:|---:|---|

---

# 07. Final missing/formatting

## Mục tiêu

Chuẩn hóa bảng model-ready, tách target/features, xử lý missing cuối và loại cột không được đưa vào model.

## Strategy mặc định

| Nhóm cột | Strategy |
|---|---|
| Target `Revenue`, `COGS` | Không fill; rows thiếu target không dùng train |
| Calendar features | Không missing; nếu missing thì fail validation |
| Lag/rolling target | Missing đầu chuỗi do lag hợp lệ; loại khỏi train hoặc giữ sau khi đủ lookback |
| Event count features | Fill 0 nếu ngày không có event |
| Money/count rolling features | Fill 0 hoặc median theo config; mặc định 0 nếu nguồn là absence-of-event |
| Raw date | Giữ làm key, không đưa vào `X` |
| Raw ID | Không đưa vào `X` |
| Same-day realized features | Exclude khỏi `X` mặc định |

## Code cần viết

1. Tạo `TARGET_COLUMNS = ["Revenue", "COGS"]`.
2. Tạo `id_columns = ["Date"]`.
3. Tạo danh sách `excluded_features`.
4. Tạo `numeric_features`, `categorical_features`, `boolean_features`.
5. Impute feature missing theo rule, không impute target.
6. Tạo `final_feature_schema`.
7. Tạo `feature_table_daily`.

## Output cần hiển thị

### `final_imputation_report`

| feature_name | missing_before | missing_after | imputation_method | reason |
|---|---:|---:|---|---|

### `final_feature_schema`

| feature_name | dtype | feature_group | transform | included_in_X | reason |
|---|---|---|---|---|---|

### `target_definition_table`

| target_column | source_table | grain | problem_type | missing_count | status |
|---|---|---|---|---:|---|

## Output biến

```python
feature_table_daily
final_feature_schema
target_definition_table
```

---

# 08. Time-based split

## Mục tiêu

Chia train/valid/test theo thời gian để tránh leakage. Không dùng random split mặc định.

## Split mặc định

Nếu không có yêu cầu khác:

| Split | Logic |
|---|---|
| Train | 70% ngày đầu |
| Valid | 15% ngày tiếp theo |
| Test | 15% ngày cuối |

Hoặc nếu `sample_submission.Date` nằm sau `sales.Date`, dùng toàn bộ `sales` có target để train/valid/test và tạo thêm `forecast_horizon_table` từ `sample_submission`.

## Code cần viết

1. Sort theo `Date`.
2. Loại rows không đủ lookback do lag/rolling trước khi split.
3. Loại rows thiếu target khỏi train/valid/test.
4. Split theo thời gian.
5. Tách:
   - `X_train`, `X_valid`, `X_test`
   - `y_train_revenue`, `y_valid_revenue`, `y_test_revenue`
   - `y_train_cogs`, `y_valid_cogs`, `y_test_cogs`
6. Tạo `forecast_horizon_table` từ `sample_submission.Date` nếu có.

## Output cần hiển thị

### `split_summary`

| split | rows | pct | date_min | date_max | revenue_mean | cogs_mean | target_missing |
|---|---:|---:|---|---|---:|---:|---:|

### `forecast_horizon_summary`

| rows | date_min | date_max | overlaps_training_dates | note |
|---:|---|---|---:|---|

---

# 09. Export model-ready files

## Mục tiêu

Xuất đủ dữ liệu cho bước modeling và report để kiểm tra lại.

## File cần xuất

| File | Nội dung |
|---|---|
| `clean_tables/*.csv` | Các bảng đã clean dùng trong pipeline |
| `daily_model_base.csv` | Bảng daily đầy đủ gồm target và features |
| `feature_table_daily.csv` | Feature table trước khi tách split |
| `X_train.csv` | Feature train |
| `X_valid.csv` | Feature validation |
| `X_test.csv` | Feature test |
| `y_train_revenue.csv` | Target Revenue train |
| `y_valid_revenue.csv` | Target Revenue validation |
| `y_test_revenue.csv` | Target Revenue test |
| `y_train_cogs.csv` | Target COGS train |
| `y_valid_cogs.csv` | Target COGS validation |
| `y_test_cogs.csv` | Target COGS test |
| `forecast_horizon_table.csv` | Ngày cần dự báo từ sample submission |
| `final_feature_schema.csv` | Schema cuối |
| `data_preparation_report.xlsx` | Report tổng hợp |

## Output cần hiển thị

### `export_manifest`

| file_name | file_type | rows | columns | purpose | path |
|---|---|---:|---:|---|---|

---

# 10. Final data preparation report

## Mục tiêu

Tổng kết notebook đã chuẩn bị dữ liệu đến đâu và còn giới hạn gì trước modeling.

## Report cần có

| Nhóm | Nội dung |
|---|---|
| Scope | Ghi rõ đã reuse EDA, không làm lại EDA |
| Load status | File/cột thiếu nếu có |
| Selection | Bảng nào dùng, bảng nào loại |
| Cleaning | Log drop/fill/replace |
| Validation | Blocking/warning issues |
| Aggregation | Bảng nào aggregate về daily grain |
| Join | Row count trước/sau join |
| Leakage | Feature nào lag, feature nào exclude |
| Feature schema | Feature cuối trong `X` |
| Target | `Revenue`, `COGS` |
| Split | Train/valid/test theo thời gian |
| Export | Danh sách file xuất |
| Limitations | Các điểm cần review trước modeling |

## Output cần hiển thị

### `final_preparation_checklist`

| checklist_item | status | evidence_table | note |
|---|---|---|---|
| raw data loaded | pass/fail | `load_status_report` |  |
| required columns checked | pass/fail | `minimal_validation_report` |  |
| cleaning logged | pass/fail | `cleaning_decision_log` |  |
| daily grain valid | pass/fail | `daily_table_build_report` |  |
| joins validated | pass/fail | `join_quality_report` |  |
| leakage checked | pass/fail | `leakage_audit_table` |  |
| final schema created | pass/fail | `final_feature_schema` |  |
| time split created | pass/fail | `split_summary` |  |
| outputs exported | pass/fail | `export_manifest` |  |

## Kết luận cuối notebook phải in

```text
Final daily forecasting dataset:
- grain:
- rows:
- date range:
- targets:
- numeric_features:
- categorical_features:
- boolean_features:
- excluded_same_day_features:
- missing_remaining_in_X:
- train/valid/test:
- forecast_horizon:
- ready_for_modeling: yes/no
- limitations:
```

---

# Tóm tắt flow notebook

```text
00 Scope & reuse EDA findings
01 Setup/load data
02 Data selection for modeling
03 Minimal validation before cleaning
04 Cleaning rules and decision log
05 Construct daily modeling table
06 Leakage-safe feature engineering
07 Final missing/formatting
08 Time-based split
09 Export model-ready files
10 Final data preparation report
```

---

# Ghi chú cho AI coder

1. Không viết lại schema/missing/outlier/revenue insight đã có trong EDA.
2. Mỗi section phải có markdown title rõ ràng và code cell riêng.
3. Mọi xử lý làm thay đổi dữ liệu phải ghi vào `cleaning_decision_log`.
4. Mọi join phải có `join_quality_report`.
5. Mọi feature theo thời gian phải đi qua `leakage_audit_table`.
6. Không dùng `sample_submission` làm training data.
7. Không dùng same-day realized features trong `X` trừ khi config cho phép.
8. Không đưa raw `Date`, raw ID hoặc target vào `X`.
9. Split mặc định theo thời gian, không random.
10. Cuối notebook phải export file và report đầy đủ.

---

# Kết luận

Bản kế hoạch này là blueprint gọn cho notebook Data Preparation sau EDA. Nó chỉ làm các phần cần thiết để biến dữ liệu ecommerce đã hiểu qua EDA thành dataset daily model-ready cho dự báo `Revenue` và `COGS`, có kiểm soát cleaning, aggregation, join, leakage, split và export.
