# Đánh Giá Model Dự Báo Doanh Thu Hàng Ngày - Kế hoạch Eval

## Mục tiêu
Đánh giá model cuối cùng đã được chọn ở bước modeling để biết model có đủ tốt, ổn định, dễ giải thích và đáng tin cậy để đưa vào báo cáo Datathon hay không.

Eval không phải là train model lại. Eval chỉ đọc kết quả đã có, kiểm tra metric, phân tích lỗi, so sánh với baseline và chuẩn bị kết luận dễ hiểu.

## Nguyên tắc trình bày notebook eval
- Mỗi cell chỉ làm một việc rõ ràng: load, kiểm tra, tính metric, vẽ biểu đồ, lưu bảng hoặc kết luận.
- Không gộp nhiều việc vào một cell dài.
- Không tuning model trong notebook eval.
- Không chọn lại model bằng test.
- Test set chỉ được dùng để đánh giá cuối cùng, đúng như Phase 10 của modeling.
- Mọi bảng/biểu đồ phải có mục đích rõ: giúp trả lời một câu hỏi đánh giá cụ thể.

## Quy trình
- **Phase 0**: Setup - chuẩn bị thư viện, đường dẫn, cấu hình chung
- **Phase 1**: Load output từ modeling - đọc prediction, metric, feature và summary
- **Phase 2**: Kiểm tra input eval - đảm bảo file đủ, cột đủ, dữ liệu không lỗi
- **Phase 3**: Chốt metric eval - nhắc lại WAPE, MAE, RMSE và vai trò từng metric
- **Phase 4**: Đánh giá performance tổng thể - final model vs baseline trên validation/test
- **Phase 5**: Phân tích prediction trên test - actual vs predicted, scatter, residual
- **Phase 6**: Phân tích lỗi theo thời gian - ngày, tháng, giai đoạn lỗi lớn
- **Phase 7**: Phân tích lỗi theo nhóm doanh thu - low/mid/high revenue
- **Phase 8**: Kiểm tra độ ổn định và rủi ro - validation vs test, prediction âm, prediction quá phẳng
- **Phase 9**: Giải thích model cho báo cáo - feature importance và ý nghĩa nghiệp vụ
- **Phase 10**: Kết luận eval - điểm mạnh, điểm yếu, rủi ro và khuyến nghị
- **Phase 11**: Chuẩn bị bảng/biểu đồ báo cáo eval - output sạch để đưa vào slide/report

## Input
- `report_8_6_2026/model_outputs/tables/phase10_final_model_test_predictions.csv`
- `report_8_6_2026/model_outputs/tables/phase10_final_model_metrics.csv`
- `report_8_6_2026/model_outputs/tables/phase10_final_feature_list.csv`
- `report_8_6_2026/model_outputs/tables/phase10_final_model_summary.csv`
- `report_8_6_2026/model_outputs/tables/phase11_metric_report_table.csv`
- `report_8_6_2026/model_outputs/tables/phase11_feature_report_table.csv`
- `report_8_6_2026/model_outputs/tables/phase11_model_report_summary.csv`
- `report_8_6_2026/model_outputs/tables/phase11_report_conclusion.csv`

## Output
- Notebook eval trình bày rõ ràng theo từng phase.
- Bảng metric eval cuối cùng.
- Bảng lỗi lớn nhất trên test.
- Bảng lỗi theo tháng, weekday và nhóm doanh thu.
- Biểu đồ actual vs predicted trên test.
- Biểu đồ error timeline trên test.
- Biểu đồ scatter actual vs predicted.
- Biểu đồ final model vs baseline.
- Bảng kết luận eval dùng trực tiếp cho báo cáo.

---

## Phase 0: Setup

### Mục tiêu
Chuẩn bị môi trường để đọc output từ modeling và tạo bảng/biểu đồ eval.

