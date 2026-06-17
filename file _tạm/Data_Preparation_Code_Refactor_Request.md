# BẢN YÊU CẦU CHỈNH SỬA CODE NOTEBOOK `Data_Preparation_Clean.ipynb`

## 1. Mục tiêu chỉnh sửa

Chỉnh lại notebook theo hướng **gọn, tối giản, dễ đọc, ít code lặp**, nhưng vẫn giữ đủ các bước chuẩn bị dữ liệu:

1. **Clean Data**
2. **Feature**
3. **Format & Export**

Notebook hiện tại đã có cấu trúc tốt, đặc biệt là có tách 3 phần rõ ràng và đã chú ý tránh leakage bằng cách tạo lag/rolling feature. Tuy nhiên code vẫn cần chỉnh vì:

- Helper function còn ít, nhiều cell vẫn viết logic trực tiếp.
- Biểu đồ đang bị viết rải rác, khó tái sử dụng.
- Phần feature selection hiện mới lọc theo `missing_pct < 95` và `nunique > 1`, chưa đủ để giải thích tại sao feature được giữ.
- Các selected feature chưa được phân tích đầy đủ với target. Hiện notebook chỉ vẽ scatter cho **1 feature có correlation cao nhất**, chưa kiểm tra toàn bộ feature được chọn.
- Impute theo keyword trong tên cột còn hơi cảm tính.
- Một số biểu đồ như scatter không phù hợp cho mọi loại feature, ví dụ binary, calendar, month, day_of_week.

Mục tiêu sau chỉnh sửa: mỗi cell chỉ nên còn **vài dòng gọi hàm**, còn logic chính nằm trong helper function. Code phải ngắn hơn nhưng không được mất kiểm soát chất lượng dữ liệu.

---

## 2. Nguyên tắc chỉnh sửa code

### 2.1. Cell trong notebook phải ngắn

Mỗi cell nên theo dạng:

```python
missing_report = build_missing_report(clean)
show_report(missing_report, top=25)
plot_top_barh(missing_report, value_col="missing_count", label_cols=["table", "column"], title="Top missing values")
```

Không nên để cell dài 50-100 dòng nếu logic có thể đóng gói thành hàm.

### 2.2. Helper function đặt tập trung ở phần setup

Ở phần `0. Setup`, bổ sung các nhóm helper:

- Helper kiểm tra dữ liệu
- Helper tạo report
- Helper vẽ biểu đồ
- Helper tạo feature
- Helper phân tích feature với target
- Helper export artifact/report

Không rải hàm ở giữa notebook, vì sau này đọc lại sẽ rất loạn. Notebook mà biến thành rừng nhiệt đới thì người chạy code chỉ còn cách cầu mưa.

---

## 3. Cấu trúc notebook sau chỉnh sửa

### Section 0. Setup

Nên gồm:

1. Import library
2. Khai báo config
3. Khai báo danh sách file
4. Khai báo target
5. Khai báo helper function

Ví dụ cấu trúc:

```python
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pandas.tseries.holiday import USFederalHolidayCalendar

warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 120)
pd.set_option("display.width", 160)

DATA_DIR = Path("data")
OUT_DIR = Path("outputs/data_preparation_clean_feature_format")
REPORT_DIR = OUT_DIR / "reports"
CLEAN_DIR = OUT_DIR / "clean_tables"

TARGETS = ["Revenue", "COGS"]
DATE_COL = "Date"
VALID_START_DATE = pd.Timestamp("2021-01-01")
LAGS = [1, 7, 14, 28, 365]
ROLL_WINDOWS = [7, 28, 90]
APPLY_PCA = False
```

---

## 4. Bổ sung helper function để giảm code thừa

### 4.1. Helper hiển thị report

```python
def show_report(df, top=20, sort_by=None, ascending=False, title=None):
    if title:
        print(f"\n{title}")
    if df is None or len(df) == 0:
        print("No data")
        return
    out = df.copy()
    if sort_by and sort_by in out.columns:
        out = out.sort_values(sort_by, ascending=ascending)
    display(out.head(top))
```

Mục tiêu: không cần lặp `display(df.sort_values(...).head(...))` ở nhiều nơi.

---

### 4.2. Helper tạo nhãn field

```python
def make_field_label(df, cols, new_col="field", sep="."):
    out = df.copy()
    out[new_col] = out[cols].astype(str).agg(sep.join, axis=1)
    return out
```

Dùng cho các report dạng `table.column`.

---

### 4.3. Helper vẽ bar ngang top N

```python
def plot_top_barh(df, value_col, label_col=None, label_cols=None, title="", top=15, figsize=(8, 5)):
    if df is None or len(df) == 0:
        print("No data to plot:", title)
        return

    plot_df = df.copy()

    if label_col is None:
        if label_cols is None:
            raise ValueError("Need label_col or label_cols")
        plot_df = make_field_label(plot_df, label_cols, new_col="_label")
        label_col = "_label"

    plot_df = plot_df.sort_values(value_col).tail(top)

    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(plot_df[label_col], plot_df[value_col])
    ax.set_title(title)
    ax.set_xlabel(value_col)
    plt.tight_layout()
    plt.show()
```

