# Báo cáo Feature Engineering dữ liệu ADS

## 1. Mục tiêu

Feature Engineering chuyển dữ liệu sau EDA thành bộ dữ liệu modeling ở đúng grain: một dòng cho mỗi `order_id`. Bước này tạo feature, kiểm soát leakage, chọn feature và materialize train/validation/test để Modeling có thể dùng trực tiếp.

Nguyên tắc chính:

- Target là binary: Returned = 1, Delivered = 0.
- Dữ liệu ở cấp order, không để nhân bản dòng do join bảng item.
- Không dùng `returns.csv` từ FE trở đi.
- Chỉ dùng feature có sẵn tại hoặc trước thời điểm đặt hàng.

## 2. Dữ liệu đầu vào và contract

| Thành phần | Kết quả |
|---|---|
| Grain | 1 dòng / `order_id` |
| Số order có nhãn | 552,858 |
| Delivered | 516,716 |
| Returned | 36,142 |
| Target source | `orders.order_status` |
| Bảng `returns.csv` | Không dùng trong FE |
| Readiness checklist | 21/21 checks pass |

FE đã xử lý duplicate item key bằng aggregate, loại bỏ `promo_id` và `promo_id_2`, đồng thời đảm bảo các tổng quantity, discount và gross value được bảo toàn sau aggregation.

## 3. Quy trình thực hiện

| Nhóm công việc | Nội dung |
|---|---|
| Audit đầu vào | Kiểm tra grain, schema, duplicate key, label source và date |
| Tạo feature | Customer, payment/order, order item aggregate, product descriptor, calendar |
| Leakage gate | Đánh dấu và loại bỏ feature dùng target history hoặc không chắc có tại order time |
| Feature selection | Quality filter, relevance, redundancy, wrapper bằng Logistic Regression và LightGBM |
| Split và preprocessing | Split theo thời gian, fit preprocessing trên train/fold, lưu raw và processed data |
| Readiness | Kiểm tra feature set, banned features, split integrity và modeling handoff |

## 4. Kết quả tạo feature

Tổng cộng có 52 candidate features được tạo và kiểm tra. Con số 52 là số feature ứng viên trước khi filter, không phải số feature cuối cùng đưa vào model. Số này đến từ việc gom dữ liệu về cấp `order_id`, tạo feature tổng hợp và bung các biến category/product thành nhiều cột multi-hot.

| Nguồn tạo feature | Số feature | Đến từ đâu |
|---|---:|---|
| Payment/order | 8 | `payment_method`, `device_type`, `order_source`, `payment_value`, `is_cod`, interaction và biến log/quantile |
| Customer | 4 | `customer_tenure_days`, `tenure_group`, `age_group`, `gender` |
| Order item aggregate | 6 | Tổng quantity, số product, discount, gross value, discount ratio, flag discounted |
| Product descriptor | 26 | Bung `category`, `segment`, `size`, `color` thành các cột multi-hot theo đơn hàng |
| Product target history | 3 | Feature lịch sử return của sản phẩm, chỉ giữ để audit leakage |
| Calendar | 5 | `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend`, `is_q4` |
| **Tổng** | **52** | Candidate features trước selection |

Sau leakage gate và selection, chỉ 28 feature được khóa cho bộ V1; 16 feature được giữ ở nhóm experimental/watch. Các feature ID, metadata và target như `order_id`, `order_date`, `customer_id`, `returned_label`, `data_split` không được tính vào 52 candidate features.

| Nhóm feature | Ví dụ |
|---|---|
| Payment/order | `payment_method`, `device_type`, `order_source`, `payment_value`, `is_cod` |
| Customer | `customer_tenure_days`, `tenure_group`, `age_group`, `gender` |
| Order item aggregate | `total_quantity`, `unique_product_count`, `discount_ratio`, `is_discounted` |
| Product descriptor | Category, segment, size, color multi-hot |
| Calendar | `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend`, `is_q4` |
| Experimental interaction | `payment_device_interaction` |

## 5. Leakage gate

Leakage gate là phần quan trọng nhất của FE. Ba feature bị cấm vì sử dụng lịch sử target hoặc không đảm bảo có sẵn tại thời điểm đặt hàng:

| Feature bị cấm | Lý do |
|---|---|
| `high_risk_product_count` | Dựa trên lịch sử returned label của sản phẩm |
| `max_product_return_rate` | Dựa trên target history |
| `mean_product_return_rate` | Dựa trên target history |

Các feature này vẫn được giữ trong audit report để giải thích quyết định, nhưng không xuất hiện trong feature set, raw split hoặc modeling input.

## 6. Feature selection

Quy trình Feature Selection được thực hiện nghiêm ngặt trên tập **Outer Train** (70% dữ liệu đầu) nhằm bảo vệ tính toàn vẹn của tập Validation và Test, tránh hiện tượng data leakage (rò rỉ dữ liệu). Quy trình gồm 4 bước tiến hành chính như sau:

### Bước 1: Bộ lọc rò rỉ dữ liệu (Leakage Gate & Availability Catalog)
* **Mục tiêu:** Kiểm tra và loại bỏ các trường thông tin không có sẵn tại thời điểm khách hàng nhấn nút đặt hàng (`order_date`), hoặc các đặc trưng vô tình sử dụng nhãn mục tiêu (`returned_label`) của tương lai.
* **Hành động:** 
  - Loại bỏ hoàn toàn 3 đặc trưng rò rỉ lịch sử: `mean_product_return_rate`, `max_product_return_rate`, và `high_risk_product_count`.
  - Loại bỏ (Exclude Representation) 3 đặc trưng có nguy cơ rò rỉ thông tin phân phối (như `payment_value_quantile_bucket`) để tránh học ranh giới bin trước khi CV. Các ranh giới này sẽ được học động trong từng fold.

### Bước 2: Bộ lọc chất lượng đặc trưng (Quality Filter)
* **Mục tiêu:** Loại bỏ các đặc trưng nhiễu hoặc không mang thông tin phân biệt.
* **Tiêu chí lọc:**
  - Drop đặc trưng không đổi (constant).
  - Drop đặc trưng có tỷ lệ khuyết thiếu (missing rate) > 60%.
  - Drop đặc trưng chứa giá trị vô cùng (infinite numeric).
  - Drop các đặc trưng bị trùng lặp nội dung hoàn toàn.
* **Kết quả:** Loại bỏ thêm 1 đặc trưng không đạt tiêu chuẩn chất lượng.

### Bước 3: Đánh giá độ tương quan & Lọc đặc trưng dư thừa (Relevance & Redundancy Filtering)
* **Phân tích Relevance:** Sử dụng tương quan điểm nhị phân (Point-biserial correlation) cho biến số và Chi-square / Cramér's V cho biến phân loại để xếp hạng mức độ đóng góp thông tin của từng đặc trưng độc lập.
* **Hành động lọc dư thừa (Redundancy):** Tính toán độ tương quan Pearson giữa các cặp biến số trên Outer Train. Nếu cặp biến có hệ số tương quan `|Pearson Correlation| > 0.98`, đặc trưng có hiệu ứng đơn biến (univariate effect size) yếu hơn sẽ bị loại bỏ để tránh đa cộng tuyến.
* **Kết quả:** Loại bỏ tiếp 1 đặc trưng bị trùng lặp thông tin cao.

### Bước 4: Đánh giá hiệu năng bằng Dual-Model Wrapper
* **Thiết lập:** Sử dụng 3 temporal CV folds dạng cuốn chiếu (expanding window) trên Outer Train để kiểm nghiệm hiệu năng thực tế.
* **Mô hình Wrapper:** Chạy đồng thời 2 mô hình khác loại:
  - **Balanced Logistic Regression** (Baseline tuyến tính)
  - **LightGBM** (Mô hình phi tuyến cây quyết định) với `scale_pos_weight` tối ưu cho từng fold.
* **Cách tiến hành:** Bắt đầu từ baseline chỉ gồm đặc trưng quan trọng nhất (`is_cod`). Thêm lần lượt từng đặc trưng ứng viên (`is_cod + candidate`) để đo lượng thay đổi hiệu năng ($\Delta$ PR-AUC). PR-AUC được chọn làm metric chính vì tập dữ liệu lệch nhãn lớn.
* **Tiêu chuẩn loại bỏ (Consensus Drop):** Một đặc trưng chỉ bị loại bỏ nếu cả 2 mô hình đồng thuận rằng nó gây hại ổn định trên cả 3 folds (tức là $\Delta$ PR-AUC trung bình $\le -0.001$).
* **Kết quả:** Không có đặc trưng nào bị loại ở bước Wrapper này (0 feature dropped), chứng tỏ các đặc trưng còn lại đều mang lại thông tin hữu ích hoặc trung hòa.

