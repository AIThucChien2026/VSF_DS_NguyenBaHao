# Quy Trình Data Science Thực Tế — CRISP-DM Adapted

## Hướng dẫn đọc tài liệu này

Tài liệu này mô tả một **framework tư duy và quy trình**, không phải một recipe cố định.
Mọi đoạn code và ví dụ trong tài liệu này đều là **minh họa một trường hợp cụ thể** —
chúng không liệt kê hết tất cả khả năng. Khi áp dụng vào bài toán thực tế, cần:

- Thay thế tên cột, tên file, tên model bằng thứ phù hợp với dữ liệu hiện có
- Mở rộng hoặc bỏ bớt các bước tùy theo đặc thù bài toán
- Chọn thư viện, metric, kỹ thuật phù hợp với loại bài toán (classification, regression, clustering, time series, NLP, v.v.)
- Đặt câu hỏi với người dùng nếu context chưa rõ, thay vì giả định theo ví dụ

---

## Triết lý nền tảng

Mọi dự án DS đều xoay quanh một vòng lặp: **hiểu bài toán → hiểu dữ liệu → tạo ra giá trị → deliver → học từ phản hồi → lặp lại**.
Không bước nào là hoàn hảo ngay từ lần đầu. Mục tiêu của Cycle 1 là hoàn thành toàn bộ pipeline từ đầu đến cuối — dù chưa tối ưu — để có thứ gì đó có thể đánh giá và cải thiện. Perfectionism ở bước đầu là kẻ thù lớn nhất của dự án DS.

---

## Bước 01 — Business Understanding

### Mục tiêu

Trước khi mở bất kỳ file dữ liệu nào, cần trả lời rõ ràng: bài toán này là gì, ai cần nó, họ sẽ dùng kết quả để làm gì.

### Các câu hỏi cần xác định

**Về stakeholder:**
- Ai là người thực sự ra quyết định dựa trên kết quả model? (CEO, manager, hệ thống tự động, khách hàng cuối...)
- Họ muốn nhận output dưới dạng nào? (con số, phân loại, ranking, xác suất, dashboard, API...)

**Về bài toán:**
- Đây là bài toán supervised hay unsupervised? Regression, classification, clustering, ranking, recommendation, anomaly detection, hay dạng khác?
- Target variable là gì? Được định nghĩa như thế nào? Đã có label chưa hay cần tạo?
- Prediction horizon là bao lâu? (dự đoán ngày mai, tuần tới, tháng tới, hay không có time component?)

**Về metric thành công:**
- Business đo thành công bằng gì? (doanh thu, tỷ lệ giữ chân khách hàng, tiết kiệm chi phí, giảm rủi ro...)
- Metric kỹ thuật nào ánh xạ gần nhất với metric business đó? (MAPE, F1, AUC-ROC, NDCG, recall@k...)
- Có constraint gì không? (model phải giải thích được, latency < Xms, không được dùng feature Y vì lý do pháp lý...)

**Về baseline:**
- Hiện tại bài toán này được giải bằng cách nào? (excel thủ công, heuristic, không có gì...)
- Baseline tối thiểu phải vượt qua là gì?

### Output cần có

Một đoạn văn ngắn (không quá nửa trang) mô tả: bài toán là gì, output của model là gì, metric đánh giá là gì, và định nghĩa "thành công" theo nghĩa business. Nếu không viết được đoạn này, chưa đủ điều kiện để bắt đầu bước tiếp theo.

---

## Bước 02 — Data Description

### Mục tiêu

Làm quen với dữ liệu ở mức tổng quan: dữ liệu có gì, thiếu gì, hình dạng tổng thể ra sao, có vấn đề chất lượng nào rõ ràng không.

### Các chiều cần khám phá

**Cấu trúc:**
- Bao nhiêu bảng / file? Mỗi bảng đại diện cho thực thể gì (transaction, user, product, store, event...)?
- Schema của mỗi bảng: tên cột, kiểu dữ liệu, ý nghĩa
- Quan hệ giữa các bảng: key nào nối với nhau, quan hệ 1-1, 1-nhiều, hay nhiều-nhiều?
- Granularity (đơn vị của một row là gì): một row là một transaction, một ngày, một user, hay một cặp user-product?

