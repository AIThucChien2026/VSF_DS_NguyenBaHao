# Kế hoạch thực hiện `EDA.ipynb`

Mục tiêu của notebook `EDA.ipynb` không phải là vẽ thật nhiều biểu đồ. Mục tiêu đúng là:

```text
Chọn một câu chuyện phân tích chính, đặt các giả thuyết liên quan trực tiếp đến target, rà soát xem dữ liệu hiện có đủ để kiểm chứng các giả thuyết đó không, sau đó dùng EDA để trả lời từng giả thuyết một cách có kiểm soát grain và leakage.
```

Lưu ý quan trọng:

- Notebook này **không làm lại toàn bộ check_quality**.
- Các kiểm tra schema, missing, duplicate, FK, logic date, outlier tổng quát đã thuộc notebook/bước `check_quality`.
- Trong EDA chỉ rà soát lại những điểm cần thiết cho giả thuyết và kiểm tra các bảng/cột mới được tạo trong EDA, ví dụ bảng daily aggregate, metric mới, kết quả join mới.
- Bảng master không nên đứng thành giả thuyết riêng. Nếu cần, chỉ dùng như bảng lookup/enrichment để giải thích bảng giao dịch.

---

## Phase A: Chọn target và scope

### 0. Load dữ liệu trong scope

**Mục tiêu**: Load các bảng dữ liệu cần thiết từ thư mục `data` để chuẩn bị cho quá trình scoping và phân tích.

#### Quy trình

- Đọc các file dữ liệu trong scope: tạo dictionary `tables` hoặc các DataFrame tương ứng.
- Chuẩn hóa tên bảng: map tên file sang tên bảng dễ đọc như `sales`, `orders`, `web_traffic`.
- Kiểm tra load status: ghi bảng nào load được, bảng nào lỗi, số dòng/cột mỗi bảng.
- Xác định bảng bắt buộc: `sales` và `sample_submission` phải tồn tại trước khi chọn target.
- Ghi output `load_scope_check`: dùng làm bằng chứng cho các bước chọn target, forecast frame và bảng EDA.

#### Output định dạng

Tạo bảng `load_scope_check`:

| table | file_path | loaded | n_rows | n_cols | required_for | status |
|---|---|---|---|---|---|---|

### 1. Chọn target

**Mục tiêu**: Xác định target chính của bài toán và kiểm tra bằng dữ liệu thật rằng target đó tồn tại trong cả bảng train và forecast frame.

Target được chọn:

```text
Revenue, COGS
```

Lý do:

- `sample_submission.csv` yêu cầu dự đoán `Revenue` và `COGS`.
- `sales.csv` chứa `Date`, `Revenue`, `COGS`.
- Target này phù hợp với câu chuyện EDA: vì sao doanh thu và giá vốn biến động theo ngày, và nhóm tín hiệu nào đủ hợp lý để đưa sang feature engineering.

#### Quy trình

- Kiểm tra target trong train: `Revenue`, `COGS` phải có trong `sales`.
- Kiểm tra target trong forecast frame: `Revenue`, `COGS` phải có trong `sample_submission`.
- Kiểm tra grain target: `sales.Date` phải unique ở grain ngày.
- Kiểm tra kiểu dữ liệu target: `Revenue`, `COGS` chuyển được sang numeric.
- Ghi câu chuyện phân tích: target phục vụ câu hỏi vì sao `Revenue`/`COGS` biến động theo ngày.

#### Câu hỏi cần trả lời

- Target cần phân tích là gì?
- Target nằm ở bảng nào?
- Target có trùng với cột cần dự đoán trong `sample_submission` không?
- Bảng target có đúng grain ngày không?
- Có đủ bằng chứng để dùng `sales` làm bảng target không?

#### Output định dạng

Tạo bảng `target_selection_check`:

| check_name | result | evidence | status |
|---|---|---|---|
| target_columns_in_sales | Revenue, COGS | sales có đủ 2 cột target | PASS |
| target_columns_in_sample_submission | Revenue, COGS | sample_submission có đủ 2 cột target | PASS |
| sales_date_unique | true/false | số dòng sales = số ngày unique | PASS/REVIEW |
| target_numeric_parseable | true/false | Revenue/COGS convert numeric được | PASS/REVIEW |

Tạo bảng `analysis_story_scope`:

| item | value | evidence | status |
|---|---|---|---|
| main_story | Vì sao Revenue và COGS biến động theo ngày? | bám target cần dự đoán | PASS |
| target_table | sales | có Date, Revenue, COGS | PASS |
| target_columns | Revenue, COGS | trùng sample_submission | PASS |
| next_pipeline_step | feature engineering | EDA chưa chọn feature cuối cùng | PASS |

#### KL

```text
Target được chọn là Revenue và COGS trong bảng sales. Bước này hoàn thành khi output cho thấy sales có đủ target, target trùng sample_submission, Date trong sales không bị duplicate ở grain ngày, và target có thể dùng cho phân tích.
```

---

### 2. Chọn forecast grain và forecast frame

**Mục tiêu**: Xác định mỗi dòng cần dự đoán đại diện cho cái gì và kiểm tra forecast frame có đúng grain ngày không.

Forecast được chọn:

```text
1 dòng = 1 ngày
Forecast frame = sample_submission
```

#### Quy trình

- Xác định forecast frame: dùng `sample_submission`.
- Kiểm tra grain forecast: mỗi dòng phải là 1 ngày unique.
- Kiểm tra continuity: forecast frame có daily frame liên tục không.
- Kiểm tra thứ tự thời gian: forecast period phải bắt đầu sau train period của `sales`.
- Khóa scope notebook: bước này chỉ xác định EDA scope, chưa modeling.

#### Câu hỏi cần trả lời

- Mỗi dòng dự báo đại diện cho ngày, order, customer hay product?
- Forecast frame là bảng nào?
- Forecast period có nối tiếp train period không?
- `sample_submission` có bị duplicate ngày không?
- Notebook này đang dừng ở EDA hay đã sang feature engineering/modeling?

#### Output định dạng

Tạo bảng `forecast_scope_check`:

| check_name | result | evidence | status |
|---|---|---|---|
| forecast_frame | sample_submission | có Date, Revenue, COGS | PASS |
| forecast_grain | daily | Date unique và không thiếu ngày trong forecast period | PASS/REVIEW |
| train_period | yyyy-mm-dd to yyyy-mm-dd | lấy từ sales.Date | PASS |
| forecast_period | yyyy-mm-dd to yyyy-mm-dd | lấy từ sample_submission.Date | PASS |
| train_forecast_order | forecast starts after train ends | ngày đầu forecast > ngày cuối train | PASS/REVIEW |
| notebook_stage | EDA only | chưa clean mạnh, chưa model | PASS |

#### KL

```text
Forecast grain là daily. Bước này hoàn thành khi output chứng minh sample_submission là forecast frame theo ngày, không duplicate Date, forecast period nối tiếp train period, và notebook chưa chuyển sang modeling.
```

---

### 3. Chọn các bảng liên quan đến target

**Mục tiêu**: Chọn các bảng có khả năng giải thích biến động daily `Revenue`/`COGS`, đồng thời ghi rõ grain, vai trò phân tích và rủi ro trước khi EDA.

#### Quy trình

- 3.1 Hypothesis backlog: lập H1-H5 gắn từng giả thuyết với target và bảng nguồn.
- 3.2 Helper và rule kiểm tra feasibility: định nghĩa rule về tồn tại bảng/cột, grain, coverage, join risk và leakage.
- 3.3 Feasibility check H1-H5: chạy kiểm tra tối thiểu để biết giả thuyết nào đủ dữ liệu EDA.
- 3.4 Chốt bảng phân tích: chọn bảng keep/skip/insight-only trước khi EDA sâu.
- 3.5 Audit câu hỏi phần A: xác nhận Phase A đã trả lời đủ target, forecast grain, bảng liên quan và rủi ro.

#### 3.1 Hypothesis backlog

**Mục tiêu**: Biến câu chuyện `Revenue`/`COGS` thành các giả thuyết H1-H5 có thể kiểm chứng bằng dữ liệu thật.

- H1: `Revenue` và `COGS` có trend, seasonality, outlier theo ngày/tháng/năm.
- H2: Web traffic tăng trước hoặc gần ngày bán thì `Revenue`/`COGS` tăng.
- H3: Order volume là driver lớn của `Revenue`.
- H4: Promotion/discount làm `Revenue` tăng nhưng margin có thể giảm.
- H5: Inventory stockout/fill rate có thể làm `Revenue` thấp.

