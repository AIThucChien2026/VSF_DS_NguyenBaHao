# Exploratory Data Analysis (EDA) - Giải mã hành vi trả hàng
## Mục tiêu
- Phân tích khám phá dữ liệu để tìm ra các mô thức trả hàng của khách hàng.
- Kiểm chứng các giả thuyết nghiệp vụ về hành vi mua sắm, đặc trưng sản phẩm, giao dịch, và tính mùa vụ.
- Đúc kết thông tin quan trọng chuẩn bị cho bước Feature Engineering và Modeling.

## Quy trình phân tích (EDA Process)
- **Phase 0**: Setup & Tích hợp dữ liệu (Temporary Flat Join). 
- **Phase 1**: Phân tích đơn biến (Univariate Analysis). 
- **Phase 2**: Phân tích lưỡng biến với Target (Bivariate Analysis). 
- **Phase 3**: Kiểm chứng Giả thuyết 1 - Chân dung Khách hàng & Hành vi. 
- **Phase 4**: Kiểm chứng Giả thuyết 2 - Đặc trưng Sản phẩm (Product Features). 
- **Phase 5**: Kiểm chứng Giả thuyết 3 - Phương thức thanh toán & Thiết bị mua sắm. 
- **Phase 6**: Kiểm chứng Giả thuyết 4 - Giá trị & Quy mô đơn hàng. 
- **Phase 7**: Kiểm chứng Giả thuyết 5 - Yếu tố Thời gian & Mùa vụ. 
- **Phase 8**: Tổng hợp Insight cho Feature Engineering. 

## Phase 0 - Setup & Tích hợp dữ liệu
### Mục tiêu
- Load các bảng dữ liệu đã được làm sạch cơ bản.
- Xử lý các khóa trùng lặp trước khi thực hiện liên kết.
- Thực hiện join tạm thời các bảng lại thành một bảng master duy nhất trên bộ nhớ (RAM) phục vụ vẽ biểu đồ.

### Việc cần làm
- Load thư viện `pandas`, `numpy`, `matplotlib`, `seaborn`.
- Đọc các bảng: `orders`, `order_items`, `customers`, `products`, `payments`.
- Loại bỏ các dòng duplicate trong `order_items` dựa trên tổ hợp `['order_id', 'product_id']`.
- Tạo cột nhãn mục tiêu `returned_label` (1: Trả hàng, 0: Đã giao thành công).
- Ép kiểu ngày tháng cho các cột datetime.
- Thực hiện `merge` các bảng lại theo luồng logic từ `orders` làm trung tâm.

## Kết luận Phase 0
- Đã load 5 bảng dữ liệu đầu vào chính: `orders`, `order_items`, `customers`, `products`, `payments`.
- Đã tạo nhãn mục tiêu `returned_label`: `1 = returned`, `0 = delivered`.
- Label audit từ `orders`:
  - `delivered`: 516,716 dòng.
  - `returned`: 36,142 dòng.
  - Trạng thái khác / không dùng làm label: 94,087 dòng.
- Các trạng thái đơn hàng khác không dùng làm nhãn và được loại khỏi EDA có target.
- Đã xử lý duplicate key trong `order_items` để tránh nhân dòng sai khi merge.
- Bảng dữ liệu liên kết tạm thời (`df_master`) được tạo từ `orders` làm trung tâm, sau đó merge với `customers`, `order_items`, `products`, `payments`.
- Shape audit:
  - Trước khi drop `returned_label` rỗng: `(714653, 35)`.
  - Sau khi drop `returned_label` rỗng: `(610906, 35)`.
- Baseline Return Rate sau khi lọc label hợp lệ khoảng **6.54%**, dùng làm mốc so sánh cho các phase sau.

**Cần làm tiếp:** Tiếp tục với các Phase còn lại (5–8) — phần trọng tâm của phiên làm việc hôm nay.