**Chất lượng:**
- Tỷ lệ missing value theo từng cột — không chỉ có/không có mà còn cần hiểu tại sao missing (missing at random hay có pattern?)
- Kiểu dữ liệu có đúng không? (số đang lưu dạng string, date đang lưu dạng object...)
- Có duplicate rows không? Duplicate theo nghĩa nào (hoàn toàn giống nhau, hay cùng key nhưng khác value)?
- Outlier: có giá trị bất thường không? Là lỗi dữ liệu hay thực sự tồn tại trong thực tế?

**Phân phối tổng quan:**
- Target variable phân phối như thế nào? Skewed? Class imbalance?
- Các feature số: range, mean, std, min, max
- Các feature categorical: bao nhiêu unique values, distribution có đều không

**Thời gian (nếu có):**
- Data trải dài từ khi nào đến khi nào?
- Có gaps (khoảng trống thời gian) không?
- Frequency là gì: daily, weekly, monthly, event-based?

### Lưu ý quan trọng khi có nhiều bảng

Khi merge nhiều bảng, ba rủi ro thường gặp nhất là:

1. **Row explosion** — join làm tăng số rows bất thường (thường do quan hệ nhiều-nhiều không được xử lý đúng). Luôn kiểm tra `shape` trước và sau mỗi lần join.
2. **Missing rows** — inner join làm mất rows có giá trị. Cần quyết định có chủ ý giữa left/right/inner/outer join dựa trên business logic, không phải mặc định.
3. **Column collision** — hai bảng có cột trùng tên nhưng ý nghĩa khác nhau. Đặt tên rõ ràng ngay khi merge.

---

## Bước 03 — Feature Engineering

### Mục tiêu

Tạo ra các biểu diễn mới của dữ liệu giúp model học được pattern tốt hơn. Feature engineering tốt thường quan trọng hơn chọn model tốt.

### Nguyên tắc: hypothesis-driven, không phải exhaustive

Đừng tạo feature vì "có thể có ích". Hãy bắt đầu bằng việc liệt kê 10–20 giả thuyết về những yếu tố nào ảnh hưởng đến target — dựa trên hiểu biết về domain. Mỗi hypothesis sẽ map đến một hoặc vài feature cụ thể cần tạo. Cách tiếp cận này giúp EDA sau đó có hướng (validate hypothesis) thay vì EDA mù quáng.

**Ví dụ tư duy (không phải danh sách đầy đủ):**
- Hypothesis: "Hành vi người dùng thay đổi theo ngày trong tuần" → feature: `day_of_week`, `is_weekend`
- Hypothesis: "Khoảng cách địa lý ảnh hưởng đến quyết định mua hàng" → feature: `distance_to_nearest_store`, `distance_to_city_center`
- Hypothesis: "Lịch sử gần đây quan trọng hơn lịch sử xa" → feature: lag values, rolling averages với các window khác nhau

### Các nhóm feature phổ biến

Đây là các nhóm thường gặp. Với từng bài toán cụ thể, có thể chỉ cần một số nhóm, hoặc có những nhóm không được liệt kê ở đây:

**Từ datetime:**
Bất kỳ cột nào chứa thông tin thời gian đều có thể được decompose thành nhiều feature: các đơn vị thời gian (giờ, ngày, tuần, tháng, quý, năm), các đặc trưng định tính (ngày lễ, cuối tuần, mùa), và khoảng cách thời gian (số ngày kể từ event X, số ngày đến event Y). Với các feature có tính chu kỳ (tháng 1 và tháng 12 thực ra "gần nhau"), nên dùng sine/cosine encoding thay vì giá trị số thô.

**Từ dữ liệu nhiều bảng:**
Sau khi xác định được granularity của bảng chính, có thể aggregate dữ liệu từ bảng phụ theo nhiều cách: trung bình, tổng, min, max, std, count, median, percentile. Ngoài ra còn có thể tính các tỷ lệ, rank, hoặc so sánh với benchmark (VD: doanh số store này so với trung bình toàn hệ thống).

