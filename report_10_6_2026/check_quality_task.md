# Kiểm Tra Chất Lượng Dữ Liệu - Kế Hoạch Check Quality

## Mục tiêu

Kiểm tra chất lượng dữ liệu trước khi làm EDA, clean data, feature engineering và modeling cho bài toán dự đoán đơn hàng có bị trả lại hay không.

Notebook này không train model, không tuning và không sửa dữ liệu gốc. Mục tiêu là tạo bảng/biểu đồ kiểm tra để biết dữ liệu có vấn đề gì trước khi đi tiếp.

Nhãn bài toán hiện tại:
- **Returned = 1**: chỉ khi `order_status == returned` và `order_id` có record trong `returns.csv`.
- **Delivered = 0**: chỉ khi `order_status == delivered` và không có record trong `returns.csv`.
- **Không gắn nhãn / NaN**: các trạng thái `created`, `paid`, `shipped`, `cancelled`, hoặc các conflict lifecycle như `returned` nhưng thiếu record trong `returns`.

## Nguyên tắc trình bày notebook

- Mỗi cell chỉ làm một việc rõ ràng.
- Comment đầu cell chỉ ghi mục đích cell, không dùng dạng `Phase X - Cell Y`.
- Mỗi phase có mục tiêu và kết luận riêng.
- Nếu phase có bảng khó đọc bằng mắt, thêm biểu đồ đơn giản.
- Tên biến, file CSV và chart phải khớp số phase hiện tại.
- Không xóa dòng dữ liệu chỉ để tạo nhãn; các dòng chưa đủ điều kiện binary được giữ lại với `returned_label = NaN`.

## Quy trình hiện tại

- **Phase 0**: Setup thư viện, đường dẫn, bảng và key cần kiểm tra.
- **Phase 1**: Load dữ liệu thô.
- **Phase 2**: Kiểm tra cấu trúc dữ liệu đầu vào gồm file, cột, shape và dtype.
- **Phase 3**: Kiểm tra missing value và vẽ missing rate.
- **Phase 4**: Kiểm tra duplicate, key cơ bản và vẽ duplicate key.
- **Phase 5**: Kiểm tra giá trị bất thường, outlier đơn giản và category.
- **Phase 6**: Kiểm tra datetime có hợp lệ không.
- **Phase 7**: Kiểm tra quan hệ giữa các bảng.
- **Phase 8**: Kiểm tra lifecycle / chu trình đơn hàng trước khi gắn nhãn.
- **Phase 9**: Tạo nhãn Returned/Delivered và kiểm tra cân bằng lớp.
- **Phase 10**: Kiểm tra leakage risk.
- **Phase 11**: Tổng hợp issue và action plan.
- **Phase 12**: Kết luận quality check.

## Input

- `Data/orders.csv`
- `Data/order_items.csv`
- `Data/customers.csv`
- `Data/products.csv`
- `Data/returns.csv`
- `Data/payments.csv`

## Output chính

- `phase1_loaded_tables_summary.csv`
- `phase2_input_structure_check.csv`
- `phase3_missing_value_summary.csv`
- `phase4_duplicate_summary.csv`
- `phase4_key_check.csv`
- `phase4_duplicate_key_summary.csv`
- `phase5_numeric_value_check.csv`
- `phase5_category_value_check.csv`
- `phase6_date_parse_check.csv`
- `phase6_date_logic_check.csv`
- `phase7_foreign_key_check.csv`
- `phase7_order_coverage_check.csv`
- `phase8_order_status_distribution.csv`
- `phase8_lifecycle_check_summary.csv`
- `phase8_lifecycle_conflict_details.csv`
- `phase9_label_distribution.csv`
- `phase9_label_exclusion_summary.csv`
- `phase9_order_label_preview.csv`
- `phase10_leakage_risk_table.csv`
- `phase11_quality_issue_log.csv`
- `phase11_quality_action_plan.csv`
- `phase12_quality_check_summary.csv`
- `phase12_quality_check_conclusion.csv`

## Biểu đồ chính

