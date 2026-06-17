# Giải thích quy trình chuẩn bị dữ liệu và phân tích feature

## 1. Mục đích của notebook

Notebook `perparation_data_update.ipynb` được dùng để chuẩn bị bảng dữ liệu theo ngày và phân tích feature cho bài toán dự báo `Revenue` và `COGS`.

Ở giai đoạn này, mục tiêu chưa phải là huấn luyện model cuối cùng. Mục tiêu chính là tạo một feature set hợp lý, giảm trùng lặp, tránh leakage và có bằng chứng rằng các feature được giữ có đóng góp cho dự báo.

Quy trình được thiết kế theo hướng:

- Tạo dữ liệu daily từ các bảng nguồn.
- Chỉ tạo feature có thể biết tại thời điểm dự báo.
- Lọc từ tập candidate lớn về tập feature gọn hơn để có thể phân tích sâu.
- Kết hợp EDA với wrapper time-aware, thay vì chỉ dựa vào cảm tính hoặc correlation.
- Xuất feature set cuối để dùng cho bước modeling tiếp theo.

## 2. Tư duy tổng thể

Nếu đưa tất cả feature vào modeling ngay, có ba rủi ro lớn:

- Quá nhiều biến trùng lặp, vì nhiều lag/rolling thực chất cùng đo một tín hiệu.
- Khó phân tích sâu, vì scatter, heatmap và kết luận sẽ bị rối.
- Dễ bị leakage nếu vô tình dùng thông tin cùng ngày với target.

Vì vậy quy trình chọn feature đi theo ba lớp lọc:

1. Lọc về mặt logic thời gian: feature phải là known-now hoặc lagged.
2. Lọc về mặt EDA: feature phải có chất lượng dữ liệu và có quan hệ hợp lý với target.
3. Lọc bằng validation: feature hoặc nhóm feature phải làm giảm lỗi dự báo trên rolling-origin.

EDA giúp hiểu dữ liệu, nhưng không nên là căn cứ duy nhất để chọn feature. Wrapper time-aware được bổ sung để trả lời câu hỏi quan trọng hơn: sau khi đã có baseline, feature này có làm model dự báo tốt hơn trên dữ liệu tương lai hay không.

## 3. Các khái niệm cần nắm khi báo cáo

### Quy ước ký hiệu và công thức chính

Khi trình bày báo cáo, các bước có tính toán nên nói rõ công thức để người nghe hiểu kết quả được tạo ra như thế nào. Ký hiệu chung:

- `t`: ngày đang cần tạo target/feature.
- `y_t`: giá trị target tại ngày `t`, ví dụ `Revenue_t` hoặc `COGS_t`.
- `x_t`: giá trị một feature/source signal tại ngày `t`.
- `y_hat_t`: giá trị model dự báo cho ngày `t`.
- `n`: số dòng/số ngày trong tập đánh giá.

Các công thức dùng trong notebook:

| Nhóm | Công thức | Ý nghĩa |
| :--- | :--- | :--- |
| Daily target | `Revenue_t = sum(Revenue trong ngày t)` | Tổng doanh thu theo ngày từ bảng `sales` |
| Daily target | `COGS_t = sum(COGS trong ngày t)` | Tổng giá vốn theo ngày từ bảng `sales` |
| Gross margin | `gross_margin_t = Revenue_t - COGS_t` | Lợi nhuận gộp theo ngày |
| Margin rate | `margin_rate_t = gross_margin_t / Revenue_t` nếu `Revenue_t != 0` | Tỷ lệ lợi nhuận gộp |
| Missing rate | `missing_pct = số ô missing / tổng số dòng * 100` | Đo mức thiếu dữ liệu của feature |
| Lag | `x_lag_k(t) = x(t-k)` | Lấy giá trị quá khứ cách `k` ngày |
| Rolling mean leakage-safe | `rolling_mean_w(t) = (x(t-1) + ... + x(t-w)) / w` | Trung bình `w` ngày quá khứ, không dùng ngày `t` |
| Absolute error | `abs_error_t = abs(y_t - y_hat_t)` | Sai số tuyệt đối từng ngày |
| MAE | `MAE = mean(abs(y_t - y_hat_t))` | Sai số tuyệt đối trung bình |
| RMSE | `RMSE = sqrt(mean((y_t - y_hat_t)^2))` | Phạt nặng hơn các ngày sai lớn |
| WAPE | `WAPE = sum(abs(y_t - y_hat_t)) / sum(abs(y_t))` | Tổng sai số tuyệt đối so với tổng actual |
| Cải thiện tương đối | `(WAPE_baseline - WAPE_model) / WAPE_baseline * 100` | Model giảm lỗi bao nhiêu phần trăm so với baseline |