#### 3.2 Helper và rule kiểm tra feasibility

**Mục tiêu**: Tạo helper/rule để kiểm tra giả thuyết có đủ bảng, đủ cột, đúng grain và đủ coverage trước khi EDA.

- Kiểm tra bảng bắt buộc có tồn tại trong `tables`.
- Kiểm tra cột bắt buộc có tồn tại trong từng bảng nguồn.
- Kiểm tra grain có thể aggregate về daily hoặc monthly không.
- Kiểm tra coverage thời gian có overlap với `sales.Date` không.
- Flag join risk và leakage risk trước khi tạo feature candidate.

#### 3.3 Feasibility check H1-H5

**Mục tiêu**: Chạy rule feasibility cho từng giả thuyết để quyết định giả thuyết nào được phân tích sâu, giả thuyết nào chỉ ghi nhận rủi ro.

- Kiểm tra H1 với `sales`.
- Kiểm tra H2 với `web_traffic` và `sales`.
- Kiểm tra H3 với `orders` và `sales`.
- Kiểm tra H4 với `promotions`, `order_items` và `sales`.
- Kiểm tra H5 với `inventory` và `sales`.

#### 3.4 Chốt bảng phân tích

**Mục tiêu**: Chọn bảng dùng trong EDA dựa trên vai trò phân tích, grain cần đưa về và rủi ro ML.

- Chọn bảng bắt buộc: `sales`, `sample_submission`.
- Chọn bảng time-varying chính: `web_traffic`, `orders`, `promotions`, `inventory`.
- Chọn bảng hỗ trợ: `order_items`, `products`.
- Ghi rõ bảng nào cần aggregate trước khi join với `sales`.
- Ghi rõ bảng nào chỉ dùng insight vì rủi ro leakage hoặc coverage.

#### 3.5 Audit câu hỏi phần A

**Mục tiêu**: Đóng Phase A bằng bảng audit để bảo đảm mọi quyết định scope đều có bằng chứng dữ liệu.

- Kiểm tra target đã được chọn và có trong train/forecast frame.
- Kiểm tra forecast grain daily đã được xác nhận.
- Kiểm tra bảng phân tích đã gắn với H1-H5.
- Kiểm tra rủi ro grain, join, leakage đã được ghi.
- Tạo `a_scope_answer_check` để notebook không bước sang EDA khi scope còn mơ hồ.

#### Câu hỏi cần trả lời

- Bảng nào là bảng target?
- Bảng nào là forecast frame?
- Bảng nào là bảng giao dịch/time-varying có thể giải thích target?
- Bảng master/lookup nào chỉ dùng hỗ trợ, không phân tích riêng?
- Bảng nào cần aggregate trước khi join với `sales`?
- Bảng nào có nguy cơ leakage nếu dùng same-day feature?
- Bảng nào nên keep, skip hoặc chỉ dùng làm insight?

#### Output định dạng

Tạo bảng `eda_scope`:

| scope_area | decision | reason | evidence | main_risk | status |
|---|---|---|---|---|---|
| target | Revenue, COGS | trùng sample_submission | target_selection_check PASS | none | PASS |
| forecast_grain | daily | mỗi dòng forecast là một ngày | forecast_scope_check PASS | none | PASS |
| primary_table | sales | chứa target chính | Date unique daily | none | PASS |
| selected_transaction_time_tables | web_traffic, orders, promotions, inventory | có tín hiệu thời gian/giao dịch | có date/order/promo/snapshot columns | cần aggregate/coverage check | PASS/REVIEW |
| supporting_tables | order_items, products | hỗ trợ promo/product insight | có order_id/product_id | target proxy nếu dùng same-day | REVIEW |
| out_of_scope | redo check_quality, cleaning mạnh, feature cuối cùng, modeling | thuộc bước khác | notebook stage = EDA only | scope creep | PASS |

Tạo bảng `hypothesis_backlog`:

| hypothesis_id | hypothesis | target_metric | source_tables | original_grain | analysis_grain | expected_pattern | join_risk | leakage_risk | priority |
|---|---|---|---|---|---|---|---|---|---|

Tạo bảng `hypothesis_feasibility_check`:

| hypothesis_id | required_tables | required_columns | data_available | grain_feasible | coverage_feasible | join_risk | leakage_risk | decision |
|---|---|---|---|---|---|---|---|---|

Tạo bảng `selected_tables_for_eda`:

| table | selected | related_hypotheses | analysis_role | required_grain | main_risk |
|---|---|---|---|---|---|

Tạo bảng `a_scope_answer_check`:

| plan_step | question | answer | evidence_output | status |
|---|---|---|---|---|

#### KL

```text
Phase A hoàn thành khi target đã được chọn, forecast grain daily được xác nhận, các bảng liên quan target được chọn có lý do, mỗi bảng có grain/risk rõ ràng, và a_scope_answer_check cho thấy các câu hỏi của phần A đều có output trả lời.
```

---

**Bảng đề xuất cho hypothesis backlog:**

| ID | Giả thuyết | Bảng cần dùng | Grain cần phân tích | Ý nghĩa với forecast |
|---|---|---|---|---|
| H1 | `Revenue` và `COGS` có trend, seasonality, outlier theo ngày/tháng/năm | `sales` | daily/monthly | tạo calendar + target lag/rolling |
| H2 | Web traffic tăng trước hoặc gần ngày bán thì Revenue/COGS tăng | `web_traffic`, `sales` | daily | tạo traffic lag/rolling |
| H3 | Order volume là driver lớn của Revenue | `orders`, `sales` | order -> daily | tạo order count lag/rolling nếu không leak |
| H4 | Promotion/discount làm Revenue tăng nhưng margin có thể giảm | `promotions`, `order_items`, `sales` | promo calendar daily + item | tạo promotion calendar feature |
| H5 | Inventory stockout/fill rate có thể làm Revenue thấp | `inventory`, `sales` | inventory snapshot -> daily/monthly | dùng nếu coverage đủ |

Ghi chú:

- Product/category mix **không pass thành giả thuyết EDA chính**.
- Nếu cần, phần product/category chỉ được xem như insight phụ để giải thích mix sau khi phân tích order/promotion, không đưa vào `hypothesis_result_summary` như một hypothesis riêng.

## Phase B: EDA theo câu chuyện chính và giả thuyết

### 1. EDA target để kiểm chứng H1

**Mục tiêu**: Kiểm chứng giả thuyết: H1: Revenue và COGS có trend, seasonality, outlier theo ngày/tháng/năm.

#### Quy trình

- Xác nhận nhanh `sales.Date`: dùng kết quả check_quality để bảo đảm grain ngày không lỗi nghiêm trọng.
- Tạo metric EDA: thêm `Gross_Profit = Revenue - COGS` và `Gross_Margin = Gross_Profit / Revenue`.
- Kiểm tra metric mới: rà soát `Revenue = 0`, `COGS > Revenue` và margin âm.
- Thống kê phân phối: tính mean, median, min, max, p95, p99 cho target và margin.
- Vẽ pattern thời gian: daily, rolling 7/30 ngày, monthly và calendar pattern.

#### Câu hỏi cần trả lời

- Revenue/COGS có trend tăng giảm không?
- Có seasonality theo tuần/tháng/năm không?
- Có outlier hoặc margin âm cần điều tra không?
- Pattern thời gian nào nên chuyển sang calendar hoặc lag/rolling feature?

#### Output định dạng

Tạo bảng:

- `target_descriptive_stats.csv`
- `target_outlier_days.csv`
- `target_monthly_summary.csv`

Tạo hình:

- `fig_01_daily_revenue_cogs.png`
- `fig_02_target_distribution.png`
- `fig_03_monthly_revenue_cogs_margin.png`
- `fig_04_calendar_pattern.png`

#### KL

```text
Kết luận H1: supported / partially supported / not supported.
Ghi rõ pattern thời gian nào có thể chuyển thành calendar hoặc lag/rolling feature.
```

---

### 2. EDA web traffic để kiểm chứng H2

**Mục tiêu**: Kiểm chứng giả thuyết: H2: Web traffic tăng trước hoặc gần ngày bán thì Revenue/COGS tăng.

#### Quy trình

