# Kế hoạch phân tích các yếu tố ảnh hưởng đến target

## 0. Mục tiêu chung

Sau bước EDA sơ khởi, ta đã biết bộ dữ liệu gồm những bảng nào, cột nào, thời gian ra sao và các bảng nối với nhau bằng khóa nào. Bước tiếp theo là phân tích các yếu tố có thể ảnh hưởng đến target.

Target chính:

- `Revenue`

Các target phụ để giải thích business:

- `COGS`
- `Gross Profit`
- `Gross Margin %`
- `Order Count`
- `AOV`
- `Return Rate`
- `Refund Amount`

Mục tiêu của giai đoạn này:

- Xác định nhóm yếu tố nào liên quan mạnh đến doanh thu.
- Hiểu doanh thu đến từ sản phẩm nào, khu vực nào, nhóm khách hàng nào, kênh nào.
- Kiểm tra khuyến mãi, web traffic, tồn kho, return/review ảnh hưởng thế nào đến revenue/profit.
- Chuẩn bị insight để viết Phần 2 của bài thi: trực quan hóa, phân tích và khuyến nghị kinh doanh.

## 1. Vị trí trong quy trình Data Science

Giai đoạn này nằm sau:

```text
Data Loading
→ Data Understanding
→ Data Quality Check sơ bộ
```

và nằm trước:

```text
Modeling
→ Model Evaluation
→ Final Report / Submission
```

Trong quy trình DS đầy đủ:

```text
1. Business Understanding
2. Data Loading
3. Data Understanding / Initial EDA
4. Data Quality Check
5. Data Cleaning
6. Data Integration / Data Mart
7. Feature Engineering
8. Analytical EDA / Target Driver Analysis
9. Modeling
10. Model Evaluation
11. Interpretation / Recommendation
12. Reporting / Submission
```

Các module trong kế hoạch này chủ yếu thuộc:

```text
Data Integration
→ Feature Engineering
→ Analytical EDA / Target Driver Analysis
→ Business Interpretation
```

## 2. Module 11 - Prepare Analysis Tables

### Làm gì?

Tạo các bảng phân tích chuẩn từ nhiều bảng gốc. Đây là bước nối dữ liệu và tạo các biến cơ bản để các phân tích sau dùng chung.

Bảng cần tạo ở mức item/order:

- `order_items_enriched`: mỗi dòng là một dòng sản phẩm trong đơn hàng, đã nối thêm thông tin order, product, customer, geography, payment, promotion.
- `orders_enriched`: mỗi dòng là một đơn hàng, đã tổng hợp revenue/profit/items.
- `daily_business_metrics`: mỗi dòng là một ngày, gồm revenue, COGS, profit, order count, AOV.

Các biến cần tạo:

- `line_gross = quantity * unit_price`
- `line_revenue = quantity * unit_price - discount_amount`
- `line_cogs = quantity * products.cogs`
- `line_profit = line_revenue - line_cogs`
- `margin_pct = line_profit / line_revenue`
- `promo_used`
- `year`
- `month`
- `quarter`
- `dayofweek`
- `region`
- `city`
- `category`
- `segment`

### Vì sao cần?

Nếu không có bảng phân tích chuẩn, mỗi module sẽ tự join dữ liệu theo một kiểu khác nhau. Điều này dễ gây:

- Nhân dòng khi join `orders` với `order_items`.
- Tính sai revenue nếu dùng nhầm cấp độ order-level và item-level.
- Mỗi biểu đồ dùng một logic lọc order khác nhau.
- Khó kiểm tra lại insight.

Module này giống như nền móng. Các module sau chỉ đọc bảng đã chuẩn hóa, không phải join lại từ đầu.

### Kết quả đầu ra dùng để làm gì?

Kết quả đầu ra không chỉ là file bảng, mà là một **data mart phân tích**. Nó dùng để:

- Làm nguồn dữ liệu thống nhất cho phân tích revenue, margin, AOV, channel, promotion, geography.
- Đảm bảo các biểu đồ sau cùng một định nghĩa revenue/profit.
- Giúp kiểm soát rõ đơn hàng nào được tính là active, đơn nào bị loại.
- Chuẩn bị dữ liệu cho modeling nếu sau này cần tạo feature.

## 3. Module 12 - Target Overview

### Làm gì?

Phân tích target ở mức tổng quan:

- Revenue thay đổi theo ngày, tháng, năm.
- Rolling average 7 ngày và 30 ngày.
- Revenue theo thứ trong tuần.
- Heatmap revenue theo năm và tháng.
- COGS và gross profit đi cùng revenue như thế nào.
- Ngày nào có revenue bất thường.

### Vì sao cần?