Nếu có chuẩn hóa feature trong bước model, công thức chuẩn hóa dùng thống kê của **train set**:

```text
x_scaled = (x - mean_train) / std_train
```

Không được fit `mean` và `std` trên cả train + test, vì như vậy test đã ảnh hưởng vào quá trình train và tạo leakage nhẹ.

### Leakage-safe

Leakage là việc dùng thông tin mà tại thời điểm dự báo thực tế chưa thể biết. Nếu có leakage, model có thể cho kết quả validation đẹp nhưng sẽ kém khi áp dụng thật.

Trong notebook này, feature được xem là leakage-safe nếu thuộc một trong hai nhóm:

- Known-now: biết trước hoặc biết ngay tại thời điểm dự báo, ví dụ `month`, `day_of_week`, lịch khuyến mãi nếu đã có kế hoạch.
- Lagged: được shift về quá khứ, ví dụ `Revenue_lag_1d`, `order_count_lag_1d`.

Same-day operational feature không được dùng trực tiếp vì có thể chưa biết khi cần dự báo doanh thu trong ngày.

### Lag

Lag là giá trị quá khứ của một biến. Ví dụ `Revenue_lag_1d` là doanh thu của ngày trước đó.

Công thức:

```text
Revenue_lag_1d(t) = Revenue(t-1)
order_count_lag_1d(t) = order_count(t-1)
```

Ý nghĩa:

- Bắt tính liên tục theo thời gian.
- Nếu doanh thu hôm qua cao, doanh thu hôm nay thường có xu hướng liên quan.
- Rất hữu ích cho dự báo chuỗi thời gian ngắn hạn.

Lý do dùng lag:

- Tránh leakage vì chỉ dùng thông tin quá khứ.
- Tạo baseline mạnh cho bài toán forecasting.

### Rolling

Rolling là thống kê trượt trên một khoảng ngày quá khứ. Ví dụ `review_count_rolling_7d_mean` là trung bình số review trong 7 ngày trước đó.

Công thức leakage-safe:

```text
review_count_rolling_7d_mean(t)
= mean(review_count(t-1), review_count(t-2), ..., review_count(t-7))
```

Điểm quan trọng là rolling phải tính từ `t-1` trở về trước, không được tính cả `t`.

Ý nghĩa:

- Làm mượt biến động ngày lẻ.
- Bắt xu hướng ngắn hạn hoặc dài hạn.
- Giảm ảnh hưởng của ngày bất thường.

Một số window thường gặp:

- Rolling 7 ngày: bắt tín hiệu ngắn hạn theo tuần.
- Rolling 30 ngày: bắt xu hướng trung hạn.
- Rolling 90 ngày: bắt xu hướng dài hơn.

Trong notebook, rolling vẫn phải được shift/leakage-safe, tức là chỉ tính từ dữ liệu quá khứ.

### Spearman correlation

Spearman đo mức độ quan hệ đơn điệu giữa feature và target. Nó không yêu cầu quan hệ phải thẳng tuyến tính.

Công thức ý tưởng:

```text
Spearman(x, y) = Pearson(rank(x), rank(y))
```

Tức là Spearman không tính trực tiếp trên giá trị gốc, mà tính Pearson correlation trên thứ hạng của giá trị. Vì vậy nó phù hợp hơn Pearson khi dữ liệu bị lệch, có outlier hoặc quan hệ tăng/giảm nhưng không thẳng tuyến tính.

Nếu Spearman dương:

- Feature tăng thì target có xu hướng tăng.

Nếu Spearman âm:

- Feature tăng thì target có xu hướng giảm.

Nếu dùng `abs_spearman`:

- Lấy trị tuyệt đối để xếp hạng độ mạnh của quan hệ.
- Dấu âm/dương vẫn cần xem riêng khi cần hiểu chiều tác động.

Ví dụ `Revenue_abs_spearman` là độ mạnh quan hệ Spearman giữa feature và `Revenue`, không quan tâm chiều âm hay dương.

Lưu ý khi báo cáo:

- Spearman cao không có nghĩa là feature chắc chắn nên giữ.
- Spearman chỉ cho thấy quan hệ riêng lẻ.
- Nếu feature trùng lặp với feature khác, nó có thể không còn đóng góp thêm trong model.