---

### Kết quả Phễu Lọc Đặc Trưng (Selection Funnel):

| Giai đoạn lọc (Stage) | Số lượng đặc trưng còn lại / bị loại |
|---|---:|
| **Candidate** (Tất cả ứng viên ban đầu) | 52 |
| **Ban leakage** (Bị loại vì rò rỉ dữ liệu) | -3 |
| **Exclude representation** (Loại để fit động trong fold) | -3 |
| **Drop quality** (Bị loại vì chất lượng kém) | -1 |
| **Drop redundant** (Bị loại vì tương quan cao) | -1 |
| **Drop consistent harm** (Bị loại do Wrapper đồng thuận) | 0 |
| **Giữ lại bộ V1 (Keep V1)** | 28 |
| **Nhóm theo dõi thêm (Watch / Experimental)** | 16 |

![Phễu lọc đặc trưng](./fe_outputs/figures/phase4_selection_funnel.png)

Bộ đặc trưng được chia thành 2 nhóm chính phục vụ Modeling:
* **Bộ Feature V1 (28 đặc trưng):** Đã vượt qua toàn bộ leakage gate và quality/redundancy filters. Các đặc trưng cốt lõi gồm có `is_cod` và `payment_method`.
* **Bộ Experimental (16 đặc trưng):** An toàn về mặt thời gian (point-in-time safe) nhưng cần được theo dõi kỹ trong quá trình huấn luyện do độ ổn định chưa cao (ví dụ: các biến interaction phức tạp hoặc calendar).

![Mức độ quan trọng đặc trưng trên Outer Train](./fe_outputs/figures/phase4_relevance_outer_train.png)

## 7. Split và dữ liệu materialized

Split được thực hiện theo thời gian để mô phỏng đúng bối cảnh dự đoán tương lai.

| Split | Số dòng | Thời gian | Return rate |
|---|---:|---|---:|
| Train | 386,907 | 2012-07-04 -> 2018-04-27 | 6.54% |
| Validation | 82,906 | 2018-04-28 -> 2020-03-27 | 6.37% |
| Test | 83,045 | 2020-03-28 -> 2022-12-31 | 6.70% |

Integrity audit xác nhận train/validation/test không overlap order, đúng thứ tự thời gian và có cùng schema đầu vào.

## 8. Readiness checklist

| Check quan trọng | Kết quả |
|---|---|
| Grain unique theo order | Pass |
| Target binary | Pass |
| `returns.csv` không load từ FE trở đi | Pass |
| Banned feature vắng mặt khỏi feature set | Pass |
| Banned feature vắng mặt khỏi raw split | Pass |
| Wrapper dùng PR-AUC | Pass |
| Duplicate item keys đã aggregate | Pass |
| Promo columns removed | Pass |
| Split integrity passed | Pass |
| V1 feature count | 28 |

Tổng kết: 21/21 readiness checks pass.

## 9. Đánh giá kết quả

FE đã tạo được bộ dữ liệu modeling sạch hơn, đúng grain order và có kiểm soát leakage. Bộ V1 đủ gọn để modeling baseline, đồng thời vẫn giữ nhóm experimental để thử nghiệm sau.

Điểm cần lưu ý là các feature mạnh liên quan đến lịch sử sản phẩm đã bị loại có chủ đích vì rủi ro leakage. Do đó, mô hình sau này có thể không đạt lift quá cao nếu chỉ dùng tín hiệu có sẵn tại thời điểm đặt hàng.

## 10. Kết luận

Feature Engineering sẵn sàng bàn giao cho Modeling.

```text
Readiness: 21/21 pass
Feature V1: 28
Experimental: 16
Processed columns: 52
Split: train / validation / test theo thời gian
Điều kiện modeling: chỉ dùng feature set đã khóa và tiếp tục fail-fast nếu banned feature xuất hiện
```