**Lag và rolling (time series / sequential data):**
Giá trị trong quá khứ thường là predictor mạnh. Cần cẩn thận với việc tính lag: phải shift đúng để không vô tình đưa thông tin từ tương lai vào feature (data leakage theo thời gian). Window size của rolling nên được chọn dựa trên business cycle (VD: rolling 7 ngày cho weekly pattern, rolling 30 ngày cho monthly trend).

**Interaction features:**
Đôi khi kết hợp hai feature cho signal tốt hơn từng feature riêng lẻ. Không nên tạo tất cả pairwise interactions vì sẽ gây curse of dimensionality — chỉ tạo khi có lý do business rõ ràng.

**Domain-specific:**
Đây thường là nguồn feature mạnh nhất và không thể generalize. Các feature này đòi hỏi hiểu biết về domain: công thức tính margin trong retail, RFM trong marketing, technical indicators trong finance, TF-IDF hay embeddings trong NLP, v.v.

### Xử lý missing values trong feature engineering

Missing value không phải lúc nào cũng nên fill bằng mean/median. Đôi khi sự vắng mặt của dữ liệu tự nó là một signal:
- Thêm cột binary `feature_was_missing` trước khi fill
- Fill bằng giá trị mang ý nghĩa business (VD: không có thông tin về đối thủ cạnh tranh → fill bằng "rất xa" thay vì mean)
- Giữ nguyên và để model tree-based tự xử lý (XGBoost, LightGBM xử lý được NaN)

---

## Bước 04 — Data Filtering

### Mục tiêu

Loại bỏ những rows và columns không nên có mặt trong quá trình training — hoặc vì chúng gây nhiễu, hoặc vì chúng sẽ gây data leakage.

### Lọc rows

Không phải mọi row trong dataset đều relevant với bài toán đang giải. Ví dụ về logic lọc (chỉ minh họa, không phải danh sách đầy đủ):
- Loại các trạng thái không thuộc scope bài toán (transaction bị cancel, store đang đóng cửa, user inactive...)
- Loại rows có target value bất thường theo business logic (không phải outlier thống kê, mà là "không thể xảy ra trong thực tế")
- Giới hạn time range nếu dữ liệu quá cũ không còn relevant (VD: behavior trước COVID có thể không reflect thực tế hiện tại)

### Lọc columns

Loại các cột thuộc một trong các nhóm sau:
- **Identifier thuần túy:** primary key, order ID, transaction ID — không mang signal
- **Data leakage:** cột chứa thông tin chỉ có được sau khi event xảy ra. Rule kiểm tra: "Tại thời điểm cần predict, thông tin này đã có chưa?" Nếu chưa có → leakage
- **Redundant:** cột là linear combination hoặc transformation đơn giản của cột khác đã có
- **Quá nhiều missing:** cột có >X% missing và không thể fill có nghĩa (ngưỡng X tùy business context, thường 50–70%)
- **Zero variance:** cột gần như không thay đổi giá trị giữa các rows

### Data leakage — rủi ro lớn nhất

Data leakage xảy ra khi thông tin từ tương lai hoặc từ "sau khi biết kết quả" lọt vào training data. Đây là lỗi thường gặp nhất và nguy hiểm nhất vì model sẽ có performance rất tốt trên test set nhưng hoàn toàn thất bại khi deploy.

Các nguồn leakage phổ biến:
- **Target leakage:** feature được tạo ra dùng thông tin của target variable (VD: tạo feature "đã thanh toán đủ chưa" để predict "có default không")
- **Temporal leakage:** trong time series, dùng dữ liệu của ngày T để predict sự kiện ở ngày T hoặc trước T
- **Train-test contamination:** fit scaler, encoder, hoặc imputer trên toàn bộ dataset trước khi split — thông tin từ test set lọt vào quá trình fit

---

## Bước 05 — Exploratory Data Analysis

### Mục tiêu

Hiểu sâu dữ liệu, validate các hypotheses đã đặt ra ở bước 03, phát hiện patterns và insights quan trọng, đồng thời tìm hiểu feature nào thực sự có quan hệ với target.