### WAPE

WAPE là Weighted Absolute Percentage Error. Công thức ý tưởng là tổng sai số tuyệt đối chia cho tổng giá trị thực tế.

Công thức:

```text
WAPE = sum(abs(y_t - y_hat_t)) / sum(abs(y_t))
```

Ý nghĩa:

- WAPE càng thấp thì model càng tốt.
- WAPE 0.20 có thể hiểu là tổng sai số tuyệt đối bằng khoảng 20% tổng actual.
- WAPE phù hợp khi target là doanh thu/chi phí vì đo lỗi theo quy mô tổng.

Trong notebook, WAPE được dùng làm metric chính vì `Revenue` và `COGS` là các đại lượng tiền tệ có quy mô lớn.

### MAE

MAE là Mean Absolute Error, tức sai số tuyệt đối trung bình.

Công thức:

```text
MAE = (1/n) * sum(abs(y_t - y_hat_t))
```

Ý nghĩa:

- Cho biết trung bình model sai bao nhiêu đơn vị tiền mỗi ngày.
- Dễ hiểu về mặt business.

Trong kết quả hiện tại:

- MAE của `Revenue` giảm từ khoảng 758,319 xuống 673,235.
- MAE của `COGS` giảm từ khoảng 659,087 xuống 586,174.

### RMSE

RMSE là Root Mean Squared Error, tức căn bậc hai của trung bình bình phương sai số.

Công thức:

```text
RMSE = sqrt((1/n) * sum((y_t - y_hat_t)^2))
```

Ý nghĩa:

- RMSE phạt mạnh các ngày dự báo sai lớn.
- Nếu RMSE cao hơn MAE nhiều, nghĩa là có một số ngày model lệch rất mạnh.

### Rolling-origin validation

Rolling-origin validation là cách đánh giá theo thời gian. Model được train trên quá khứ và validate trên một giai đoạn tương lai.

Trong notebook, validation theo năm:

- Train trên các năm trước.
- Validate trên năm tiếp theo.
- Lặp lại cho các năm 2018, 2019, 2020, 2021, 2022.

Ý nghĩa:

- Gần với cách model sẽ được dùng thật trong forecasting.
- Giảm rủi ro đánh giá sai do trộn dữ liệu quá khứ và tương lai.
- Tốt hơn random split cho bài toán chuỗi thời gian.

### Wrapper time-aware

Wrapper time-aware là bước dùng model validation để thử thêm feature theo nhóm.

Tư duy:

- Bắt đầu từ baseline an toàn.
- Thử thêm từng nhóm feature.
- Nếu nhóm đó làm giảm WAPE đủ rõ trên rolling-origin thì giữ.
- Nếu không cải thiện hoặc làm tệ hơn thì loại.

Wrapper này không thay thế modeling cuối cùng. Nó là bộ lọc giúp feature set có bằng chứng dự báo, thay vì chỉ dựa vào EDA.

Trong wrapper, điểm cải thiện của một nhóm feature được tính bằng:

```text
mean_wape_delta = mean_wape_before - mean_wape_after
```

Nếu `mean_wape_delta > 0`, nhóm feature làm giảm lỗi. Nếu giá trị này nhỏ hơn ngưỡng `0.0002` hoặc âm, nhóm đó không được giữ trong vòng wrapper hiện tại.

### Baseline

Baseline là tập feature nền trước khi thử các nhóm khác.

Baseline hiện tại gồm:

- `Revenue_lag_1d`
- `COGS_lag_1d`
- `month`
- `day_of_week`

Lý do chọn baseline:

- Target lag 1 ngày thường là tín hiệu mạnh nhất trong forecasting.
- Calendar giúp model học chu kỳ theo ngày trong tuần và tháng.
- Tất cả đều leakage-safe.

Baseline naive khi so sánh model ở bước train có công thức:

```text
y_hat_t = y_(t-1)
```

Nghĩa là dự báo hôm nay bằng giá trị hôm qua. Nếu model phức tạp hơn không thắng được baseline này thì feature/model chưa đủ tốt.

### Ridge Regression

Ridge là model tuyến tính có regularization L2. Dự báo của Ridge có dạng:

```text
y_hat = b + w1*x1 + w2*x2 + ... + wp*xp
```

Hàm mất mát Ridge tối ưu:

```text
min sum((y_i - y_hat_i)^2) + alpha * sum(w_j^2)
```