- `phase3_missing_rate_by_column.png`
- `phase4_duplicate_key_count_by_table.png`
- `phase5_zero_count_by_column.png`
- `phase5_numeric_min_max_range.png`
- `phase5_category_unique_values.png`
- `phase8_order_status_distribution.png`
- `phase8_lifecycle_consistency.png`
- `phase9_label_distribution.png`
- `phase11_issue_count_by_severity.png`

---

## Phase 0 - Setup

### Mục tiêu

Chuẩn bị thư viện, đường dẫn input/output, thư mục lưu bảng/hình và danh sách bảng cần kiểm tra.

### Việc cần làm

- Import `pandas`, `numpy`, `matplotlib`, `seaborn`.
- Tạo `TABLE_DIR` và `FIGURE_DIR`.
- Khai báo `table_files`.
- Khai báo `expected_columns`.
- Khai báo `primary_key_checks`.

### Kết luận mong đợi

Sau phase này, notebook có đủ cấu hình để mọi phase sau dùng chung cùng một chuẩn đường dẫn, cùng một danh sách bảng và cùng một định nghĩa key.

---

## Phase 1 - Load dữ liệu thô

### Mục tiêu

Đọc toàn bộ file CSV đầu vào và xác nhận bảng nào load được, bảng nào thiếu hoặc lỗi.

### Việc cần làm

- Load `orders`, `order_items`, `customers`, `products`, `returns`, `payments`.
- Ghi nhận shape của từng bảng.
- Xuất `phase1_loaded_tables_summary.csv`.
- Hiển thị preview từng bảng để kiểm tra nhanh cấu trúc thực tế.

### Kết luận theo kết quả chạy

- 6 bảng đều load được.
- Bảng lớn nhất là `order_items` với 714,669 dòng.
- `orders` và `payments` đều có 646,945 dòng.
- `returns` có 39,939 dòng return-level, tương ứng 36,062 order hoàn/trả duy nhất.

---

## Phase 2 - Kiểm tra cấu trúc dữ liệu đầu vào

### Mục tiêu

Đảm bảo file có đầy đủ cột cần thiết, số dòng/cột hợp lý và dtype sơ bộ không lệch quá xa kỳ vọng.

### Việc cần làm

- Kiểm tra từng file có tồn tại không.
- Kiểm tra từng cột bắt buộc có tồn tại không.
- Ghi nhận dtype thực tế.
- Phân nhóm dtype kỳ vọng: `id`, `date`, `numeric`, `category`.
- Xuất `phase2_input_structure_check.csv`.

### Kết luận theo kết quả chạy

- Tất cả bảng đều có đủ cột cần thiết.
- Không phát hiện thiếu schema ở bước đầu vào.
- Có thể chuyển sang kiểm tra missing, duplicate và logic nghiệp vụ sâu hơn.

---

## Phase 3 - Kiểm tra missing value

### Mục tiêu

Xác định cột nào thiếu dữ liệu, mức độ thiếu nhiều hay ít, và missing đó có phải lỗi dữ liệu hay là missing có ý nghĩa nghiệp vụ.

### Việc cần làm

- Tính `missing_count` và `missing_rate` cho từng cột.
- Phân mức missing: `none`, `low`, `medium`, `high`.
- Xuất `phase3_missing_value_summary.csv`.
- Vẽ `phase3_missing_rate_by_column.png`.

### Kết luận theo kết quả chạy

- Phần lớn cột quan trọng không bị missing.
- `order_items.promo_id` thiếu khoảng 61.34%, có thể hiểu là đơn không dùng khuyến mãi.
- `order_items.promo_id_2` thiếu gần như toàn bộ, cần cân nhắc loại bỏ hoặc chỉ dùng khi có giải thích nghiệp vụ rõ.

**Ý nghĩa DS:** Missing ở `promo_id` không nhất thiết là lỗi. Đây có thể là missing có nghĩa, nên hướng xử lý tốt hơn là tạo feature `has_promo` thay vì fill bừa.

---

## Phase 4 - Kiểm tra duplicate và key cơ bản

### Mục tiêu

Kiểm tra bảng có duplicate full row không và các key chính có duy nhất theo grain kỳ vọng không.

### Việc cần làm

