import json
from pathlib import Path


NOTEBOOK_PATH = Path("report_14_6_2026/4_Modeling.ipynb")


def md(text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


conclusions = {
    "# Phase 0.3": """### Kết luận Phase 0

- **Mục tiêu phase:** chuẩn bị môi trường, dependency và thư mục output cho toàn bộ Modeling.
- **Output chính:** các thư mục `modeling_outputs/tables`, `modeling_outputs/figures`, `modeling_outputs/models`, `modeling_outputs/optuna`.
- **Kết luận:** phase này chưa tạo metric model, nhưng đã thiết lập nền để mọi artifact sau đó ghi đúng một chuẩn đường dẫn. Việc kiểm tra dependency sớm giúp notebook fail sớm nếu thiếu thư viện thay vì lỗi giữa quá trình train/tuning.
""",
    "# Phase 1.1": """### Kết luận Phase 1

- **Contract bài toán:** binary classification, grain là **một dòng trên mỗi `order_id`**, target là `returned_label`, positive class là **returned = 1**.
- **Nguồn label:** `orders.order_status`; chỉ dùng feature available at/before `order_date`.
- **Metric chính:** **PR-AUC / average precision** vì positive class mất cân bằng.
- **Feature chính:** `feature_cols_v1.csv` có **28 feature**.
- **Input manifest:** ghi nhận đủ 6 artifact đầu vào quan trọng gồm feature list, leakage gate, preprocessing policy và 3 raw split train/validation/test, có size và sha256 để truy vết.
- **Kết luận:** Modeling không tự chọn lại feature từ dữ liệu gốc; toàn bộ bước sau bám theo contract và feature set đã khóa từ FE.
""",
    "# Phase 2.3": """### Kết luận Phase 2

- **Data contract:** `phase2_data_audit.csv` pass **11/11 checks**.
- **Số dòng có nhãn:** **552,858 orders**, gồm **516,716 delivered** và **36,142 returned**.
- **Schema/split:** train, validation và test có schema giống nhau; không có overlap order; thứ tự thời gian đúng.
- **Leakage:** banned features không xuất hiện trong feature set hoặc raw split.
- **Missing:** `phase2_missing_audit.csv` cho thấy `missing_count` tối đa bằng **0** và `missing_rate` tối đa bằng **0.0** trên các feature modeling.
- **Kết luận:** dữ liệu đủ sạch để train model; class imbalance rõ nên các phase sau cần ưu tiên PR-AUC, recall/precision và threshold review thay vì accuracy.
""",
    "# Phase 3.3": """### Kết luận Phase 3

- **Preprocessing numeric:** 6 numeric features dùng **median -> standard scaler**.
- **Preprocessing categorical:** 6 categorical features dùng **most frequent -> one-hot**.
- **Preprocessing binary:** 16 binary features dùng **most frequent -> passthrough**.
- **Derived feature:** `payment_value` có thêm **4 quantile bins**, fit bên trong từng model/CV fold.
- **Temporal CV:** 3 expanding folds chỉ nằm trong train:
  - Fold 1: **215,042 train / 63,195 validation**.
  - Fold 2: **278,237 train / 57,325 validation**.
  - Fold 3: **335,562 train / 51,345 validation**.
- **Kết luận:** preprocessing và CV được thiết kế đúng để tránh học thông tin từ validation/test; các fold có return rate gần nhau nên phù hợp để so sánh stability theo thời gian.
""",
    "# Phase 4.2": """### Kết luận Phase 4

- **Dummy prior:** validation **PR-AUC = 0.063723**, **ROC-AUC = 0.500000**.
- **Core Logistic:** dùng 2 core features (`is_cod`, `payment_method`) đạt:
  - **PR-AUC = 0.076408**
  - **ROC-AUC = 0.553883**
  - **Precision = 0.109254**
  - **Recall = 0.237554**
  - **F1 = 0.149672**
- **Kết luận:** dữ liệu có tín hiệu dự đoán thật so với Dummy, nhưng lift ban đầu còn mỏng. Phase sau cần kiểm tra liệu 28 V1 features và model phi tuyến có cải thiện đáng kể hay không.
""",
    "# Phase 5.3": """### Kết luận Phase 5

- **Logistic Regression initial:** validation **PR-AUC = 0.080873**, **ROC-AUC = 0.550431**.
- **Random Forest initial:** validation **PR-AUC = 0.080320**, **ROC-AUC = 0.547571**.
- **LightGBM initial:** validation **PR-AUC = 0.078067**, **ROC-AUC = 0.538708**.
- **Output chính:** `phase5_initial_model_metrics.csv`, `phase5_validation_predictions.csv`, `phase5_model_comparison.png`.
- **Kết luận:** 28 V1 features cải thiện so với core baseline, nhưng ba model vẫn chỉ tạo lift vừa phải. Logistic Regression đang dẫn nhẹ ở initial run, còn model phức tạp chưa cho thấy ưu thế rõ trước tuning.
""",
    "# Phase 6.2": """### Kết luận Phase 6

- **Threshold metrics:** `phase6_threshold_metrics.csv` có **246,770 dòng metric** cho 3 model.
- **Max F1 policy:**
  - Logistic Regression: threshold **0.619667**, precision **0.109873**, recall **0.235094**, F1 **0.149756**.
  - Random Forest: threshold **0.465958**, precision **0.106354**, recall **0.208783**, F1 **0.140922**.
  - LightGBM initial: threshold **0.513171**, precision **0.091717**, recall **0.230551**, F1 **0.131229**.
- **Recall >= 70% policy:** đạt recall mục tiêu nhưng precision giảm về khoảng **0.0665-0.0675**.
- **Kết luận:** nếu business ép recall rất cao thì false positive sẽ nhiều. Với baseline V1, threshold theo max F1 hợp lý hơn để cân bằng precision/recall.
""",
    "# Phase 7.4": """### Kết luận Phase 7

- **Logistic GridSearch:** thử **2 cấu hình**; best config là `C=0.1`, `class_weight=balanced`, `penalty=l2`, mean CV **PR-AUC = 0.086350**.
- **Random Forest RandomizedSearch:** thử **5 cấu hình**; best config dùng **250 trees**, `max_depth=8`, `min_samples_leaf=5`, `balanced_subsample`, mean CV **PR-AUC = 0.084661**.
- **LightGBM Optuna:** hoàn thành **15 trials**; best trial đạt mean CV **PR-AUC khoảng 0.086532**.
- **Kết luận:** tuning cải thiện CV PR-AUC, nhưng các model vẫn nằm sát nhau. Giới hạn hiện tại có vẻ đến từ signal feature và class imbalance nhiều hơn là do thiếu tuning sâu.
""",
    "# Phase 8.3": """### Kết luận Phase 8

- **Champion:** `LightGBM Tuned`.
- **Validation metric của champion:**
  - **PR-AUC = 0.082374**
  - **ROC-AUC = 0.552626**
  - **Precision = 0.108733**
  - **Recall = 0.240394**
  - **F1 = 0.149738**
  - **Balanced accuracy = 0.553142**
- **Locked threshold:** **0.063357**, chọn theo policy max F1 trên outer validation.
- **Temporal stability:** LightGBM Tuned có fold PR-AUC **0.086432**, **0.083248**, **0.089069**; mean fold PR-AUC **0.086250**, std **0.002915**.
- **Kết luận:** LightGBM là champion hợp lệ theo metric chính, nhưng khoảng cách với Random Forest/Logistic nhỏ; không nên diễn giải là model vượt trội áp đảo.
""",
    "# Phase 9.3": """### Kết luận Phase 9

- **Validation error analysis:** trên **82,906** dòng validation:
  - **TN = 67,213**
  - **FP = 10,410**
  - **FN = 4,013**
  - **TP = 1,270**
- **Top importance của champion:**
  - `numeric__log_payment_value`: **12**
  - `numeric__payment_value`: **10**
  - `categorical__device_type_tablet`: **9**
  - `categorical__payment_method_cod`: **9**
  - `binary__size_S`: **8**
  - `numeric__discount_ratio`: **7**
- **SHAP:** chạy OK trên **2,000 validation rows**.
- **Kết luận:** model bắt được một phần returned orders nhưng vẫn tạo nhiều false positive. Các driver quan trọng đều là tín hiệu order-time hợp lệ, nên chưa thấy dấu hiệu leakage rõ từ feature importance/SHAP.
""",
    "# Phase 10.4": """### Kết luận Phase 10

- **Final fit:** refit champion trên train + validation với **469,813 dòng**.
- **Final test:** đánh giá đúng một lần trên **83,045 dòng test**.
- **Test metrics:**
  - **PR-AUC = 0.084922**
  - **ROC-AUC = 0.548519**
  - **Precision = 0.115128**
  - **Recall = 0.235675**
  - **F1 = 0.154690**
  - **Balanced accuracy = 0.552761**
- **Reload audit:** pass, prediction sau khi load lại khớp trên **100 sample rows**.
- **Decile lift:** decile 10 có return rate **11.459872%**, lift **1.7095x** so với base rate test; decile 9 có return rate **8.525410%**, lift **1.2718x**.
- **Kết luận:** score có ích cho ranking nhóm rủi ro cao, nhưng separation còn yếu. Model phù hợp làm risk ranking/triage, chưa đủ mạnh cho auto-block hoặc auto-reject.
""",
    "# Phase 11.2": """### Kết luận Phase 11

- **Readiness:** `modeling_readiness_checklist.csv` pass **13/13 checks**.
- **Governance đã pass:**
  - FE readiness pass.
  - Data contract pass.
  - Leakage gate load đủ **52 dòng**.
  - Không có banned feature trong feature set.
  - Preprocessing và quantile binning nằm trong model pipeline/CV fold.
  - Logistic grid hoàn thành **2 cấu hình**.
  - Random Forest random search hoàn thành **5 trials**.
  - Optuna hoàn thành **15 trials**.
  - Threshold lấy từ outer validation.
  - Test chỉ dùng sau champion lock.
  - Final model reload match.
- **Kết luận:** pipeline modeling chạy được end-to-end và có governance tốt. Model V1 có lift thật nhưng hiệu năng còn mỏng; nên dùng như baseline/risk ranking trước khi mở rộng feature hoặc định nghĩa threshold theo cost matrix.
""",
}


final_conclusion = """## Kết luận tổng hợp

- **Notebook đã chạy end-to-end:** contract -> data audit -> preprocessing -> baseline -> initial models -> threshold analysis -> tuning -> champion selection -> explainability -> final test -> readiness report.
- **Champion cuối:** `LightGBM Tuned`.
- **Validation PR-AUC:** **0.082374**.
- **Test PR-AUC:** **0.084922**.
- **Test ROC-AUC:** **0.548519**.
- **Test recall:** **0.235675**.
- **Top score decile trên test:** return rate **11.459872%**, lift **1.7095x** so với base rate.
- **Kết luận sử dụng:** model có lift so với Dummy prior và hữu ích để **rank/risk triage** nhóm đơn hàng rủi ro cao. Tuy nhiên separation còn yếu, nên **chưa nên dùng cho quyết định tự động** nếu chưa có thêm feature order-time mạnh hơn và cost matrix rõ ràng.
"""


def main() -> None:
    nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))

    filtered = []
    for cell in nb["cells"]:
        src = "".join(cell.get("source", []))
        if cell.get("cell_type") == "markdown" and (
            src.startswith("### Ket luan Phase")
            or src.startswith("### Kết luận Phase")
            or src.startswith("## Ket luan tong hop")
            or src.startswith("## Kết luận tổng hợp")
        ):
            continue
        filtered.append(cell)

    new_cells = []
    for cell in filtered:
        new_cells.append(cell)
        src = "".join(cell.get("source", []))
        for anchor, conclusion in conclusions.items():
            if src.startswith(anchor):
                new_cells.append(md(conclusion))
                break

    new_cells.append(md(final_conclusion))
    nb["cells"] = new_cells

    NOTEBOOK_PATH.write_text(
        json.dumps(nb, ensure_ascii=False, indent=1),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