### Việc cần thực hiện
- Import thư viện cần dùng: `pandas`, `numpy`, `matplotlib`, `seaborn`.
- Cấu hình display để xem bảng dễ hơn.
- Định nghĩa đường dẫn:
  - `MODEL_TABLE_DIR`: nơi chứa output từ `report_8_6_2026`.
  - `EVAL_TABLE_DIR`: nơi lưu bảng eval của `report_10_6_2026`.
  - `EVAL_FIG_DIR`: nơi lưu biểu đồ eval.
- Tạo thư mục output nếu chưa có.
- Định nghĩa tên cột chính:
  - `Date`
  - `Revenue`
  - `final_model_prediction`
  - `yesterday_baseline`

### Output
- Không lỗi import.
- In ra các đường dẫn chính.
- Tạo được thư mục output eval.

---

## Phase 1: Load output từ modeling

### Mục tiêu
Đọc toàn bộ file cần dùng để đánh giá model cuối cùng.

### Việc cần thực hiện
- Load prediction test từ `phase10_final_model_test_predictions.csv`.
- Load metric validation/test từ `phase10_final_model_metrics.csv`.
- Load feature list cuối từ `phase10_final_feature_list.csv`.
- Load summary model cuối từ `phase10_final_model_summary.csv`.
- Load bảng report-ready từ Phase 11 nếu cần đối chiếu.
- In `.shape` và `.head()` của từng bảng.

### Output
- DataFrame prediction test.
- DataFrame metric cuối.
- DataFrame feature cuối.
- DataFrame summary model cuối.
- Bảng `phase1_loaded_input_summary.csv` ghi lại file nào đã load, số dòng, số cột.

---

## Phase 2: Kiểm tra input eval

### Mục tiêu
Đảm bảo dữ liệu dùng để eval đủ và đúng trước khi phân tích.

### Việc cần thực hiện
- Kiểm tra các file input có tồn tại không.
- Kiểm tra các cột bắt buộc có đủ không:
  - `Date`
  - `Revenue`
  - `final_model_prediction`
  - `yesterday_baseline`
  - `final_model_error`
  - `final_model_abs_error`
  - `baseline_error`
  - `baseline_abs_error`
- Kiểm tra `Date` parse được dạng ngày.
- Kiểm tra có duplicate date không.
- Kiểm tra có missing prediction không.
- Kiểm tra prediction âm không.
- Kiểm tra test set có đúng là chỉ dùng để đánh giá không bằng cách đọc `test_used_for_tuning` từ summary.

### Output
- `phase2_eval_input_check.csv`: bảng kiểm tra input.
- Nếu có lỗi thiếu file/cột/missing, notebook phải báo rõ lỗi trước khi đi tiếp.

---

## Phase 3: Chốt metric eval

### Mục tiêu
Nhắc lại metric nào dùng để đánh giá và vì sao.

### Việc cần thực hiện
- Dùng WAPE làm metric chính.
- Dùng MAE để hiểu trung bình mỗi ngày sai bao nhiêu tiền.
- Dùng RMSE để phát hiện model có sai nặng ở vài ngày không.
- Không dùng MAPE làm metric chính nếu có ngày doanh thu thấp.
- Tạo bảng giải thích metric bằng ngôn ngữ dễ hiểu:
  - WAPE: sai số theo tỷ lệ tổng doanh thu.
  - MAE: sai số trung bình theo đơn vị tiền.
  - RMSE: phạt nặng lỗi lớn.

### Output
- `phase3_eval_metric_policy.csv`: metric, vai trò, cách hiểu, lý do dùng.

---

## Phase 4: Đánh giá performance tổng thể

### Mục tiêu
Trả lời câu hỏi: model cuối có tốt hơn baseline không?

### Việc cần thực hiện
- Lấy metric validation/test của final model và baseline.
- So sánh WAPE, MAE, RMSE giữa final model và `yesterday_baseline`.
- Tính mức cải thiện:
  - Cải thiện tuyệt đối: `baseline_wape - final_model_wape`.
  - Cải thiện tương đối: `(baseline_wape - final_model_wape) / baseline_wape`.
- Kiểm tra test WAPE có lệch quá xa validation WAPE không.
- Ghi kết luận ngắn:
  - model thắng baseline hay không.
  - thắng nhiều hay ít.
  - test có ổn so với validation không.