Điểm cần sửa so với notebook hiện tại: không truyền hard-code `color` ở từng nơi nếu không cần. Ít màu lại cho đỡ biến dashboard thành hội chợ.

---

### 4.4. Helper vẽ histogram target

```python
def plot_target_distributions(df, targets, bins=50):
    for target in targets:
        if target not in df.columns:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(df[target].dropna(), bins=bins)
        ax.set_title(f"{target} distribution")
        ax.set_xlabel(target)
        ax.set_ylabel("count")
        plt.tight_layout()
        plt.show()
```

Thay vì viết riêng từng target trong `axes[0]`, `axes[1]`.

---

### 4.5. Helper vẽ time series

```python
def plot_time_series(df, date_col, value_cols, title="Time series", figsize=(10, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    for col in value_cols:
        if col in df.columns:
            ax.plot(df[date_col], df[col], label=col, linewidth=1)
    ax.set_title(title)
    ax.set_xlabel(date_col)
    ax.legend()
    plt.tight_layout()
    plt.show()
```

Dùng cho `Daily Revenue/COGS`, feature theo thời gian, hoặc target trend.

---

### 4.6. Helper scatter feature với target

```python
def plot_scatter_feature_target(df, feature, target, sample_n=3000, alpha=0.35):
    cols = [feature, target]
    sample = df[cols].dropna()

    if len(sample) == 0:
        print(f"No valid pair for {feature} vs {target}")
        return

    if len(sample) > sample_n:
        sample = sample.sample(sample_n, random_state=42)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(sample[feature], sample[target], s=8, alpha=alpha)
    ax.set_title(f"{target} vs {feature}")
    ax.set_xlabel(feature)
    ax.set_ylabel(target)
    plt.tight_layout()
    plt.show()
```

Lưu ý: scatter chỉ nên dùng cho feature numeric liên tục. Không nên ép mọi feature phải scatter, vì `is_weekend` mà scatter thì nhìn như 2 cột điểm, không giúp hiểu nhiều.

---

### 4.7. Helper phân tích feature dạng binary / low cardinality

```python
def plot_target_by_feature_group(df, feature, target):
    sample = df[[feature, target]].dropna()
    if len(sample) == 0:
        print(f"No valid data for {feature} and {target}")
        return

    summary = (
        sample.groupby(feature, as_index=False)
        .agg(
            target_mean=(target, "mean"),
            target_median=(target, "median"),
            rows=(target, "size")
        )
        .sort_values(feature)
    )

    display(summary)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(summary[feature].astype(str), summary["target_mean"])
    ax.set_title(f"Mean {target} by {feature}")
    ax.set_xlabel(feature)
    ax.set_ylabel(f"mean {target}")
    plt.tight_layout()
    plt.show()
```

Dùng cho:

- `is_weekend`
- `is_holiday`
- `month`
- `quarter`
- `day_of_week`
- các feature có số lượng unique thấp

---

## 5. Chỉnh phần Clean Data

### 5.1. Load file

Hiện tại phần load ổn, nhưng có thể đóng gói lại:

```python
def load_csv_files(files, data_dir):
    raw = {}
    rows = []

    for name, file_name in files.items():
        path = data_dir / file_name
        if not path.exists():
            rows.append([name, file_name, "missing", 0, 0])
            continue

        df = pd.read_csv(path)
        df.columns = [str(c).strip() for c in df.columns]
        raw[name] = df
        rows.append([name, file_name, "loaded", len(df), df.shape[1]])

    report = pd.DataFrame(rows, columns=["table", "file", "status", "rows", "cols"])
    return raw, report
```

Cell chính chỉ còn:

```python
raw, load_report = load_csv_files(FILES, DATA_DIR)
show_report(load_report, title="Load report")
```

---

### 5.2. Correct type

Tạo hàm chung cho date và numeric:

```python
def convert_date_columns(clean, date_cols):
    rows = []
    for table, cols in date_cols.items():
        if table not in clean:
            continue
        for col in cols:
            if col not in clean[table].columns:
                continue
            before_na = clean[table][col].isna().sum()
            parsed = pd.to_datetime(clean[table][col], errors="coerce").dt.normalize()
            invalid = int(parsed.isna().sum() - before_na)
            clean[table][col] = parsed
            rows.append([table, col, "date", invalid])
    return clean, rows


def convert_numeric_columns(clean, num_cols):
    rows = []
    for table, cols in num_cols.items():
        if table not in clean:
            continue
        for col in cols:
            if col not in clean[table].columns:
                continue
            before_na = clean[table][col].isna().sum()
            converted = pd.to_numeric(clean[table][col], errors="coerce")
            invalid = int(converted.isna().sum() - before_na)
            clean[table][col] = converted
            rows.append([table, col, "numeric", invalid])
    return clean, rows
```