Trong đó:

- `sum((y_i - y_hat_i)^2)` giúp model fit dữ liệu train.
- `alpha * sum(w_j^2)` phạt hệ số quá lớn để giảm overfit.
- `alpha` càng lớn thì model càng bị ép đơn giản hơn.

Lý do dùng Ridge trong wrapper là nó ổn định khi nhiều feature tương quan với nhau, phù hợp để kiểm tra incremental gain của nhóm feature trước khi sang model chính.

### Incremental gain

Incremental gain là phần cải thiện thêm sau khi đã có tập feature hiện tại.

Ví dụ:

- Một feature có Spearman cao với target.
- Nhưng nếu target lag đã giải thích gần hết tín hiệu đó, feature này có thể không giảm WAPE thêm.

Do đó wrapper không hỏi "feature này có liên quan với target không", mà hỏi "feature này có giúp thêm sau các feature đã có không".

## 4. Quy trình thực hiện trong notebook

Trước khi đọc từng bước chi tiết, cần hiểu mỗi bước này thuộc phần nào trong pipeline tổng quát. Notebook này vẫn nằm trong giai đoạn **chuẩn bị dữ liệu và chọn feature trước khi train model**, không phải modeling cuối cùng.

| Mục lớn trong notebook | Thuộc pipeline tổng quát | Các mục con chính |
| :--- | :--- | :--- |
| 4.1. Load data và tổng quan | Data Description | Nạp dữ liệu, kiểm tra file/shape/schema |
| 4.2. Clean data | Data Cleaning | Chuẩn hóa tên cột, chuỗi rỗng, date/numeric, duplicate, missing/invalid |
| 4.3. Feature Engineering | Feature Engineering + Leakage Control | Tạo target, known-now feature, source aggregate, lag/rolling |
| 4.4. Data Filtering & Feature Selection | Data Filtering + Feature Selection | Feature catalog, compact selection, giảm trùng signal |
| 4.5. Feature Analysis & Validation | EDA + Feature Selection validation | Univariate, bivariate, multivariate, stability, wrapper time-aware |

Điểm cần nhấn mạnh khi trình bày: wrapper có dùng Ridge Regression, nhưng mục tiêu ở đây là **chọn feature**, không phải huấn luyện model chính thức. Modeling sẽ là bước sau, dùng feature set đã được chuẩn bị và audit.

### 4.1. Load data và tổng quan

Mục tiêu của bước này là đọc các bảng nguồn và nắm được tình trạng dữ liệu ban đầu.

Những việc chính:

- Load đủ 14 bảng dữ liệu.
- Kiểm tra file nào có/thiếu.
- Kiểm tra shape và schema sơ bộ.
- Chưa tạo target và chưa tạo feature.

Ý nghĩa:

- Đây là bước Data Description.
- Nếu dữ liệu đầu vào thiếu hoặc sai schema, các bước clean/feature sau đó sẽ sai.

Kết quả:

- 14 bảng nguồn được load đầy đủ, gồm cả `payments`, `shipments` và `geography`.
- Có bảng load summary để audit input.

### 4.2. Clean data

Mục tiêu là chuẩn hóa dữ liệu nguồn sau khi load và trước khi tạo target.

Những việc chính:

- Chuẩn hóa tên cột và strip khoảng trắng.
- Đổi chuỗi rỗng thành missing value.
- Chuẩn hóa cột ngày về dạng datetime.
- Chuẩn hóa cột số để có thể aggregate và tính feature.
- Drop duplicate hoàn toàn.
- Fill `discount_amount = 0` nếu missing vì missing discount có thể hiểu là không giảm giá.
- Drop dòng `sales` thiếu `Date`, `Revenue` hoặc `COGS` vì không thể dùng để tạo nhãn train.
- Flag giá trị âm/nghi vấn để review, chưa tự động cap hoặc xóa outlier.

Ý nghĩa:

- Đây là bước Data Cleaning.
- Clean phải diễn ra trước khi tạo bảng target, vì target tạo từ dữ liệu lỗi sẽ làm sai toàn bộ pipeline.
- Không fill/cap tùy tiện; chỉ xử lý khi có lý do kỹ thuật hoặc business rõ ràng.

Kết quả:

- Có các report: type conversion, duplicate impact, safe cleaning actions, target cleaning, invalid value flags, missing sau clean.
- Dữ liệu đã clean nằm trong biến `clean`.

### 4.3. Feature Engineering

