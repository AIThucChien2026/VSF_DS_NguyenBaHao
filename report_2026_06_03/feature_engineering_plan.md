# Data Preparation & Feature Engineering Plan

Bản kế hoạch này dùng cho bước **chuẩn bị dữ liệu trước khi train model** trong bài toán thương mại điện tử.

Mục tiêu cuối:

```text
Dự đoán Revenue và COGS theo ngày
```

File này không viết code. Nó chỉ nói rõ cần làm gì, vì sao làm, và sau mỗi bước cần kết luận điều gì.

Quy tắc trình bày notebook:

- Mỗi task heading trong notebook phải có code/output ngay bên dưới.
- Text dưới heading phải viết theo mẫu **Mục tiêu:** làm gì và giúp gì cho pipeline/model.
- Nếu chỉ là giải thích không có code kiểm tra, không để thành task heading độc lập.

---

## 0. Setup & Project Context

**Cần làm**

Xác định bộ dữ liệu, thư mục output, target modeling và nguyên tắc chung trước khi tạo feature.

**Vì sao làm**

Bước setup giúp notebook và plan có cùng context: dự đoán `Revenue` và `COGS` theo ngày cho bài toán thương mại điện tử.

**Kết luận sau mục này**

```text
Đã xác định context dự án, input data và output cần lưu.
```

---

## 1. Problem Definition & Target Setup

### 1.1. Target Variables

**Cần làm**

Dùng bảng `sales.csv` làm bảng target.

Target gồm:

- `Revenue`
- `COGS`

Cột thời gian:

- `Date`

**Vì sao làm**

Bảng `sample_submission.csv` cũng có `Date, Revenue, COGS`, nên đây là đầu ra cần dự đoán.

**Kết luận sau mục này**

```text
Model sẽ dự đoán Revenue và COGS cho từng ngày.
Mỗi dòng dữ liệu modeling = 1 ngày.
```

### 1.2. Prediction Grain

Prediction grain của bài toán là `1 dòng = 1 ngày`. Tất cả feature phải được đưa về grain ngày trước khi join vào target.

---

## 2. Modeling Table Design

### 2.1. Modeling Grain Validation

**Cần làm**

Tạo bảng modeling có grain:

```text
1 dòng = 1 ngày
```

Bảng này sẽ gồm:

- `Date`
- `Revenue`
- `COGS`
- các feature theo ngày

**Vì sao làm**

Target là doanh thu/ngày, nên feature cũng phải đưa về ngày. Không được join raw order hoặc raw order_items trực tiếp vào bảng target, vì sẽ làm nhân dòng và sai target.

**Kết luận sau mục này**

```text
Tất cả bảng khác nếu muốn dùng làm feature phải aggregate về ngày trước.
```

### 2.2. Date Coverage Check

Kiểm tra khoảng thời gian train/test và coverage của các bảng nguồn theo `Date`.

---

## 3. Data Preparation Before Feature Engineering

### 3.1. Date Parsing & Time Alignment

**Cần làm**

Chuẩn hóa các cột ngày quan trọng:

- `sales.Date`
- `orders.order_date`
- `web_traffic.date`
- `inventory.snapshot_date`
- `promotions.start_date`, `promotions.end_date`
- `shipments.ship_date`, `shipments.delivery_date`
- `returns.return_date`
- `reviews.review_date`

**Vì sao làm**

Feature theo ngày, lag, rolling, promotion active, shipping delay đều phụ thuộc vào date. Sai date thì feature sai.

**Kết luận sau mục này**

```text
Các cột ngày đúng format và có thể group theo ngày/tháng.
```

### 3.2. Key Validation Before Join

**Cần làm**

Trước khi join, kiểm tra:

- `products.product_id` có unique không
- `customers.customer_id` có unique không
- `orders.order_id` có unique không
- `promotions.promo_id` có unique không

**Vì sao làm**

Nếu bảng dimension bị duplicate key, join sẽ làm nhân dòng, làm feature doanh thu/số lượng bị phóng đại.

**Kết luận sau mục này**

```text
Chỉ join khi biết quan hệ join là gì và có làm nhân dòng không.
```

### 3.3. Missing Value Treatment Strategy

**Cần làm**

Không fill null hàng loạt. Cần phân loại:

- `promo_id` null: có thể là không dùng promotion.
- shipment null với `cancelled/created/paid`: có thể hợp lý.
- shipment null với `delivered/returned/shipped`: cần flag bất thường.
- `applicable_category` null: có thể là promotion áp dụng cho nhiều category.

