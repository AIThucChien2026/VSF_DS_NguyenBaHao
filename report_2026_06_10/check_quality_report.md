# Báo cáo Check Quality dữ liệu Datathon

## 1. Mục tiêu

Bước check quality được thực hiện để đánh giá dữ liệu đầu vào trước khi chuyển sang EDA, làm sạch dữ liệu, feature engineering và modeling cho bài toán dự đoán đơn hàng bị trả lại.

Mục tiêu chính là kiểm tra dữ liệu có đủ tin cậy để sử dụng hay không, bao gồm: cấu trúc bảng, missing value, duplicate, key liên kết, logic ngày tháng, vòng đời đơn hàng, nhãn returned/delivered và nguy cơ leakage.

Báo cáo này không train model và không sửa dữ liệu gốc. Kết quả được dùng để quyết định dữ liệu đã sẵn sàng cho bước tiếp theo hay cần xử lý thêm.

## 2. Dữ liệu đầu vào

Notebook check quality đã load thành công 6 bảng dữ liệu chính:

| Bảng | Vai trò | Số dòng | Số cột | Trạng thái |
|---|---:|---:|---:|---|
| `orders` | Thông tin đơn hàng | 646,945 | 8 | Loaded |
| `order_items` | Sản phẩm trong từng đơn | 714,669 | 7 | Loaded |
| `customers` | Thông tin khách hàng | 121,930 | 7 | Loaded |
| `products` | Thông tin sản phẩm | 2,412 | 8 | Loaded |
| `returns` | Sự kiện trả hàng | 39,939 | 7 | Loaded |
| `payments` | Thanh toán đơn hàng | 646,945 | 4 | Loaded |

Kết quả kiểm tra schema cho thấy các bảng đều có đủ cột cần thiết, không phát hiện thiếu file hoặc thiếu cột bắt buộc ở bước đầu vào.

## 3. Quy trình thực hiện

Quy trình check quality được triển khai theo 12 phase, gom thành các nhóm kiểm tra chính:

| Nhóm kiểm tra | Phase | Nội dung thực hiện |
|---|---:|---|
| Chuẩn bị và load dữ liệu | 0-2 | Cấu hình đường dẫn, load 6 bảng CSV, kiểm tra file, cột, shape và dtype |
| Chất lượng từng bảng | 3-6 | Kiểm tra missing value, duplicate, key chính, giá trị số, category và datetime |
| Chất lượng liên bảng | 7-8 | Kiểm tra foreign key, coverage, lifecycle đơn hàng và conflict giữa `orders` với `returns` |
| Nhãn và leakage | 9-10 | Tạo nhãn `returned_label`, kiểm tra mất cân bằng lớp và đánh dấu feature có nguy cơ leakage |
| Tổng hợp kết luận | 11-12 | Lập issue log, action plan và kết luận mức độ sẵn sàng của dữ liệu |

## 4. Kết quả kiểm tra chính

### 4.1 Missing value

Phần lớn các cột quan trọng không bị missing. Vấn đề missing tập trung ở hai cột khuyến mãi trong bảng `order_items`.

| Bảng | Cột | Missing count | Missing rate | Mức độ |
|---|---|---:|---:|---|
| `order_items` | `promo_id` | 438,353 | 61.34% | High |
| `order_items` | `promo_id_2` | 714,463 | 99.97% | High |

![Missing rate by column](./check_quality_outputs/figures/phase3_missing_rate_by_column.png)

Nhận xét: `promo_id` có thể là missing có ý nghĩa nghiệp vụ, tức là đơn hàng không dùng khuyến mãi. Không nên fill tùy tiện; nên tạo feature như `has_promo`. Với `promo_id_2`, tỷ lệ thiếu gần như toàn bộ nên cần cân nhắc loại bỏ hoặc chỉ giữ khi có giải thích nghiệp vụ rõ ràng.

### 4.2 Duplicate và key

Các bảng `orders`, `customers`, `products`, `returns`, `payments` đều có key chính duy nhất. Riêng bảng `order_items` có duplicate trên tổ hợp key `(order_id, product_id)`.