### Ba tầng phân tích

**Tầng 1 — Univariate (phân tích từng biến riêng lẻ):**
Mục đích: hiểu phân phối, phát hiện vấn đề chất lượng còn sót, xác định transformation cần thiết.
Với numerical: distribution shape, skewness, kurtosis, outliers.
Với categorical: frequency của từng category, rare categories, imbalance.
Với target variable: đây là phần quan trọng nhất ở tầng này — nếu target bị skew nặng, cần transform; nếu class imbalanced cần chiến lược xử lý.

**Tầng 2 — Bivariate (feature so với target):**
Mục đích: validate hypotheses, xác định feature nào có predictive power.
Với numerical feature và numerical target: scatter plot, correlation coefficient, partial correlation.
Với categorical feature và numerical target: boxplot, violin plot, mean/median target theo từng category.
Với feature và binary target: distribution của feature theo từng class, odds ratio.
Mỗi hypothesis được đặt ra ở bước 03 cần được đánh dấu TRUE / FALSE / INCONCLUSIVE sau bước này.

**Tầng 3 — Multivariate (tương quan giữa các feature):**
Mục đích: phát hiện multicollinearity, redundancy, và interaction effects.
Correlation matrix cho numerical features.
Xác định nhóm features "nói cùng một thứ" để sau này feature selection có thể loại bớt.

### EDA có hướng vs EDA mù quáng

EDA không có hypothesis dẫn đến việc "nhìn tất cả mọi thứ" nhưng không rút ra được insight cụ thể. EDA tốt luôn bắt đầu từ câu hỏi, rồi mới tìm biểu đồ để trả lời câu hỏi đó — không phải vẽ hết tất cả rồi mới nghĩ.

---

## Bước 06 — Data Preparation

### Mục tiêu

Transform dữ liệu thành dạng mà machine learning model có thể học được. Đây là bước đòi hỏi nhiều quyết định kỹ thuật nhất, và mọi quyết định đều phải tuân theo một nguyên tắc tuyệt đối.

### Nguyên tắc tuyệt đối: Train-Test Isolation

**Tách train/test set TRƯỚC KHI làm bất cứ điều gì liên quan đến fitting (scaler, encoder, imputer...).**
Sau khi tách, chỉ được `.fit()` trên train set. Với test set chỉ được `.transform()`.
Vi phạm nguyên tắc này dẫn đến "optimistic bias" — model tưởng tốt nhưng thực ra đang nhìn vào data mà nó sẽ gặp lúc predict.

Cách tách phụ thuộc vào bản chất dữ liệu:
- **Time series hoặc data có temporal dependency:** tách theo thời gian (mọi data trước mốc T là train, sau T là test). Không dùng random split vì sẽ leak thông tin tương lai.
- **Independent và identically distributed:** có thể random split. Với classification, nên stratify để giữ tỷ lệ class.
- **Group structure** (VD: nhiều rows thuộc cùng 1 user/store): nên split theo group (GroupKFold) để tránh model "nhận ra" các entities trong test set.

### Rescaling numerical features

Model dựa trên distance hoặc gradient (linear regression, SVM, neural network, KNN...) nhạy cảm với scale. Tree-based models (random forest, XGBoost, LightGBM) không cần rescaling.

Các phương pháp rescaling (không giới hạn ở đây) cần được chọn dựa trên đặc điểm phân phối của feature:
- Features phân phối gần normal, ít outlier → StandardScaler hoặc MinMaxScaler
- Features có outlier mạnh → RobustScaler (dùng median và IQR thay vì mean và std)
- Features có phân phối skewed nặng → log transform, square root, hoặc power transform (Yeo-Johnson, Box-Cox)
- Target variable skewed (thường gặp trong sales, revenue, count data) → thường log-transform, nhớ inverse transform khi tính metric

### Encoding categorical features