**Vì sao làm**

Missing trong thương mại điện tử thường mang ý nghĩa nghiệp vụ. Fill sai có thể làm mất tín hiệu.

**Kết luận sau mục này**

```text
Missing nào hợp lý thì giữ/tạo flag.
Missing nào bất thường thì flag để model hoặc report biết.
```

### 3.4. Outlier Review Strategy

**Cần làm**

Không xóa outlier ngay. Cần kiểm tra:

- Tiền cao có đi kèm quantity cao không?
- Revenue cao có đi kèm COGS cao không?
- Discount cao có do promotion không?
- Refund cao có đi kèm return_quantity cao không?

**Vì sao làm**

Ngày doanh thu cao có thể là ngày sale lớn, không phải lỗi. Xóa nhầm sẽ làm model không học được mùa cao điểm.

**Kết luận sau mục này**

```text
Outlier hợp lý thì giữ.
Outlier vô lý thì flag hoặc xử lý ở bản clean.
```

---

## 4. Feature Engineering By Data Source

### 4.1. Historical Target Features

**Cần làm**

Tạo các feature từ lịch sử trước đó:

- Revenue ngày hôm qua
- Revenue 7 ngày trước
- Revenue trung bình 7 ngày gần nhất
- Revenue trung bình 28 ngày gần nhất
- COGS ngày hôm qua
- COGS 7 ngày trước
- COGS trung bình 7/28 ngày gần nhất

**Vì sao làm**

Doanh thu thường có tính lặp lại theo ngày gần đây và theo chu kỳ tuần. Lịch sử gần nhất là tín hiệu rất mạnh cho dự báo doanh thu.

**Cần tránh**

Không dùng Revenue/COGS của chính ngày cần dự đoán làm feature, vì đó là target.

**Kết luận sau mục này**

```text
Feature target quá khứ phải được shift về quá khứ để tránh leakage.
```

### 4.2. Calendar Features

**Cần làm**

Tạo feature từ `Date`:

- thứ trong tuần
- có phải cuối tuần không
- tháng
- quý
- năm
- đầu tháng/cuối tháng nếu cần

**Vì sao làm**

Hành vi mua sắm có thể khác nhau giữa ngày thường, cuối tuần, tháng cao điểm, mùa lễ tết.

**Kết luận sau mục này**

```text
Calendar feature an toàn, vì biết trước cho cả train và test.
```

### 4.3. Web Traffic Features

**Cần làm**

Dùng bảng `web_traffic`, đưa về ngày:

- sessions
- unique_visitors
- page_views
- bounce_rate
- avg_session_duration_sec

Có thể tạo:

- traffic ngày trước
- traffic trung bình 7 ngày
- traffic trung bình 28 ngày

Chỉ tạo rolling mean cho traffic. Không tạo rolling sum cho `bounce_rate`, `avg_session_duration_sec` hoặc các ratio vì tổng của ratio không có ý nghĩa nghiệp vụ rõ ràng.

**Vì sao làm**

Traffic cao thường liên quan đến nhiều khách vào web hơn, có thể làm Revenue tăng.

**Cần kiểm tra**

- `unique_visitors <= sessions`
- `page_views >= sessions`
- bounce_rate nằm trong `[0, 1]`

**Kết luận sau mục này**

```text
Traffic là nhóm feature quan trọng, nhưng chỉ tạo lag/rolling cho metric có ý nghĩa và không sinh feature hàng loạt.
```

### 4.4. Order Behavior Features

**Cần làm**

Aggregate bảng `orders` theo ngày:

- số order
- số customer unique

Mặc định chỉ dùng:

- `order_count`
- `order_unique_customers`

Chưa dùng tỉ lệ status/device/source/payment_method ở bản đầu vì các biến này dễ làm phình feature space và một số status có thể là kết quả sau mua.

**Vì sao làm**

Số đơn hàng và kênh đặt hàng nói rất nhiều về nhu cầu mua sắm trong ngày.

**Cần tránh**

Nếu bài toán là dự đoán trước khi ngày diễn ra, không được dùng số order của chính ngày đó. Khi đó phải dùng lag/rolling của order.

**Kết luận sau mục này**

```text
Order feature rất mạnh, nhưng ban đầu chỉ giữ count/customer quá khứ để tránh feature thừa và giảm leakage.
```

### 4.5. Product & Order Item Features

**Cần làm**

Join `order_items` với `products` qua `product_id`, sau đó aggregate theo ngày:

- tổng quantity
- số product unique
- discount trung bình
- tỉ lệ có promotion
- tỉ lệ category theo quantity cho các category lớn

**Vì sao làm**

Nhóm này giúp model hiểu ngày nào bán nhiều sản phẩm, category nào đóng góp lớn, discount có cao không.

**Cần tránh**

Không join raw order_items vào target daily. Phải aggregate về ngày trước.
Không mặc định đưa `line_revenue_after_discount` hoặc `estimated_line_cogs` vào feature set, vì chúng quá gần với target `Revenue/COGS` và có thể tạo feature proxy trùng lặp với target history.

**Kết luận sau mục này**

```text
Feature sản phẩm/category giúp giải thích demand, nhưng ban đầu ưu tiên quantity, promo và category mix thay vì proxy doanh thu/COGS.
```

### 4.6. Promotion Features

**Cần làm**

Tạo feature promotion theo ngày:

- có promotion active không
- số promotion active
- discount trung bình của promotion active
- promo_type
- promo_channel
- có stackable promo không

**Vì sao làm**

Khuyến mãi có thể làm tăng Revenue nhưng làm thay đổi margin/COGS.

**Cần kiểm tra**

Promotion active khi:

```text
start_date <= Date <= end_date
```

**Kết luận sau mục này**

```text
Promotion feature nên được tạo theo calendar của promotion, không đưa trực tiếp promo_id raw vào model.
```

### 4.7. Inventory Features

**Cần làm**

Aggregate `inventory` theo ngày:

- tổng stock_on_hand
- avg fill_rate
- stockout rate

Chỉ dùng inventory nếu coverage theo ngày đủ cao. Nếu bảng inventory chỉ có ít ngày/snapshot thưa thớt so với target daily, bỏ qua và ghi vào `skipped_feature_sources.csv`.

**Vì sao làm**

Nếu hàng hết tồn kho, doanh thu có thể giảm. Nếu tồn kho cao, có thể liên quan đến demand yếu hoặc chuẩn bị sale.

**Kết luận sau mục này**

```text
Inventory feature chỉ được đưa vào model khi coverage theo ngày đủ tin cậy; nếu coverage thấp thì skip để tránh feature missing nhiều.
```

### 4.8. Fulfillment, Return & Review Features

**Cần làm**

Tạo feature quá khứ:

- return_count lag/rolling
- refund_amount lag/rolling
- avg_rating lag/rolling
- review_count lag/rolling
- delivery_delay trung bình của các ngày trước

**Vì sao làm**

Return, refund, review phản ánh chất lượng đơn hàng và trải nghiệm khách hàng. Tuy nhiên chúng thường xảy ra sau khi mua, nên rất dễ leak.

**Cần tránh**

Không dùng return/review của chính ngày cần dự đoán nếu nó chỉ xuất hiện sau khi bán hàng đã xảy ra.

**Kết luận sau mục này**

```text
Nhóm shipment/return/review chỉ nên dùng dạng lag/rolling từ quá khứ.
```

---

## 5. Feature Consolidation

### 5.1. Daily Feature Join

**Cần làm**

Sau khi từng nhóm feature đã aggregate về ngày, join tất cả vào bảng `sales` theo `Date`.

**Vì sao làm**

Join theo Date giữ đúng grain 1 dòng = 1 ngày.

**Kết luận sau mục này**

```text
Sau mỗi lần join, số dòng không được tăng.
Date vẫn phải unique.
```

### 5.2. Post-Join Missing Check

**Cần làm**

Kiểm tra cột nào missing nhiều sau khi join feature.

**Vì sao làm**

Missing sau join có thể do bảng nguồn không phủ hết time range của `sales`.

**Kết luận sau mục này**

```text
Feature missing quá nhiều cần cân nhắc loại, fill có lý do, hoặc chỉ dùng trong giai đoạn có đủ dữ liệu.
```

---

## 6. Feature Quality Review

### 6.1. Missing, Constant & Invalid Feature Check

**Cần làm**

Kiểm tra:

- feature toàn null
- feature missing quá nhiều
- feature toàn 1 giá trị
- feature có giá trị vô lý
- feature quá nhiều outlier

**Vì sao làm**

Feature tạo ra có thể sai do aggregate, join, date range hoặc logic shift.

**Kết luận sau mục này**

```text
Feature lỗi thì sửa hoặc loại trước khi train.
```

### 6.2. Leakage Risk Review

**Cần làm**

Với mỗi feature, trả lời:

```text
Feature này có biết được trước ngày cần dự đoán không?
```