| Bảng | Key kiểm tra | Duplicate key | Dòng bị ảnh hưởng | Mức độ |
|---|---|---:|---:|---|
| `order_items` | `order_id`, `product_id` | 16 | 32 | Medium |

![Duplicate key count by table](./check_quality_outputs/figures/phase4_duplicate_key_count_by_table.png)

Nhận xét: duplicate này không quá lớn về số lượng nhưng có thể làm sai các feature tổng hợp như tổng số lượng sản phẩm, tổng giá trị đơn hàng hoặc số sản phẩm duy nhất nếu aggregate trực tiếp.

### 4.3 Giá trị số, category và datetime

Kết quả kiểm tra không phát hiện giá trị âm bất thường ở các cột số. Các giá trị bằng 0 như `discount_amount = 0` phù hợp với nghiệp vụ vì nhiều đơn không dùng giảm giá.

Các cột category chính có domain hợp lý, chưa phát hiện nhóm giá trị lạ rõ ràng. Các cột ngày như `order_date`, `signup_date`, `return_date` parse được và không phát hiện lỗi `return_date` trước `order_date`.

### 4.4 Quan hệ giữa các bảng

Các foreign key quan trọng đều match 100%, không phát hiện orphan record. Điều này cho thấy có thể join dữ liệu theo key cơ bản một cách an toàn.

Các kiểm tra chính gồm:

| Quan hệ kiểm tra | Kết quả |
|---|---|
| `order_items.order_id` -> `orders.order_id` | Pass |
| `returns.order_id` -> `orders.order_id` | Pass |
| `payments.order_id` -> `orders.order_id` | Pass |
| `orders.customer_id` -> `customers.customer_id` | Pass |
| `order_items.product_id` -> `products.product_id` | Pass |
| `returns.product_id` -> `products.product_id` | Pass |

### 4.5 Lifecycle đơn hàng

Lifecycle returned nhìn chung nhất quán. Trong 36,142 order có trạng thái `returned`, có 36,062 order có record tương ứng trong `returns`. Có 80 order trạng thái `returned` nhưng thiếu record trong bảng `returns`.

| Kiểm tra lifecycle | Issue count | Severity | Trạng thái |
|---|---:|---|---|
| `returned` nhưng thiếu record trong `returns` | 80 | Medium | Review |
| Có record `returns` nhưng status không phải `returned` | 0 | High | Pass |
| Returned thiếu payment | 0 | High | Pass |
| Returned thiếu order_items | 0 | High | Pass |
| `returns.product_id` không thuộc order_items cùng order | 0 | High | Pass |
| `return_quantity` lớn hơn số lượng mua | 0 | High | Pass |
| `return_date` trước `order_date` | 0 | High | Pass |

![Lifecycle consistency](./check_quality_outputs/figures/phase8_lifecycle_consistency.png)

Nhận xét: 80 order conflict không nên ép thành returned hợp lệ khi tạo nhãn. Các dòng này nên giữ `returned_label = NaN` để audit hoặc xử lý nghiệp vụ riêng.

### 4.6 Tạo nhãn returned/delivered

Nhãn được tạo theo nguyên tắc:

- `Returned = 1`: `order_status == returned` và có record trong `returns`.
- `Delivered = 0`: `order_status == delivered` và không có record trong `returns`.
- `NaN`: các trạng thái chưa đủ điều kiện binary như `created`, `paid`, `shipped`, `cancelled`, hoặc conflict lifecycle.

| Nhãn | Ý nghĩa | Số order | Tỷ lệ trong tập có nhãn |
|---:|---|---:|---:|
| 0 | Delivered | 516,716 | 93.48% |
| 1 | Returned | 36,062 | 6.52% |
|  | Tổng có nhãn hợp lệ | 552,778 | 100.00% |

Ngoài ra, có 94,167 order được giữ `returned_label = NaN` để không làm sai nhãn mô hình.

![Label distribution](./check_quality_outputs/figures/phase9_label_distribution.png)

Nhận xét: bài toán bị mất cân bằng lớp mạnh, returned chỉ chiếm 6.52% trong tập có nhãn. Khi modeling không nên dùng accuracy làm metric chính; nên ưu tiên PR-AUC, recall, F1 hoặc các metric tập trung vào lớp returned.

### 4.7 Leakage risk