Không có một phương pháp encoding nào là tốt nhất trong mọi tình huống. Lựa chọn phụ thuộc vào:
- **Ordinal vs nominal:** category có thứ tự (small/medium/large) hay không có (red/blue/green)?
- **Cardinality:** bao nhiêu unique values? Thấp (<10) hay cao (>100)?
- **Model type:** tree-based models xử lý label encoding tốt; linear models cần one-hot
- **Relationship với target:** target encoding hiệu quả với high-cardinality nhưng dễ gây leakage nếu không cross-validate

Các kỹ thuật thông dụng (không giới hạn): one-hot encoding, label/ordinal encoding, target encoding, binary encoding, frequency encoding, embedding (cho deep learning).

### Xử lý class imbalance (nếu classification)

Nếu tỷ lệ class không đều (VD: 95% negative, 5% positive), accuracy không phải metric phù hợp. Các chiến lược xử lý:
- **Resampling:** oversample minority class (SMOTE và các biến thể), undersample majority class, hoặc kết hợp cả hai
- **Class weight:** nhiều model hỗ trợ `class_weight` parameter để penalize nặng hơn khi sai ở minority class
- **Threshold tuning:** thay vì mặc định threshold 0.5, tìm threshold tối ưu trên validation set cho metric business mong muốn
- **Metric phù hợp:** dùng precision-recall AUC, F1, F-beta thay vì accuracy

---

## Bước 07 — Feature Selection

### Mục tiêu

Loại bỏ các features không đóng góp hoặc gây hại cho model. Nhiều feature hơn không phải lúc nào cũng tốt hơn.

### Tại sao cần feature selection

- Giảm overfitting: noise features làm model học pattern không tồn tại trong thực tế
- Giảm training time và inference time
- Tăng interpretability
- Một số model xuống performance khi có quá nhiều irrelevant features

### Các chiều tiếp cận

**Filter methods (không phụ thuộc vào model, nhanh):**
Đánh giá feature độc lập với model dựa trên thống kê: correlation với target, mutual information, chi-square test, ANOVA F-test. Ưu điểm: nhanh, không bị overfit. Nhược điểm: không capture interaction giữa các features.

**Wrapper methods (dựa trên model performance, chậm nhưng mạnh hơn):**
Thử các subset feature khác nhau và đánh giá model. Ví dụ: Boruta (so sánh mỗi feature với "shadow feature" ngẫu nhiên), RFE (Recursive Feature Elimination), forward/backward selection. Boruta được recommend vì tự động, không cần specify số feature muốn giữ.

**Embedded methods (feature selection trong quá trình training):**
L1 regularization (Lasso) shrink coefficient của irrelevant feature về 0. Feature importance từ tree-based models. Đây là phương pháp thực tế nhất vì không cần bước riêng.

### Nguyên tắc thực hành

- Luôn giữ lại reasoning khi drop một feature, không drop "vì thấy ít quan trọng"
- Đôi khi một feature có importance thấp trên toàn dataset nhưng rất quan trọng với một subgroup — cần validate
- Feature importance từ tree models phụ thuộc vào hyperparameters — không nên dùng một lần duy nhất để quyết định

---

## Bước 08 — Machine Learning Modeling

### Mục tiêu

Tìm được model đủ tốt cho bài toán trong thời gian hợp lý. Luôn bắt đầu từ đơn giản.

### Nguyên tắc: complexity ladder

Bắt đầu từ model đơn giản nhất có thể giải bài toán, rồi tăng dần độ phức tạp khi cần thiết. Lý do: model đơn giản dễ debug, dễ interpret, và đôi khi đã đủ tốt.

**Bậc thang phổ biến (minh họa — không phải danh sách tuyệt đối):**