Cell chính:

```python
clean = {name: df.copy() for name, df in raw.items()}

clean, date_type_rows = convert_date_columns(clean, DATE_COLS)
clean, numeric_type_rows = convert_numeric_columns(clean, NUM_COLS)

type_report = pd.DataFrame(
    date_type_rows + numeric_type_rows,
    columns=["table", "column", "target_type", "invalid_after_convert"]
)

show_report(type_report, sort_by="invalid_after_convert", title="Type conversion report")
```

---

### 5.3. Missing, duplicate, logic check, outlier

Các phần này nên viết thành hàm riêng:

```python
duplicate_report = build_duplicate_report(clean)
missing_report = build_missing_report(clean)
logic_report = build_logic_report(clean, NUM_COLS)
outlier_report = build_outlier_report(clean, OUTLIER_CHECKS)
```

Cell hiển thị:

```python
show_report(missing_report, top=25, sort_by="missing_pct", title="Missing overview")
plot_top_barh(missing_report, "missing_count", label_cols=["table", "column"], title="Top missing values")
```

Điểm nên giữ: **không tự động xóa/cap outlier** nếu chưa có bằng chứng nghiệp vụ. Ý này đúng.

---

## 6. Chỉnh phần Feature Engineering

### 6.1. Tách hàm tạo từng nhóm feature

Hiện notebook đang tạo `feature_tables` theo từng cell. Có thể giữ cách đó, nhưng mỗi cell nên gọi hàm:

```python
daily_base = build_daily_base(clean["sales"])
traffic_features = build_traffic_features(clean)
order_features = build_order_features(clean)
return_features = build_return_features(clean)
inventory_features = build_inventory_features(clean, daily_base)
promotion_features = build_promotion_features(clean, daily_base)
review_features = build_review_features(clean)
customer_features = build_customer_features(clean)
```

Sau đó gom:

```python
feature_tables = collect_feature_tables({
    "traffic": traffic_features,
    "orders": order_features,
    "items": item_features,
    "returns": return_features,
    "inventory": inventory_features,
    "promotions": promotion_features,
    "reviews": review_features,
    "customers": customer_features,
})
```

---

### 6.2. Tạo feature catalog

Bắt buộc nên có `feature_catalog`, vì nếu không thì `selected_features` chỉ là một list tên cột vô hồn. Máy thì thích list, người thì cần lý do.

`feature_catalog` nên có các cột:

| Cột | Ý nghĩa |
|---|---|
| `feature` | tên feature |
| `source_table` | lấy từ bảng nào |
| `feature_family` | calendar, target_lag, traffic_lag, order_lag, promo_known_now... |
| `timing_type` | known_now, lagged, rolling, same_day_excluded |
| `transformation` | raw, lag_7d, rolling_28d_mean... |
| `leakage_risk` | low, medium, high |
| `expected_impute_method` | fill_0, train_median, no_impute |
| `note` | giải thích ngắn |

Ví dụ:

```python
feature_catalog = pd.DataFrame([
    ["is_weekend", "calendar", "calendar", "known_now", "raw", "low", "no_impute", "Known before prediction date"],
    ["Revenue_lag_7d", "sales", "target_lag", "lagged", "lag_7d", "low", "train_median", "Past target value"],
    ["sessions_sum_lag_1d", "web_traffic", "traffic_lag", "lagged", "lag_1d", "low", "fill_0", "Past traffic"],
])
```

Nên viết hàm sinh tự động catalog từ tên feature, nhưng vẫn cho phép override thủ công nếu cần.

---

### 6.3. Rule tạo candidate feature

Giữ ý tưởng hiện tại:

- `known_now`: calendar + promotion biết trước ngày dự đoán
- `target_lag_cols`: lag/rolling của target
- `source_lag_cols`: lag/rolling của event source
- loại bỏ raw same-day event feature để tránh leakage

Điểm này hiện tại làm đúng hướng, nên giữ.

Tuy nhiên cần ghi rõ hơn:

```python
candidate_features = known_now + target_lag_cols + source_lag_cols
excluded_same_day_features = raw_same_day_cols
```

Và xuất report:

```python
feature_source_report = pd.DataFrame({
    "group": ["known_now", "target_lag", "source_lag", "excluded_same_day"],
    "count": [
        len(known_now),
        len(target_lag_cols),
        len(source_lag_cols),
        len(raw_same_day_cols),
    ]
})
display(feature_source_report)
```

---

## 7. Chỉnh phần Feature Selection

### 7.1. Vấn đề hiện tại

Hiện code chọn feature bằng rule:

```python
selected_features = feature_quality.query("nunique > 1 and missing_pct < 95")["feature"].tolist()
```