**Vì sao làm**

Leakage làm model có điểm số đẹp giả nhưng dùng thật sẽ tệ.

**Kết luận sau mục này**

```text
Feature có leakage risk cao thì không đưa vào model chính.
```

### 6.3. Feature EDA

**Cần làm**

Xem nhanh:

- phân bố feature
- feature có liên quan đến Revenue/COGS không
- feature có ổn định theo thời gian không
- feature có trùng lặp với feature khác không

**Vì sao làm**

Sau feature engineering, cần EDA lại feature mới. EDA ban đầu chỉ giúp hiểu dữ liệu gốc.

**Kết luận sau mục này**

```text
Chỉ giữ feature có logic đúng, chất lượng ổn, và có khả năng giúp target.
```

---

## 7. Time-Based Train/Validation Split

### 7.1. Train/Validation Period Definition

**Cần làm**

Chia train/validation theo thứ tự thời gian.

**Vì sao làm**

Dự đoán doanh thu theo ngày là bài toán chuỗi thời gian. Random split sẽ để dữ liệu tương lai lọt vào train.

**Kết luận sau mục này**

```text
Train là quá khứ, validation là giai đoạn sau train.
```

---

## 8. Feature Selection

### 8.1. Rule-Based Feature Filtering

**Cần làm**

Loại feature:

- leakage risk cao
- missing quá nhiều
- constant
- duplicate
- không có ý nghĩa nghiệp vụ
- feature ratio bị tạo rolling sum
- feature proxy target quá trực tiếp
- feature source coverage theo ngày quá thấp

**Vì sao làm**

Loại feature lỗi trước giúp model đơn giản hơn và tránh học sai.

**Kết luận sau mục này**

```text
Danh sách feature bị loại/skip phải có lý do trong catalog hoặc skipped source summary.
```

### 8.2. Validation-Based Feature Review

**Cần làm**

Đánh giá feature bằng:

- liên quan với target
- kết quả validation theo thời gian
- tính ổn định qua các giai đoạn
- giới hạn số feature mỗi nhóm để tránh một nhóm áp đảo model

**Vì sao làm**

Feature tốt không chỉ là feature có correlation cao. Nó phải đúng logic, không leak, và giúp validation.

**Kết luận sau mục này**

```text
Feature được chọn phải có lý do nghiệp vụ, pass quality filter, có tín hiệu ổn định trên train/validation và không vượt group cap.
```

---

## 9. Required Outputs

### 9.1. Modeling Table

Cần lưu:

```text
report_3_6_2026/feature_outputs/modeling_table_daily.csv
```

**Nội dung**

- `Date`
- `Revenue`
- `COGS`
- các feature cuối cùng trước train

**Kết luận**

```text
File này là input cho modeling.
```

### 9.2. Feature Catalog

Cần lưu:

```text
report_3_6_2026/feature_outputs/feature_catalog.csv
```

**Nội dung**

Mỗi feature cần có:

- `feature_name`
- `source_table`
- `feature_group`
- `logic_tao_feature`
- `co_dung_lag_khong`
- `missing_rate`
- `leakage_risk`
- `business_reason`
- `status`

**Kết luận**

```text
File này giúp review feature có đúng logic không.
```

### 9.3. Selected Feature Summary

Cần lưu:

```text
report_3_6_2026/feature_outputs/selected_features_summary.csv
```

**Nội dung**

Mỗi feature được chọn cần có:

- `feature_name`
- `selected_for_target`: Revenue, COGS, hoặc both
- `feature_group`
- `business_reason`
- `quality_status`
- `leakage_risk`
- `selection_reason`
- `validation_result`
- `final_decision`
- `review_note`

**Kết luận**

```text
Đây là file quan trọng nhất để review feature trước khi train model.
```

### 9.4. Train/Validation Split Summary

Cần lưu tóm tắt train/validation split để review giai đoạn train và validation.

---

## 10. Completion Criteria

Bước Feature Engineering được xem là xong khi:

- Target `Revenue` và `COGS` đã rõ.
- Modeling table có grain 1 dòng = 1 ngày.
- Các feature đều aggregate về ngày.
- Các feature rủi ro leakage đã bị loại hoặc flag.
- Missing, outlier, duplicate đã xử lý có lý do.
- Có EDA lại sau khi tạo feature.
- Có train/validation split theo thời gian.
- Có `modeling_table_daily.csv`.
- Có `feature_catalog.csv`.
- Có `selected_features_summary.csv`.
