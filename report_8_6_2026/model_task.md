# Dự báo Doanh Thu Hàng Ngày - Kế hoạch Model

## Mục tiêu
Xây dựng model dự báo doanh thu theo ngày (daily revenue forecasting) phục vụ báo cáo và đánh giá cuộc thi Datathon.

## Quy trình
- **Phase 0**: Setup – cài đặt môi trường, load data, cấu hình chung
- **Phase 1**: Chốt bài toán model – xác định target, feature, grain, split
- **Phase 2**: Chuẩn bị dữ liệu modeling – merge, kiểm tra, tạo bảng cuối
- **Phase 3**: Chia train, validation, test
- **Phase 4**: Xây baseline model
- **Phase 5**: Train model lần đầu
- **Phase 6**: Chọn metric đánh giá
- **Phase 7**: Phân tích lỗi model
- **Phase 8**: Giải thích model
- **Phase 9**: Cải thiện model
- **Phase 10**: Chọn model cuối
- **Phase 11**: Chuẩn bị báo cáo model

## Input
- Dữ liệu doanh thu thô sau bước Feature Engineering
- Các bảng feature đã được tạo (lag, rolling, calendar, promotion, traffic...)
- Lịch khuyến mãi, dữ liệu web traffic (nếu có)

## Output
- Notebook model hoàn chỉnh với các phase được trình bày rõ ràng
- Bảng metric so sánh các model
- Biểu đồ actual vs predicted
- Giải thích model (feature importance, SHAP)
- Tóm tắt phần model dùng cho báo cáo cuối

---

## Phase 0: Setup

### Mục tiêu
Chuẩn bị môi trường làm việc, import thư viện, thiết lập cấu hình chung cho toàn bộ notebook model.

### Code
- Import các thư viện cần thiết: pandas, numpy, matplotlib, seaborn, sklearn, lightgbm/xgboost
- Cấu hình display: `pd.set_option`, `matplotlib rcParams`
- Định nghĩa hàm helper dùng chung: tính metric (MAE, RMSE, WAPE, MAPE), vẽ actual vs predicted
- Định nghĩa hằng số: đường dẫn file, random seed, ngưỡng ngày chia train/val/test
- Load toàn bộ data cần dùng (bảng target, các bảng feature)

### Output
- Không có lỗi import
- Hiển thị `.shape` và `.head()` của các bảng đã load

---

## Phase 1: Chốt bài toán model

### Mục tiêu
Xác định rõ và ghi lại định nghĩa bài toán trước khi code, tránh nhầm lẫn và làm rõ scope cho người đọc báo cáo.

### Việc cần thục hiện
- Xác định Loại bài toán: **Regression** – dự báo giá trị số liên tục, không phân loại
- Xác định Target: doanh thu daily (daily revenue)
- Xác định Grain của bảng model: mỗi dòng = một ngày
- Liệt kê feature dự kiến theo nhóm (từ bước Feature Engineering)
- Xác định và ghi rõ giai đoạn chia data:
  - Train: từ ngày ... đến ngày ...
  - Validation: từ ngày ... đến ngày ...
  - Test: từ ngày ... đến ngày ...
  - Lý do: time-based split, không random vì bài toán là dự báo theo thời gian
- Ghi rõ model dự kiến sẽ thử: Linear Regression, LightGBM, XGBoost

### Output
- Markdown cell tóm tắt định nghĩa bài toán (dùng lại cho báo cáo)
- Bảng danh sách feature theo nhóm
- Bảng hoặc markdown timeline chia train/validation/test



## Phase 2: Chuẩn bị dữ liệu modeling

### Mục tiêu: 
check target , feature và tạo một bảng cuối cùng để train model.
### Việc cần thục hiện:

- Load dữ liệu file (chứa cả feature + target thu được ở bước trước feature engineering)
- Kiểm tra duplicate, miss, ... . Nếu có xử lý
- kiểm tra date modeling có bị đứt gãy không (số ngày liên tiếp)
- kiểm tra fearure có bị leakage không

### Output: DataFrame modeling có grain rõ ràng.
- biểu đồ kiểm tra time feature và target có bị gãy không
- biểu đồ chart : (check miss, duplicate trước và sau khi xử lý cho feature)


## Phase 3: Chia train, validation, test

### Mục tiêu
Chia dữ liệu modeling thành 3 tập theo thời gian để chuẩn bị train và đánh giá model.