Rule này quá lỏng. Nó chỉ trả lời:

- feature không constant
- feature không thiếu gần hết

Nhưng chưa trả lời:

- feature có leakage không?
- feature có đủ quan sát trong train không?
- feature có liên quan với target không?
- feature có bị trùng thông tin với feature khác không?
- feature có phân phối bất thường không?
- feature có hợp lý về mặt nghiệp vụ không?

Nói thẳng: rule hiện tại chỉ là “feature này chưa chết hẳn”, chứ chưa chứng minh nó đáng được dùng.

---

### 7.2. Feature selection nên dùng train-only

Nếu correlation dùng để quyết định chọn feature, phải tính trên train thôi. Không dùng validation để chọn, vì validation là phần để kiểm tra mô hình.

Nên tạo:

```python
train_feature_table = feature_table[feature_table["Date"] < VALID_START_DATE].copy()
valid_feature_table = feature_table[feature_table["Date"] >= VALID_START_DATE].copy()
```

Sau đó tính quality và correlation trên `train_feature_table`.

---

### 7.3. Rule chọn feature đề xuất

Feature được chọn nếu đạt các điều kiện:

1. Không phải target, không phải Date
2. Không nằm trong danh sách same-day raw bị loại
3. Không có leakage risk cao
4. `nunique_train > 1`
5. `missing_train_pct < 95`
6. Có ít nhất 30 cặp non-null với target trong train
7. Nếu feature trùng cực mạnh với feature khác, giữ feature dễ hiểu hơn

Correlation không nên là điều kiện bắt buộc duy nhất. Feature correlation thấp vẫn có thể hữu ích cho model phi tuyến hoặc interaction.

---

### 7.4. Hàm tạo quality report

```python
def build_feature_quality_report(df, features, targets):
    rows = []

    for feature in features:
        if feature not in df.columns:
            continue

        s = df[feature]
        row = {
            "feature": feature,
            "missing_pct": round(s.isna().mean() * 100, 2),
            "nunique": int(s.nunique(dropna=True)),
            "dtype": str(s.dtype),
            "non_null_count": int(s.notna().sum()),
        }

        for target in targets:
            pair = df[[feature, target]].dropna()
            row[f"{target}_pair_count"] = len(pair)

            if len(pair) >= 30 and pair[feature].nunique() > 1:
                row[f"{target}_pearson"] = pair[feature].corr(pair[target], method="pearson")
                row[f"{target}_spearman"] = pair[feature].corr(pair[target], method="spearman")
            else:
                row[f"{target}_pearson"] = np.nan
                row[f"{target}_spearman"] = np.nan

        rows.append(row)

    return pd.DataFrame(rows)
```

---

### 7.5. Hàm chọn feature có lý do

```python
def select_features_with_reason(feature_quality, feature_catalog=None, missing_threshold=95, min_pair_count=30):
    report = feature_quality.copy()

    if feature_catalog is not None and len(feature_catalog):
        report = report.merge(feature_catalog, on="feature", how="left")

    reasons = []
    selected = []

    for _, row in report.iterrows():
        drop_reasons = []

        if row["nunique"] <= 1:
            drop_reasons.append("constant_or_single_value")

        if row["missing_pct"] >= missing_threshold:
            drop_reasons.append("too_many_missing")

        pair_cols = [c for c in report.columns if c.endswith("_pair_count")]
        if pair_cols and max([row[c] for c in pair_cols]) < min_pair_count:
            drop_reasons.append("not_enough_target_pairs")

        if "leakage_risk" in report.columns and row.get("leakage_risk") == "high":
            drop_reasons.append("high_leakage_risk")

        is_selected = len(drop_reasons) == 0
        selected.append(is_selected)
        reasons.append("selected" if is_selected else ";".join(drop_reasons))

    report["selected"] = selected
    report["selection_reason"] = reasons

    selected_features = report.loc[report["selected"], "feature"].tolist()
    return selected_features, report
```

---

## 8. Bắt buộc phân tích selected feature với target

### 8.1. Yêu cầu chính

Tất cả feature được chọn trong `selected_features` phải có phân tích với target. Không chỉ chọn xong rồi để đó.

Mỗi selected feature cần có:

1. Missing rate
2. Unique count
3. Pearson/Spearman correlation với từng target
4. Pair count với từng target
5. Loại feature: continuous / binary / low_cardinality / calendar / lag / rolling
6. Biểu đồ phù hợp:
   - Continuous numeric: scatter với target
   - Binary/low-cardinality: bar mean target theo nhóm
   - Calendar feature: group mean target theo `day_of_week`, `month`, `quarter`
   - Time-series feature: line plot feature theo thời gian và target theo thời gian nếu cần

---

### 8.2. Không nên scatter máy móc cho mọi feature

