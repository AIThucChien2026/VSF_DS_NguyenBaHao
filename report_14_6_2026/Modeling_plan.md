# Kế Hoạch Modeling
## Dự đoán order có bị trả lại tại thời điểm đặt hàng

## 1. Contract

- Grain: **1 dòng = 1 `order_id` = 1 label**.
- Target: `returned_label`, lấy từ `orders.order_status`.
- Prediction time: thời điểm order được đặt.
- Chỉ sử dụng feature đã pass centralized FE leakage gate.
- Primary metric: PR-AUC.
- Outer validation dùng chọn champion và threshold.
- Test chỉ đánh giá một lần sau khi khóa toàn bộ cấu hình.

## 2. Input

Modeling đọc:

- `feature_cols_core.csv`
- `feature_cols_v1.csv`
- `feature_cols_experimental.csv`
- `phase4_leakage_gate.csv`
- `phase4_feature_selection_report.csv`
- `phase5_preprocessing_policy.csv`
- `fe_readiness_checklist.csv`
- Ba raw temporal splits.

Không đọc `returns.csv` hoặc bất kỳ return-detail field nào.

## Phase 1 - Modeling Contract

- Load feature sets và FE readiness.
- Load leakage gate.
- Tạo SHA-256 manifest cho toàn bộ input.
- Fail nếu feature mang action `BAN_LEAKAGE` xuất hiện trong feature set.

## Phase 2 - Data Audit

- Kiểm tra exact schema.
- Target chỉ có 0/1.
- Một dòng cho mỗi order.
- Không overlap giữa split.
- Train trước validation, validation trước test.
- Banned feature không xuất hiện trong raw split.
- Mọi banned feature có reason trong leakage audit.

## Phase 3 - Preprocessing & Temporal CV

Preprocessing policy:

- Numeric: median → StandardScaler.
- Categorical: most frequent → OneHotEncoder.
- Binary/multi-hot: most frequent → passthrough.
- `payment_value`: thêm bốn quantile bins bằng `KBinsDiscretizer` trong pipeline;
  không dùng cột bucket đã tính trước.

Quan trọng:

- Preprocessing luôn nằm trong model pipeline.
- GridSearch và RandomizedSearch tự fit pipeline lại trong mỗi temporal fold.
- LightGBM Optuna cache cũng fit preprocessor riêng cho từng fold.
- Không dùng ma trận đã fit từ toàn bộ outer train để đánh giá inner fold.

Temporal CV:

- Chỉ tạo từ outer train.
- Ba expanding folds.
- Mọi validation fold xảy ra sau train fold.

## Phase 4 - Baseline

- Dummy prior.
- Core Logistic Regression.
- Đánh giá outer validation bằng PR-AUC, ROC-AUC, precision, recall, F1 và balanced accuracy.

## Phase 5 - Initial Models

So sánh:

- Logistic Regression.
- Random Forest.
- LightGBM.

Mất cân bằng:

- `class_weight="balanced"` cho Logistic.
- `class_weight="balanced_subsample"` cho Random Forest.
- `scale_pos_weight` cho LightGBM.

## Phase 6 - Threshold

- Tạo Precision-Recall và ROC curves.
- Báo threshold tối đa F1.
- Báo threshold đạt recall tối thiểu 70%.
- Chỉ khóa threshold bằng outer validation.

## Phase 7 - Tuning

- Logistic: GridSearchCV.
- Random Forest: RandomizedSearchCV.
- LightGBM: 15 Optuna trials, không dùng class weight vì temporal benchmark cho PR-AUC tốt hơn.
- LightGBM dùng early stopping trong từng fold và refit bằng median `best_iteration`.
- Scoring chính: `average_precision`.
- Tất cả search dùng temporal CV của outer train.

## Phase 8 - Champion

- Refit tuned candidates trên outer train.
- Đánh giá outer validation.
- Precision, recall và F1 của từng candidate dùng threshold tối đa F1 trên outer validation; không so sánh các model mất cân bằng bằng threshold `0.5` cố định.
- Vẽ PR/ROC curves sau tuning và đánh dấu điểm threshold tối đa F1 của từng model.
- Kiểm tra stability qua temporal folds; tái sử dụng CV results của Logistic/Random Forest để tránh fit lặp.
- Chọn champion theo:
  1. Validation PR-AUC.
  2. Mean fold PR-AUC.
  3. Fold stability.
  4. Khả năng giải thích và chi phí train.
- Khóa threshold trên outer validation.

## Phase 9 - Explainability & Error Analysis

- TP/TN/FP/FN trên validation.
- Confusion matrix và calibration.
- Logistic coefficient hoặc tree importance.
- SHAP sample nhỏ nếu champion là tree model.
- Top feature phải được đối chiếu lại với leakage gate.

## Phase 10 - Final Test

- Clone champion config.
- Fit pipeline trên train + validation.
- Predict test một lần.
- Không đổi feature, hyperparameter hoặc threshold sau khi xem test.
- Lưu model bundle, feature list và threshold.
- Reload model và xác nhận prediction khớp.

## Phase 11 - Readiness & Report

Checklist:

- FE readiness pass.
- Leakage gate được load.
- Không có banned feature.
- Preprocessing nằm trong CV/model pipeline.
- Tuning hoàn tất.
- Threshold lấy từ outer validation.
- Test chỉ dùng sau champion lock.
- Reloaded model cho prediction khớp.

Báo cáo cuối phải ghi:

- Prediction-time contract.
- Feature availability policy.
- Danh sách banned features.
- Champion và validation metrics.
- Locked threshold.
- Final test metrics.
- Input hashes và model artifact.