---
## Phase 1 - Phân tích đơn biến (Univariate Analysis)
### Mục tiêu
- Khảo sát hình dạng phân phối, biên độ giá trị và xu hướng tập trung của từng cột dữ liệu đơn lẻ.
- Phát hiện các bất thường về phân phối (lệch, mất cân bằng nhóm danh mục) có thể ảnh hưởng đến mô hình.

### Việc cần làm
- Vẽ Histogram + KDE cho các biến số liên tục: `unit_price`, `quantity`, `discount_amount`, `payment_value`; riêng tuổi dùng `age_group` ở phần biến danh mục.
- Vẽ Countplot cho các biến danh mục: `category`, `gender`, `acquisition_channel`, `device_type`.
- Lưu biểu đồ vào `figures/`.

## Kết luận Phase 1
- **Biến số liên tục:** `unit_price` và `payment_value` thường lệch phải (right-skewed). Cân nhắc log-transform cho các thuật toán nhạy cảm với outlier.
- `discount_amount` tập trung rất nhiều ở giá trị 0.
- Tuổi khách hàng (`age`) phân bố tương đối đều.
- **Biến danh mục:** `gender` cân bằng. Các cột `acquisition_channel`, `device_type`, `category` phân bổ lành mạnh.

**Ý nghĩa DS:** Nắm phân phối đơn biến giúp lên chiến lược chuẩn bị: biến nào cần Log-transform, biến nào có outlier cần xử lý.

**Cần làm tiếp:** Phân tích lưỡng biến với Target ở Phase 2.

---
## Phase 2 - Phân tích lưỡng biến với Nhãn (Bivariate Analysis with Target Label)
### Mục tiêu
- Đánh giá sơ bộ mối quan hệ giữa từng biến độc lập với nhãn mục tiêu `returned_label`.
- Phát hiện các biến có sự phân tách rõ rệt giữa nhóm Delivered (0) và Returned (1).

### Việc cần làm
- Vẽ Boxplot so sánh sơ bộ các biến số theo 2 nhóm Delivered/Returned: `unit_price`, `payment_value`, `quantity`, `discount_amount`.
- Lưu biểu đồ kiểm tra nhanh vào thư mục `figures/`.
- Ghi chú: `quantity` và `discount_amount` chỉ kiểm tra nhanh ở Phase 2; phân tích kỹ hơn sẽ nằm ở Phase 6.
- Ghi chú: `category` không phân tích ở Phase 2 để tránh trùng với Phase 4 - Đặc trưng sản phẩm.

## Kết luận Phase 2
- **Biến số liên tục:** `unit_price`, `payment_value`, `quantity`, `discount_amount` không cho thấy sự tách biệt rõ ràng giữa Delivered và Returned khi xem riêng lẻ.
- `unit_price` và `payment_value` vẫn lệch phải, nên nếu đưa sang Feature Engineering thì nên cân nhắc log-transform hoặc bucket theo quantile.
- `quantity` và `discount_amount` chỉ được xem nhanh ở đây để không bỏ sót biến giao dịch cơ bản; phần kết luận chính sẽ nằm ở Phase 6.
- `category` được để dành cho Phase 4 vì đây là đặc trưng sản phẩm.

**Ý nghĩa DS:** Phase 2 chưa tìm thấy biến số đơn lẻ nào tách nhãn thật mạnh. Các phase sau sẽ kiểm tra có định hướng hơn theo khách hàng, sản phẩm, thanh toán, giá trị đơn hàng và thời gian.

**Cần làm tiếp:** Kiểm chứng Giả thuyết 1 ở Phase 3.

---
## Phase 3 - Kiểm chứng Giả thuyết 1: Chân dung Khách hàng & Hành vi (Customer Profile)
### Mục tiêu
- Kiểm chứng: *"Khách hàng mới có xu hướng trả hàng nhiều hơn khách hàng lâu năm."*
- Khảo sát ảnh hưởng của Nhóm tuổi (`age_group`) và Giới tính (`gender`) lên Return Rate.