Ý tưởng “feature nào chọn cũng vẽ scatter với target” là đúng về mặt muốn kiểm tra, nhưng không phải lúc nào scatter cũng hợp lý.

Ví dụ:

| Feature | Scatter có hợp lý không? | Biểu đồ nên dùng |
|---|---:|---|
| `sessions_sum_lag_7d` | Có | scatter |
| `Revenue_lag_28d` | Có | scatter |
| `is_weekend` | Không tốt | bar mean target by group |
| `month` | Không tốt | line/bar mean target by month |
| `is_holiday` | Không tốt | grouped target summary |
| `promo_count_active` | Tạm được nếu nhiều mức | scatter hoặc bar theo nhóm |

Vậy yêu cầu sửa lại là: **mỗi selected feature phải được phân tích với target bằng biểu đồ phù hợp**, không nhất thiết tất cả đều scatter.

---

### 8.3. Hàm nhận diện kiểu feature

```python
def infer_feature_view_type(s, low_cardinality_threshold=12):
    nunique = s.nunique(dropna=True)

    if nunique <= 2:
        return "binary"
    if nunique <= low_cardinality_threshold:
        return "low_cardinality"
    if pd.api.types.is_numeric_dtype(s):
        return "continuous"
    return "other"
```

---

### 8.4. Hàm phân tích một feature với target

```python
def analyze_one_feature_vs_targets(df, feature, targets, date_col="Date"):
    if feature not in df.columns:
        print(f"Missing feature: {feature}")
        return

    view_type = infer_feature_view_type(df[feature])

    print(f"\nFeature: {feature}")
    print(f"View type: {view_type}")
    print(f"Missing pct: {df[feature].isna().mean() * 100:.2f}%")
    print(f"Nunique: {df[feature].nunique(dropna=True)}")

    for target in targets:
        if target not in df.columns:
            continue

        pair = df[[feature, target]].dropna()

        if len(pair) >= 30 and pair[feature].nunique() > 1:
            pearson = pair[feature].corr(pair[target], method="pearson")
            spearman = pair[feature].corr(pair[target], method="spearman")
            print(f"{target}: pair_count={len(pair)}, pearson={pearson:.3f}, spearman={spearman:.3f}")
        else:
            print(f"{target}: not enough valid pairs")

        if view_type == "continuous":
            plot_scatter_feature_target(df, feature, target)
        elif view_type in ["binary", "low_cardinality"]:
            plot_target_by_feature_group(df, feature, target)
        else:
            print(f"No default plot for {feature}")
```

---

### 8.5. Hàm phân tích toàn bộ selected features

```python
def analyze_selected_features(df, selected_features, targets, max_display_features=None):
    features_to_plot = selected_features

    if max_display_features is not None:
        features_to_plot = selected_features[:max_display_features]

    for feature in features_to_plot:
        analyze_one_feature_vs_targets(df, feature, targets)
```

Nếu số feature quá nhiều, không nên hiển thị hết trong notebook vì sẽ rất dài. Cách tốt hơn:

- Hiển thị top 10-20 feature quan trọng trong notebook.
- Export report đầy đủ cho tất cả selected features.
- Nếu cần, lưu toàn bộ biểu đồ ra folder `outputs/.../feature_plots`.

---

## 9. Nên export thêm report cho feature analysis

Bổ sung các file export:

```python
reports = {
    ...
    "feature_quality_report.csv": feature_quality,
    "feature_selection_report.csv": feature_selection_report,
    "feature_catalog.csv": feature_catalog,
    "selected_feature_target_report.csv": selected_feature_target_report,
}
```

`selected_feature_target_report.csv` nên có:

| Cột | Ý nghĩa |
|---|---|
| `feature` | tên feature |
| `target` | target được so sánh |
| `view_type` | continuous / binary / low_cardinality |
| `pair_count` | số dòng đủ dữ liệu |
| `missing_pct` | tỷ lệ missing |
| `nunique` | số unique |
| `pearson` | tương quan Pearson |
| `spearman` | tương quan Spearman |
| `analysis_plot_type` | scatter / group_bar / time_series |
| `selected` | có được chọn không |
| `selection_reason` | lý do chọn hoặc loại |

---

## 10. Chỉnh phần imputation

### 10.1. Vấn đề hiện tại

Hiện notebook dùng:

```python
zero_tokens = ["count", "quantity", "sessions", "visitors", "views", "return", "refund", "stock", "discount", "promo"]
```

Cách này chạy được, nhưng hơi cảm tính. Tên cột có chữ `discount` chưa chắc missing nên fill 0. Tên cột có chữ `stock` cũng chưa chắc missing là 0. Nếu fill sai, model học sai luôn. Một cách rất con người để làm hỏng mô hình.

---

### 10.2. Đề xuất sửa

Dùng `feature_catalog["expected_impute_method"]` thay cho đoán bằng tên cột.

Ví dụ:

```python
def impute_train_valid(X_train_raw, X_valid_raw, selected_features, feature_catalog=None):
    X_train = X_train_raw.copy()
    X_valid = X_valid_raw.copy()
    rows = []

    impute_map = {}
    if feature_catalog is not None and "expected_impute_method" in feature_catalog.columns:
        impute_map = dict(zip(feature_catalog["feature"], feature_catalog["expected_impute_method"]))

    for col in selected_features:
        method = impute_map.get(col, "train_median")

        if method == "fill_0":
            value = 0
        elif method == "no_impute":
            value = X_train[col].median()
            if pd.isna(value):
                value = 0
            method = "train_median_fallback"
        else:
            value = X_train[col].median()
            if pd.isna(value):
                value = 0

        tr_before = int(X_train[col].isna().sum())
        va_before = int(X_valid[col].isna().sum())

        X_train[col] = X_train[col].fillna(value)
        X_valid[col] = X_valid[col].fillna(value)

        rows.append([
            col, method, value,
            tr_before, int(X_train[col].isna().sum()),
            va_before, int(X_valid[col].isna().sum())
        ])

    report = pd.DataFrame(rows, columns=[
        "feature", "method", "fill_value_from_train",
        "train_missing_before", "train_missing_after",
        "valid_missing_before", "valid_missing_after"
    ])

    return X_train, X_valid, report
```

---

## 11. Chỉnh phần high correlation giữa feature

Hiện có `high_corr_report`, nên giữ.

Nhưng nên bổ sung cột gợi ý hành động:

```python
def build_high_corr_report(X_train, threshold=0.95):
    if X_train.shape[1] <= 1:
        return pd.DataFrame(columns=["feature_a", "feature_b", "abs_corr", "suggested_action"])

    corr = X_train.corr().abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))

    report = upper.stack().reset_index()
    report.columns = ["feature_a", "feature_b", "abs_corr"]
    report = report[report["abs_corr"] >= threshold].sort_values("abs_corr", ascending=False)

    report["suggested_action"] = "review_keep_one_if_linear_model"
    return report
```

Không tự động drop feature high correlation, vì model tree-based vẫn có thể chịu được. Nhưng nếu dùng linear/PCA thì cần xem.

---

## 12. Chỉnh phần PCA

PCA hiện đang viết thủ công bằng SVD. Không sai, nhưng với notebook chuẩn bị dữ liệu thì hơi làm người đọc phân tâm.

Đề xuất:

- Nếu mục tiêu chỉ chuẩn bị dữ liệu: giữ `APPLY_PCA = False`
- Nếu bật PCA: dùng helper riêng
- Không để logic PCA dài trong cell chính

```python
def apply_pca_if_enabled(X_train_scaled, X_valid_scaled, enabled=False, variance_threshold=0.95):
    pca_report = pd.DataFrame()
    X_train_pca = pd.DataFrame(index=X_train_scaled.index)
    X_valid_pca = pd.DataFrame(index=X_valid_scaled.index)

    if not enabled or X_train_scaled.shape[1] <= 1:
        return X_train_pca, X_valid_pca, pca_report

    U, S, Vt = np.linalg.svd(X_train_scaled.values, full_matrices=False)
    explained = (S ** 2) / np.sum(S ** 2)
    keep = int(np.searchsorted(np.cumsum(explained), variance_threshold) + 1)

    cols = [f"PC{i+1}" for i in range(keep)]
    X_train_pca = pd.DataFrame(X_train_scaled.values @ Vt[:keep].T, columns=cols, index=X_train_scaled.index)
    X_valid_pca = pd.DataFrame(X_valid_scaled.values @ Vt[:keep].T, columns=cols, index=X_valid_scaled.index)

    pca_report = pd.DataFrame({
        "component": cols,
        "explained_variance_ratio": explained[:keep],
        "cumulative_explained_variance": np.cumsum(explained[:keep])
    })

    return X_train_pca, X_valid_pca, pca_report
```

---

## 13. Những điểm hiện tại chưa hợp lý cần sửa thẳng

### 13.1. `selected_features` chưa được giải thích đủ

Hiện chỉ chọn theo missing và nunique. Cần thêm `selection_reason`, `feature_catalog`, `target_report`.

### 13.2. Chỉ vẽ scatter cho 1 top feature là chưa đủ

Hiện code:

```python
top_feature = corr_report.assign(abs_pearson=lambda d: d.pearson.abs()).sort_values("abs_pearson", ascending=False).iloc[0]["feature"]
```

Cái này chỉ giúp xem feature mạnh nhất, không giúp kiểm tra toàn bộ feature đã chọn.

Cần thay bằng:

```python
selected_feature_target_report = build_selected_feature_target_report(
    train_feature_table,
    selected_features,
    TARGETS
)

show_report(selected_feature_target_report, sort_by="abs_spearman", title="Selected feature vs target report")

analyze_selected_features(
    train_feature_table,
    selected_features=selected_features,
    targets=TARGETS,
    max_display_features=20
)
```