```
Bậc 0 — Baseline không dùng ML:
  Regression: predict bằng mean/median của target
  Classification: predict class majority
  Time series: predict bằng giá trị kỳ trước (naive forecast)
  → Đây là "floor" — model tốt phải vượt được floor này

Bậc 1 — Linear/Logistic Model:
  Nhanh, interpretable, tốt khi relationship tuyến tính
  → Nếu linear model đã đủ tốt, không cần đi xa hơn

Bậc 2 — Tree-based single model:
  Decision Tree, Random Forest
  Xử lý nonlinearity, không cần scale features
  Random Forest ít tune hơn decision tree đơn lẻ

Bậc 3 — Gradient Boosting:
  XGBoost, LightGBM, CatBoost
  Thường win trên tabular data
  Cần tune nhiều hơn Random Forest

Bậc 4 — Neural Networks / Deep Learning:
  Cần nhiều data hơn, khó tune hơn
  Thường không vượt gradient boosting trên tabular data nhỏ
  Mạnh hơn với unstructured data (ảnh, text, audio)

Bậc 5 — Ensemble / Stacking:
  Kết hợp nhiều model
  Tốn compute và thời gian
  Chỉ đáng khi đã tối ưu từng model riêng lẻ
```

Lưu ý: đây là ví dụ phổ biến với tabular data. Với NLP, CV, hay các domain khác, bậc thang sẽ khác.

### Đánh giá model đúng cách

Không đánh giá chỉ trên một split train/test. Cross-validation cho ước lượng đáng tin cậy hơn về generalization performance. Cách cross-validate cũng phải phù hợp với cấu trúc data:
- KFold thông thường: khi data independent
- TimeSeriesSplit hoặc walk-forward validation: khi data có temporal dependency
- GroupKFold: khi có group structure (nhiều rows cùng entity)

Ngoài metric tổng thể, cần phân tích error theo slice: model có underperform với một subgroup nào không? Điều này quan trọng cả về kỹ thuật lẫn fairness.

---

## Bước 09 — Hyperparameter Fine-Tuning

### Mục tiêu

Tối ưu hyperparameters của model đã chọn. Không làm bước này quá sớm — chỉ bắt đầu sau khi đã confirm được model architecture và feature set.

### Các phương pháp (từ đơn giản đến phức tạp)

**Manual tuning:** thay đổi thủ công dựa trên hiểu biết về ý nghĩa của từng hyperparameter. Chậm nhưng giúp hiểu model sâu hơn. Tốt để bắt đầu.

**Grid search:** thử mọi combination trong một grid định sẵn. Exhaustive nhưng tốn compute theo hàm mũ khi số hyperparameter tăng.

**Random search:** sample ngẫu nhiên từ distribution. Theo nghiên cứu, thường hiệu quả hơn grid search cùng số lần thử vì budget được phân bổ đều hơn trên không gian tham số.

**Bayesian optimization (Optuna, Hyperopt...):** dùng kết quả các lần thử trước để guide lần thử tiếp theo. Hiệu quả nhất khi số lần thử bị giới hạn. Recommend dùng khi cần tune nhiều hyperparameter.

**Early stopping:** với gradient boosting và neural network, dùng early stopping trên validation set để tìm số iterations tối ưu — nhanh và effective hơn tune `n_estimators` qua grid search.

### Thứ tự ưu tiên tune (với gradient boosting — ví dụ minh họa)

Không phải mọi hyperparameter đều quan trọng như nhau. Nên tune theo thứ tự ảnh hưởng từ cao đến thấp — thứ tự cụ thể phụ thuộc vào model và bài toán. Với gradient boosting, thường `learning_rate` + `n_estimators` → `max_depth` + `min_samples` → regularization terms.

---

## Bước 10 — Error Analysis và Deliver

### Mục tiêu

Hiểu model sai ở đâu và tại sao, rồi dịch kết quả kỹ thuật sang ngôn ngữ business.

### Error analysis

Không chỉ nhìn vào aggregate metric. Phân tích:
- Phân phối của errors: có systematic bias không (model luôn predict thấp hơn thực tế)?
- Errors phân bố theo subgroup nào: theo thời gian, theo category, theo region...?
- Những cases nào model sai nhiều nhất? Có pattern gì không?
- Residual analysis (với regression): residuals có random không hay còn structure?

Những insight từ error analysis thường là input quan trọng nhất cho Cycle 2: cần thêm feature gì, cần thêm data gì, hay model architecture cần thay đổi gì.

### Dịch metric sang business language