Feature Engineering là mục lớn tạo dữ liệu ở grain ngày và tạo các biến dự báo. Trong notebook này, Feature Engineering gồm ba nhánh chính: tạo target theo ngày, tạo feature biết trước, và tạo lag/rolling từ lịch sử.

#### 4.3.1. Tạo bảng daily target

Mục tiêu là đưa bài toán về cấp độ ngày.

Những biến chính được tạo:

- `Revenue`
- `COGS`
- `gross_margin`
- `margin_rate`

Ý nghĩa:

- `Revenue` và `COGS` là target cần dự báo.
- `gross_margin` và `margin_rate` giúp theo dõi biên lợi nhuận, nhưng không mặc định được đưa vào feature cuối nếu không có đóng góp validation.

#### 4.3.2. Tạo known-now feature

Known-now feature là feature có thể biết tại thời điểm dự báo.

Ví dụ:

- `month`
- `day_of_week`
- Calendar feature khác.
- Planned promotion nếu thông tin đã biết trước.

Ý nghĩa:

- Calendar giúp model học chu kỳ ngày trong tuần, tháng, mùa vụ.
- Known-now feature an toàn về leakage.

Kết quả:

- `month` và `day_of_week` được giữ trong baseline.

#### 4.3.3. Tạo lag và rolling feature

Mục tiêu là biến các tín hiệu quá khứ thành feature dự báo.

Feature được tạo từ:

- Target history: Revenue, COGS.
- Demand volume: order count.
- Return/refund.
- Review.
- Inventory.
- Traffic.
- Discount.
- Payment.
- Shipment.
- Geography.
- Margin history.

Ý nghĩa:

- Lag bắt tín hiệu ngày gần nhất.
- Rolling bắt xu hướng ổn định hơn.
- Tất cả feature lịch sử phải shift để tránh dùng thông tin cùng ngày.

Kết quả:

- Candidate ban đầu có 491 feature.
- Số lượng này lớn vì mỗi nguồn có nhiều lag window và rolling window.
- Không nên đưa thẳng 491 feature vào phân tích sâu vì trùng lặp quá nhiều.

### 4.4. Data Filtering & Feature Selection

Sau khi có candidate feature, bước này lọc bớt những biến không phù hợp hoặc trùng signal. Đây chưa phải modeling; đây là phần chuẩn bị feature set gọn, có lý do và an toàn hơn trước khi train.

#### 4.4.1. Lọc compact trước khi phân tích sâu

Mục tiêu là giảm 491 feature về tập gọn hơn.

Tiêu chí lọc:

- Feature phải leakage-safe.
- Chất lượng dữ liệu chấp nhận được.
- Có quan hệ nhất định với target.
- Không lấy quá nhiều feature trùng lặp trong cùng một family.
- Ưu tiên đại diện tốt cho từng nhóm tín hiệu.

Ý nghĩa:

- Giữ lại feature đại diện thay vì giữ tất cả biến gần giống nhau.
- Giúp scatter, heatmap và kết luận đọc được.
- Giảm nguy cơ model học trùng lặp tín hiệu.

Kết quả:

- Từ 491 candidate, compact selection giữ 24 feature để phân tích sâu.
- Cách chọn mới cho phép một số nhóm tín hiệu giữ nhiều hơn một đại diện, ví dụ payment, shipment, inventory hoặc order/demand, để giảm rủi ro bỏ sót feature hữu ích.

### 4.5. Feature Analysis & Validation

Mục lớn này kiểm tra feature từ nhiều góc nhìn trước khi chốt danh sách cuối. Các phân tích ở đây giúp trả lời: feature có sạch không, có quan hệ với target không, có trùng thông tin không, có ổn định theo thời gian không, và có thật sự cải thiện WAPE khi thêm vào baseline không.

#### 4.5.1. Phân tích đơn biến

Mục tiêu là kiểm tra từng feature riêng lẻ.

Nội dung xem:

- Missing rate.
- Số giá trị khác nhau.
- Phân phối.
- Skew/outlier.

Ý nghĩa:

- Feature missing quá cao có thể khó dùng.
- Feature gần như hằng số thường ít có giá trị.
- Feature skew mạnh cần cẩn thận trong modeling, nhưng chưa chắc phải loại ngay.

Kết luận:

- Target lag missing thấp do chỉ mất một số ngày đầu.
- Calendar feature không missing.
- Một số source feature có missing nhẹ do coverage theo ngày không đồng đều.
- Không drop chỉ vì missing ở bước này; cần xem tiếp quan hệ với target và validation.