Trước khi phân tích yếu tố ảnh hưởng, cần hiểu target tự nó đang có pattern gì. Nếu revenue có mùa vụ mạnh, trend tăng/giảm hoặc ngày bất thường, các phân tích khác phải được đọc trong bối cảnh đó.

Ví dụ:

- Nếu tháng 11-12 luôn cao, promotion trong giai đoạn đó có thể không phải nguyên nhân duy nhất.
- Nếu cuối tuần revenue cao hơn, channel analysis cần kiểm tra theo day-of-week.
- Nếu có ngày spike lớn, cần biết đó là chiến dịch thật hay lỗi dữ liệu.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Doanh thu có trend hay mùa vụ không?
- Giai đoạn nào là peak season?
- Có ngày bất thường cần giải thích không?
- Revenue và COGS có đi cùng nhau không?

Đây là phần mở đầu cho câu chuyện EDA. Nó giúp người đọc hiểu “target đang hoạt động như thế nào” trước khi đi vào nguyên nhân.

## 4. Module 13 - Product Drivers

### Làm gì?

Phân tích ảnh hưởng của sản phẩm đến revenue/profit:

- Revenue theo category.
- Revenue theo segment.
- Gross margin theo category.
- Gross margin theo segment x category.
- Top sản phẩm theo revenue.
- Sản phẩm revenue cao nhưng margin thấp.
- Size/color nào bán nhiều hoặc có return cao nếu nối thêm returns.

### Vì sao cần?

Trong e-commerce thời trang, sản phẩm là driver trực tiếp của doanh thu. Không chỉ cần biết bán được bao nhiêu, mà còn phải biết bán cái gì và lời bao nhiêu.

Một category có revenue cao chưa chắc tốt nếu margin thấp. Một segment margin cao nhưng volume thấp có thể là cơ hội tăng trưởng.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Category nào kéo revenue chính?
- Segment nào sinh lời tốt?
- Có nhóm sản phẩm nào bán nhiều nhưng biên lợi nhuận thấp không?
- Nên ưu tiên sản phẩm nào trong chiến dịch marketing hoặc tồn kho?

Đây là nền cho khuyến nghị kiểu:

- Tăng tập trung vào category có revenue cao và margin tốt.
- Xem lại pricing/discount cho nhóm revenue cao nhưng margin thấp.
- Đẩy sản phẩm margin cao qua kênh phù hợp.

## 5. Module 14 - Geography & Customer Drivers

### Làm gì?

Phân tích ảnh hưởng của khu vực và khách hàng:

- Revenue theo region.
- Revenue theo city.
- AOV theo region/city.
- Region x category revenue heatmap.
- Region x segment margin heatmap.
- Khu vực nào mua nhiều category/segment nào.
- Revenue theo age_group, gender, acquisition_channel.
- Customer segment nào có AOV hoặc order count cao.

### Vì sao cần?

Doanh thu không chỉ phụ thuộc sản phẩm mà còn phụ thuộc nơi bán và ai mua. Với dữ liệu Việt Nam, region/city có thể cho thấy khác biệt về nhu cầu thời trang, sức mua, kênh tiếp cận và logistics.

Ví dụ:

- Một region có revenue cao nhưng margin thấp có thể do hay dùng discount.
- Một city có AOV cao có thể phù hợp với premium products.
- Một age_group có order count cao nhưng AOV thấp cần chiến lược bundle/upsell.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Khu vực nào đóng góp revenue lớn nhất?
- Khu vực nào mua nhiều sản phẩm thuộc category nào?
- Nhóm khách hàng nào đáng ưu tiên?
- Có sự khác biệt rõ giữa region/city/age_group không?

Đây là phần rất hữu ích cho khuyến nghị:

- Cá nhân hóa sản phẩm theo khu vực.
- Phân bổ tồn kho theo region-category.
- Chạy campaign riêng cho nhóm khách hàng/khu vực có tiềm năng.

## 6. Module 15 - Promotion Drivers

### Làm gì?

Phân tích ảnh hưởng của khuyến mãi đến revenue và margin:

- Revenue của item/order có promo so với không promo.
- Gross margin của promo vs non-promo.
- Promo type nào hiệu quả hơn: percentage hay fixed.
- Campaign nào tạo revenue cao nhất.
- Campaign nào làm margin giảm mạnh.
- Category nào phụ thuộc nhiều vào khuyến mãi.
- Promo channel nào đem lại revenue tốt.

### Vì sao cần?

Khuyến mãi có thể tăng doanh thu nhưng làm giảm lợi nhuận. Nếu chỉ nhìn revenue, dễ kết luận sai rằng campaign tốt, trong khi margin bị bào mòn.