Stakeholder không quan tâm đến MAPE = 0.08. Họ quan tâm đến:
- "Model dự đoán sai trung bình ±8% so với thực tế"
- "Với budget dự phòng X%, model đảm bảo đúng trong Y% trường hợp"
- "Nếu dùng model thay vì phương pháp cũ, tiết kiệm được Z đồng mỗi tháng"

Luôn trình bày kết quả kèm best case / worst case / expected case thay vì một con số duy nhất.

### Delivery format

Output của model cần phù hợp với cách stakeholder sẽ sử dụng:
- Dashboard interactive (Tableau, PowerBI, Streamlit, Metabase...)
- API endpoint để tích hợp vào hệ thống hiện có
- Batch prediction export ra file định kỳ
- Telegram bot, Slack bot, email report...

---

## Vòng lặp CRISP-DM

```
Cycle 1 (2–4 tuần):
  Mục tiêu: hoàn thành toàn bộ 10 bước, có model chạy được
  Tiêu chí: vượt baseline, deliver được thứ gì đó cho stakeholder review
  Không perfectionism — rough and working > perfect and unfinished

Cycle 2 (2–4 tuần):
  Cải thiện dựa trên feedback từ Cycle 1
  Thêm features mới từ insights của EDA
  Tune model sâu hơn
  Fix các vấn đề phát hiện ra ở error analysis

Cycle 3+:
  Cải thiện theo marginal gains
  Monitor production performance
  Drift detection — khi data thực tế bắt đầu khác với training data
```

---

## Cấu trúc project nên có

```
project/
├── data/
│   ├── raw/          # dữ liệu gốc — không bao giờ chỉnh sửa trực tiếp
│   ├── interim/      # sau khi clean nhưng chưa feature engineering
│   ├── processed/    # sẵn sàng cho modeling
│   └── external/     # data từ nguồn bên ngoài
├── notebooks/
│   ├── 01_data_description.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_eda.ipynb
│   ├── 04_data_preparation.ipynb
│   ├── 05_modeling.ipynb
│   └── 06_error_analysis.ipynb
├── src/
│   ├── data/         # scripts load và clean data
│   ├── features/     # scripts tạo feature
│   └── models/       # scripts train và evaluate
├── models/           # trained model artifacts (.pkl, .joblib, .pt...)
├── reports/          # outputs: charts, tables, slide
└── requirements.txt
```

---

## Checklist trước khi gọi model là "done"

```
Dữ liệu:
[ ] Train/test split không bị leak (đặc biệt với time series)
[ ] Scaler / encoder / imputer chỉ fit trên train set
[ ] Không có cột leakage trong feature set
[ ] Missing values đã được xử lý có chủ ý (không chỉ fill mean mặc định)

Model:
[ ] Đã vượt được baseline đơn giản (predict mean / majority class)
[ ] Đánh giá bằng cross-validation, không chỉ một split
[ ] Error analysis đã làm — biết model sai ở đâu
[ ] Reproducible: random state được đặt ở mọi nơi
[ ] Model đã được serialize và có thể load lại

Delivery:
[ ] Metric đã được dịch sang ngôn ngữ business
[ ] Stakeholder hiểu được kết quả mà không cần biết về ML
[ ] Biết model sẽ được update như thế nào khi có data mới
[ ] Có plan monitoring sau khi deploy
```

---

## Tài liệu tham khảo để đọc thêm

Các repo sau được dùng làm nguồn tham khảo khi xây dựng quy trình này. Đọc code thực tế trong các repo này để thấy từng bước được implement như thế nào trong một dự án cụ thể — nhớ rằng chúng là ví dụ của một domain, không phải blueprint tuyệt đối:

- **CRISP-DM end-to-end (sales forecasting):** https://github.com/KattsonBastos/rossmann_sales_prediction
- **EDA hypothesis-driven chi tiết:** https://github.com/alanmaehara/Sales-Prediction  
- **Multiple CSV merge + LSTM:** https://github.com/Shobha-m-collab/EDA-and-Feature-Engineering-on-M5-Forecasting-Accuracy
- **Boruta feature selection:** https://github.com/scikit-learn-contrib/boruta_py
- **Optuna hyperparameter tuning:** https://optuna.readthedocs.io/