#### 4.5.2. Phân tích song biến với target

Mục tiêu là xem từng feature liên quan thế nào với `Revenue` và `COGS`.

Phương pháp:

- Tính Spearman correlation.
- Xếp hạng theo `Revenue_abs_spearman` và `COGS_abs_spearman`.
- Vẽ scatter hoặc binned mean để xem hình dạng quan hệ.
- So sánh theo feature family.

Ý nghĩa:

- Spearman cho biết độ mạnh quan hệ đơn điệu.
- Scatter giúp xem quan hệ có rõ không hay chỉ là nhiễu.
- Nếu Spearman cao nhưng scatter xấu, cần cẩn thận khi giữ.

Kết quả chính:

- `Revenue_lag_1d` và `COGS_lag_1d` là hai feature mạnh nhất.
- `order_count_lag_1d` có tín hiệu demand rõ.
- Sau khi load đủ 14 bảng, các feature như `payment_value_sum_lag_1d`, `order_district_count_lag_1d` và `shipment_count_lag_1d` cũng có Spearman cao. Tuy nhiên các feature này cần qua kiểm tra redundancy và wrapper vì dễ trùng thông tin với target lag hoặc demand volume.
- Nhóm review và return/refund có quan hệ đáng kể với target.
- Calendar có correlation thấp hơn nhưng vẫn có ý nghĩa về chu kỳ.
- Một số nhóm như discount, inventory, traffic có correlation nhất định nhưng scatter nhiễu hoặc đóng góp thêm không rõ.

#### 4.5.3. Phân tích đa biến và redundancy

Mục tiêu là xem các feature có trùng thông tin với nhau không.

Phương pháp:

- Heatmap Spearman có annotation số.
- Bảng correlation với target.
- Danh sách high-correlation pairs.
- So sánh theo feature family.

Ý nghĩa:

- Nếu hai feature quá tương quan, giữ cả hai có thể không thêm nhiều thông tin.
- Feature có correlation cao với target nhưng cũng cao với feature khác có thể bị wrapper loại nếu không tạo incremental gain.

Kết luận:

- Target lag là nhóm mạnh nhất.
- Demand, review, return/refund có tín hiệu bổ sung.
- Payment, margin history, discount, inventory, traffic có nguy cơ trùng lặp hoặc không cải thiện thêm đủ rõ sau baseline. Shipment và geography được giữ sau wrapper vì tạo thêm incremental WAPE khi đã có các nhóm mạnh hơn.

#### 4.5.4. Stability theo thời gian

Mục tiêu là xem feature có ổn định qua các năm không.

Ý nghĩa:

- Feature chỉ tốt ở một năm nhưng đảo chiều ở năm khác có rủi ro khi modeling.
- Forecasting cần feature có tính ổn định theo thời gian.

Cách hiểu:

- Nếu quan hệ giữa feature và target ổn định qua nhiều năm, đó là tín hiệu tốt.
- Nếu quan hệ thay đổi mạnh, feature cần được validation kỹ hơn.

#### 4.5.5. Wrapper time-aware

Mục tiêu là lọc lại bằng validation theo thời gian.

Thiết lập:

- Validation years: 2018, 2019, 2020, 2021, 2022.
- Metric chính: WAPE.
- Model dùng trong wrapper: Ridge.
- Baseline: target lag 1 ngày và calendar.
- Ngưỡng chấp nhận: nhóm feature phải giảm mean WAPE ít nhất 0.0002, tương đương 0.02 điểm phần trăm WAPE.

Lý do dùng Ridge trong wrapper:

- Ridge ổn định với feature có tương quan.
- Phù hợp để so sánh incremental gain của nhóm feature.
- Không quá phức tạp cho bước lọc feature.

Lý do validation theo rolling-origin:

- Đúng logic thời gian của forecasting.
- Train trên quá khứ, test trên tương lai.
- Tránh đánh giá quá lạc quan do random split.

Kết quả wrapper:

- Baseline mean WAPE ban đầu khoảng 0.2257.
- Nhóm `review` được chọn đầu tiên, giảm WAPE xuống khoảng 0.2063.
- Sau đó `demand_volume` được thêm, giảm WAPE xuống khoảng 0.2054.
- Sau đó `return_refund` được thêm, giảm WAPE xuống khoảng 0.2025.
- Sau khi giữ nhiều đại diện hơn, `shipment` tiếp tục được thêm, giảm WAPE xuống khoảng 0.2009.
- Sau đó `geography` được thêm, giảm WAPE xuống khoảng 0.1997.
- Các nhóm còn lại, trong đó có `payment`, không đạt ngưỡng incremental gain sau khi đã có các nhóm trên.