- Đếm duplicate full row cho từng bảng.
- Kiểm tra key chính:
  - `orders.order_id`
  - `customers.customer_id`
  - `products.product_id`
  - `returns.return_id`
  - `payments.order_id`
  - `order_items(order_id, product_id)`
- Xuất các bảng phase 4.
- Vẽ `phase4_duplicate_key_count_by_table.png`.

### Kết luận theo kết quả chạy

- `orders`, `customers`, `products`, `returns`, `payments`: key chính đều duy nhất.
- `order_items` có 16 tổ hợp key `(order_id, product_id)` bị trùng, ảnh hưởng 32 dòng.

**Ý nghĩa DS:** Duplicate key trong `order_items` có thể làm sai feature số lượng và tổng tiền nếu aggregate trực tiếp. Cần xử lý hoặc ghi chú trước khi feature engineering.

---

## Phase 5 - Kiểm tra giá trị bất thường, outlier đơn giản và category

### Mục tiêu

Phát hiện các giá trị số bất thường và kiểm tra các cột category có domain hợp lý không.

### Việc cần làm

- Kiểm tra giá trị âm ở các cột số.
- Đếm giá trị bằng 0 ở các cột số.
- Tính min, max, mean, median cho numeric columns.
- Kiểm tra số lượng unique value ở các cột category.
- Xuất bảng phase 5 và vẽ các biểu đồ numeric/category.

### Kết luận theo kết quả chạy

- Không phát hiện giá trị âm ở các cột số.
- `discount_amount = 0` xuất hiện nhiều, phù hợp với nghiệp vụ đơn không dùng giảm giá.
- Các category chính có domain hợp lý và không phát hiện category dị thường rõ ràng.

---

## Phase 6 - Kiểm tra datetime có hợp lệ

### Mục tiêu

Đảm bảo các cột ngày parse được và không vi phạm logic thời gian cơ bản.

### Việc cần làm

- Parse `order_date`, `signup_date`, `return_date`.
- Kiểm tra lỗi parse.
- Kiểm tra `return_date` có trước `order_date` không.
- Xuất `phase6_date_parse_check.csv` và `phase6_date_logic_check.csv`.

### Kết luận theo kết quả chạy

- Các cột ngày parse được.
- Không phát hiện `return_date` trước `order_date`.
- `return_date` là thông tin sau khi trả hàng, không được dùng làm feature trước khi dự đoán.

---

## Phase 7 - Kiểm tra quan hệ giữa các bảng

### Mục tiêu

Kiểm tra các khóa liên kết giữa bảng con và bảng chính để đảm bảo join không tạo orphan record hoặc mất dữ liệu âm thầm.

### Việc cần làm

- Kiểm tra foreign key:
  - `order_items.order_id` -> `orders.order_id`
  - `returns.order_id` -> `orders.order_id`
  - `payments.order_id` -> `orders.order_id`
  - `orders.customer_id` -> `customers.customer_id`
  - `order_items.product_id` -> `products.product_id`
  - `returns.product_id` -> `products.product_id`
- Kiểm tra coverage order trong `order_items`, `returns`, `payments`.
- Xuất `phase7_foreign_key_check.csv` và `phase7_order_coverage_check.csv`.

### Kết luận theo kết quả chạy

- Tất cả foreign key được kiểm tra đều match 100%, không có orphan record.
- `order_items` và `payments` cover 100% orders.
- `returns` chỉ cover nhóm đơn hoàn/trả, nên không kỳ vọng cover 100% toàn bộ orders.

**Ý nghĩa DS:** Có thể join các bảng theo key cơ bản an toàn. Tuy nhiên `returns` là bảng sự kiện hậu nghiệm, nên cần kiểm tra lifecycle riêng trước khi gắn nhãn.

---

## Phase 8 - Kiểm tra lifecycle / chu trình đơn hàng

### Mục tiêu

Kiểm tra logic vòng đời đơn hàng trước khi tạo nhãn model. Phase này trả lời câu hỏi: một đơn được coi là returned hợp lệ có thật sự nhất quán giữa `orders`, `returns`, `payments` và `order_items` không.

### Việc cần làm