### Việc cần làm
- Dùng `customer_tenure_days` đã tạo ở Phase 0, chia thành 4 nhóm thâm niên.
- Vẽ Return Rate theo Nhóm thâm niên.
- Vẽ Return Rate chéo theo Nhóm tuổi × Giới tính.

## Kết luận Phase 3
- **Thâm niên khách hàng:** Return Rate giữa các nhóm thâm niên chỉ dao động quanh baseline khoảng **6.4%-6.8%**. Nhóm `30-180 days` nhỉnh hơn nhẹ, nhưng không đủ để kết luận khách mới là driver mạnh.
- **Tuổi & Giới tính:** Đa số nhóm `age_group × gender` vẫn quanh baseline. Một vài ô cao hơn có thể do quy mô nhóm nhỏ hơn, nên chỉ nên xem là tín hiệu yếu.

**Ý nghĩa DS:** `customer_tenure_days` và `tenure_group` nên giữ ở mức **Medium / Supporting** vì dễ hiểu và có ý nghĩa nghiệp vụ. `age_group`, `gender` chỉ nên để **Low / Experimental**.

**Cần làm tiếp:** Phase 4 — kiểm chứng Giả thuyết 2 (Size, Color, Category).

---
## Phase 4 - Kiểm chứng Giả thuyết 2: Đặc trưng Sản phẩm (Product Features)
### Mục tiêu
- Kiểm chứng: *"Một số đặc trưng sản phẩm như ngành hàng, phân khúc, size, color hoặc SKU cụ thể có liên quan tới tỷ lệ trả hàng hay không."*
- Tránh kết luận quá mạnh nếu Return Rate chỉ dao động nhẹ quanh baseline khoảng **6.5%**.

### Việc cần làm
- Phân tích Top sản phẩm có Return Rate cao nhất, có lọc ngưỡng số đơn tối thiểu để tránh nhiễu.
- Tính Return Rate theo `category` và `segment`.
- Return Rate theo `size` (S, M, L, XL).
- Return Rate theo `color`.
- Vẽ heatmap tương tác nhẹ: `gender × category` và `category × size`.
- Lưu biểu đồ và bảng thống kê.
- Ghi chú: không thêm `product_age_days` vì dữ liệu không có ngày tạo sản phẩm.
- Ghi chú: `product_historical_return_rate` là feature nâng cao, chỉ dùng nếu tính bằng lịch sử quá khứ để tránh leakage.

## Kết luận Phase 4
- **Category:** Return Rate giữa các ngành hàng khá gần nhau: `GenZ` khoảng **6.69%**, `Outdoor` khoảng **6.64%**, `Streetwear` khoảng **6.49%**, `Casual` khoảng **6.37%**. Chênh lệch nhỏ, nên `category` chưa phải driver mạnh nếu xét đơn lẻ.
- **Segment:** Return Rate dao động hẹp, khoảng **6.32%-6.69%**. Không có phân khúc nào nổi bật bất thường.
- **Size:** Return Rate theo `size` dao động khoảng **6.47%-6.63%**, gần baseline.
- **Color:** Return Rate theo `color` dao động khoảng **6.36%-6.66%**, cũng gần baseline.
- **Tương tác:** `gender × category` và `category × size` có vài ô nhỉnh hơn, nhưng vẫn nên để **Low/Experimental**, không xem là kết luận chắc chắn.
- **SKU/Product cụ thể:** Top sản phẩm có Return Rate khoảng **10.7%-12.7%**, cao hơn baseline rõ hơn các thuộc tính chung. Đây là tín hiệu đáng chú ý nhất của Phase 4, nhưng nếu tạo feature cho model thì phải dùng lịch sử quá khứ để tránh leakage.

**Ý nghĩa DS:** Các thuộc tính sản phẩm đơn lẻ (`category`, `segment`, `size`, `color`) chỉ nên là feature hỗ trợ. Không nên kết luận size/color là nguyên nhân chính gây trả hàng. Tín hiệu sản phẩm đáng chú ý hơn nằm ở cấp SKU, nhưng phần này thuộc nhóm nâng cao vì cần chống leakage.