- Xác nhận grain `web_traffic`: kiểm tra dữ liệu đang ở mức ngày hay `date x traffic_source`.
- Aggregate về ngày: sum traffic volume và dùng mean/weighted mean cho biến tỷ lệ.
- Kiểm tra output mới: `date` unique sau aggregate và join với `sales` không tăng dòng.
- Tạo lag/rolling: tạo traffic lag 1/7 ngày và rolling 7/30 ngày nếu không leak.
- Đánh giá quan hệ: so sánh correlation/scatter giữa traffic và `Revenue`/`COGS`.

#### Câu hỏi cần trả lời

- Traffic có coverage đủ để phân tích với sales không?
- Traffic same-day và lag/rolling có quan hệ với Revenue không?
- Traffic source nào đáng chú ý nếu dữ liệu có source-level?
- Nếu forecast trước ngày diễn ra, feature traffic nào an toàn hơn?

#### Output định dạng

Tạo bảng:

- `web_traffic_daily_summary.csv`
- `web_traffic_target_relationship.csv`

Tạo hình:

- `fig_05_web_traffic_coverage.png`
- `fig_06_traffic_vs_revenue.png`
- `fig_07_traffic_lag_rolling_relationship.png`

#### KL

```text
Kết luận H2: supported / partially supported / not supported.
Nếu supported, ưu tiên traffic lag/rolling cho feature engineering.
Không rolling sum các biến tỷ lệ như bounce_rate.
```

---

### 3. EDA orders để kiểm chứng H3

**Mục tiêu**: Kiểm chứng giả thuyết: H3: Order volume là driver lớn của Revenue.

#### Quy trình

- Xác nhận grain `orders`: kiểm tra 1 dòng có thật sự là 1 order không.
- Aggregate orders về ngày: tạo `order_count`, `unique_customer_count` và nhóm theo source/device/payment/status nếu hữu ích.
- Kiểm tra output mới: `order_date` unique sau aggregate và join với `sales` không tăng dòng.
- Phân tích quan hệ: so sánh `order_count` với `Revenue`, `COGS` và `Revenue/order`.
- Đánh dấu leakage: same-day `order_count` chỉ dùng để hiểu quan hệ, feature forecast nên ưu tiên lag/rolling.

#### Câu hỏi cần trả lời

- Số order theo ngày có giải thích biến động Revenue không?
- Source/device/payment/status nào liên quan đến biến động order volume?
- Same-day order_count có được dùng làm feature forecast không?

#### Output định dạng

Tạo bảng:

- `orders_daily_summary.csv`
- `orders_target_relationship.csv`
- `orders_group_distribution.csv`

Tạo hình:

- `fig_08_orders_daily_trend.png`
- `fig_09_order_count_vs_revenue.png`
- `fig_10_orders_by_source_device_payment.png`

#### KL

```text
Kết luận H3: supported / partially supported / not supported.
Order volume có thể là driver mạnh, nhưng same-day order_count thường không an toàn nếu model cần dự báo trước ngày diễn ra.
```

---

### 4. EDA promotions để kiểm chứng H4

**Mục tiêu**: Kiểm chứng giả thuyết: H4: Promotion/discount làm Revenue tăng nhưng margin có thể giảm.

#### Quy trình

- Xác nhận lịch promotion: kiểm tra `start_date`, `end_date` dùng được và có overlap với sales period.
- Tạo promotion calendar daily: tính `active_promo_count`, `avg_active_discount`, `stackable_promo_count`.
- Kiểm tra output mới: mỗi ngày chỉ 1 dòng và join với `sales` không tăng dòng.
- So sánh hiệu ứng promo: ngày có promo vs không promo theo `Revenue`, `COGS`, `Gross_Margin`.
- Kiểm tra promo usage: dùng `order_items` để giải thích, không tự động đưa same-day usage vào feature.

#### Câu hỏi cần trả lời

- Lịch promotion có phủ giai đoạn sales không?
- Ngày có promo Revenue có cao hơn không?
- Ngày có promo margin có thấp hơn không?
- Promotion calendar có an toàn cho forecast không?
- Promo usage trong order_items có nên chỉ dùng để giải thích, không dùng same-day feature không?

#### Output định dạng

Tạo bảng:

- `promotion_calendar_daily.csv`
- `promotion_target_summary.csv`
- `order_item_promo_usage_summary.csv`

Tạo hình:

- `fig_15_promotion_calendar.png`
- `fig_16_promo_vs_revenue_margin.png`

#### KL