### Việc cần thực hiện
- Dùng bảng sạch từ Phase 2: `phase2_modeling_table.csv`.
- Chia dữ liệu theo thời gian, không dùng random split.
- Train: từ `2012-07-04` đến `2020-11-24`.
- Validation: từ `2020-11-25` đến `2021-12-12`.
- Test: từ `2021-12-13` đến `2022-12-31`.
- Kiểm tra ngày bắt đầu thực tế của từng tập sau khi Phase 2 đã xử lý missing.
- Kiểm tra train, validation, test không bị trùng ngày.
- Kiểm tra tổng số dòng sau split có bằng số dòng của bảng modeling không.
- Kiểm tra mỗi tập vẫn có target `Revenue` và đủ feature.
- Kiểm tra phân phối doanh thu giữa train, validation, test.
- Kiểm tra số dòng theo tháng để xem tập nào có bị thiếu giai đoạn quan trọng không.

### Biểu đồ sử dụng
- Timeline split: xem khoảng thời gian của train, validation, test.
- Line chart Revenue theo thời gian: xem target trên 3 tập có bị lệch mạnh không.
- Boxplot Revenue theo tập: so sánh phân phối doanh thu train/validation/test.
- Bar chart số dòng theo tháng: kiểm tra mỗi tập có đủ dữ liệu theo thời gian không.

### Output
- `modeling_train_dataset.csv`: dữ liệu train.
- `modeling_validation_dataset.csv`: dữ liệu validation.
- `modeling_test_dataset.csv`: dữ liệu test.
- `phase3_split_summary.csv`: bảng tóm tắt số dòng, ngày bắt đầu, ngày kết thúc của từng tập.
- `phase3_target_distribution.csv`: bảng so sánh phân phối target giữa các tập.

## Phase 4: Xây baseline model

### Mục tiêu
Tạo các cách dự báo đơn giản để làm mốc so sánh trước khi train model ML.

### Việc cần thực hiện
- Dùng train, validation, test đã chia ở Phase 3.
- Baseline không dùng model phức tạp, chỉ dùng quy tắc dự báo đơn giản.
- Baseline 1 - Mean baseline: dự báo bằng doanh thu trung bình của train.
- Baseline 2 - Yesterday baseline: dự báo bằng doanh thu ngày liền trước.
- Baseline 3 - Same weekday baseline: dự báo bằng doanh thu cùng ngày tuần trước.
- Tính metric cho từng baseline trên validation và test.
- So sánh baseline để biết cách dự báo đơn giản nào mạnh nhất.
- Dùng baseline tốt nhất làm mốc cho các model ML ở Phase 5.
- Nếu model ML sau này không thắng baseline, cần xem lại feature, split hoặc target.

### Biểu đồ sử dụng
- Actual vs baseline: xem dự báo baseline bám sát thực tế không.
- Error theo thời gian: xem baseline sai mạnh ở giai đoạn nào.
- Bảng metric baseline: so sánh MAE, RMSE, WAPE giữa các baseline.

### Output
- `phase4_baseline_predictions.csv`: dự báo của từng baseline.
- `phase4_baseline_metrics.csv`: metric của từng baseline trên validation/test.
- `phase4_best_baseline_summary.csv`: baseline tốt nhất để làm mốc so sánh.
## Phase 5: Train model lần đầu

### Mục tiêu
Train các model ML đầu tiên và so sánh với baseline tốt nhất .

### Việc cần thực hiện
- Dùng train, validation, test đã chia .
- Dùng 21 selected features làm input `X`.
- Dùng `Revenue` làm target `y`.
- Không dùng `Date`, `COGS` làm feature đầu vào.
- Fit model trên train set.
- Đánh giá model chính trên validation set.
- Chưa dùng test để chọn model, test để kiểm tra cuối ở phase sau.
- Dùng `yesterday_baseline` của Phase 4 làm mốc so sánh.
- Train model đơn giản trước: Linear Regression hoặc Ridge Regression.
- Train thêm model tree-based chính: LightGBM.
- Nếu model cần scale, chỉ fit scaler trên train rồi transform validation/test.
- Kiểm tra prediction có âm không vì doanh thu không nên âm.
- Kiểm tra model có dự báo quá phẳng hoặc lệch mạnh so với thực tế không.
- So sánh MAE, RMSE, WAPE của model với baseline trên validation.
- Chọn model đầu tiên tốt nhất theo WAPE validation.

