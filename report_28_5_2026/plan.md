# Kế hoạch EDA dựa trên notebook `Business_and data.ipynb`

Tài liệu này viết lại kế hoạch phân tích theo đúng những gì notebook `Business_and data.ipynb` đang triển khai: hiểu dữ liệu, kiểm tra chất lượng, dựng bảng phân tích Revenue & Profit, sau đó đi sâu vào các lát cắt có giá trị kinh doanh và gợi ý đặc trưng cho bài toán dự báo.

---

## 1. Mục tiêu phân tích

Mục tiêu chính là biến bộ dữ liệu e-commerce/retail thành một câu chuyện phân tích rõ ràng:

- Hiểu cấu trúc dữ liệu, grain của từng bảng và quan hệ join.
- Đánh giá dữ liệu có đủ sạch, đúng logic và đủ tin cậy để phân tích hay không.
- Tạo hai bảng phân tích chính ở cấp `order_item` và `order`.
- Đo doanh thu, COGS, lợi nhuận, margin, AOV, tác động của discount, return/refund và độ tập trung doanh thu.
- Khai thác thêm quan hệ giữa sales, web traffic, fulfillment, review và product mix để đề xuất feature cho dự báo Revenue/COGS.

Phạm vi thời gian chính:

- `orders` và `sales`: từ `2012-07-04` đến `2022-12-31`.
- `web_traffic`: từ `2013-01-01` đến `2022-12-31`.
- `sample_submission`: từ `2023-01-01` đến `2024-07-01`, dùng cho giai đoạn dự báo/nộp kết quả.

---

## 2. Bản đồ dữ liệu

| Bảng | Nhóm | Số dòng | Vai trò nghiệp vụ |
|---|---:|---:|---|
| `orders` | transaction | 646,945 | Bảng trung tâm ở cấp đơn hàng: ngày đặt, khách hàng, trạng thái, phương thức thanh toán, thiết bị, nguồn đơn. |
| `order_items` | transaction | 714,669 | Chi tiết sản phẩm trong từng đơn; là grain chính để tính gross/net revenue theo product/category. |
| `payments` | transaction | 646,945 | Giá trị thanh toán và installments ở cấp đơn hàng. |
| `shipments` | transaction | 566,067 | Ngày ship, ngày giao, shipping fee; dùng để đo lead time và fulfillment. |
| `returns` | transaction | 39,939 | Sự kiện trả hàng/hoàn tiền theo order/product. |
| `reviews` | transaction | 113,551 | Rating và review theo order/product/customer. |
| `customers` | master | 121,930 | Hồ sơ khách hàng: zip, city, signup, gender, age group, acquisition channel. |
| `products` | master | 2,412 | Danh mục sản phẩm: category, segment, size, color, price, COGS. |
| `promotions` | master | 50 | Chương trình khuyến mãi, discount, kênh áp dụng, điều kiện đơn tối thiểu. |
| `geography` | master | 39,948 | Mapping zip sang city/region/district. |
| `inventory` | operational | 60,247 | Snapshot tồn kho theo sản phẩm/tháng. |
| `web_traffic` | operational | 3,652 | Traffic daily theo nguồn: sessions, visitors, page views, bounce rate. |
| `sales` | analytical | 3,833 | Doanh thu và COGS daily, là bảng lõi cho trend và forecasting. |
| `sample_submission` | analytical | 548 | Khung ngày cần dự báo Revenue/COGS. |

Grain quan trọng:

- `orders`: 1 dòng = 1 đơn hàng.
- `order_items`: 1 dòng = 1 product line trong 1 đơn hàng.
- `payments`: 1 dòng = 1 thanh toán cho 1 đơn hàng.
- `shipments`: 1 dòng = 1 thông tin vận chuyển cho 1 đơn hàng đã ship.
- `returns`: 1 dòng = 1 lần return/refund theo order/product; một order có thể có nhiều return record.
- `reviews`: 1 dòng = 1 review theo order/product/customer; một order có thể có nhiều review.
- `sales` và `web_traffic`: 1 dòng = 1 ngày.
- `inventory`: 1 dòng = 1 product snapshot theo tháng.

---

## 3. Quan hệ join và nguyên tắc tránh sai grain

Các quan hệ FK đã được notebook kiểm tra đều PASS, không có orphan record trong 13 quan hệ chính.