```text
Kết luận H4: supported / partially supported / not supported.
Promotion calendar thường an toàn hơn promo usage cùng ngày, vì lịch promo có thể biết trước.
```

---

### 5. EDA inventory để kiểm chứng H5

**Mục tiêu**: Kiểm chứng giả thuyết: H5: Inventory stockout/fill rate có thể làm Revenue thấp.

#### Quy trình

- Xác nhận grain `inventory`: phân biệt daily product snapshot hay monthly product snapshot.
- Aggregate theo grain phù hợp: daily nếu có snapshot ngày, monthly nếu chỉ có snapshot tháng.
- Kiểm tra output mới: ngày/tháng sau aggregate phải unique, không tự forward-fill khi chưa có lý do.
- Tạo metric inventory: total stock, stockout rate, avg fill rate và sell-through rate nếu hợp lý.
- So sánh với target: đối chiếu stockout/fill rate với `Revenue` ở cùng tần suất.

#### Câu hỏi cần trả lời

- Inventory có đủ coverage daily không?
- Nếu chỉ monthly, có nên dùng cho daily forecast không?
- Stockout có đi cùng Revenue thấp không?
- Có nên đưa inventory vào feature engineering bản đầu không?

#### Output định dạng

Tạo bảng:

- `inventory_coverage_summary.csv`
- `inventory_time_summary.csv`

Tạo hình:

- `fig_17_inventory_coverage.png`
- `fig_18_stockout_vs_revenue.png`

#### KL

```text
Kết luận H5: supported / partially supported / not supported.
Nếu inventory coverage không phù hợp với daily target, ghi skip hoặc chỉ dùng như context, không ép join daily.
```

---

### 6. Tổng hợp giả thuyết, chọn feature candidate và viết Executive Summary

**Mục tiêu**: Tổng hợp kết quả EDA theo H1-H5, đề xuất feature candidate cho bước feature engineering, ghi lại risk register và kết thúc notebook bằng Executive Summary ra quyết định.

#### Quy trình

- 6.1 Hypothesis result summary: chốt kết luận supported/partially supported/not supported cho H1-H5.
- 6.2 Feature candidate catalog: liệt kê feature candidate có grain, nguồn, transformation và leakage risk.
- 6.3 EDA risk register: ghi rủi ro grain, join, leakage, coverage và target proxy còn lại.
- 6.4 Executive Summary: tóm tắt câu chuyện dữ liệu và quyết định bước tiếp theo.

#### 6.1 Hypothesis result summary

**Mục tiêu**: Tổng hợp bằng chứng chính của từng giả thuyết H1-H5 và quyết định giả thuyết đó được dữ liệu ủng hộ ở mức nào.

- Ghi kết luận H1-H5: supported, partially supported hoặc not supported.
- Gắn mỗi kết luận với bảng/biểu đồ bằng chứng.
- Diễn giải business meaning của từng kết quả.
- Ghi feature implication nếu giả thuyết nên đi tiếp sang feature engineering.
- Ghi remaining risk nếu dữ liệu chưa đủ mạnh hoặc có rủi ro leakage.

#### 6.2 Feature candidate catalog

**Mục tiêu**: Đề xuất feature candidate cho bước feature engineering nhưng chưa chốt feature cuối cùng trong EDA.

- Liệt kê feature từ target history, calendar, traffic, orders, promotions và inventory.
- Ghi source table và original grain của từng feature candidate.
- Ghi modeling grain cần đưa về, thường là daily.
- Ghi suggested transformation như lag, rolling, count, rate hoặc calendar flag.
- Ghi leakage risk và decision for next step.

#### 6.3 EDA risk register

**Mục tiêu**: Ghi lại các rủi ro có thể làm sai phân tích hoặc làm model bị leakage trước khi chuyển sang feature engineering.

- Ghi rủi ro grain mismatch giữa bảng nguồn và target daily.
- Ghi rủi ro join làm nhân dòng hoặc sai doanh thu.
- Ghi rủi ro same-day feature dùng thông tin không biết trước tại thời điểm forecast.
- Ghi rủi ro coverage không đủ theo thời gian.
- Ghi mitigation cho từng rủi ro để bước sau kiểm tra lại.

#### 6.4 Executive Summary

**Mục tiêu**: Kết thúc notebook bằng bản tóm tắt ra quyết định: dữ liệu đang nói gì, bảng nào dùng được, bảng nào rủi ro và bước sau nên làm gì.

