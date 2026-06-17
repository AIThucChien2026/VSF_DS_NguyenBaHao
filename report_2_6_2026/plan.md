# Plan train model - Ngày 02/06/2026

Tài liệu này mô tả kế hoạch tiếp theo sau phần chuẩn bị dữ liệu và chọn feature ngày 01/06/2026. Mục tiêu là huấn luyện, so sánh và chọn mô hình dự báo `Revenue` và `COGS` theo ngày dựa trên feature set đã được kiểm tra leakage-safe.

---

## 1. Mục tiêu modeling

### 1.1. Bài toán

- Dự báo `Revenue` theo ngày.
- Dự báo `COGS` theo ngày.
- Sử dụng dữ liệu lịch sử đã được chuẩn bị ở grain `Date`.
- Dự báo cho horizon có sẵn trong `sample_submission.csv`.

### 1.2. Input chính

Hai file modeling chính được xuất ở cuối notebook chuẩn bị dữ liệu ngày 01/06/2026:

- `report_1_6_2026/outputs/data_preparation_daily/train.csv`
- `report_1_6_2026/outputs/data_preparation_daily/test.csv`
- `report_1_6_2026/outputs/feature_analysis_focused/selected_features_final.csv`
- `report_1_6_2026/outputs/feature_analysis_focused/wrapper_model_summary.csv`

Ghi chú:

- `train.csv` gồm dữ liệu lịch sử đến hết 2020 để train và rolling validation; thực tế bắt đầu từ 2012-07-04 theo min date của dataset.
- `test.csv` gồm dữ liệu holdout 2021-2022 có nhãn thật để đánh giá offline.
- `test.csv` ở đây khác với provided test/submission horizon trong `sample_submission.csv`.
- Notebook modeling ngày 02/06/2026 chỉ load các file này, không tự chia train/test lại.

### 1.3. Feature set khởi điểm

Feature set chính gồm 11 biến đã được wrapper time-aware giữ lại:

| Nhóm | Feature |
| :--- | :--- |
| Target lag | `Revenue_lag_1d`, `COGS_lag_1d` |
| Demand | `order_count_lag_1d` |
| Geography | `order_district_count_lag_1d` |
| Shipment | `shipment_count_lag_1d`, `shipping_fee_sum_lag_1d` |
| Return/refund | `return_count_rolling_7d_mean`, `refund_amount_sum_rolling_7d_mean` |
| Review | `review_count_rolling_7d_mean` |
| Calendar | `month`, `day_of_week` |

Feature set mở rộng chỉ được thử sau khi baseline modeling ổn định, gồm các nhóm `payment`, `discount`, `inventory`, `traffic`, `promo/event` nếu chứng minh được cải thiện validation mà không tăng rủi ro leakage.

---

## 2. Chọn model và lý do

### 2.1. Model chính đề xuất: LightGBM Regressor

LightGBM là model chính nên thử đầu tiên trong nhóm model mạnh vì:

- Phù hợp với dữ liệu tabular có feature lag, rolling, count, amount và calendar.
- Bắt được quan hệ phi tuyến và interaction giữa feature tốt hơn Ridge.
- Không yêu cầu scale feature nghiêm ngặt như linear model.
- Chịu được skew/outlier tốt hơn linear model nếu cấu hình regularization hợp lý.
- Train nhanh, phù hợp để chạy nhiều rolling-origin window và tune hyperparameter.
- Có thể train riêng 2 mô hình cho `Revenue` và `COGS`, giúp mỗi target có cấu hình tối ưu riêng.

Điều kiện: cần thêm dependency `lightgbm`. Nếu môi trường không cài được LightGBM, dùng fallback theo thứ tự ở mục 2.4.

### 2.2. Model baseline bắt buộc

Không nhảy thẳng vào model phức tạp. Cần có các baseline để biết model mới thật sự tốt hơn:

| Model | Vai trò | Lý do |
| :--- | :--- | :--- |
| Naive lag-1 | Baseline tối thiểu | Dự báo ngày mai gần bằng ngày hôm trước; nếu model không hơn baseline này thì feature/model chưa đạt |
| Ridge Regression | Baseline tuyến tính chính | Đã dùng trong wrapper, dễ giải thích, ổn định với feature ít |
| ElasticNet | Baseline tuyến tính có chọn lọc hệ số | Kiểm tra xem regularization L1/L2 có giúp loại nhiễu tốt hơn Ridge không |