| Quan hệ | Kiểu | Cách dùng |
|---|---|---|
| `orders.order_id` -> `order_items.order_id` | 1-n | Join trực tiếp sẽ nhân dòng order; cần aggregate `order_items` trước khi phân tích ở cấp order. |
| `orders.order_id` -> `payments.order_id` | 1-1 | Dùng để kiểm tra payment value và bổ sung thông tin thanh toán. |
| `orders.order_id` -> `shipments.order_id` | 1-0/1 | Dùng cho lead time; order chưa ship có thể không có shipment. |
| `orders.order_id` -> `returns.order_id` | 1-n | Aggregate refund/return quantity trước khi join vào order. |
| `orders.order_id` -> `reviews.order_id` | 1-n | Aggregate rating/review count trước khi join vào order. |
| `order_items.product_id` -> `products.product_id` | n-1 | Bổ sung category, segment, size, color, COGS để tính profit/margin. |
| `order_items.promo_id`, `promo_id_2` -> `promotions.promo_id` | n-1 nullable | Null là hợp lệ: không dùng khuyến mãi hoặc không dùng khuyến mãi thứ hai. |
| `orders.customer_id` -> `customers.customer_id` | n-1 | Bổ sung gender, age group, acquisition channel. |
| `orders.zip` -> `geography.zip` | n-1 | Bổ sung vùng địa lý của đơn. |
| `web_traffic.date` -> `sales.Date` | daily | Dùng left join từ `sales`; web traffic thiếu 181 ngày đầu vì traffic bắt đầu từ 2013. |

Nguyên tắc kỹ thuật:

- Khi phân tích product/category, dùng grain `order_item`.
- Khi phân tích AOV, channel, customer, status, trend theo order, dùng grain `order`.
- Khi phân tích daily/monthly forecasting, dùng grain ngày/tháng từ `sales`, sau đó join traffic, return rate, product mix hoặc feature đã lag.
- Không dùng same-period realized feature cho forecasting nếu tại thời điểm dự báo chưa biết giá trị đó.

---

## 4. Luồng notebook cần giữ

### 4.1. Setup

- Load thư viện, cấu hình hiển thị và metadata nghiệp vụ.
- Chuẩn hóa path đầu vào/đầu ra.
- Định nghĩa helper để đọc bảng, lưu bảng kết quả, lưu hình và viết markdown summary.

### 4.2. Bước 1: Data & Business Understanding

Output cần có:

- Data catalog cho toàn bộ CSV.
- Schema overview: dtype, missing, unique values, sample values.
- Date coverage cho các cột ngày.
- Bản đồ grain, key và relationship notes.
- Nhận định nghiệp vụ: dataset mô tả vòng đời e-commerce gồm acquisition, order, payment, shipment, return, review, inventory, traffic và sales.

Biểu đồ ưu tiên:

- Bar chart số dòng/cột theo bảng.
- Timeline coverage cho `sales`, `orders`, `web_traffic`.
- ERD hoặc bảng relationship để trình bày join map.

### 4.3. Bước 2: Data Quality

Kiểm tra bắt buộc:

- Missing values theo cột và phân loại missing hợp lệ/nghi vấn.
- Full duplicate và duplicate trên khóa.
- Outlier numeric cho quantity, price, discount, refund, stock, traffic.
- Logic validation theo nghiệp vụ.
- FK integrity.

Kết quả hiện tại từ notebook:

- `promo_id` missing 61.337% và `promo_id_2` missing 99.971% là hợp lệ nghiệp vụ vì nhiều item không dùng promo hoặc không stack promo.
- `promotions.applicable_category` missing 80% cần review ý nghĩa nghiệp vụ.
- Các rule logic chính PASS: quantity > 0, unit price > 0, discount không âm, discount không vượt gross item value, payment value > 0, rating trong 1-5, delivery date >= ship date.
- Timeline chéo PASS: ship date >= order date, return date >= order date, review date >= order date.
- FK integrity PASS 13/13, orphan rows = 0.

Biểu đồ ưu tiên:

- Top missing columns.
- Boxplot/outlier plot cho numeric fields.
- Heatmap hoặc bảng status cho logic/FK checks.

### 4.4. Bước 3: Chuẩn bị bảng Revenue & Profit

Tạo hai bảng phân tích:

- `items`: join `order_items` với `products`, `orders`, `returns`/refund aggregate nếu cần. Dùng để phân tích product/category/segment/size/color.
- `orders`: aggregate từ item-level về order-level, rồi join payment, shipment, return, review, customer, geography. Dùng để phân tích AOV, channel, status, customer segment, lead time.

Công thức chính:

- `gross_item_revenue = quantity * unit_price`
- `net_item_revenue = gross_item_revenue - discount_amount`
- `estimated_cogs = quantity * cogs`
- `estimated_profit = net_item_revenue - estimated_cogs`
- `margin = estimated_profit / net_item_revenue`
- `gross_profit = Revenue - COGS` trên bảng `sales`
- `sales_margin = gross_profit / Revenue`
- `AOV = order_revenue / number_of_orders`
- `return_rate = returned_orders / total_orders`

Ràng buộc:

- `sales` có Revenue/COGS chính thức, dùng cho trend tổng thể và forecasting.
- `order_items + products.cogs` dùng để ước tính profit theo product/category.
- Refund/return cần tách riêng khỏi discount để tránh kết luận nhầm về nguyên nhân bào mòn doanh thu.

---

## 5. Các module phân tích chính

### 5.1. Revenue Overview

Mục tiêu:

- Đo tổng Revenue, COGS, Gross Profit, Margin.
- Đo số đơn, số khách, số item bán, AOV, median order value.
- Kiểm tra phân phối doanh thu có lệch phải hay không.

Kết quả cần nhấn mạnh:

- Daily `sales.Revenue` lệch phải mạnh: mean khoảng 4.29M, median khoảng 3.65M, p99 khoảng 13.80M.
- Vì mean cao hơn median đáng kể, báo cáo phải dùng cả AOV/mean và median để tránh bị outlier dẫn dắt.

### 5.2. Revenue Trend

Mục tiêu:

- Phân tích Revenue, COGS, Gross Profit, Margin theo ngày/tháng/năm.
- Tách biến động doanh thu thành volume/order count và AOV nếu dùng order-level.
- Đọc các điểm gãy, mùa vụ, tháng tăng/giảm bất thường.

Kết quả cần có:

- Sales không thiếu ngày từ `2012-07-04` đến `2022-12-31`.
- Năm 2022 có Revenue khoảng 1.17B, tăng khoảng 12.15% YoY so với 2021.
- Tháng 12/2022 có margin âm trong bảng monthly sales, cần đưa vào nhóm cảnh báo kiểm tra nguyên nhân COGS/discount/return/mix.

### 5.3. Revenue by Product, Category, Segment

Mục tiêu:

- Xếp hạng category/product/segment theo revenue, quantity, revenue share.
- Tìm nhóm bán nhiều nhưng doanh thu thấp, bán ít nhưng doanh thu cao.
- Đo rủi ro phụ thuộc vào category top.

Kết quả hiện tại:

- `Streetwear` đóng góp khoảng 80.09% item-level revenue, là category trụ cột nhưng cũng là rủi ro tập trung.
- `Outdoor` đứng thứ hai với khoảng 15.01%.
- `Casual` và `GenZ` đóng góp nhỏ hơn nhiều, cần xem vai trò margin/churn/segment thay vì chỉ nhìn revenue.

### 5.4. Revenue by Channel, Device, Payment, Customer

Mục tiêu:

- So sánh doanh thu và AOV theo `order_source`, `device_type`, `payment_method`.
- So sánh khách hàng theo `age_group`, `gender`, `acquisition_channel`, city/region.
- Đề xuất ưu tiên ngân sách theo kênh có revenue lớn và chất lượng đơn tốt.

Kết quả hiện tại:

- `organic_search` dẫn đầu order source với khoảng 27.97% revenue.
- `paid_search` khoảng 21.95%, `social_media` khoảng 20.03%.
- `mobile` chiếm khoảng 45.07% revenue, `desktop` khoảng 39.95%.
- `credit_card` chiếm khoảng 55.04% revenue theo payment method.
- Nhóm tuổi `25-34` và `35-44` là hai nhóm doanh thu lớn nhất.

### 5.5. Profit & Margin

Mục tiêu:

- Không dừng ở revenue; kiểm tra revenue có chuyển thành profit hay không.
- So sánh category/segment/product theo estimated profit và weighted margin.
- Nhận diện nhóm revenue cao nhưng margin thấp.

Kết quả hiện tại:

- `Streetwear` revenue rất lớn nhưng weighted margin khoảng 9.28%.
- `GenZ` revenue nhỏ hơn nhiều nhưng weighted margin khoảng 15.47%, đáng xem như nhóm có hiệu quả margin tốt.
- Cần dùng scatter revenue vs margin để chia nhóm: revenue cao-margin cao, revenue cao-margin thấp, revenue thấp-margin cao, revenue thấp-margin thấp.

### 5.6. Discount Impact

Mục tiêu:

- So sánh đơn/item không discount và có discount.
- Phân tích discount bucket: `0`, `0-5%`, `5-10%`, `10-20%`, `20%+`.
- Kiểm tra discount có làm tăng AOV/revenue hay đang bào mòn profit.

Kết quả hiện tại:

- Nhóm không discount có weighted margin khoảng 20.11%.
- Bucket `10-20%` và `20%+` có estimated profit âm.
- Bucket `0-5%` cũng âm nặng trong dữ liệu hiện tại, cần kiểm tra vì có thể là cơ chế promo đặc biệt hoặc lệch COGS/product mix.

### 5.7. Return/Refund Impact

Mục tiêu:

- Đo return rate, refund amount, revenue bị mất do refund.
- Tìm category/product có return rate cao và đủ volume để ưu tiên xử lý.
- Kiểm tra return có liên quan delivery delay/rating không.