**Cần làm tiếp:** Phase 5 — Phương thức thanh toán & Thiết bị (Giả thuyết 3).

---
## Phase 5 - Kiểm chứng Giả thuyết 3: Phương thức thanh toán & Thiết bị mua sắm
### Mục tiêu
- Kiểm chứng phát biểu: *"Đơn hàng thanh toán bằng tiền mặt (`cod`) hoặc thực hiện trên thiết bị di động (`mobile`) và đến từ nguồn `social_media` có tỷ lệ trả hàng cao hơn do hành vi mua sắm bốc đồng."*

### Việc cần làm
- So sánh Return Rate theo `payment_method`: `credit_card`, `cod`, `paypal`, `bank_transfer`, `apple_pay`.
- So sánh Return Rate theo `device_type`: `desktop`, `mobile`, `tablet`.
- Phân tích Return Rate theo `order_source` (nguồn đơn hàng).
- Vẽ biểu đồ tổng hợp 3 chiều và lưu kết quả.

## Kết luận Phase 5
- **Phương thức thanh toán:** `cod` có Return Rate khoảng **11.37%**, cao rõ so với các phương thức khác chỉ quanh **5.8%**. Đây là tín hiệu mạnh nhất của Phase 5.
- **Thiết bị:** `desktop`, `mobile`, `tablet` đều quanh baseline khoảng **6.4%-6.6%**, không có thiết bị nào nổi bật bất thường.
- **Nguồn đơn hàng:** `order_source` dao động rất hẹp, khoảng **6.50%-6.61%**. `social_media` không cao hơn baseline.
- **Tương tác payment × device:** Nếu giữ, chỉ nên xem là interaction thử nghiệm; không diễn giải là driver chính nếu tín hiệu chủ yếu đến từ COD.

**Ý nghĩa DS:** Đề xuất `payment_method` là **High**, đặc biệt có thể tạo `is_cod`. `device_type` và `order_source` chỉ là **Medium / Supporting**; Phase 8 sẽ dùng biến gốc thay vì tạo thêm cờ riêng cho từng giá trị của thiết bị hoặc nguồn đơn.

**Cần làm tiếp:** Phase 5 tạm bỏ qua trong lượt chỉnh hiện tại; chuyển sang Phase 6 để phân tích Giá trị & Quy mô đơn hàng.

---
## Phase 6 - Kiểm chứng Giả thuyết 4: Giá trị & Quy mô đơn hàng (Order Value & Quantity)
### Mục tiêu
- Kiểm chứng phát biểu: *"Giá trị đơn hàng, số lượng sản phẩm và mức giảm giá có liên quan tới xác suất trả hàng hay không."*

### Việc cần làm
- Phân nhóm `payment_value` theo **quantile** thay vì ngưỡng cố định, vì giá trị thanh toán trong dữ liệu nằm trên thang đo lớn.
- Tính Return Rate cho từng nhóm giá trị đơn hàng và vẽ biểu đồ.
- Phân tích mối quan hệ giữa `quantity` và Return Rate.
- Phân tích ảnh hưởng của giảm giá bằng 2 cách dễ hiểu:
  - `is_discounted`: đơn có giảm giá hay không.
  - `discount_ratio = discount_amount / unit_price`: tỷ lệ giảm giá tương đối.
- Không thêm `price_vs_category_avg` ở v1 vì dễ làm Phase 6 bị rộng và trùng với Product Features.