### Biểu đồ sử dụng
- Actual vs predicted: xem dự báo bám sát doanh thu thật không.
- Scatter actual vs predicted: xem model dự báo cao/thấp có cân bằng không.
- Residual distribution: xem sai số tập trung quanh 0 hay lệch hẳn một phía.
- Bar chart metric: so sánh model ML với baseline tốt nhất.

### Output
- `phase5_model_predictions_validation.csv`: dự báo của các model trên validation.
- `phase5_model_metrics.csv`: metric của từng model và baseline trên validation.
- `phase5_best_model_summary.csv`: model tốt nhất ở lần train đầu.
- `phase5_prediction_check.csv`: kiểm tra prediction âm, prediction quá phẳng, sai số lớn.

## Phase 6: Chọn metric đánh giá

### Mục tiêu
Chốt metric chính để đánh giá model và phân tích sai số theo cách có ý nghĩa kinh doanh.

### Việc cần thực hiện
- Dùng kết quả dự báo validation từ Phase 5.
- Chọn WAPE làm metric chính vì dễ hiểu theo tỷ lệ tổng doanh thu.
- Dùng MAE làm metric phụ để biết trung bình sai bao nhiêu tiền mỗi ngày.
- Dùng RMSE làm metric phụ để phát hiện model sai rất nặng ở vài ngày.
- Không dùng MAPE làm metric chính nếu có ngày doanh thu thấp hoặc gần 0.
- So sánh metric của model tốt nhất với `yesterday_baseline`.
- Tính WAPE, MAE, RMSE theo toàn bộ validation.
- Tính WAPE theo tháng để xem model yếu ở giai đoạn nào.
- Tính error trung bình để xem model hay dự báo cao hơn hay thấp hơn thực tế.
- Ghi rõ metric chính sẽ dùng để chọn model ở các phase sau.

### Biểu đồ sử dụng
- Bar chart metric tổng: so sánh best model với baseline.
- Line chart WAPE theo tháng: xem tháng nào model sai nhiều.
- Error timeline: xem sai số có tập trung theo giai đoạn không.

### Output
- `phase6_metric_policy.csv`: metric chính và lý do chọn.
- `phase6_metric_by_model.csv`: metric tổng của best model và baseline.
- `phase6_monthly_wape.csv`: WAPE theo tháng trên validation.
- `phase6_error_summary.csv`: tóm tắt sai số, bias và ngày sai lớn.

## Phase 7: Phân tích lỗi model

### Mục tiêu
Tìm các giai đoạn, ngày và kiểu dữ liệu mà best model dự báo sai nhiều nhất.

### Việc cần thực hiện
- Dùng prediction validation của best model từ Phase 5.
- Tính error = `Revenue thực tế - Revenue dự báo`.
- Tính absolute error = độ lớn sai số, không xét dấu.
- Lấy top ngày có absolute error lớn nhất.
- Kiểm tra model hay dự báo cao hơn hay thấp hơn thực tế.
- Kiểm tra lỗi theo tháng để xem giai đoạn nào model yếu.
- Kiểm tra lỗi theo ngày trong tuần để xem có pattern tuần không.
- Kiểm tra lỗi theo nhóm doanh thu thấp, trung bình, cao.
- So sánh lỗi của best model với `yesterday_baseline`.
- Kiểm tra các ngày lỗi lớn có feature bất thường không, ví dụ lag/rolling revenue, gross profit, gross margin, web traffic.
- Ghi nhận nguyên nhân nghi ngờ, chưa vội sửa model ở Phase 7.

### Biểu đồ sử dụng
- Top error days: xem ngày nào model sai lớn nhất.
- Error timeline: xem lỗi có tập trung theo giai đoạn không.
- Boxplot absolute error theo tháng: xem tháng nào lỗi cao.
- Boxplot absolute error theo nhóm doanh thu: xem model yếu ở doanh thu thấp hay cao.

### Output
- `phase7_top_error_days.csv`: top ngày lỗi lớn nhất.
- `phase7_error_by_month.csv`: sai số theo tháng.
- `phase7_error_by_weekday.csv`: sai số theo ngày trong tuần.
- `phase7_error_by_revenue_group.csv`: sai số theo nhóm doanh thu.
- `phase7_error_feature_review.csv`: review feature tại các ngày lỗi lớn.

