# Báo cáo Modeling dữ liệu ADS

## 1. Mục tiêu

Modeling xây dựng mô hình phân loại nhị phân để dự đoán đơn hàng có bị trả lại hay không.

| Thành phần | Thiết lập |
|---|---|
| Bài toán | Binary classification |
| Nhãn dương | Returned = 1 |
| Nhãn âm | Delivered = 0 |
| Grain | 1 dòng / order |
| Thời điểm dự đoán | Order placement |
| Số feature chính | 28 |
| Metric chính | PR-AUC |

Do returned chỉ chiếm khoảng 6.5%, PR-AUC được chọn làm metric chính thay vì accuracy.

## 2. Dữ liệu modeling

Modeling sử dụng output đã khóa từ Feature Engineering.

| Split | Số dòng |
|---|---:|
| Train | 386,907 |
| Validation | 82,906 |
| Test | 83,045 |

Các feature leakage đã bị chặn từ FE:

- `high_risk_product_count`
- `max_product_return_rate`
- `mean_product_return_rate`

Modeling cũng có kiểm tra fail-fast để dừng trước training nếu banned feature xuất hiện.

![Label distribution](./modeling_outputs/figures/phase2_label_distribution.png)

## 3. Quy trình thực hiện

| Bước | Nội dung |
|---|---|
| Data audit | Kiểm tra input manifest, missing, schema và feature contract |
| Baseline | Tạo baseline để so sánh |
| Initial models | Train Logistic Regression, Random Forest, LightGBM |
| Threshold selection | Chọn threshold trên outer validation |
| Tuning | Grid/Random/Optuna cho các model chính |
| Champion lock | Chọn model tốt nhất theo validation PR-AUC |
| Final test | Mở test một lần sau khi khóa champion và threshold |
| Review | Calibration, confusion matrix, score distribution, lift, feature importance, SHAP |

## 4. Baseline

Trước khi so sánh các mô hình chính, Modeling tạo baseline để có mốc đánh giá. Baseline trả lời câu hỏi: mô hình có học được tín hiệu tốt hơn cách dự đoán rất đơn giản hay không?

| Baseline | Số feature | PR-AUC | ROC-AUC | Precision | Recall | F1 | Ý nghĩa |
|---|---:|---:|---:|---:|---:|---:|---|
| Dummy prior | 2 | 0.063723 | 0.500000 | 0.000000 | 0.000000 | 0.000000 | Mốc gần bằng tỷ lệ returned trong validation |
| Core Logistic | 2 | 0.076408 | 0.553883 | 0.109254 | 0.237554 | 0.149672 | Logistic đơn giản với nhóm feature core |

Nhận xét: Dummy prior chỉ phản ánh baseline mất cân bằng lớp, chưa học tín hiệu phân biệt. Core Logistic với rất ít feature đã vượt Dummy prior khá rõ về PR-AUC, cho thấy dữ liệu có tín hiệu dự đoán ban đầu, đặc biệt từ nhóm payment/core feature.

## 5. So sánh mô hình

Ba mô hình với cấu hình ban đầu (initial configuration) được so sánh trên validation trước khi thực hiện tuning.

| Model | PR-AUC | ROC-AUC | Precision | Recall | F1 | Threshold |
|---|---:|---:|---:|---:|---:|---:|
| Logistic Regression | 0.080873 | 0.550431 | 0.108468 | 0.239069 | 0.149229 | 0.500000 |
| Random Forest | 0.080320 | 0.547571 | 0.107898 | 0.154647 | 0.127110 | 0.500000 |
| LightGBM | 0.078067 | 0.538708 | 0.088053 | 0.249858 | 0.130216 | 0.500000 |

![Model comparison](./modeling_outputs/figures/phase5_model_comparison.png)

Nhận xét: Trong lần chạy ban đầu với cấu hình mặc định (hoặc balanced class weight mặc định), Logistic Regression có hiệu năng PR-AUC cao nhất (0.080873), theo sau là Random Forest và LightGBM. Cả ba mô hình đều có hiệu năng ở mức cơ bản và cần được tối ưu hóa siêu tham số (tuning) ở các bước tiếp theo.

## 6. Metric & threshold