### 2.3. Model ứng viên để so sánh

| Model | Khi nào dùng | Điểm mạnh | Rủi ro |
| :--- | :--- | :--- | :--- |
| LightGBM Regressor | Model chính | Nhanh, mạnh với tabular, bắt interaction tốt | Cần cài thêm package, cần tune chống overfit |
| XGBoost Regressor | Ứng viên thay thế LightGBM | Mạnh, ổn định, phổ biến | Train có thể chậm hơn |
| CatBoost Regressor | Ứng viên nếu có categorical mở rộng | Xử lý categorical tốt, ít preprocessing | Cần cài package, train có thể nặng |
| HistGradientBoostingRegressor | Fallback sklearn | Có sẵn nếu cài scikit-learn, tree boosting tương đối mạnh | Ít linh hoạt hơn LightGBM/XGBoost |
| RandomForestRegressor | Sanity check nonlinear | Ít tune, dễ chạy | Dự báo chuỗi thời gian thường kém boosting, extrapolate yếu |

### 2.4. Quyết định model theo môi trường

1. Nếu cài được `lightgbm`: chọn `LGBMRegressor` làm model chính.
2. Nếu không có LightGBM nhưng có `xgboost`: dùng `XGBRegressor`.
3. Nếu không có cả hai nhưng có `catboost`: dùng `CatBoostRegressor`.
4. Nếu chỉ có `scikit-learn`: dùng `HistGradientBoostingRegressor` làm model tree boosting chính, kèm Ridge/ElasticNet.

### 2.5. Chiến lược target

- Train 2 model riêng:
  - `model_revenue` dự báo `Revenue`.
  - `model_cogs` dự báo `COGS`.
- Không train multi-output ở vòng đầu vì `Revenue` và `COGS` có phân phối khác nhau, error scale khác nhau và có thể cần hyperparameter riêng.
- Sau khi model riêng ổn định, có thể thử thêm ràng buộc business như kiểm tra `COGS <= Revenue` hoặc post-processing nhẹ nếu dự báo vi phạm quá nhiều.

---

## 3. Metric đánh giá

### 3.1. Metric chính

| Metric | Vai trò | Lý do |
| :--- | :--- | :--- |
| WAPE | Metric chính | Dễ diễn giải theo phần trăm sai số tổng, phù hợp forecasting doanh thu |
| MAE | Metric phụ | Cho biết sai lệch tiền trung bình mỗi ngày |
| RMSE | Metric phụ | Nhạy với ngày sai rất lớn, dùng để bắt outlier error |
| Bias | Metric kiểm tra | Biết model có dự báo thấp/cao hệ thống không |

### 3.2. Công thức cần dùng

```text
WAPE = sum(abs(y_true - y_pred)) / sum(abs(y_true))
MAE  = mean(abs(y_true - y_pred))
RMSE = sqrt(mean((y_true - y_pred)^2))
Bias = mean(y_pred - y_true)
```

### 3.3. Ngưỡng thành công vòng đầu

Model được coi là tốt hơn baseline nếu:

- WAPE validation thấp hơn Ridge wrapper final cho cả `Revenue` và `COGS`.
- Không chỉ tốt trung bình, mà ít nhất 3/5 rolling-origin window phải cải thiện.
- Bias không lệch quá lớn theo một chiều.
- Error không bùng lên ở các tháng hoặc năm cụ thể.

Baseline hiện tại từ ngày 01/06/2026:

| Target | Baseline Ridge wrapper final WAPE | MAE |
| :--- | ---: | ---: |
| `Revenue` | 0.1987 | 673,235 |
| `COGS` | 0.2007 | 586,174 |

---

## 4. Nguyên tắc modeling

- Giữ nguyên nguyên tắc leakage-safe: không dùng same-day source feature chưa shift.
- Split train/test đã được thực hiện ở cuối notebook chuẩn bị dữ liệu ngày 01/06/2026, không chia lại trong notebook modeling.
- Modeling notebook chỉ load `train.csv` và `test.csv`; nếu cần đổi split thì quay lại chỉnh ở bước chuẩn bị dữ liệu để giữ pipeline rõ ràng.
- Không để cùng một năm/ngày xuất hiện đồng thời trong train và test.
- Không dùng `sample_submission` làm nhãn train.
- Mọi imputation, scaling, target transform phải fit trên train window rồi mới apply sang validation/test.
- Không tune trực tiếp trên final validation duy nhất; dùng rolling-origin CV để tránh chọn model ăn may.
- Không mở rộng feature set trước khi baseline model với 11 feature chạy ổn.
- Không chọn model chỉ vì một metric đẹp; phải xem error theo thời gian và theo slice.
- Không cap target ở vòng đầu. Nếu thử `log1p`, phải report cả kết quả inverse-transform và metric trên scale gốc.