- Tính phân bố `order_status`.
- Kiểm tra `order_status == returned` có record trong `returns`.
- Kiểm tra record trong `returns` có thuộc order `returned`.
- Kiểm tra returned orders có `payments` và `order_items`.
- Kiểm tra `returns.product_id` có nằm trong `order_items` cùng `order_id`.
- Kiểm tra `return_date >= order_date`.
- Kiểm tra `return_quantity <= ordered_quantity`.
- Xuất `phase8_lifecycle_check_summary.csv`.
- Xuất `phase8_lifecycle_conflict_details.csv`.
- Vẽ `phase8_order_status_distribution.png`.
- Vẽ `phase8_lifecycle_consistency.png`.

### Kết luận theo kết quả chạy

- `order_status` có 6 trạng thái: `delivered`, `returned`, `cancelled`, `shipped`, `paid`, `created`.
- Có 36,142 orders mang trạng thái `returned`.
- Trong 36,142 orders `returned`, có 36,062 orders có record tương ứng trong `returns`.
- Có 80 orders `returned` nhưng thiếu record trong `returns`; đây là conflict lifecycle mức medium.
- Tất cả record trong `returns` đều thuộc order có `order_status = returned`.
- Returned orders có đủ `payments` và `order_items`.
- Không phát hiện lỗi `return_date < order_date`.
- Không phát hiện lỗi `return_quantity > ordered_quantity`.
- Không phát hiện `returns.product_id` nằm ngoài order_items của cùng order.

**Ý nghĩa DS:** Phase này tách rõ kiểm tra vòng đời dữ liệu khỏi gắn nhãn model. Nếu bỏ qua phase này, các trạng thái chưa hoàn tất như `created`, `paid`, `shipped` hoặc conflict như `returned` thiếu record returns có thể bị gán nhãn sai.

**Quyết định cho Phase 9:** Không xóa dòng khỏi notebook. Chỉ outcome hợp lệ mới nhận nhãn `0/1`; các trạng thái chưa đủ điều kiện binary hoặc conflict lifecycle giữ `returned_label = NaN`.

---

## Phase 9 - Tạo nhãn Returned/Delivered và kiểm tra cân bằng lớp

### Mục tiêu

Tạo nhãn binary đúng nghiệp vụ sau khi đã kiểm tra lifecycle, đồng thời thống kê rõ phần có nhãn và phần giữ NaN.

### Việc cần làm

- Tạo `returned_label` ở cấp order.
- Gắn `1` cho `order_status == returned` và có record trong `returns`.
- Gắn `0` cho `order_status == delivered` và không có record trong `returns`.
- Gắn `NaN` cho các trạng thái `created`, `paid`, `shipped`, `cancelled`.
- Gắn `NaN` cho conflict lifecycle như `returned` nhưng thiếu record returns.
- Tạo `label_reason` để giải thích vì sao dòng được gắn `0/1/NaN`.
- Xuất `phase9_order_label_preview.csv`.
- Xuất `phase9_label_distribution.csv`.
- Xuất `phase9_label_exclusion_summary.csv`.
- Vẽ `phase9_label_distribution.png`.

### Kết luận theo kết quả chạy

- Không xóa dòng khỏi dữ liệu kiểm tra; các dòng không đủ điều kiện binary được giữ lại với `returned_label = NaN`.
- Tập có nhãn hợp lệ gồm 552,778 orders:
  - Delivered = 0: 516,716 orders, chiếm 93.48%.
  - Returned = 1: 36,062 orders, chiếm 6.52%.
- Có 94,167 orders giữ `returned_label = NaN`:
  - 94,087 orders ở trạng thái `created`, `paid`, `shipped`, `cancelled`.
  - 80 orders `returned` nhưng thiếu record trong `returns`.

**Ý nghĩa DS:** Đây là bài toán mất cân bằng lớp mạnh. Khi train model binary, cần lọc `returned_label.notna()` cho tập train/validation/test. Phần NaN vẫn có giá trị audit và giúp hiểu dữ liệu vận hành, nhưng không được ép thành returned.