## 5. Feature set hiện tại

Feature set cuối hiện tại gồm 11 biến:

- `Revenue_lag_1d`
- `COGS_lag_1d`
- `order_count_lag_1d`
- `order_district_count_lag_1d`
- `shipment_count_lag_1d`
- `shipping_fee_sum_lag_1d`
- `refund_amount_sum_rolling_7d_mean`
- `review_count_rolling_7d_mean`
- `return_count_rolling_7d_mean`
- `month`
- `day_of_week`

Giải thích từng nhóm:

- `Revenue_lag_1d`: bắt tính liên tục của doanh thu ngày gần nhất.
- `COGS_lag_1d`: bắt tính liên tục của chi phí hàng bán ngày gần nhất.
- `order_count_lag_1d`: đại diện cho demand volume gần nhất.
- `order_district_count_lag_1d`: đại diện cho độ phủ địa lý/ngày của đơn hàng trong quá khứ gần nhất.
- `shipment_count_lag_1d`: đại diện cho khối lượng shipment gần nhất.
- `shipping_fee_sum_lag_1d`: đại diện cho quy mô chi phí vận chuyển gần nhất.
- `review_count_rolling_7d_mean`: đại diện cho mức độ tương tác/phản hồi gần đây.
- `return_count_rolling_7d_mean`: đại diện cho xu hướng hàng trả lại gần đây.
- `refund_amount_sum_rolling_7d_mean`: đại diện cho quy mô refund gần đây.
- `month`: bắt chu kỳ theo tháng.
- `day_of_week`: bắt chu kỳ theo ngày trong tuần.

## 6. Kết quả đánh giá

Baseline WAPE:

- `Revenue`: khoảng 0.2249.
- `COGS`: khoảng 0.2264.

Wrapper final WAPE:

- `Revenue`: khoảng 0.1987.
- `COGS`: khoảng 0.2007.

Mức cải thiện:

- `Revenue` giảm WAPE khoảng 0.0262, tương đương 2.62 điểm phần trăm.
- `COGS` giảm WAPE khoảng 0.0258, tương đương 2.58 điểm phần trăm.

MAE:

- `Revenue` giảm từ khoảng 758,319 xuống 673,235.
- `COGS` giảm từ khoảng 659,087 xuống 586,174.

Ý nghĩa:

- Feature set hiện tại có cải thiện rõ so với baseline.
- Cải thiện đến từ việc thêm review, demand volume, return/refund, shipment và geography ngoài target lag/calendar.
- Tuy nhiên đây vẫn là feature preparation, chưa phải kết quả model cuối cùng.

## 7. Vì sao không giữ nhiều feature hơn

Không giữ nhiều feature hơn vì feature forecasting rất dễ trùng thông tin.

Ví dụ:

- Nhiều lag của cùng một biến có thể cùng nói về một xu hướng.
- Rolling 7 ngày, 30 ngày, 90 ngày có thể trùng lặp nếu dữ liệu thay đổi chậm.
- Feature có Spearman cao với target nhưng lại trùng với `Revenue_lag_1d` hoặc `COGS_lag_1d`.

Nếu giữ quá nhiều:

- Phân tích sau khó hơn.
- Model có thể kém ổn định hơn.
- Dễ overfit trên validation.
- Khó giải thích với business.

Vì vậy notebook chỉ giữ các feature có lý do rõ về logic và có bằng chứng validation.

## 8. Vì sao có feature Spearman cao nhưng vẫn bị loại

Một feature có Spearman cao chỉ chứng minh rằng nó có liên quan riêng lẻ với target.

Nhưng trong model, câu hỏi quan trọng là:

- Sau khi đã có target lag và calendar, feature đó có thêm thông tin mới không?
- Feature đó có làm giảm WAPE trên năm tương lai không?
- Feature đó có ổn định qua thời gian không?

Nếu câu trả lời là không, feature sẽ không được giữ trong feature set hiện tại.

Đây là lý do một số nhóm như payment, discount, inventory, traffic hoặc margin history chưa được giữ dù có thể có correlation nhất định. Ngược lại, shipment và geography được giữ vì tạo thêm incremental WAPE sau khi đã có các nhóm mạnh hơn.