### 4.1. Split train/test đã chốt ở bước chuẩn bị dữ liệu

Phần chia dữ liệu thuộc cuối pipeline chuẩn bị dữ liệu ngày 01/06/2026, sau khi đã clean data, tạo target, tạo feature leakage-safe và chọn feature final. Report ngày 02/06/2026 không tự chia lại để tránh mỗi notebook dùng một split khác nhau.

| File | Thời gian | Vai trò | Ghi chú |
| :--- | :--- | :--- | :--- |
| `train.csv` | 2012-07-04 đến 2020-12-31 | Train/development | Dùng để train baseline, rolling validation và tune model |
| `test.csv` | 2021-01-01 đến 2022-12-31 | Offline holdout test | Chỉ dùng đánh giá cuối sau khi chọn model/hyperparameter |

Lý do không dùng `test 2020-2022`: năm 2020 đã nằm trong `train.csv`, nên nếu đưa tiếp vào `test.csv` thì metric đánh giá sẽ overlap thời gian. Nếu muốn test bắt đầu từ 2020, cần đổi split ở notebook chuẩn bị dữ liệu thành train 2012-2019 và test 2020-2022.

---

## 5. Phase triển khai chi tiết

### Phase 0 - Setup modeling notebook

Mục tiêu: tạo môi trường và cấu trúc notebook/script rõ ràng để chạy modeling có audit.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M00.1 | Tạo notebook `report_2_6_2026/train_model.ipynb` | Notebook modeling |
| M00.2 | Import thư viện và helper | Environment ready |
| M00.3 | Kiểm tra dependency model: `sklearn`, `lightgbm`, `xgboost`, `catboost` | `dependency_report` |
| M00.4 | Khai báo path input/output | `MODEL_OUT_DIR` |
| M00.5 | Khai báo constants: `DATE_COL`, `TARGETS`, `RANDOM_SEED`, metric list | Config block |
| M00.6 | Tạo helper metric `wape`, `mae`, `rmse`, `bias` | Metric functions |
| M00.7 | Tạo helper hiển thị bảng/plot | Display helpers |

Ghi chú:

- Nếu thiếu `scikit-learn`, cần cập nhật `requirements.txt`.
- Nếu chọn LightGBM, cần thêm `lightgbm` vào requirements hoặc ghi rõ fallback.

### Phase 1 - Load train/test artifact và kiểm tra readiness

Mục tiêu: đảm bảo dữ liệu đầu vào cho modeling đã được chuẩn bị đúng schema, đúng thời gian, không mất feature và không cần chia lại.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M01.1 | Load `report_1_6_2026/outputs/data_preparation_daily/train.csv` và `report_1_6_2026/outputs/data_preparation_daily/test.csv` | `train_df`, `test_df` |
| M01.2 | Load `selected_features_final.csv` | Feature list |
| M01.3 | Kiểm tra 11 selected features có trong cả `train_df/test_df` | `feature_availability_report` |
| M01.4 | Kiểm tra `Date`, `Revenue`, `COGS` tồn tại và đúng dtype | `input_schema_report` |
| M01.5 | Kiểm tra target không nằm trong feature columns khi fit model | `leakage_schema_check` |
| M01.6 | Kiểm tra `train.csv` kết thúc trước `test.csv` và không overlap ngày | `time_split_check` |
| M01.7 | Kiểm tra missing theo train/test trước imputation | `model_input_missing_report` |
| M01.8 | Vẽ quick target trend train vs test | Target split plot |

Điều kiện qua phase:

- Không thiếu selected feature.
- Không có target leakage column trong `X_train/X_test`.
- Train/test không overlap theo ngày.
- Imputer/scaler chỉ fit trên train fold hoặc train full, rồi mới apply sang validation/test.

### Phase 2 - Tạo baseline dự báo

Mục tiêu: tạo sàn so sánh trước khi chạy model phức tạp.