**Cần làm tiếp:** Khi modeling, không dùng Accuracy làm metric chính. Nên ưu tiên Recall/F1/PR-AUC cho lớp returned và cân nhắc `class_weight` hoặc sampling phù hợp.

---

## Phase 10 - Kiểm tra leakage risk

### Mục tiêu

Ghi chú các cột không nên dùng làm feature vì có thể lộ thông tin tương lai hoặc trực tiếp lộ nhãn.

### Việc cần làm

- Đánh dấu các cột từ `returns`: `return_date`, `return_reason`, `refund_amount`, `return_quantity`.
- Đánh dấu `order_status` vì dùng trực tiếp trong logic nhãn/lifecycle.
- Đánh dấu biến dẫn xuất như `has_return_record` vì dùng trực tiếp để xác định returned hợp lệ.
- Xuất `phase10_leakage_risk_table.csv`.

### Kết luận theo kết quả chạy

- Các cột từ bảng `returns` có leakage risk cao.
- `order_status` và `has_return_record` không được dùng làm feature.
- Chỉ dùng thông tin có sẵn tại thời điểm đặt hàng hoặc trước đó khi train model.

---

## Phase 11 - Tổng hợp issue

### Mục tiêu

Tổng hợp các vấn đề quan trọng thành issue log và action plan.

### Việc cần làm

- Gom issue missing value.
- Gom issue duplicate key.
- Gom issue foreign key/date/numeric nếu có.
- Gom issue lifecycle từ Phase 8.
- Xuất `phase11_quality_issue_log.csv`.
- Xuất `phase11_quality_action_plan.csv`.
- Vẽ `phase11_issue_count_by_severity.png`.

### Kết luận theo kết quả chạy

- **2 issue HIGH**: Missing value cao ở `order_items.promo_id` và `order_items.promo_id_2`.
- **2 issue MEDIUM**:
  - Duplicate key `(order_id, product_id)` trong `order_items`.
  - 80 orders `returned` thiếu record trong `returns`.
- Không có issue về foreign key, date parse, return date, return quantity hoặc product pair trong returns.

**Action plan được ưu tiên:**
1. Xử lý `promo_id` thành feature như `has_promo`.
2. Loại bỏ hoặc giải thích `promo_id_2`.
3. Kiểm tra 32 dòng duplicate key trong `order_items` trước khi aggregate.
4. Ghi chú hoặc xử lý nghiệp vụ 80 orders `returned` thiếu record returns.

---

## Phase 12 - Kết luận quality check

### Mục tiêu

Chốt dữ liệu đã sẵn sàng chuyển sang bước nào tiếp theo và ghi rõ nguyên tắc cho EDA/modeling.

### Kết luận

**Dữ liệu có thể chuyển sang EDA** nhưng **chưa nên modeling trực tiếp** nếu chưa xử lý/ghi chú các issue trong Phase 11.

**Tổng kết những gì đã xác nhận:**
- 6 bảng đều load được, schema đầy đủ, không thiếu cột.
- Foreign key cơ bản khớp 100%, có thể join an toàn.
- Ngày tháng hợp lệ, không có lỗi logic ngày trả trước ngày đặt.
- Không có giá trị âm ở cột số.
- Lifecycle returned nhìn chung nhất quán: returns khớp status returned, có payment và order_items đầy đủ.
- Có 80 orders `returned` thiếu record trong `returns`; các dòng này giữ `returned_label = NaN`.
- Nhãn binary hợp lệ gồm 516,716 delivered và 36,062 returned.
- Các trạng thái `created`, `paid`, `shipped`, `cancelled` giữ NaN, không bị ép thành returned.
- Leakage risk đã được xác định và blacklist.
- `promo_id`, `promo_id_2`, duplicate key trong `order_items`, và 80 conflict lifecycle cần được xử lý/ghi chú trước modeling.

**Lộ trình tiếp theo:**

```text
Clean Data -> EDA -> Feature Engineering -> Modeling
```

**Nguyên tắc quan trọng:** Khi train model binary, dùng `returned_label.notna()` để chọn tập có nhãn hợp lệ. Không tự động biến `created`, `paid`, `shipped`, `cancelled` thành returned.