### 13.3. Scatter không phù hợp cho mọi feature

Không nên bắt tất cả feature scatter. Với binary/calendar, dùng grouped summary tốt hơn.

### 13.4. Correlation nếu dùng để chọn thì phải train-only

Nếu chỉ để hiểu dữ liệu thì có thể xem toàn bộ, nhưng nếu ảnh hưởng đến lựa chọn feature thì chỉ dùng train.

### 13.5. Impute theo tên cột còn yếu

Nên chuyển sang `feature_catalog.expected_impute_method`.

### 13.6. Promotion feature đang loop từng ngày

Đoạn này ổn nếu dữ liệu nhỏ, nhưng nếu dữ liệu lớn sẽ chậm:

```python
for d in promo_daily["Date"]:
    active = promo[(promo["start_date"] <= d) & (promo["end_date"] >= d)]
```

Có thể giữ nếu dataset nhỏ, nhưng nên ghi chú:

```python
# OK for small/medium data. For large data, replace with interval expansion/vectorized approach.
```

### 13.7. Inventory forward-fill cần xác nhận thời điểm snapshot

Đoạn forward-fill inventory hợp lý nếu snapshot có nghĩa là thông tin đã biết từ ngày snapshot trở đi. Nếu snapshot là báo cáo cuối tháng nhưng lại dùng cho các ngày trong tháng thì có nguy cơ leakage. Hiện code đang `ffill`, không backfill, nên tạm ổn, nhưng vẫn cần note nghiệp vụ.

### 13.8. Nên export biểu đồ hoặc ít nhất export report

Nếu phân tích nhiều feature mà chỉ hiển thị trong notebook, rất khó kiểm tra lại. Nên export CSV report đầy đủ. Nếu cần đẹp hơn thì lưu plot vào folder.

---

## 14. Cell mẫu sau khi chỉnh

### 14.1. Setup helper

```python
# Sau import/config
for folder in [OUT_DIR, REPORT_DIR, CLEAN_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

print("Output:", OUT_DIR.resolve())
```

---

### 14.2. Clean data

```python
raw, load_report = load_csv_files(FILES, DATA_DIR)
clean = {name: df.copy() for name, df in raw.items()}

clean, date_rows = convert_date_columns(clean, DATE_COLS)
clean, numeric_rows = convert_numeric_columns(clean, NUM_COLS)

type_report = pd.DataFrame(
    date_rows + numeric_rows,
    columns=["table", "column", "target_type", "invalid_after_convert"]
)

duplicate_report = build_duplicate_report(clean)
missing_report = build_missing_report(clean)
logic_report = build_logic_report(clean, NUM_COLS)
outlier_report = build_outlier_report(clean, OUTLIER_CHECKS)

show_report(load_report, title="Load report")
show_report(type_report, sort_by="invalid_after_convert", title="Type conversion report")
show_report(missing_report, top=25, sort_by="missing_pct", title="Missing overview")

plot_top_barh(missing_report, "missing_count", label_cols=["table", "column"], title="Top missing values")
plot_top_barh(outlier_report, "outlier_count", label_cols=["table", "column"], title="IQR outlier count")
```

---

### 14.3. Feature build

```python
daily_base = build_daily_base(clean["sales"])
plot_time_series(daily_base, "Date", TARGETS, title="Daily Revenue/COGS")

feature_tables = build_all_feature_tables(clean, daily_base)
agg_report = build_aggregation_report(feature_tables)
daily_model, join_report = join_feature_tables(daily_base, feature_tables)

show_report(agg_report, title="Feature table grain check")
show_report(join_report, title="Feature join report")
```

---

### 14.4. Leakage-safe feature generation

```python
daily_model, target_lag_cols = add_lag_roll(daily_model, "Date", TARGETS)

known_now = build_known_now_features(daily_model)
raw_same_day_cols = find_raw_same_day_numeric_cols(
    daily_model,
    exclude_cols=["Date"] + TARGETS + known_now + target_lag_cols
)

daily_model, source_lag_cols = add_lag_roll(daily_model, "Date", raw_same_day_cols)

candidate_features = known_now + target_lag_cols + source_lag_cols

feature_table = daily_model[["Date"] + TARGETS + candidate_features].copy()
feature_catalog = build_feature_catalog(candidate_features, known_now, target_lag_cols, source_lag_cols, raw_same_day_cols)

display_feature_source_summary(known_now, target_lag_cols, source_lag_cols, raw_same_day_cols)
```

---

### 14.5. Feature selection and analysis