## Phase 8: Giải thích model

### Mục tiêu
Hiểu best model đang dựa nhiều vào feature nào và kiểm tra các feature đó có hợp lý không.

### Việc cần thực hiện
- Dùng best model từ Phase 5, hiện là `lightgbm`.
- Lấy feature importance của model tree-based.
- Sắp xếp feature theo mức độ quan trọng giảm dần.
- Kiểm tra top feature có phải lag/rolling hợp lý với bài toán daily forecasting không.
- Đối chiếu top feature với metadata leakage từ feature engineering.
- Kiểm tra top feature có phải feature biết trước tại thời điểm dự báo không.
- Đối chiếu top feature với các ngày lỗi lớn ở Phase 7.
- Kiểm tra model có phụ thuộc quá nhiều vào một vài feature không.
- Nếu top feature có rủi ro leakage hoặc khó giải thích, ghi lại để Phase 9 xử lý.
- Không loại feature ngay ở Phase 8, chỉ giải thích và ghi nhận rủi ro.
- SHAP chỉ làm nếu môi trường có thư viện và thời gian chạy phù hợp.

### Biểu đồ sử dụng
- Feature importance bar chart: xem model dựa nhiều vào feature nào.
- Cumulative importance chart: xem bao nhiêu feature đang chi phối model.
- Optional SHAP summary: giải thích hướng tác động của feature nếu chạy được.

### Output
- `phase8_feature_importance.csv`: bảng importance của 21 feature.
- `phase8_top_feature_review.csv`: review top feature theo leakage và ý nghĩa DS.
- `phase8_cumulative_importance.csv`: mức importance tích lũy.
- `phase8_top_error_feature_context.csv`: giá trị top feature tại các ngày lỗi lớn.
- `phase8_model_explanation_summary.csv`: kết luận ngắn về model đang học từ đâu.

## Phase 9: Cải thiện model

### Mục tiêu
Cải thiện model có kiểm soát dựa trên kết quả Phase 5-8, không thay đổi dữ liệu bừa bãi.

### Việc cần thực hiện
- Dùng best model hiện tại làm mốc, hiện là `lightgbm`.
- Dùng `yesterday_baseline` làm mốc baseline.
- Dùng WAPE validation làm metric chính để so sánh.
- Không dùng test để tuning hoặc chọn model.
- Tuning một vài tham số quan trọng của LightGBM trước.
- Thử thêm một model tree-based khác nếu có sẵn trong môi trường, ví dụ XGBoost hoặc Gradient Boosting.
- Thử calendar feature rescue sau tuning LightGBM để biết cải thiện đến từ tuning hay từ feature.
- So sánh 3 cấu hình chính:
  - `LightGBM Phase 5`: model ban đầu làm mốc.
  - `LightGBM tuned`: model sau tuning hyperparameter.
  - `LightGBM tuned + calendar rescue`: model tuned cộng thêm `day_of_week` và `is_weekend`.
- So sánh model cải thiện với best model Phase 5 và baseline Phase 4.
- Kiểm tra model cải thiện có giảm WAPE nhưng làm prediction quá phẳng không.
- Kiểm tra model cải thiện có tăng lỗi ở nhóm doanh thu thấp/cao không.
- Kiểm tra top error days sau cải thiện có giảm không.
- .Thử nghiệm với các feature cho là quan trọng như `day_of_week` và `is_weekend` như một calendar feature rescue experiment vì có ý nghĩa nghiệp vụ rõ với daily forecasting. (Không thêm nhiều hay quá rộng)
- Chỉ giữ calendar features bổ sung nếu validation WAPE tốt hơn hoặc lỗi theo weekday/weekend giảm rõ.
- Nếu calendar rescue không cải thiện, giữ feature set cũ và ghi nhận là đã thử.

### Biểu đồ sử dụng
- Bar chart WAPE trước và sau cải thiện.
- Actual vs predicted của model cải thiện.
- Error timeline trước và sau cải thiện.
- Boxplot absolute error theo nhóm doanh thu.
- Error theo weekday/weekend để xem calendar rescue có giúp đúng vấn đề không.

