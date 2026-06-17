# Plan notebook chuẩn bị dữ liệu và phân tích feature

## 1. Mục tiêu

Notebook `report_1_6_2026/perparation_data_update.ipynb` dùng để chuẩn bị dữ liệu theo ngày và phân tích feature cho bài toán dự báo `Revenue` và `COGS`.

Mục tiêu chính:

- Tạo bảng dữ liệu daily leakage-safe.
- Lọc feature từ tập candidate lớn xuống một tập đủ gọn để phân tích sâu.
- Kiểm tra feature bằng EDA đơn biến, song biến, đa biến và ổn định theo thời gian.
- Dùng wrapper time-aware để kiểm tra feature/group nào cải thiện WAPE ngoài baseline.
- Xuất bảng feature cuối và báo cáo quyết định để phục vụ bước modeling sau.

Notebook này không nhằm huấn luyện model cuối cùng, không scale/PCA, không tạo train/valid/test chính thức cho modeling.

## 2. File và output hiện tại

Notebook chính và duy nhất:

- `report_1_6_2026/perparation_data_update.ipynb`

Helper dùng chung:

- `ds_utils.py`

Output chính:

- `outputs/feature_analysis_focused/selected_feature_analysis_summary.csv`
- `outputs/feature_analysis_focused/selected_features_final.csv`
- `outputs/feature_analysis_focused/wrapper_group_validation_report.csv`
- `outputs/feature_analysis_focused/wrapper_model_summary.csv`

## 3. Nguyên tắc triển khai

- Chỉ dùng feature biết trước ngày dự báo hoặc feature lịch sử đã shift.
- Không dùng thông tin vận hành cùng ngày của target làm feature trực tiếp.
- Không chọn quá nhiều biến lag/rolling trùng cùng một tín hiệu.
- Không dựa hoàn toàn vào correlation; correlation chỉ là bước hiểu dữ liệu.
- Wrapper time-aware dùng để kiểm tra đóng góp dự báo ngoài baseline.
- Feature set hiện tại có thể tiếp tục được điều chỉnh sau khi đánh giá thêm scatter, redundancy và validation model.

## 4. Cấu trúc notebook hiện tại

### Section 0 - Setup

Mục tiêu:

- Import thư viện.
- Xác định project root, data folder và output folder.
- Import `ds_utils.py` để dùng lại helper chung.
- Khai báo target, lag window và rolling window.

Ghi chú:

- Các helper chung như đọc CSV, hiển thị bảng, chia loại feature, tạo lag/rolling và plot feature-target đã được đưa sang `ds_utils.py`.
- Notebook chỉ giữ logic riêng của bài toán.

### Section 1 - Load và kiểm tra dữ liệu đầu vào

Mục tiêu:

- Load toàn bộ bảng nguồn.
- Chuẩn hóa kiểu ngày và kiểu số.
- Kiểm tra missing, duplicate và target overview.

Kết quả chính:

- Load đủ 14 bảng dữ liệu.
- Daily target base được tạo từ `sales`.
- Missing cao chủ yếu nằm ở một số cột nguồn không nhất thiết dùng trực tiếp cho daily forecasting.

### Section 2 - Tạo daily feature table leakage-safe

Mục tiêu:

- Tạo daily base có `Revenue`, `COGS`, `gross_margin`, `margin_rate`.
- Tạo feature known-now như calendar và planned promotion.
- Aggregate nguồn vận hành theo ngày.
- Tạo lag/rolling cho target và source bằng dữ liệu quá khứ.
- Tạo bảng candidate feature.

Kết quả chính:

- Candidate ban đầu: 491 feature.
- Các nhóm feature gồm known-now, target lag/rolling và source lag/rolling.
- Ba bảng bổ sung `payments`, `shipments`, `geography` được aggregate theo ngày rồi tạo lag/rolling trước khi đưa vào candidate.
- Same-day source feature được loại khỏi candidate trực tiếp để tránh leakage.

### Section 3 - Lọc feature gọn trước khi phân tích sâu