Subtask:

| Subtask | Model | Việc làm | Output |
| :--- | :--- | :--- | :--- |
| M02.1 | Naive lag-1 | Dự báo bằng `Revenue_lag_1d` và `COGS_lag_1d` | `baseline_naive_report` |
| M02.2 | Seasonal naive 7d | Nếu có lag 7 trong data mở rộng, thử dự báo bằng lag 7 | `baseline_seasonal_report` |
| M02.3 | Ridge | Train Ridge trên 11 feature | `ridge_report` |
| M02.4 | ElasticNet | Train ElasticNet trên 11 feature | `elasticnet_report` |
| M02.5 | Baseline comparison | So sánh WAPE/MAE/RMSE/Bias | `baseline_comparison.csv` |
| M02.6 | Plot prediction vs actual | Vẽ valid actual/pred theo thời gian | Baseline plots |

Ghi chú:

- Ridge/ElasticNet cần scale nếu dùng raw feature. Nếu input đã impute nhưng chưa scale, fit scaler trên train.
- Naive lag không cần fit model.

### Phase 3 - Rolling-origin validation framework

Mục tiêu: đánh giá model đúng kiểu time-series thay vì chỉ một split cố định.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M03.1 | Tạo function sinh rolling windows theo năm | `rolling_windows` |
| M03.2 | Mỗi window: train trên quá khứ, validate trên năm tiếp theo | Window splits |
| M03.3 | Fit preprocessing trong từng window | No leakage preprocessing |
| M03.4 | Fit model trong từng window | Trained fold models |
| M03.5 | Tính metric từng target/từng window | `rolling_metric_report` |
| M03.6 | Tổng hợp mean/std metric | `rolling_summary_report` |
| M03.7 | Vẽ WAPE theo window | Stability chart |

Thiết lập gợi ý:

- Rolling validation chỉ chạy bên trong `train.csv`, ưu tiên windows 2018, 2019, 2020. `test.csv` (2021-2022) chỉ dùng để đánh giá cuối.
- Mỗi target được đánh giá riêng.
- Chỉ chọn model nếu performance ổn định qua nhiều window.

### Phase 4 - Train model chính với feature set 11 biến

Mục tiêu: huấn luyện model mạnh nhưng vẫn kiểm soát overfit.

Subtask:

| Subtask | Model | Việc làm | Output |
| :--- | :--- | :--- | :--- |
| M04.1 | LightGBM default | Train `LGBMRegressor` cấu hình nhẹ | `lgbm_default_report` |
| M04.2 | LightGBM regularized | Thêm regularization, giảm depth/leaf | `lgbm_regularized_report` |
| M04.3 | HistGradientBoosting fallback | Chạy nếu không có LightGBM | `hgb_report` |
| M04.4 | RandomForest sanity | Chạy sanity nonlinear baseline | `rf_report` |
| M04.5 | Compare all models | So sánh với baseline | `model_comparison.csv` |
| M04.6 | Select provisional best | Chọn best theo WAPE + stability | `provisional_best_model.json` |

LightGBM config khởi điểm:

```text
n_estimators: 300-800
learning_rate: 0.03-0.08
num_leaves: 15-63
max_depth: 3-8
min_child_samples: 20-80
subsample: 0.8-1.0
colsample_bytree: 0.8-1.0
reg_alpha: 0-1
reg_lambda: 0.5-5
random_state: fixed
```

Ghi chú:

- Không tune rộng ngay. Vòng đầu chỉ cần biết boosting có thắng baseline ổn định không.
- Nếu default tốt nhưng regularized tốt hơn trên rolling window, chọn regularized.

### Phase 5 - Hyperparameter tuning có kiểm soát

Mục tiêu: tối ưu model đã chọn mà không overfit validation.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M05.1 | Xác định search space hẹp dựa trên Phase 4 | `tuning_config` |
| M05.2 | Manual tuning 5-10 cấu hình đầu | `manual_tuning_report` |
| M05.3 | Random search nhỏ nếu cần | `random_search_report` |
| M05.4 | Chọn cấu hình theo mean WAPE và std WAPE | `best_params.json` |
| M05.5 | Kiểm tra overfit train vs valid | `overfit_check_report` |
| M05.6 | Refit best model trên train full | `best_model_revenue`, `best_model_cogs` |

Thứ tự tune ưu tiên:

1. `learning_rate` và `n_estimators`.
2. `num_leaves`, `max_depth`, `min_child_samples`.
3. `subsample`, `colsample_bytree`.
4. `reg_alpha`, `reg_lambda`.

Không tune:

- Không tune quá nhiều feature set cùng lúc với hyperparameter.
- Không chọn cấu hình chỉ vì thắng một window.

### Phase 6 - Target transform experiment

Mục tiêu: kiểm tra liệu `log1p` target có giúp giảm ảnh hưởng ngày doanh thu rất lớn không.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M06.1 | Train best model trên target raw | `raw_target_report` |
| M06.2 | Train best model trên `log1p(target)` | `log_target_report` |
| M06.3 | Inverse transform bằng `expm1` trước khi tính metric | Predictions scale gốc |
| M06.4 | So sánh WAPE/MAE/RMSE/Bias | `target_transform_comparison.csv` |
| M06.5 | Kiểm tra error ở ngày doanh thu cao | High target slice report |

Quyết định:

- Nếu `log1p` giảm RMSE nhưng làm WAPE/MAE xấu hơn rõ, không chọn.
- Nếu `log1p` giúp ổn định cả WAPE và high-error days, giữ làm candidate chính.

### Phase 7 - Feature set mở rộng sau baseline

Mục tiêu: thử thêm feature ngoài 11 biến chỉ khi model chính đã ổn.

Subtask:

| Subtask | Feature group | Việc làm | Output |
| :--- | :--- | :--- | :--- |
| M07.1 | Payment | Thêm `payment_value_sum_lag_1d` và related selected candidates | `payment_ablation_report` |
| M07.2 | Discount | Thêm rolling discount candidates | `discount_ablation_report` |
| M07.3 | Inventory | Thêm stockout/inventory lag candidates | `inventory_ablation_report` |
| M07.4 | Traffic | Thêm sessions/page views lag candidates | `traffic_ablation_report` |
| M07.5 | Promo/event | Thêm known-now promo/calendar event nếu có | `promo_ablation_report` |
| M07.6 | Group comparison | So sánh từng nhóm theo rolling WAPE | `feature_group_comparison.csv` |

Quy tắc giữ feature group:

- Giữ nếu WAPE giảm rõ ở mean và không làm tăng std window quá nhiều.
- Giữ nếu ít nhất 3/5 windows cải thiện.
- Drop nếu chỉ cải thiện một target nhưng làm target còn lại tệ đáng kể.
- Drop nếu feature importance cao bất thường nhưng giải thích business không hợp lý.

### Phase 8 - Error analysis

Mục tiêu: hiểu model sai ở đâu, không chỉ nhìn metric tổng.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M08.1 | Tạo prediction dataframe valid | `valid_predictions.csv` |
| M08.2 | Tính absolute error, pct error, signed error | Error columns |
| M08.3 | Vẽ actual vs predicted theo thời gian | Trend plot |
| M08.4 | Vẽ residual distribution | Residual plot |
| M08.5 | Phân tích error theo tháng | `error_by_month.csv` |
| M08.6 | Phân tích error theo day_of_week | `error_by_day_of_week.csv` |
| M08.7 | Top 20 ngày sai lớn nhất | `top_error_days.csv` |
| M08.8 | Kiểm tra bias theo giai đoạn 2018-2022 | `bias_by_period.csv` |
| M08.9 | Ghi nhận nguyên nhân nghi ngờ | `error_analysis_notes.md` |

Câu hỏi cần trả lời:

- Model có hay underpredict ngày spike không?
- Model có overpredict ở ngày thấp điểm không?
- Sai số tập trung ở tháng/quý nào?
- `Revenue` và `COGS` sai cùng chiều hay khác chiều?
- Có ngày nào target bất thường cần kiểm tra dữ liệu gốc không?

### Phase 9 - Model interpretation

Mục tiêu: giải thích model đã học gì để kết quả có thể trình bày.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M09.1 | Extract feature importance gain/split | `feature_importance.csv` |
| M09.2 | So sánh importance giữa Revenue và COGS | Importance comparison |
| M09.3 | Permutation importance trên validation | `permutation_importance.csv` |
| M09.4 | Partial dependence hoặc binned effect cho top features | Effect plots |
| M09.5 | Kiểm tra feature quan trọng có hợp lý business không | Interpretation notes |