### Output
- `phase9_tuning_results.csv`: kết quả các cấu hình model đã thử.
- `phase9_improved_predictions_validation.csv`: prediction validation của model cải thiện.
- `phase9_improved_model_summary.csv`: model cải thiện tốt nhất và mức tăng/giảm so với Phase 5.
- `phase9_error_comparison.csv`: so sánh lỗi trước và sau cải thiện.
- `phase9_calendar_rescue_comparison.csv`: so sánh LightGBM Phase 5, LightGBM tuned và LightGBM tuned + calendar rescue.

## Phase 10: Chọn model cuối

### Mục tiêu
Chọn model cuối cùng để báo cáo, sau khi đã cải thiện và kiểm tra trên validation.

### Việc cần thực hiện
- Dùng kết quả Phase 9 để chọn candidate tốt nhất theo WAPE validation.
- Dùng test set một lần để đánh giá cuối, không dùng test để tuning tiếp.
- Train lại model cuối trên train + validation nếu cần, rồi đánh giá trên test.
- So sánh model cuối với `yesterday_baseline` trên test.
- Tính MAE, RMSE, WAPE trên test.
- Kiểm tra model cuối có thắng baseline trên test không.
- Kiểm tra test WAPE có lệch quá nhiều so với validation WAPE không.
- Kiểm tra prediction trên test có âm hoặc quá phẳng không.
- Kiểm tra model cuối có rủi ro leakage từ Phase 8 không.
- Ghi lại 21 feature cuối cùng được dùng.
- Ghi lại điểm mạnh, điểm yếu và rủi ro còn lại của model.
- Không chọn model chỉ vì test đẹp nếu validation hoặc leakage không ổn.

### Biểu đồ sử dụng
- Bar chart metric validation/test: so sánh model cuối với baseline.
- Actual vs predicted trên test: xem dự báo bám sát thực tế không.
- Error timeline trên test: xem sai số có tập trung theo giai đoạn không.
- Scatter actual vs predicted trên test: xem model dự báo cao/thấp có cân bằng không.

### Output
- `phase10_final_model_test_predictions.csv`: prediction test của model cuối.
- `phase10_final_model_metrics.csv`: metric validation/test của model cuối và baseline.
- `phase10_final_feature_list.csv`: 21 feature dùng cho model cuối.
- `phase10_final_model_summary.csv`: kết luận model cuối, điểm mạnh, điểm yếu và rủi ro.

## Phase 11: Chuẩn bị báo cáo model

### Mục tiêu
Tổng hợp kết quả model thành bảng và biểu đồ dùng trực tiếp cho báo cáo, không train lại, không tuning và không chọn lại model.

### Việc cần thực hiện
- Load các output chính từ Phase 1-10.
- Nói rõ bài toán là dự báo doanh thu theo ngày.
- Nói rõ grain của model là 1 dòng = 1 ngày.
- Nói rõ cách chia train, validation, test theo thời gian.
- Nói rõ baseline chính là `yesterday_baseline`.
- Nói rõ model cuối là model nào.
- Nói rõ metric chính là WAPE và lý do chọn metric.
- Nói rõ model tốt hơn baseline bao nhiêu trên test.
- Nói rõ test set chỉ được dùng một lần ở Phase 10 để đánh giá cuối.
- Ghi lại điểm mạnh, điểm yếu và rủi ro còn lại của model.
- Ghi lại danh sách feature cuối cùng từ Phase 10.
- Dùng feature importance từ Phase 8 để làm phần giải thích model.

### Biểu đồ sử dụng
- Pipeline overview: tóm tắt Phase 0-10.
- Bar chart WAPE validation/test: so sánh final model với baseline, có số phần trăm trên cột.
- Top 10 feature importance: feature quan trọng nhất dùng để giải thích model.

### Output
- `phase11_model_report_summary.csv`: bảng tóm tắt bài toán, split, baseline, final model, metric và kết quả chính.
- `phase11_metric_report_table.csv`: bảng metric gọn để đưa vào báo cáo.
- `phase11_feature_report_table.csv`: top feature importance dùng cho báo cáo.
- `phase11_report_conclusion.csv`: kết luận ngắn về performance, model selection, điểm mạnh, điểm yếu và rủi ro.
- `phase11_pipeline_overview.csv`: bảng pipeline overview.
- `phase11_metric_summary.png`: biểu đồ WAPE final model vs baseline.
- `phase11_top_feature_importance.png`: biểu đồ top 10 feature importance.
- `phase11_pipeline_overview.png`: biểu đồ pipeline overview.
