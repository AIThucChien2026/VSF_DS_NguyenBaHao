# Báo cáo EDA dữ liệu ADS

## 1. Mục tiêu

EDA được thực hiện sau bước check quality để hiểu dữ liệu ở cấp đơn hàng, quan sát phân bố nhãn returned/delivered và tìm các tín hiệu có thể hữu ích cho Feature Engineering.

Báo cáo này chọn câu chuyện phân tích là: **tìm các tín hiệu có sẵn tại thời điểm khách đặt hàng để nhận diện sớm rủi ro trả hàng**. Nghĩa là chỉ xem các biến có sẵn khi khách đặt hàng, không dùng dữ liệu hậu nghiệm từ bảng `returns`.

Báo cáo tập trung trả lời ba câu hỏi:

- Nhãn returned có phân bố như thế nào?
- Nhóm khách hàng, sản phẩm, thanh toán, thiết bị, giá trị đơn hàng và thời gian có khác biệt tỷ lệ return không?
- Những biến nào nên ưu tiên đưa sang Feature Engineering?

## 2. Câu chuyện theo biến và giả thuyết

Từ check quality, dữ liệu đã đủ điều kiện để phân tích: bảng load ổn, key liên bảng khớp và nhãn `returned_label` đã được xác định. Vì vậy, EDA đi theo câu hỏi: **những biến nào làm `returned_label = 1` xuất hiện nhiều hơn?**

Câu chuyện được chia thành 5 nhóm giả thuyết bám theo biến:

| Giả thuyết theo biến | Vì sao kiểm tra | Nhóm dữ liệu dùng |
|---|---|---|
| GS1 - `age_group`, `gender`, `tenure_group` | Kiểm tra nhóm khách hàng nào có return rate cao hơn | `customers`, `orders` |
| GS2 - `category`, `segment`, `size`, `color`, `product_id` | Kiểm tra thuộc tính sản phẩm nào gắn với return nhiều hơn | `products`, `order_items` |
| GS3 - `payment_method`, `is_cod`, `device_type`, `order_source` | Kiểm tra COD, thiết bị và nguồn đặt hàng có khác biệt return rate không | `orders`, `payments` |
| GS4 - `payment_value`, `quantity`, `discount_amount`, `discount_ratio` | Kiểm tra giá trị đơn, số lượng và khuyến mãi có liên quan đến return không | `payments`, `order_items` |
| GS5 - `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend` | Kiểm tra yếu tố thời gian/mùa vụ của đơn hàng | `orders.order_date` |

Các giả thuyết đều xuất phát từ nhóm biến có sẵn tại order time. Biến hậu nghiệm như `return_date`, `return_reason`, `refund_amount` không được dùng vì sẽ gây leakage.

## 3. Dữ liệu và nhãn phân tích

EDA sử dụng dữ liệu đã qua kiểm tra chất lượng, trong đó nhãn được hiểu như sau:

| Nhãn | Ý nghĩa | Số order |
|---:|---|---:|
| 0 | Delivered | 516,716 |
| 1 | Returned | 36,142 |
| NaN | Trạng thái khác, không dùng để tính return rate binary | 94,087 |

Tập phân tích returned/delivered có tỷ lệ returned khoảng 6.5%, cho thấy đây là bài toán mất cân bằng lớp (nhưng đúng với thực tế). Vì vậy, EDA ưu tiên so sánh return rate theo nhóm thay vì chỉ nhìn số lượng tuyệt đối.

## 4. Quy trình thực hiện

| Nhóm phân tích | Nội dung |
|---|---|
| Phân bố cơ bản | Phân bố biến số, biến category và nhãn returned |
| Sản phẩm | Category, segment, size, color và top sản phẩm có tỷ lệ return cao |
| Khách hàng | Age group, gender, tenure group |
| Thanh toán và thiết bị | Payment method, device type, order source, payment x device |
| Giá trị đơn hàng | Payment value, quantity, discount, discount ratio |
| Thời gian | Tháng, quý, ngày trong tuần, weekend |
| Tổng hợp feature | Xếp hạng tín hiệu High / Medium / Low để chuyển sang FE |

## 5. Kết quả phân tích chính

### 5.1 Phân bố dữ liệu và nhãn

Các biến đầu vào có đủ thông tin để phân tích ở cấp đơn hàng. Tỷ lệ returned thấp hơn nhiều so với delivered, vì vậy khi đánh giá mô hình sau này cần ưu tiên metric như PR-AUC, recall và F1.

![Categorical distributions](./eda_outputs/figures/eda_phase1_categorical_distributions.png)

### 5.2 Tín hiệu sản phẩm

Tỷ lệ return theo category chỉ chênh lệch nhẹ quanh baseline 6.5%.

| Category | Return rate |
|---|---:|
| GenZ | 6.69% |
| Outdoor | 6.64% |
| Streetwear | 6.49% |
| Casual | 6.37% |

![Return rate by category](./eda_outputs/figures/eda_phase2_return_rate_by_category.png)

Nhận xét: category đơn lẻ không phải tín hiệu quá mạnh, nhưng vẫn nên giữ làm feature hỗ trợ vì có ý nghĩa nghiệp vụ và chi phí encoding thấp.