Một số cột không được dùng làm feature vì chỉ xuất hiện sau khi đơn hàng bị trả hoặc trực tiếp lộ nhãn.

| Nguồn | Cột | Mức rủi ro | Dùng làm feature |
|---|---|---|---|
| `returns` | `return_date` | High | No |
| `returns` | `return_reason` | High | No |
| `returns` | `refund_amount` | High | No |
| `returns` | `return_quantity` | High | No |
| `orders` | `order_status` | High | No |
| Derived | `has_return_record` | High | No |

Nguyên tắc sử dụng dữ liệu cho modeling: chỉ dùng thông tin có sẵn tại thời điểm đặt hàng hoặc trước thời điểm đặt hàng. Không dùng dữ liệu hậu nghiệm từ bảng `returns`.

### 4.8 Tổng hợp issue

![Issue count by severity](./check_quality_outputs/figures/phase11_issue_count_by_severity.png)

| Severity | Số issue | Nội dung |
|---|---:|---|
| High | 2 | Missing cao ở `promo_id`, `promo_id_2` |
| Medium | 2 | Duplicate key trong `order_items`, 80 returned order thiếu record `returns` |
| Low | 0 | Không ghi nhận issue low quan trọng |

## 5. Đánh giá chất lượng dữ liệu

Nhìn chung, dữ liệu đủ tốt để chuyển sang EDA vì 6 bảng đều load thành công, schema đầy đủ, foreign key khớp, ngày tháng hợp lệ và lifecycle returned phần lớn nhất quán.

Tuy nhiên, dữ liệu chưa nên đưa trực tiếp vào modeling nếu chưa xử lý hoặc ghi chú rõ các issue sau:

| Vấn đề | Ảnh hưởng | Đánh giá |
|---|---|---|
| Missing cao ở `promo_id`, `promo_id_2` | Có thể gây sai xử lý feature khuyến mãi | Cần xử lý ở clean data/FE |
| Duplicate key trong `order_items` | Có thể làm sai aggregate cấp order | Cần review trước khi tổng hợp feature |
| 80 order `returned` thiếu record trong `returns` | Có thể gây sai nhãn returned | Giữ `returned_label = NaN` hoặc xử lý nghiệp vụ |
| Class imbalance | Model dễ thiên về delivered | Cần chọn metric và threshold phù hợp |
| Leakage từ bảng `returns` | Làm model tốt giả tạo, không dùng được thực tế | Phải blacklist feature leakage |

## 6. Khuyến nghị xử lý tiếp theo

Các bước nên thực hiện trước khi modeling:

1. Xử lý `promo_id` theo hướng tạo feature `has_promo` hoặc nhóm `no_promo`, không fill tùy tiện.
2. Loại bỏ hoặc chỉ giữ `promo_id_2` nếu có giải thích nghiệp vụ rõ ràng.
3. Review 16 duplicate key trong `order_items` trước khi aggregate lên cấp order.
4. Giữ 80 order returned thiếu record returns ở trạng thái audit, không đưa vào tập train binary nếu chưa xác minh.
5. Khi tạo tập train, chỉ dùng các dòng `returned_label.notna()`.
6. Không dùng `returns.*`, `order_status`, `has_return_record` làm feature.
7. Khi modeling, ưu tiên PR-AUC, recall, F1 và cân nhắc class weight hoặc sampling vì lớp returned chỉ chiếm 6.52%.

## 7. Kết luận

Dữ liệu đã sẵn sàng để chuyển sang EDA. Các kiểm tra nền tảng như load dữ liệu, schema, key liên bảng, datetime và lifecycle đều đạt mức tốt.

Dữ liệu chưa nên modeling trực tiếp nếu chưa xử lý hoặc ghi chú các issue high/medium. Tập nhãn hợp lệ hiện có 552,778 order, gồm 516,716 delivered và 36,062 returned; 94,167 order còn lại giữ `returned_label = NaN` để tránh gán nhãn sai.

Kết luận triển khai:

```text
Check Quality: Đạt để sang EDA
Modeling trực tiếp: Chưa khuyến nghị
Điều kiện tiếp theo: xử lý missing promo, duplicate order_items, conflict lifecycle và khóa leakage feature
```