### Biểu đồ sử dụng
- Bar chart WAPE final model vs baseline trên validation/test.
- Bar chart MAE final model vs baseline trên test.

### Output
- `phase4_eval_metric_comparison.csv`
- `phase4_eval_performance_summary.csv`
- `phase4_wape_model_vs_baseline.png`
- `phase4_mae_model_vs_baseline.png`

---

## Phase 5: Phân tích prediction trên test

### Mục tiêu
Xem prediction của model cuối có bám sát doanh thu thực tế không.

### Việc cần thực hiện
- Vẽ actual revenue và final model prediction theo thời gian.
- Vẽ thêm baseline để so sánh nếu biểu đồ vẫn dễ đọc.
- Vẽ scatter actual vs predicted:
  - điểm càng gần đường chéo càng tốt.
  - nếu model hay dự báo thấp/cao, scatter sẽ lệch khỏi đường chéo.
- Tính residual:
  - `error = actual - prediction`
  - error dương: model dự báo thấp hơn thực tế.
  - error âm: model dự báo cao hơn thực tế.
- Vẽ residual distribution để xem lỗi tập trung quanh 0 hay lệch một phía.

### Biểu đồ sử dụng
- Actual vs predicted timeline.
- Scatter actual vs predicted.
- Residual distribution.

### Output
- `phase5_test_prediction_detail.csv`
- `phase5_prediction_summary.csv`
- `phase5_actual_vs_predicted_test.png`
- `phase5_scatter_actual_predicted_test.png`
- `phase5_residual_distribution_test.png`

---

## Phase 6: Phân tích lỗi theo thời gian

### Mục tiêu
Tìm giai đoạn nào model sai nhiều nhất.

### Việc cần thực hiện
- Tính lỗi theo từng ngày trên test.
- Lấy top ngày có absolute error lớn nhất.
- Tính WAPE/MAE theo tháng.
- Tính WAPE/MAE theo weekday.
- Kiểm tra lỗi có tập trung vào một vài tháng hoặc một vài ngày trong tuần không.
- So sánh lỗi của final model với baseline ở các nhóm thời gian.

### Biểu đồ sử dụng
- Error timeline trên test.
- Bar chart top error days.
- Line chart hoặc bar chart WAPE theo tháng.
- Bar chart WAPE theo weekday.

### Output
- `phase6_top_error_days.csv`
- `phase6_error_by_month.csv`
- `phase6_error_by_weekday.csv`
- `phase6_error_timeline_test.png`
- `phase6_top_error_days.png`
- `phase6_monthly_wape.png`
- `phase6_weekday_wape.png`

---

## Phase 7: Phân tích lỗi theo nhóm doanh thu

### Mục tiêu
Xem model yếu ở ngày doanh thu thấp, trung bình hay cao.

### Việc cần thực hiện
- Chia test set thành 3 nhóm theo doanh thu thật:
  - `low_revenue`
  - `mid_revenue`
  - `high_revenue`
- Tính MAE, WAPE, win rate so với baseline cho từng nhóm.
- Kiểm tra nhóm nào có WAPE cao nhất.
- Kiểm tra model có hay dự báo quá cao ở nhóm doanh thu thấp không.
- Kiểm tra model có bỏ lỡ các ngày doanh thu rất cao không.

### Biểu đồ sử dụng
- Boxplot absolute error theo nhóm doanh thu.
- Bar chart WAPE theo nhóm doanh thu.

### Output
- `phase7_error_by_revenue_group.csv`
- `phase7_revenue_group_summary.csv`
- `phase7_abs_error_by_revenue_group.png`
- `phase7_wape_by_revenue_group.png`

---

## Phase 8: Kiểm tra độ ổn định và rủi ro

### Mục tiêu
Kiểm tra model có dấu hiệu rủi ro khi đưa vào báo cáo không.

### Việc cần thực hiện
- Kiểm tra prediction âm:
  - doanh thu không nên âm.
- Kiểm tra prediction quá phẳng:
  - so sánh `std(prediction)` với `std(actual)`.
  - nếu prediction std quá thấp, model có thể dự báo quá an toàn.