```python
train_feature_table = feature_table[feature_table["Date"] < VALID_START_DATE].copy()

feature_quality = build_feature_quality_report(
    train_feature_table,
    candidate_features,
    TARGETS
)

selected_features, feature_selection_report = select_features_with_reason(
    feature_quality,
    feature_catalog=feature_catalog,
    missing_threshold=95,
    min_pair_count=30
)

selected_feature_target_report = build_selected_feature_target_report(
    train_feature_table,
    selected_features,
    TARGETS
)

show_report(feature_selection_report, top=30, sort_by="missing_pct", title="Feature selection report")
show_report(selected_feature_target_report, top=30, sort_by="abs_spearman", title="Selected feature vs target report")

plot_target_distributions(train_feature_table, TARGETS)

analyze_selected_features(
    train_feature_table,
    selected_features=selected_features,
    targets=TARGETS,
    max_display_features=20
)
```

Ghi chú: Nếu muốn phân tích **tất cả** selected features, đặt `max_display_features=None`, nhưng notebook có thể rất dài.

---

### 14.6. Format and export

```python
model_data, train, valid = split_model_data(
    feature_table,
    selected_features,
    targets=TARGETS,
    valid_start_date=VALID_START_DATE,
    min_lag_days=max(LAGS)
)

X_train_raw, X_valid_raw, y_train, y_valid = make_xy_split(train, valid, selected_features, TARGETS)

X_train, X_valid, imputation_report = impute_train_valid(
    X_train_raw,
    X_valid_raw,
    selected_features,
    feature_catalog=feature_catalog
)

X_train_scaled, X_valid_scaled, scale_report = scale_train_valid(X_train, X_valid)

high_corr_report = build_high_corr_report(X_train_scaled, threshold=0.95)

X_train_pca, X_valid_pca, pca_report = apply_pca_if_enabled(
    X_train_scaled,
    X_valid_scaled,
    enabled=APPLY_PCA
)

final_checks = build_final_checks(X_train, X_valid, train, valid, TARGETS)

show_report(imputation_report, top=20, sort_by="train_missing_before", title="Imputation report")
show_report(high_corr_report, top=20, sort_by="abs_corr", title="High correlation feature pairs")
show_report(final_checks, title="Final checks")
```

---

## 15. Checklist sau khi chỉnh

Notebook sau chỉnh sửa cần đạt checklist này:

### Code style

- [ ] Cell ngắn, chủ yếu gọi hàm.
- [ ] Không lặp code vẽ biểu đồ.
- [ ] Không hard-code quá nhiều logic ở giữa notebook.
- [ ] Helper đặt tập trung ở setup.
- [ ] Tên hàm rõ nghĩa.

### Clean data

- [ ] Có load report.
- [ ] Có type conversion report.
- [ ] Có duplicate report.
- [ ] Có missing report và biểu đồ top missing.
- [ ] Có logic check.
- [ ] Có outlier report.
- [ ] Không tự động xóa/cap outlier nếu chưa có bằng chứng.

### Feature

- [ ] Có daily base.
- [ ] Có feature table theo source.
- [ ] Có aggregation report kiểm tra one row per date.
- [ ] Có join report.
- [ ] Có loại bỏ same-day raw event feature.
- [ ] Có lag/rolling để tránh leakage.
- [ ] Có feature catalog.

### Feature selection

- [ ] Chọn feature bằng train-only nếu rule chọn dùng correlation/target.
- [ ] Có feature quality report.
- [ ] Có selection reason cho từng feature.
- [ ] Có selected feature target report.
- [ ] Tất cả selected features đều có phân tích với target.
- [ ] Biểu đồ phân tích feature-target phù hợp loại feature.
- [ ] Không chỉ vẽ duy nhất một top feature.

### Format & Export

- [ ] Split theo thời gian.
- [ ] Impute bằng train-only.
- [ ] Scale bằng train-only.
- [ ] Có high correlation report.
- [ ] PCA optional, mặc định tắt.
- [ ] Có final checks.
- [ ] Export đủ data và reports.

---

## 16. Kết luận chỉnh sửa

Ý tưởng chính của bản chỉnh sửa là đúng:

- Code cần gọn hơn.
- Nên viết helper để tái sử dụng.
- Feature đã chọn phải được phân tích với target.
- Không nên để selected feature chỉ là một list tên cột.

Nhưng cần sửa lại một điểm trong ý tưởng ban đầu:

> Không phải feature nào cũng nên vẽ scatter với target.

Yêu cầu đúng hơn là:

> Mỗi selected feature phải được phân tích với target bằng loại biểu đồ phù hợp với bản chất của feature.

Với feature liên tục thì scatter. Với binary/calendar/low-cardinality thì group summary hoặc bar mean target. Với time series thì thêm line plot nếu cần.

Nếu chỉnh theo hướng này, notebook sẽ vừa gọn hơn, vừa có khả năng giải thích rõ vì sao một feature được chọn, thay vì “chọn vì code bảo thế”. Và vâng, code mà không giải thích được quyết định của nó thì chỉ là một hộp đen đội mũ Pandas.