## Kết luận Phase 6
- **Giá trị đơn hàng (`payment_value`)**: Sau khi chia theo quantile, Return Rate giữa 4 nhóm khá sát nhau: nhóm thấp nhất khoảng **6.69%**, nhóm thấp khoảng **6.63%**, nhóm cao khoảng **6.44%**, nhóm cao nhất khoảng **6.45%**. Nhóm giá trị thấp nhỉnh hơn nhẹ, nhưng chênh lệch nhỏ.
- **Số lượng sản phẩm (`quantity`)**: Return Rate theo quantity dao động quanh **6.50%-6.63%**, không có xu hướng tăng/giảm rõ ràng.
- **Giảm giá (`discount_amount`, `discount_ratio`)**: Đơn có giảm giá chỉ cao hơn đơn không giảm giá rất nhẹ: khoảng **6.57%** so với **6.54%**. Khi chia theo `discount_ratio`, các nhóm cũng chỉ quanh **6.54%-6.61%**.
- **Kết luận chung:** Giả thuyết “giá trị đơn hàng, quantity hoặc giảm giá ảnh hưởng mạnh đến trả hàng” **chưa được xác nhận rõ** qua EDA. Các biến này nên giữ làm feature hỗ trợ vì dễ hiểu và có ý nghĩa nghiệp vụ, nhưng không nên coi là driver chính.

**Feature đề xuất từ Phase 6:**
- `payment_value`, `log_payment_value`, `payment_value_quantile_bucket` - Medium / Supporting.
- `quantity` - Medium / Supporting.
- `is_discounted`, `discount_ratio` - Medium / Supporting.

**Ý nghĩa DS:** Phase 6 giúp học cách chọn bucket hợp lý theo phân phối dữ liệu. Không dùng ngưỡng tiền cố định nếu dữ liệu đang nằm ở scale khác hoàn toàn.

**Cần làm tiếp:** Phase 7 tạm bỏ qua theo yêu cầu hiện tại; phần còn lại cần đồng bộ Feature Summary ở Phase 8.

---
## Phase 7 - Kiểm chứng Giả thuyết 5: Yếu tố Thời gian & Mùa vụ (Time & Seasonality)
### Mục tiêu
- Kiểm chứng phát biểu: *"Tỷ lệ trả hàng tăng mạnh vào các mùa mua sắm cao điểm (cuối năm, dịp lễ) do vận chuyển chậm hoặc mua quà không phù hợp."*

### Việc cần làm
- Trích xuất từ `order_date`: `order_month`, `order_day_of_week`, `order_quarter`, `is_weekend`.
- Vẽ biểu đồ đường xu hướng Return Rate theo từng tháng (12 tháng).
- Phân tích Return Rate theo thứ trong tuần (Monday-Sunday).
- So sánh Return Rate giữa cuối tuần (Sat, Sun) vs ngày thường.
- Vẽ heatmap Return Rate theo Tháng × Thứ.

## Kết luận Phase 7
- **Theo tháng:** Return Rate dao động nhẹ, khoảng **6.28%-6.79%**. Tháng 10 cao nhất nhẹ, nhưng không tạo điểm nóng đủ rõ.
- **Theo quý:** Q3 khoảng **6.67%**, Q4 khoảng **6.57%**. Vì Q4 không cao nhất, giả thuyết mùa cao điểm cuối năm chưa được xác nhận.
- **Theo thứ trong tuần:** Dao động nhẹ quanh baseline, khoảng **6.48%-6.65%**.
- **Cuối tuần:** Không có bằng chứng đủ mạnh để xem `is_weekend` là driver chính.

**Ý nghĩa DS:** Calendar features như `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend`, `is_q4` chỉ nên để **Low / Experimental**. Không thêm `order_hour` vì dữ liệu chỉ có `order_date`, không có giờ.

**Cần làm tiếp:** Tổng hợp toàn bộ insight vào Phase 8 — danh sách feature cho bước tiếp theo.

---
## Phase 8 - Tổng hợp Insight cho Feature Engineering
### Mục tiêu
- Đúc kết tất cả insight từ Phase 3–7 thành một bản đồ ánh xạ:
  - `Giả thuyết → Insight quan sát được → Feature cần tạo → Mức độ ưu tiên`