- Tóm tắt câu chuyện chính quanh daily `Revenue`/`COGS`.
- Tóm tắt kết quả theo H1-H5.
- Tóm tắt driver có vẻ quan trọng nhất.
- Tóm tắt feature candidate nên đưa sang feature engineering.
- Ghi open questions trước modeling.

#### Câu hỏi cần trả lời

- Giả thuyết nào được dữ liệu ủng hộ mạnh?
- Giả thuyết nào chưa đủ bằng chứng?
- Feature candidate nào có business logic tốt?
- Feature nào có leakage risk cao?
- Feature nào cần skip vì coverage/grain không phù hợp?
- Câu chuyện chính được dữ liệu kể lại là gì?
- Driver nào có vẻ quan trọng nhất với Revenue/COGS?
- Rủi ro lớn nhất nếu train model ngay là gì?
- Bước tiếp theo cần làm gì?

#### Output định dạng

Tạo bảng `hypothesis_result_summary`:

| hypothesis_id | result | key_evidence | business_interpretation | feature_implication | remaining_risk |
|---|---|---|---|---|---|

Tạo bảng `eda_feature_candidate_catalog`:

| feature_candidate | source_table | original_grain | modeling_grain | suggested_transformation | expected_relation_to_target | leakage_risk | business_reason | decision_for_next_step |
|---|---|---|---|---|---|---|---|---|

Tạo bảng `eda_risk_register`:

| risk_area | description | affected_tables | impact_on_analysis_or_model | mitigation |
|---|---|---|---|---|

Tạo file:

- `report_4_6_2026/EDA_summary.md`
- `report_4_6_2026/eda_outputs/hypothesis_backlog.csv`
- `report_4_6_2026/eda_outputs/hypothesis_feasibility_check.csv`
- `report_4_6_2026/eda_outputs/hypothesis_result_summary.csv`
- `report_4_6_2026/eda_outputs/eda_feature_candidate_catalog.csv`
- `report_4_6_2026/eda_outputs/eda_risk_register.csv`

#### KL

```text
EDA hoàn thành khi H1-H5 có kết luận rõ ràng, feature candidate có lý do nghiệp vụ, grain đúng, coverage được kiểm tra, leakage được flag, và Executive Summary trả lời được dữ liệu đang nói gì về Revenue/COGS, bảng nào dùng được, bảng nào rủi ro, feature engineering nên bắt đầu từ đâu.
```

---

## C. Checklist hoàn thành `EDA.ipynb`

- [ ] Có câu chuyện phân tích chính.
- [ ] Có scope rõ ràng: target, time range, grain, bảng được chọn, ngoài scope.
- [ ] Có hypothesis backlog H1-H5.
- [ ] Có feasibility check H1-H5 dựa trên kết quả check_quality, không redo check_quality toàn bộ.
- [ ] Mỗi bảng trong EDA gắn với ít nhất một giả thuyết H1-H5.
- [ ] Master table không đứng thành giả thuyết riêng.
- [ ] Target `Revenue`/`COGS` được phân tích theo daily trend, seasonality, outlier.
- [ ] Không join raw bảng one-to-many/many-to-many vào `sales` daily.
- [ ] Có dùng `validate=` khi merge nếu quan hệ join đã biết.
- [ ] Có kiểm tra output mới tạo trong EDA: daily aggregate, metric mới, join mới, reconcile mới.
- [ ] Có kiểm tra rủi ro leakage cho từng nhóm feature candidate.
- [ ] Có kết luận supported/partially supported/not supported cho H1-H5.
- [ ] Có feature candidate catalog cho bước feature engineering.
- [ ] Có risk register.
- [ ] Có Executive Summary cuối notebook.

---

## D. Ghi chú phương pháp

- Phase A là **Chọn target và scope**, không phải data quality profiling.
- Check_quality đã làm nhiệm vụ kiểm tra chất lượng dữ liệu toàn cục.
- EDA chỉ kiểm tra dữ liệu ở mức vừa đủ để biết giả thuyết có phân tích được không và các output mới tạo có đúng grain không.
- Các bảng master chỉ đóng vai trò lookup/enrichment; giả thuyết nên bám vào target, thời gian và bảng giao dịch/time-varying.