- Kiểm tra bias:
  - mean error > 0: model hay dự báo thấp.
  - mean error < 0: model hay dự báo cao.
- Kiểm tra validation WAPE và test WAPE có lệch quá nhiều không.
- Ghi rủi ro còn lại:
  - ngày doanh thu bất thường.
  - tháng có distribution shift.
  - nhóm doanh thu thấp/cao nếu WAPE cao.

### Output
- `phase8_eval_risk_check.csv`
- `phase8_eval_risk_summary.csv`

---

## Phase 9: Giải thích model cho báo cáo

### Mục tiêu
Giải thích model đang dựa vào những feature nào và các feature đó có hợp lý không.

### Việc cần thực hiện
- Load `phase11_feature_report_table.csv` hoặc `phase8_feature_importance.csv`.
- Lấy top feature importance.
- Nhóm feature theo loại:
  - lag revenue.
  - rolling revenue.
  - calendar.
  - gross profit/margin.
  - web traffic.
- Viết giải thích đơn giản:
  - feature lịch sử doanh thu quan trọng là hợp lý với bài toán dự báo daily revenue.
  - calendar feature giúp model hiểu pattern theo ngày/tháng nếu có.
  - web traffic có thể phản ánh nhu cầu trước khi doanh thu xảy ra.
- Kiểm tra có feature nào khó giải thích hoặc có rủi ro leakage không.

### Biểu đồ sử dụng
- Bar chart top 10 feature importance.

### Output
- `phase9_eval_feature_explanation.csv`
- `phase9_top_feature_importance.png`

---

## Phase 10: Kết luận eval

### Mục tiêu
Tổng hợp kết quả đánh giá thành kết luận ngắn, dễ đưa vào report.

### Việc cần thực hiện
- Viết kết luận về performance:
  - final model test WAPE bao nhiêu.
  - baseline test WAPE bao nhiêu.
  - model cải thiện bao nhiêu so với baseline.
- Viết kết luận về độ ổn định:
  - test có tương đương validation không.
  - prediction có âm không.
  - prediction có quá phẳng không.
- Viết điểm mạnh:
  - thắng baseline.
  - dùng time-based split.
  - test chỉ dùng cuối cùng.
- Viết điểm yếu:
  - vẫn sai ở ngày biến động mạnh.
  - nhóm doanh thu nào còn yếu nếu có.
- Viết khuyến nghị:
  - nếu dùng thực tế, nên theo dõi lỗi theo tháng và nhóm doanh thu.
  - cần cập nhật model khi dữ liệu mới có distribution shift.

### Output
- `phase10_eval_conclusion.csv`
- `phase10_eval_report_summary.csv`

---

## Phase 11: Chuẩn bị bảng và biểu đồ báo cáo eval

### Mục tiêu
Tạo bộ output cuối cùng dùng trực tiếp cho slide/report.

### Việc cần thực hiện
- Gom các bảng quan trọng thành bảng nhỏ dễ đọc.
- Đảm bảo biểu đồ có tên rõ ràng.
- Không tạo lại model.
- Không thay đổi metric.
- Không chọn lại model.
- Tạo checklist output cuối.

### Output
- `eval_metric_summary.csv`
- `eval_error_summary.csv`
- `eval_risk_summary.csv`
- `eval_feature_explanation.csv`
- `eval_final_conclusion.csv`
- `eval_actual_vs_predicted.png`
- `eval_error_timeline.png`
- `eval_wape_model_vs_baseline.png`
- `eval_top_feature_importance.png`

---

## Checklist cuối
- Đã load đúng output từ modeling.
- Không train lại model trong notebook eval.
- Không tuning bằng test.
- Có so sánh final model với baseline.
- Có WAPE, MAE, RMSE.
- Có phân tích lỗi theo thời gian.
- Có phân tích lỗi theo nhóm doanh thu.
- Có kiểm tra prediction âm và prediction quá phẳng.
- Có giải thích feature importance.
- Có kết luận điểm mạnh, điểm yếu và rủi ro.