Ghi chú:

- Feature importance của tree model không dùng làm bằng chứng duy nhất để chọn feature.
- Nếu feature quan trọng nhưng unstable qua window, cần đánh dấu review.

### Phase 10 - Train final model và dự báo test horizon

Mục tiêu: tạo prediction cho horizon trong `sample_submission.csv`.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M10.1 | Load `provided_test_table.csv` hoặc build X_test đúng schema | Test feature table |
| M10.2 | Kiểm tra test có đủ selected features | `test_schema_report` |
| M10.3 | Apply preprocessing fit từ train full | `X_test_ready` |
| M10.4 | Train final model trên train+valid nếu được phép | Final fitted models |
| M10.5 | Predict `Revenue` và `COGS` cho horizon | `test_predictions.csv` |
| M10.6 | Post-process giá trị âm về 0 nếu có | Clean predictions |
| M10.7 | Kiểm tra business sanity: phân phối, min/max, trend | `prediction_sanity_report` |
| M10.8 | Tạo submission theo format yêu cầu | `submission.csv` |

Ghi chú:

- Nếu test horizon cần recursive lag target tương lai, phải ghi rõ chiến lược recursive forecasting.
- Nếu chỉ có feature biết trước và lag quá khứ đến ngày cuối train, cần kiểm tra từng ngày horizon có feature hợp lệ không.
- Không dùng target giả trong `sample_submission` để train.

### Phase 11 - Export artifacts và report

Mục tiêu: lưu đủ output để review, tái chạy và trình bày.

Subtask:

| Subtask | Việc làm | Output |
| :--- | :--- | :--- |
| M11.1 | Lưu model bằng `joblib` hoặc pickle | `models/*.joblib` |
| M11.2 | Lưu preprocessing objects | `preprocessors/*.joblib` |
| M11.3 | Lưu model comparison | `reports/model_comparison.csv` |
| M11.4 | Lưu rolling metrics | `reports/rolling_metric_report.csv` |
| M11.5 | Lưu error analysis | `reports/error_analysis/*.csv` |
| M11.6 | Lưu feature importance | `reports/feature_importance.csv` |
| M11.7 | Lưu prediction plots | `images/*.png` |
| M11.8 | Lưu submission | `submission.csv` |
| M11.9 | Tạo `export_manifest.csv` | Manifest |
| M11.10 | Viết markdown summary | `modeling_report.md` |

---

## 6. Cấu trúc thư mục đề xuất

```text
report_2_6_2026/
  plan.md
  train_model.ipynb
  modeling_report.md
  submission.csv
  models/
    revenue_model.joblib
    cogs_model.joblib
  preprocessors/
    revenue_preprocessor.joblib
    cogs_preprocessor.joblib
  reports/
    dependency_report.csv
    model_input_missing_report.csv
    baseline_comparison.csv
    model_comparison.csv
    rolling_metric_report.csv
    rolling_summary_report.csv
    best_params.json
    feature_group_comparison.csv
    feature_importance.csv
    prediction_sanity_report.csv
    export_manifest.csv
  images/
    target_split_trend.png
    valid_actual_vs_pred_revenue.png
    valid_actual_vs_pred_cogs.png
    residual_distribution_revenue.png
    residual_distribution_cogs.png
    wape_by_window.png
```

---

## 7. Cell plan chi tiết cho notebook