Cần phân tích cả:

- Revenue uplift.
- Discount cost.
- Gross margin.
- Category hưởng lợi.
- Channel hiệu quả.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Promo có thật sự giúp tăng revenue không?
- Loại promo nào tốt hơn cho lợi nhuận?
- Campaign nào nên nhân rộng?
- Campaign nào cần điều chỉnh vì làm giảm margin?
- Category nào nên hoặc không nên dùng discount mạnh?

Đây là nền cho khuyến nghị:

- Tối ưu discount theo category.
- Ưu tiên campaign có revenue cao nhưng vẫn giữ margin.
- Giảm promo ở nhóm sản phẩm vốn đã bán tốt không cần giảm giá.

## 7. Module 16 - Channel & Payment Drivers

### Làm gì?

Phân tích kênh bán, thiết bị và thanh toán:

- Revenue theo `order_source`.
- Revenue theo `device_type`.
- Revenue theo `payment_method`.
- AOV theo từng kênh.
- Margin theo từng kênh.
- Channel share theo thời gian.
- Payment method nào gắn với đơn hàng giá trị cao.

### Vì sao cần?

Kênh mua hàng ảnh hưởng đến revenue và hành vi khách hàng. Một kênh có nhiều đơn chưa chắc tạo revenue tốt nếu AOV thấp. Một payment method có ít đơn nhưng AOV cao có thể là nhóm khách hàng giá trị.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Kênh nào tạo revenue chính?
- Thiết bị nào có AOV cao hơn?
- Payment method nào liên quan đến đơn giá trị cao?
- Channel mix có thay đổi theo thời gian không?

Đây là nền cho khuyến nghị:

- Tối ưu marketing budget theo channel.
- Tối ưu trải nghiệm mobile/desktop.
- Thiết kế ưu đãi thanh toán cho nhóm có AOV cao.

## 8. Module 17 - Web Traffic Drivers

### Làm gì?

Phân tích quan hệ giữa web traffic và revenue:

- Sessions theo thời gian.
- Page views theo thời gian.
- Revenue vs sessions.
- Revenue vs unique visitors.
- Bounce rate vs revenue.
- Revenue theo traffic_source.
- Lag correlation: traffic hôm nay/hôm trước có liên quan revenue không.

### Vì sao cần?

Web traffic là tín hiệu đầu vào của demand. Nếu sessions tăng nhưng revenue không tăng, có thể conversion thấp. Nếu bounce rate cao đi cùng revenue thấp, cần kiểm tra chất lượng traffic hoặc landing page.

Lag correlation cũng quan trọng vì traffic có thể dẫn revenue sau 1-3 ngày.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Traffic có đi cùng revenue không?
- Nguồn traffic nào đáng giá?
- Bounce rate có ảnh hưởng xấu đến revenue không?
- Traffic có thể dùng làm chỉ báo sớm cho forecasting không?

Đây là nền cho:

- Đề xuất tối ưu marketing channel.
- Đề xuất cải thiện conversion.
- Tạo feature cho forecasting model.

## 9. Module 18 - Inventory & Operations Drivers

### Làm gì?

Phân tích ảnh hưởng của tồn kho và vận hành:

- Stockout theo category/segment.
- Overstock theo category/segment.
- Reorder flag theo sản phẩm.
- Units sold vs stockout_days.
- Fill rate theo category.
- Days of supply theo segment.
- So sánh monthly inventory với monthly revenue hoặc units sold.

### Vì sao cần?

Doanh thu không chỉ do demand, mà còn do khả năng đáp ứng hàng. Nếu sản phẩm bán tốt nhưng stockout nhiều, revenue có thể bị mất. Nếu overstock cao, vốn bị kẹt ở sản phẩm bán chậm.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Category nào bị stockout nhiều?
- Stockout có thể làm mất revenue ở đâu?
- Segment nào bị overstock?
- Sản phẩm nào cần reorder sớm?

Đây là nền cho khuyến nghị:

- Phân bổ tồn kho theo region/category.
- Ưu tiên nhập hàng cho nhóm có demand cao và stockout cao.
- Giảm tồn kho cho nhóm overstock nhưng sell-through thấp.

## 10. Module 19 - Returns, Reviews & Satisfaction Drivers

### Làm gì?

Phân tích return, refund và review:

- Return rate theo category.
- Return rate theo size.
- Return reason phổ biến.
- Refund amount theo reason/category.
- Rating distribution theo category/segment.
- Rating thấp có liên quan đến return không.
- Khu vực hoặc sản phẩm nào có return cao.

### Vì sao cần?

Return và review ảnh hưởng trực tiếp đến revenue net, customer satisfaction và chi phí vận hành. Một category revenue cao nhưng return cao có thể không thật sự tốt.