Yêu cầu phân tích:

- Không chỉ xếp hạng return rate; phải lọc theo volume tối thiểu để tránh kết luận từ nhóm quá nhỏ.
- Tách `return_activity_rate` theo tháng và `cohort_return_rate` theo đơn để tránh sai diễn giải thời điểm return.
- Waterfall chart nên trình bày Gross Revenue -> Discount -> Refund -> Net Revenue.

### 5.8. Revenue Concentration / Pareto

Mục tiêu:

- Kiểm tra top product/customer đóng góp bao nhiêu % revenue.
- Đánh giá nguyên lý 80/20 và rủi ro phụ thuộc vào nhóm đầu.

Yêu cầu:

- Vẽ Pareto chart cho product và customer.
- Báo cáo cả top 10, top 20% và cumulative share.
- Nếu concentration cao, khuyến nghị quản trị rủi ro tồn kho, chất lượng và nguồn cung cho nhóm top.

### 5.9. Relationship & Feature Candidates cho Forecasting

Mục tiêu:

- Tìm quan hệ có thể biến thành feature dự báo Revenue/COGS.
- Phân biệt feature dùng được trước thời điểm dự báo và feature có leakage.

Kết quả hiện tại:

- `sessions`, `unique_visitors`, `page_views`, `sessions_lag_1d`, `sessions_lag_7d`, `sessions_rolling_7d`, `sessions_rolling_30d` có tương quan dương vừa phải với Revenue/COGS.
- `Revenue` với `sessions_rolling_7d` có Pearson khoảng 0.325.
- Lead time gần như không tương quan với rating trong dữ liệu hiện tại, nên không nên phóng đại tác động của delivery delay lên satisfaction.

Feature đề xuất:

- Traffic lag/rolling: `sessions_lag_1d`, `sessions_lag_7d`, `sessions_rolling_7d`, `sessions_rolling_30d`.
- Discount mix lagged hoặc planned discount calendar.
- Product/category mix lagged hoặc planned assortment.
- Return rate lag/rolling.
- Rating lagged average và review volume.
- Historical delivery lead time summary.

---

## 6. Cấu trúc đầu ra cần bàn giao

| Nhóm output | File/Thư mục | Nội dung |
|---|---|---|
| Catalog/schema | `outputs/tables/01_*`, `02_*`, `03_*` | Danh sách bảng, schema, date coverage. |
| Data quality | `outputs/tables/04*`, `05*` | Missing, duplicate, outlier, logic validation, FK integrity. |
| Distribution/trend | `outputs/tables/06*`, `outputs/reports/06*` | Phân phối revenue, revenue group, daily/monthly/yearly trend. |
| Relationship | `outputs/tables/07*`, `outputs/reports/07_relationship_summary.md` | Traffic-sales, discount-profit, leadtime-rating, category-margin, feature candidates. |
| Figures | `outputs/figures/*.png` | Biểu đồ dùng cho báo cáo/thuyết trình. |
| Báo cáo cuối | `EDA_REPORT.md`, `EDA_PRESENTATION_SLIDES.html` | Bản kể chuyện phân tích và slide trình bày. |

---

## 7. Executive Summary cần viết ở cuối notebook/báo cáo

Báo cáo cuối nên có 3 phần ngắn gọn:

1. **Thực trạng dòng tiền:** Revenue/COGS/profit/margin đang ở mức nào, xu hướng tăng giảm ra sao, biến động đến từ volume hay AOV/product mix.
2. **Điểm sáng và điểm nghẽn:** Category/channel/customer segment nào đóng góp tốt; discount bucket, return/refund hoặc COGS/product mix nào đang kéo margin xuống.
3. **Khuyến nghị hành động:** Ưu tiên category/channel có revenue và margin tốt; kiểm soát discount bucket âm profit; rà soát product có return cao; quản trị rủi ro phụ thuộc vào `Streetwear` và nhóm sản phẩm top; dùng traffic lag/rolling và feature lagged để phục vụ forecast.

---

## 8. Checklist hoàn thành

- [ ] Chạy lại notebook từ đầu không lỗi.
- [ ] Các bảng output trong `outputs/tables` được cập nhật.
- [ ] Các hình trong `outputs/figures` được cập nhật.
- [ ] Data quality summary ghi rõ lỗi nào là hợp lệ nghiệp vụ, lỗi nào cần xử lý.
- [ ] Revenue/profit không bị sai grain do join trực tiếp order với item/return/review.
- [ ] Executive Summary có số liệu cụ thể, không chỉ mô tả chung.
- [ ] Feature candidates cho forecasting ghi rõ leakage risk.
- [ ] `EDA_REPORT.md` và `EDA_PRESENTATION_SLIDES.html` đồng nhất với notebook.