| Cell | Phase | Subtask | Input | Output |
| :--- | :--- | :--- | :--- | :--- |
| S01 | Setup | Import libraries | Python env | Imports |
| S02 | Setup | Define paths | Project root | Path constants |
| S03 | Setup | Dependency check | Import attempts | `dependency_report` |
| S04 | Setup | Define constants | Manual config | `TARGETS`, `RANDOM_SEED` |
| S05 | Setup | Define metric helpers | Code | Metric functions |
| S06 | Setup | Define plotting helpers | Code | Plot helpers |
| D01 | Readiness | Load `train.csv` và `test.csv` | CSV files | `train_df`, `test_df` |
| D02 | Readiness | Load selected features | `selected_features_final.csv` | `selected_features` |
| D03 | Readiness | Validate feature schema | `train_df/test_df` | Schema report |
| D04 | Readiness | Validate missing/leakage/split | `train_df/test_df` | Readiness reports |
| B01 | Baseline | Naive lag model | X/y | Naive metrics |
| B02 | Baseline | Ridge model | X/y | Ridge metrics |
| B03 | Baseline | ElasticNet model | X/y | ElasticNet metrics |
| B04 | Baseline | Compare baselines | Metric tables | Baseline comparison |
| CV01 | Rolling CV | Build rolling windows | Dates | Window table |
| CV02 | Rolling CV | Run baseline rolling CV | Feature table | Baseline rolling report |
| CV03 | Rolling CV | Run candidate model rolling CV | Feature table | Candidate rolling report |
| M01 | Modeling | Train LightGBM default | X/y | Default model report |
| M02 | Modeling | Train LightGBM regularized | X/y | Regularized report |
| M03 | Modeling | Train fallback model if needed | X/y | Fallback report |
| M04 | Modeling | Compare all models | Reports | Model comparison |
| T01 | Tuning | Manual tuning | Search config | Manual tuning report |
| T02 | Tuning | Random search small | Search config | Random search report |
| T03 | Tuning | Select best params | Metric reports | `best_params.json` |
| E01 | Error | Build validation predictions | Best model | `valid_predictions.csv` |
| E02 | Error | Error by month/day | Predictions | Error slice reports |
| E03 | Error | Plot actual vs predicted | Predictions | Plots |
| I01 | Interpret | Feature importance | Best model | Importance report |
| I02 | Interpret | Permutation importance | Best model, valid | Permutation report |
| P01 | Predict | Build/load test features | Test artifacts | X_test |
| P02 | Predict | Predict horizon | Final models | Test predictions |
| P03 | Predict | Create submission | Predictions | `submission.csv` |
| R01 | Export | Save models/reports | Artifacts | Output folder |
| R02 | Export | Write final modeling summary | Reports | `modeling_report.md` |

---

## 8. Rủi ro và cách kiểm soát

| Rủi ro | Tác động | Cách kiểm soát |
| :--- | :--- | :--- |
| Leakage từ feature same-day | Metric đẹp giả | Dùng feature catalog và leakage schema check |
| Overfit rolling windows | Model yếu khi dự báo thật | Rolling-origin CV, regularization, chọn theo mean/std |
| Dependency thiếu LightGBM | Không chạy được model chính | Có fallback XGBoost/CatBoost/HistGradientBoosting |
| Test horizon thiếu lag target | Không predict được nhiều ngày tương lai | Thiết kế recursive forecasting hoặc chỉ dùng feature có sẵn |
| Target spike lớn | MAE/WAPE biến động | Error analysis theo top error days và thử `log1p` |
| Dự báo âm | Submission sai business | Post-process `max(pred, 0)` và report số dòng bị chỉnh |
| `COGS > Revenue` quá nhiều | Vi phạm business sanity | Tạo sanity report, cân nhắc post-processing sau khi đánh giá |

---

## 9. Definition of Done

Modeling phase được coi là hoàn thành khi:

- Có notebook `train_model.ipynb` chạy từ đầu đến cuối.
- Có ít nhất 3 baseline: naive lag-1, Ridge, ElasticNet.
- Có ít nhất 1 model nonlinear/tree boosting được train và so sánh.
- Có rolling-origin validation report cho `Revenue` và `COGS`.
- Có bảng `model_comparison.csv` với WAPE, MAE, RMSE, Bias.
- Có error analysis theo thời gian, tháng, day-of-week và top error days.
- Có feature importance/interpretation cho model tốt nhất.
- Có prediction cho provided test horizon.
- Có `submission.csv` đúng format.
- Có `modeling_report.md` giải thích model được chọn, vì sao chọn, metric đạt được, rủi ro còn lại.
- Có `export_manifest.csv` liệt kê toàn bộ artifact.

---

## 10. Quyết định khởi đầu

Quyết định cho vòng modeling đầu tiên:

- Model baseline chính: Ridge Regression trên 11 selected features.
- Model chính để thử: LightGBM Regressor, train riêng cho `Revenue` và `COGS`.
- Model fallback nếu thiếu dependency: HistGradientBoostingRegressor của scikit-learn.
- Metric chọn model: WAPE trung bình trên rolling-origin windows.
- Metric phụ bắt buộc: MAE, RMSE, Bias.
- Feature set đầu tiên: 11 feature đã được wrapper giữ.
- Feature mở rộng: chỉ thử sau khi model chính vượt baseline và error analysis hoàn tất.