Mục tiêu:

- Tạo feature catalog gồm family, timing type và leakage risk.
- Tính quality và relation với target.
- Chọn một đại diện gọn cho từng nhóm tín hiệu.
- Giảm feature trùng lặp trước khi phân tích sâu.

Kết quả chính:

- Từ 491 candidate, bước compact selection giữ 24 feature.
- Một số signal quan trọng được phép giữ nhiều hơn một đại diện để giảm rủi ro bỏ sót, nhưng vẫn bị giới hạn bằng signal cap và family cap.
- Các feature được chọn dựa trên chất lượng dữ liệu, Spearman với target, family cap và signal group.
- Các biến trùng trực tiếp với target hoặc nhiều biến cùng một signal bị loại bớt.

### Section 4 - Phân tích đơn biến

Mục tiêu:

- Kiểm tra missing, số giá trị khác nhau, skew và phân phối của selected features.
- Xem feature nào ổn, feature nào cần review thêm khi modeling.

Kết luận hiện tại:

- Target lag missing rất thấp do chỉ mất ngày đầu.
- Calendar/known-now không missing.
- Một số feature nguồn có missing nhẹ do coverage theo ngày không đầy đủ.
- Không drop chỉ vì missing ở bước này; tiếp tục dùng wrapper/time-aware để kiểm tra đóng góp.

### Section 5 - Phân tích song biến với target

Mục tiêu:

- Xếp hạng selected features theo quan hệ với `Revenue` và `COGS`.
- Dùng Spearman để đo quan hệ đơn điệu.
- Vẽ scatter/binned mean cho feature liên tục.
- So sánh calendar/binary feature với target.
- Xem target lag/rolling và source lag theo family.

Ghi chú:

- `Revenue_abs_spearman` và `COGS_abs_spearman` là trị tuyệt đối của Spearman correlation.
- Trị tuyệt đối dùng để xếp hạng độ mạnh, còn dấu của Spearman dùng để biết chiều quan hệ.
- Scatter vẫn cần xem thủ công vì correlation cao chưa chắc feature có signal sạch.

### Section 6 - Phân tích đa biến và redundancy

Mục tiêu:

- Kiểm tra feature nào trùng thông tin với nhau.
- Dùng heatmap có số tương quan rõ ràng cho target và top selected features.
- Tìm high-correlation pairs.
- So sánh relation theo feature family.

Điều chỉnh đã làm:

- Heatmap đã được giảm còn top 15 feature để dễ đọc.
- Heatmap có annotation số tương quan.
- Có thêm bảng Spearman với target trước heatmap để đọc chính xác.

Kết luận hiện tại:

- `target_lag` là nhóm mạnh nhất.
- `order_lag`, `payment_lag`, `geography_lag`, `shipment_lag`, `return_lag`, `review_lag` có tín hiệu rõ ở EDA.
- Nhóm shipment và geography có đóng góp thêm trong wrapper khi compact selection giữ nhiều đại diện hơn. Nhóm payment, traffic, inventory, discount có tương quan nhưng chưa tạo đủ incremental WAPE sau target lag và các nhóm đã chọn.

### Section 7 - Stability, wrapper time-aware và export

Mục tiêu:

- Kiểm tra stability theo năm.
- Dùng wrapper rolling-origin để kiểm tra incremental WAPE.
- Dùng ngưỡng wrapper đủ nhỏ để giữ các nhóm có cải thiện dương rõ, nhưng vẫn loại nhóm có incremental WAPE quá nhỏ hoặc âm.
- Xuất feature summary, final feature list và wrapper reports.

Thiết lập hiện tại:

- Validation years: 2018, 2019, 2020, 2021, 2022.
- Baseline features: `Revenue_lag_1d`, `COGS_lag_1d`, `month`, `day_of_week`.
- Wrapper threshold: 0.0002 mean WAPE delta, tương đương 0.02 điểm phần trăm WAPE.

Lý do chọn ngưỡng wrapper hiện tại:

- Ngưỡng 0.0002 vẫn yêu cầu incremental gain dương, đồng thời giữ thêm các nhóm có cải thiện rõ như `demand_volume` và `return_refund`.
- Các nhóm mới `shipment` và `geography` được wrapper giữ sau khi compact selection có thêm đại diện. Nhóm `payment` vẫn chưa được giữ vì không cải thiện đủ sau các nhóm mạnh hơn.

## 5. Kết quả feature hiện tại

Feature set hiện tại gồm 11 biến:

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

Nhóm được wrapper chấp nhận:

- Baseline: target lag và calendar.
- `review`
- `demand_volume`
- `return_refund`
- `shipment`
- `geography`

Nhóm chưa giữ:

- `discount`
- `margin_history`
- `payment`
- `inventory`
- `traffic`
- `promo/event`

Lý do chưa giữ:

- Sau khi đã có baseline, review, demand volume và return/refund, incremental WAPE gain của các nhóm này quá nhỏ hoặc âm.
- Một số feature có scatter nhiễu hoặc bị trùng tín hiệu với target lag.
- `payment_value_sum_lag_1d` và `payment_method_credit_card_count_lag_1d` có Spearman cao nhưng chưa tạo thêm incremental gain đủ tốt trong wrapper.
- Các nhóm này cần được đánh giá thêm nếu mở rộng feature set cho modeling.

## 6. Kết quả wrapper hiện tại

Baseline WAPE:

- `Revenue`: khoảng 0.2249
- `COGS`: khoảng 0.2264

Wrapper final WAPE:

- `Revenue`: khoảng 0.1987
- `COGS`: khoảng 0.2007

Diễn giải:

- Feature set 11 biến cải thiện WAPE rõ hơn baseline.
- Kết quả này chưa phải model cuối cùng.
- Đây là bằng chứng để dùng feature set hiện tại làm đầu vào cho bước modeling tiếp theo.

## 7. Những điểm cần review tiếp

Các feature nên xem kỹ bằng scatter/redundancy trước khi quyết định mở rộng:

- `gross_margin_lag_1d`
- `margin_rate_rolling_90d_mean`
- `year`
- `payment_value_sum_lag_1d`
- `discount_amount_sum_rolling_90d_mean`
- `stockout_days_sum_lag_1d`
- `inventory_product_count_lag_1d`
- `sessions_sum_rolling_7d_mean`

Lý do:

- Một số biến tương quan tốt nhưng quan hệ scatter không sạch.
- Một số biến có thể chỉ ăn theo trend hoặc quy mô target lag.
- Một số biến có incremental WAPE gain âm sau khi đã thêm nhóm mạnh hơn.

## 8. Definition of Done hiện tại

Notebook được coi là đạt yêu cầu hiện tại nếu:

- Chạy từ đầu đến cuối không lỗi.
- Code cell có output đầy đủ.
- Tiêu đề và markdown mô tả đúng quy trình chuẩn bị dữ liệu.
- Có kết luận sau các bước phân tích chính.
- Dùng `ds_utils.py` cho helper tái dùng.
- Candidate feature được tạo theo hướng leakage-safe.
- Compact selection giảm 491 candidate xuống 24 selected features để phân tích.
- Wrapper time-aware xuất được feature set hiện tại gồm 11 biến.
- Output CSV được cập nhật theo kết quả hiện tại.

## 9. Việc không làm trong notebook này

- Không train model cuối cùng.
- Không tune hyperparameter.
- Không tạo submission.
- Không scale/PCA.
- Không tạo split modeling chính thức.
- Không dùng wrapper như bằng chứng duy nhất để kết luận business impact.

## 10. Bước tiếp theo đề xuất

- Review scatter của các feature bị loại nhưng còn nghi ngờ.
- Đánh giá feature set 11 biến và phương án mở rộng lên khoảng 12-16 biến cho model tree/boosting nếu cần.
- Nếu mở rộng, cần ghi rõ feature nào là `core`, feature nào là `review/modeling_candidate`.
- Làm notebook/modeling riêng để đánh giá feature set bằng model thật.