Top sản phẩm có tỷ lệ return cao hơn baseline rõ rệt, khoảng 10.7% đến 12.7%. Tuy nhiên, các feature kiểu lịch sử return của sản phẩm cần xử lý rất cẩn thận để tránh target leakage.

![Top returned products](./eda_outputs/figures/eda_phase4_top10_returned_products.png)

### 5.3 Tín hiệu khách hàng

Age group và gender không tạo ra khác biệt mạnh. Một số nhóm nhỏ có return rate cao hơn nhưng chưa đủ để kết luận là driver độc lập.

![Return rate by age and gender](./eda_outputs/figures/eda_phase3_return_rate_by_age_gender.png)

Tenure group cũng chỉ dao động nhẹ:

| Tenure group | Return rate |
|---|---:|
| < 30 days | 6.56% |
| 30-180 days | 6.77% |
| 180-365 days | 6.42% |
| > 365 days | 6.55% |

![Return rate by tenure](./eda_outputs/figures/eda_phase3_return_rate_by_tenure.png)

Nhận xét: các biến khách hàng nên được giữ như feature hỗ trợ, không nên mô tả là tín hiệu mạnh nếu chỉ dựa trên EDA.

### 5.4 Thanh toán và thiết bị

Payment method là tín hiệu nổi bật nhất trong EDA. Đơn COD có return rate cao hơn rõ rệt so với các phương thức còn lại.

| Payment method | Return rate | Số order |
|---|---:|---:|
| COD | 11.37% | 84,099 |
| Bank transfer | 5.82% | 30,863 |
| PayPal | 5.80% | 92,872 |
| Apple Pay | 5.79% | 61,951 |
| Credit card | 5.78% | 341,121 |

![Payment and device impact](./eda_outputs/figures/eda_phase5_payment_and_device_impact.png)

Device type không khác biệt nhiều: desktop 6.58%, mobile 6.57%, tablet 6.42%. Do đó, device nên được xem là feature hỗ trợ, còn `is_cod` và `payment_method` là nhóm feature ưu tiên cao.

### 5.5 Giá trị đơn hàng và khuyến mãi

Discount group chỉ chênh lệch nhẹ:

| Discount group | Return rate | Số order |
|---|---:|---:|
| Không giảm | 6.54% | 374,684 |
| Giảm vừa | 6.83% | 2,269 |
| Giảm mạnh | 6.57% | 233,953 |

![Return rate by order value](./eda_outputs/figures/eda_phase6_return_rate_by_order_value.png)

Nhận xét: payment value, quantity, discount ratio và is_discounted vẫn nên dùng trong FE vì là biến giao dịch cơ bản, nhưng EDA không cho thấy đây là driver rất mạnh.

### 5.6 Thời gian và mùa vụ

Return rate theo tháng dao động nhẹ, khoảng 6.28% đến 6.79%. Tháng 10 cao nhất trong bảng EDA, tháng 6 thấp nhất, nhưng mức chênh lệch không lớn.

![Seasonality trend](./eda_outputs/figures/eda_phase7_seasonality_trend.png)

Nhận xét: calendar feature như `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend`, `is_q4` nên được đưa vào nhóm experimental hoặc supporting feature.

## 6. Tổng hợp feature candidate

EDA phân loại feature candidate theo mức ưu tiên:

| Priority | Số feature candidate | Ghi chú |
|---|---:|---|
| High | 2 | `is_cod`, `payment_method`; nhóm lịch sử sản phẩm chỉ dùng nếu chống leakage tốt |
| Medium | 6 | Customer tenure, product descriptors, device/source, order value, quantity, discount |
| Low/Experimental | 6 | Interaction, calendar, age/gender và một số biến hỗ trợ |

![Feature priority summary](./eda_outputs/figures/eda_phase8_feature_priority_summary.png)

## 7. Đánh giá kết quả

EDA cho thấy dữ liệu có tín hiệu nhưng không quá mạnh. Tín hiệu rõ nhất là phương thức thanh toán COD. Các nhóm sản phẩm, khách hàng, giá trị đơn hàng và thời gian có chênh lệch nhưng phần lớn chỉ quanh baseline 6.5%.

Điều quan trọng nhất là không được dùng trực tiếp lịch sử return của sản phẩm nếu chưa có logic thời gian an toàn. Các feature như product historical return rate có vẻ mạnh trong EDA nhưng có nguy cơ leakage cao nếu tạo sai cách.

## 8. Kết luận

EDA đã hoàn thành vai trò định hướng cho Feature Engineering:

```text
Tín hiệu mạnh nhất: payment_method / is_cod
Tín hiệu hỗ trợ: product descriptors, customer tenure, order value, quantity, discount
Tín hiệu experimental: calendar, interaction, age/gender
Rủi ro chính: target leakage từ lịch sử return của sản phẩm
```

Dữ liệu đủ điều kiện chuyển sang Feature Engineering, với yêu cầu FE phải khóa leakage gate và chỉ dùng feature có sẵn tại thời điểm đặt hàng.