Quyết định lựa chọn threshold dựa trên sự đánh đổi giữa Precision và Recall. Dưới đây là bảng so sánh ngưỡng tối ưu F1 (Max F1) và ngưỡng đạt tối thiểu 70% Recall (Recall >= 70%) trên tập validation cho các mô hình ban đầu:

| Mô hình | Chính sách | Ngưỡng (Threshold) | Precision | Recall | F1-Score |
|---|---|---:|---:|---:|---:|
| **Logistic Regression** | Max F1 | 0.619667 | 0.109873 | 0.235094 | 0.149756 |
| | Recall >= 70% | 0.458162 | 0.066494 | 0.700170 | 0.121454 |
| **Random Forest** | Max F1 | 0.465958 | 0.106354 | 0.208783 | 0.140922 |
| | Recall >= 70% | 0.359948 | 0.067481 | 0.703010 | 0.123141 |
| **LightGBM** | Max F1 | 0.513171 | 0.091717 | 0.230551 | 0.131229 |
| | Recall >= 70% | 0.342978 | 0.066534 | 0.700738 | 0.121528 |

Đối với mô hình Champion được lựa chọn (**LightGBM Tuned**), chúng tôi khóa ngưỡng phân loại (Locked threshold) dựa trên chính sách tối ưu hóa F1-Score trên tập validation:

| Thông số Champion | Giá trị |
|---|---:|
| Champion Model | LightGBM Tuned |
| Locked Threshold | 0.063357 |
| Validation PR-AUC | 0.082374 |
| Validation ROC-AUC | 0.552626 |
| Mean fold PR-AUC | 0.086250 |
| Std fold PR-AUC | 0.002915 |

![Tuned PR ROC curves](./modeling_outputs/figures/phase8_tuned_pr_roc_curves.png)

*Nhận xét:* Threshold tối ưu cho LightGBM Tuned là 0.063357, rất thấp so với mặc định 0.5. Điều này hoàn toàn hợp lý trong bối cảnh lớp positive (đơn trả hàng) rất hiếm (chỉ khoảng 6.5%). Nếu dùng threshold mặc định 0.5, mô hình sẽ bỏ sót hầu hết các đơn hàng bị trả lại.

## 7. Hyperparameter tuning

Quá trình tối ưu hóa siêu tham số (Hyperparameter Tuning) được thực hiện độc lập trên tập temporal CV folds của outer train:
- **Logistic Regression**: Sử dụng `GridSearchCV` để dò tìm tối ưu.
- **Random Forest**: Sử dụng `RandomizedSearchCV` để tìm ngẫu nhiên có kiểm soát.
- **LightGBM**: Sử dụng `Optuna` tối ưu hóa Bayesian với 15 trials và cơ chế early stopping.

Dưới đây là bảng so sánh chi tiết hiệu năng trên tập validation trước và sau khi thực hiện tuning để người xem có thể theo dõi điều chỉnh:

| Mô hình | Trạng thái | PR-AUC | ROC-AUC | Precision | Recall | F1-Score | Threshold | Cải thiện PR-AUC |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| **LightGBM** | Trước Tuning (Initial) | 0.078067 | 0.538708 | 0.088053 | 0.249858 | 0.130216 | 0.500000 | - |
| | Sau Tuning (Tuned) | **0.082374** | **0.552626** | **0.108733** | 0.240394 | **0.149738** | 0.063357 | **+0.004307** (+5.52%) |
| **Random Forest** | Trước Tuning (Initial) | 0.080320 | 0.547571 | 0.107898 | 0.154647 | 0.127110 | 0.500000 | - |
| | Sau Tuning (Tuned) | **0.081616** | **0.553099** | **0.108905** | **0.239826** | **0.149790** | 0.503857 | **+0.001296** (+1.61%) |
| **Logistic Regression** | Trước Tuning (Initial) | 0.080873 | 0.550431 | 0.108468 | **0.239069** | 0.149229 | 0.500000 | - |
| | Sau Tuning (Tuned) | **0.080880** | **0.550467** | **0.109349** | 0.237554 | **0.149761** | 0.605029 | **+0.000007** (+0.01%) |