## 9. Cách trình bày ngắn gọn khi báo cáo

Có thể trình bày theo ý sau:

"Quy trình chuẩn bị dữ liệu được thiết kế theo nguyên tắc leakage-safe. Tất cả feature đưa vào phân tích đều là biến biết trước tại thời điểm dự báo hoặc biến quá khứ đã được shift. Notebook load đủ 14 bảng dữ liệu; từ 491 candidate feature, nhóm thực hiện lọc compact còn 24 feature đại diện theo family/signal để tránh trùng lặp nhưng vẫn đủ đa dạng cho phân tích sâu. Sau đó, các feature được đánh giá bằng Spearman, scatter, redundancy, stability theo năm và cuối cùng là wrapper time-aware theo rolling-origin. Wrapper bắt đầu từ baseline gồm target lag và calendar, sau đó chỉ giữ thêm những nhóm feature làm giảm WAPE trên validation theo năm. Kết quả cuối giữ 11 feature, trong đó ngoài baseline có thêm demand volume, review, return/refund, shipment và geography. WAPE trung bình giảm từ khoảng 0.2249 xuống 0.1987 cho Revenue và từ 0.2264 xuống 0.2007 cho COGS."

## 10. Câu hỏi có thể gặp và cách trả lời

### Vì sao không chỉ dùng EDA để chọn feature?

EDA giúp hiểu quan hệ giữa feature và target, nhưng không đủ để kết luận feature có hữu ích cho model. Một feature có correlation cao có thể trùng thông tin với feature khác. Vì vậy cần wrapper time-aware để kiểm tra incremental gain trên validation theo thời gian.

### Vì sao dùng Spearman thay vì Pearson?

Spearman phù hợp khi quan hệ giữa feature và target không nhất thiết là tuyến tính. Nó đo quan hệ đơn điệu, nên ổn hơn cho các feature kinh doanh có phân phối lệch và outlier.

### Vì sao dùng WAPE?

WAPE phù hợp với bài toán doanh thu và chi phí vì đo sai số theo tỷ lệ trên tổng actual. Nó giúp đánh giá sai số theo quy mô business, dễ diễn giải hơn so với chỉ nhìn sai số tuyệt đối.

### Vì sao validation theo rolling-origin?

Vì đây là bài toán thời gian. Khi dự báo thật, model chỉ có dữ liệu quá khứ để dự báo tương lai. Rolling-origin mô phỏng đúng tình huống đó, nên đáng tin hơn random split.

### Vì sao baseline có target lag?

Doanh thu và COGS thường có tính tương quan theo ngày liên tiếp. Target lag 1 ngày là tín hiệu quá khứ mạnh, leakage-safe và tạo baseline hợp lý cho forecasting.

### Vì sao calendar correlation thấp nhưng vẫn giữ?

Calendar feature có thể không mạnh khi xét riêng lẻ, nhưng nó giúp model học chu kỳ ngày trong tuần và tháng. Ngoài ra calendar là known-now, không có rủi ro leakage.

### Vì sao nhóm payment/traffic/inventory/discount chưa được giữ?

Sau khi đã có baseline, review, demand volume, return/refund, shipment và geography, các nhóm payment/traffic/inventory/discount không tạo incremental WAPE gain đủ lớn trên rolling-origin. `payment_value_sum_lag_1d` và `payment_method_credit_card_count_lag_1d` có quan hệ đơn biến mạnh nhưng dễ trùng với target lag hoặc demand volume, nên chưa được đưa vào feature set hiện tại.

### Kết quả này có phải model cuối cùng không?

Không. Đây là kết quả chuẩn bị dữ liệu và lọc feature. Feature set này sẽ được dùng làm đầu vào cho bước modeling, tuning và đánh giá chính thức sau.

## 11. Kết luận

Quy trình hiện tại đã chuyển từ cách chọn feature dựa nhiều vào EDA sang cách kết hợp EDA và validation time-aware. Điều này phù hợp hơn với bài toán forecasting vì vừa giải thích được quan hệ dữ liệu, vừa kiểm tra được feature có cải thiện dự báo trên tương lai hay không.

Feature set hiện tại gọn, leakage-safe và có bằng chứng cải thiện WAPE. Các nhóm feature bị loại không có nghĩa là vô dụng, mà là chưa tạo đủ incremental gain trong cấu hình validation hiện tại. Khi sang bước modeling, có thể tiếp tục kiểm tra các nhóm này nếu cần mở rộng feature set.