Đặc biệt với thời trang, size và expectation mismatch thường là nguyên nhân quan trọng.

### Kết quả đầu ra dùng để làm gì?

Kết quả giúp trả lời:

- Nhóm sản phẩm nào gây return nhiều?
- Lý do return chính là gì?
- Return có làm giảm hiệu quả revenue không?
- Rating có phản ánh vấn đề sản phẩm không?

Đây là nền cho khuyến nghị:

- Cải thiện size guide.
- Kiểm soát chất lượng sản phẩm.
- Điều chỉnh mô tả sản phẩm.
- Giảm refund/return ở category rủi ro cao.

## 11. Module 20 - Target Driver Summary

### Làm gì?

Gom toàn bộ kết quả từ các module 12-19 thành một bảng/tài liệu tổng hợp driver ảnh hưởng đến target.

Mỗi dòng nên ghi:

- Nhóm driver: product, geography, promotion, channel, traffic, inventory, returns.
- Driver cụ thể: category, region, promo_type, order_source...
- Metric chính: revenue, margin, AOV, return rate.
- Kết quả nổi bật.
- Ý nghĩa kinh doanh.
- Hướng hành động hoặc phân tích tiếp.

### Vì sao cần?

Nếu chỉ có nhiều biểu đồ rời rạc, rất khó viết report. Module này biến output phân tích thành insight có cấu trúc.

Nó giúp chọn biểu đồ nào đáng đưa vào report và biểu đồ nào chỉ dùng để tham khảo.

### Kết quả đầu ra dùng để làm gì?

Kết quả là một bản đồ insight:

- Driver nào ảnh hưởng target rõ nhất.
- Evidence nằm ở phân tích nào.
- Insight nào có thể chuyển thành recommendation.
- Phần nào nên đưa vào báo cáo cuối.

Đây là cầu nối từ EDA sang storytelling.

## 12. Thứ tự triển khai đề xuất

Nên triển khai theo thứ tự:

```text
11_prepare_analysis_tables.py
12_target_overview.py
13_product_drivers.py
14_geography_customer_drivers.py
15_promotion_drivers.py
16_channel_payment_drivers.py
17_web_traffic_drivers.py
18_inventory_operations_drivers.py
19_returns_reviews_drivers.py
20_target_driver_summary.py
```

Không nên làm module 12-19 trước khi có module 11, vì các phân tích sâu cần cùng một bảng chuẩn và cùng một định nghĩa revenue/profit.

## 13. Phần code A1-A5 đã gửi nằm ở đâu?

Đoạn A1-A5 thuộc các module sau:

- A1 Revenue Trend: thuộc `12_target_overview.py`.
- A2 Gross Margin: thuộc `13_product_drivers.py`.
- A3 AOV & Order Mix: thuộc `12_target_overview.py` hoặc một phần của `16_channel_payment_drivers.py`, nhưng nên đặt gần target overview.
- A4 Revenue by Channel: thuộc `16_channel_payment_drivers.py`.
- A5 Revenue Reconcile: thuộc `11_prepare_analysis_tables.py` hoặc một module validation riêng trước khi phân tích sâu.

Nếu triển khai sạch, A5 nên chạy sớm để kiểm tra định nghĩa revenue giữa `sales.csv` và transaction data trước khi dùng transaction data để phân tích revenue.

## 14. Câu hỏi cần trả lời sau giai đoạn này

Sau khi hoàn thành các module trên, phải trả lời được:

- Revenue đến chủ yếu từ category/segment nào?
- Khu vực nào tạo revenue/AOV/margin tốt?
- Nhóm khách hàng nào có giá trị cao?
- Campaign/promotion nào hiệu quả thật sự?
- Channel nào đem lại revenue và margin tốt?
- Web traffic có liên quan đến revenue không?
- Inventory có đang giới hạn doanh thu không?
- Return/review đang làm giảm hiệu quả ở nhóm nào?
- 3-5 insight nào đủ mạnh để đưa vào report?
- Recommendation nào có thể viết dựa trên số liệu?

## 15. Đích của giai đoạn này

Đích không chỉ là có biểu đồ. Đích là có một bảng insight rõ:

```text
Driver -> Evidence -> Business meaning -> Recommendation
```

Ví dụ:

```text
Region A mua nhiều category X
-> Evidence: region-category heatmap
-> Meaning: nhu cầu category X tập trung ở Region A
-> Recommendation: ưu tiên inventory và campaign category X tại Region A
```

Khi có được dạng này, phần EDA sẽ chuyển từ “vẽ biểu đồ” sang “kể chuyện bằng dữ liệu”.