- Chuẩn bị danh sách feature chính thức cho bước **Feature Engineering** tiếp theo.

### Quy ước Mức độ ưu tiên
- **High** — Tín hiệu EDA rõ hoặc có ý nghĩa nghiệp vụ rất mạnh; nếu là feature lịch sử thì phải tạo bằng dữ liệu quá khứ để tránh leakage.
- **Medium / Supporting** — Tín hiệu đơn lẻ yếu nhưng dễ hiểu, chi phí tạo thấp, nên giữ để model kiểm chứng.
- **Low / Experimental** — Tương tác hoặc calendar flag có tín hiệu chưa ổn định; chỉ thử nếu còn thời gian.

## Kết luận Phase 8 & Tổng kết EDA

### Tổng kết các Giả thuyết đã kiểm chứng

| Giả thuyết | Phát biểu | Kết quả | Insight chính |
|---|---|---|---|
| GS1 - Customer Profile | Khách mới / nhóm khách hàng khác nhau có Return Rate khác nhau | **Tín hiệu yếu / supporting** | `customer_tenure_days`, `tenure_group` giữ mức Medium; `age_group`, `gender` để Low/Experimental |
| GS2 - Product Features | Size/Color/Category gây trả hàng cao | **Thuộc tính đơn lẻ yếu; SKU-level mạnh hơn** | `category`, `segment`, `size`, `color` là Medium; top SKU cao hơn baseline nhưng phải tạo feature lịch sử quá khứ |
| GS3 - Payment & Device | COD tăng Return Rate; device/source cần kiểm chứng | **COD xác nhận rõ; device/source yếu** | `is_cod`, `payment_method` là High; `device_type`, `order_source` chỉ Supporting |
| GS4 - Order Value | Giá trị đơn, số lượng, giảm giá ảnh hưởng Return Rate | **Tín hiệu yếu / cần model kiểm chứng** | Dùng `payment_value_quantile_bucket`, `log_payment_value`, `quantity`, `discount_ratio`, `is_discounted` ở mức Medium |
| GS5 - Time & Seasonality | Q4/weekend tăng Return Rate | **Không xác nhận driver mạnh** | Calendar features chỉ Low/Experimental |

### Danh sách Feature ưu tiên cho bước tiếp theo

**High**
- `is_cod`, `payment_method`
- `product_historical_return_rate`, `is_high_return_product` — chỉ dùng nếu tính bằng lịch sử quá khứ / train-time encoding để tránh leakage.

**Medium / Supporting**
- `customer_tenure_days`, `tenure_group`
- `category`, `segment`, `size`, `color`
- `device_type`, `order_source`
- `payment_value`, `log_payment_value`, `payment_value_quantile_bucket`
- `quantity`, `discount_ratio`, `is_discounted`

**Low / Experimental**
- `age_group`, `gender`
- `gender_category_interaction`
- `category_size_interaction`
- `payment_device_interaction`
- `order_month`, `order_quarter`, `order_day_of_week`, `is_weekend`, `is_q4`

### Ghi chú chống hiểu nhầm cho người mới
- Không đưa `customer_tenure_days`, `category`, `device_type`, `order_source`, `payment_value_quantile_bucket` lên High chỉ vì chúng dễ tạo.
- Không tạo thêm cờ riêng cho từng giá trị của `device_type` hoặc `order_source` trong v1; Feature Summary hiện dùng biến gốc `device_type`, `order_source`.
- `product_historical_return_rate` không được tính bằng toàn bộ dữ liệu sau khi đã biết label; phải dùng lịch sử trước thời điểm đơn hàng.
- Các feature Medium/Low vẫn có thể hữu ích trong model, nhưng EDA chưa đủ để kết luận chúng là nguyên nhân chính.

---

**Bước tiếp theo:** Chuyển sang `3_Feature_Engineering.ipynb` để thực hiện tạo các feature đã đề xuất, scale dữ liệu và chuẩn bị training set cho bước Modeling.