*Nhận xét:*
- **LightGBM** là mô hình cải thiện nhiều nhất sau tuning (+5.52% PR-AUC), từ vị trí thấp nhất vươn lên thành mô hình Champion (PR-AUC đạt 0.082374). Điều này cho thấy thuật toán gradient boosting rất nhạy và hưởng lợi lớn từ việc tinh chỉnh siêu tham số cũng như điều chỉnh threshold.
- **Random Forest** cải thiện nhẹ (+1.61% PR-AUC), đạt 0.081616.
- **Logistic Regression** gần như không thay đổi (+0.01% PR-AUC), cho thấy mô hình tuyến tính đã đạt giới hạn học tín hiệu từ các feature hiện tại ngay từ cấu hình ban đầu.

## 8. Kết quả final test

Final test chỉ được đánh giá sau khi đã khóa champion và threshold.

| Metric | Giá trị |
|---|---:|
| PR-AUC | 0.084922 |
| ROC-AUC | 0.548519 |
| Precision | 0.115128 |
| Recall | 0.235675 |
| F1 | 0.154690 |
| Balanced accuracy | 0.552761 |
| Threshold | 0.063357 |
| Train rows dùng final fit | 469,813 |
| Test rows | 83,045 |

![Score distribution by label](./modeling_outputs/figures/phase10_test_score_distribution_by_label.png)

![Test score decile lift](./modeling_outputs/figures/phase10_test_score_decile_lift.png)

Nhận xét: model có khả năng ranking tốt hơn random ở một mức nhất định, nhưng score giữa returned và delivered vẫn overlap nhiều. Kết quả phù hợp với nhận định từ EDA/FE rằng tín hiệu order-time hiện tại không quá mạnh.

## 9. Giải thích mô hình

Modeling đã tạo các chart để kiểm tra calibration, confusion matrix, feature importance và SHAP.

![Confusion and calibration](./modeling_outputs/figures/phase9_confusion_calibration.png)

![Top feature importance](./modeling_outputs/figures/phase9_top_feature_importance.png)

![SHAP summary](./modeling_outputs/figures/phase9_shap_summary.png)

Các feature liên quan đến payment, đặc biệt nhóm COD/payment method, là tín hiệu quan trọng đúng với kết quả EDA.

## 10. Governance và kiểm soát leakage

| Check | Kết quả |
|---|---|
| FE readiness passed | True |
| Data contract passed | True |
| Centralized leakage gate loaded | True |
| No banned features used | True |
| Preprocessing fit trong từng temporal CV fold | True |
| Threshold lấy từ outer validation | True |
| Test dùng sau champion lock | True |
| Final model reload match | True |

Điều này giúp đảm bảo kết quả test không bị optimistic do leakage, tuning trên test hoặc preprocessing sai scope.

## 11. Đánh giá kết quả

Mô hình LightGBM Tuned là lựa chọn tốt nhất trong các mô hình đã thử, nhưng hiệu năng tuyệt đối còn khiêm tốn:

- PR-AUC test 0.084922 cao hơn baseline positive rate khoảng 6.7%, nhưng chưa phải mức rất mạnh.
- Recall 23.57% cho thấy model bắt được một phần đơn returned nhưng vẫn bỏ sót nhiều.
- Precision 11.51% nghĩa là trong các đơn bị flag, tỷ lệ returned thật còn thấp.
- Balanced accuracy 55.28% cho thấy khả năng phân tách chỉ nhỉnh hơn random.

Model phù hợp hơn cho bài toán ranking/triage rủi ro hơn là tự động quyết định cứng.

## 12. Khuyến nghị tiếp theo

1. Dùng model như công cụ xếp hạng rủi ro, ưu tiên review top decile thay vì quyết định tự động.
2. Không dùng accuracy làm metric chính vì dữ liệu mất cân bằng.
3. Theo dõi PR-AUC, recall, precision theo threshold và chi phí vận hành.
4. Bổ sung thêm tín hiệu order-time nếu muốn cải thiện lift, ví dụ lịch sử hành vi khách hàng được timestamp an toàn.
5. Giữ leakage gate trong mọi lần retrain và deployment.

## 13. Kết luận

Modeling đã hoàn thành quy trình từ input FE đến champion model, threshold lock và final test.

```text
Champion: LightGBM Tuned
Metric chính: PR-AUC
Validation PR-AUC: 0.082374
Test PR-AUC: 0.084922
Locked threshold: 0.063357
Kết luận: dùng tốt hơn cho risk ranking/triage, chưa nên dùng như quyết định tự động độc lập
```
