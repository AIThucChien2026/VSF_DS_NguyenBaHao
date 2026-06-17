# Hướng Dẫn Trình Bày & Chia Shell Hợp Lý Cho Dự Án Data Science

> Tài liệu này hướng dẫn AI (và người dùng) cách tổ chức notebook/script Data Science một cách rõ ràng, dễ đọc, dễ debug và dễ tái sử dụng.

---

## 1. Nguyên Tắc Cốt Lõi

| Nguyên tắc | Giải thích |
|---|---|
| **Một cell, một mục đích** | Mỗi cell chỉ làm một việc duy nhất, có thể chạy độc lập |
| **Thứ tự tuyến tính** | Chạy từ trên xuống dưới không bị lỗi |
| **Markdown giải thích** | Trước mỗi nhóm cell lớn phải có markdown mô tả ngắn gọn |
| **Output có ý nghĩa** | Mỗi cell quan trọng nên in ra kết quả kiểm chứng |
| **Tái sử dụng được** | Hàm/logic dùng nhiều lần → tách ra cell riêng hoặc file `.py` |

---

## 2. Cấu Trúc Notebook Chuẩn

### 2.1 Sơ đồ tổng thể

```
[0] Tiêu đề & Mô tả dự án (Markdown)
[1] Import thư viện
[2] Cấu hình & Hằng số
[3] Load dữ liệu
[4] Khám phá dữ liệu (EDA)
[5] Làm sạch & Tiền xử lý
[6] Feature Engineering
[7] Chia tập train/val/test
[8] Xây dựng & Huấn luyện mô hình
[9] Đánh giá mô hình
[10] Trực quan hóa kết quả
[11] Lưu mô hình / Kết luận
```

---

## 3. Quy Tắc Chia Shell Theo Từng Giai Đoạn

### 3.1 Import & Cấu hình

```python
# ✅ ĐÚNG — Gom toàn bộ import vào 1 cell duy nhất ở đầu
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Cấu hình hiển thị
pd.set_option("display.max_columns", 50)
plt.style.use("seaborn-v0_8-whitegrid")
%matplotlib inline
```

```python
# ✅ Cell riêng cho hằng số & đường dẫn
DATA_PATH   = "data/raw/dataset.csv"
MODEL_PATH  = "models/best_model.pkl"
RANDOM_SEED = 42
TEST_SIZE   = 0.2
```

> ❌ **Tránh**: import rải rác nhiều cell, hoặc hardcode đường dẫn lẫn trong logic.

---

### 3.2 Load dữ liệu

```python
# ✅ Cell load — luôn in shape và vài dòng đầu để kiểm chứng
df = pd.read_csv(DATA_PATH)
print(f"Shape: {df.shape}")
df.head()
```

```python
# ✅ Cell kiểm tra sơ bộ — tách riêng để dễ bỏ qua khi chạy lại
print(df.dtypes)
print("\nMissing values:\n", df.isnull().sum())
print("\nDuplicates:", df.duplicated().sum())
```

> ❌ **Tránh**: gộp load + clean + visualize vào cùng một cell.

---

### 3.3 EDA (Khám phá dữ liệu)

Mỗi câu hỏi phân tích = 1 cell. Ví dụ:

```python
# Phân phối biến mục tiêu
df["target"].value_counts(normalize=True).plot(kind="bar")
plt.title("Phân phối nhãn")
plt.show()
```

```python
# Tương quan giữa các biến số
corr = df.select_dtypes("number").corr()
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm")
plt.title("Ma trận tương quan")
plt.show()
```

```python
# Phân tích outlier cho từng cột quan trọng
for col in ["age", "income", "score"]:
    print(f"{col}: Q1={df[col].quantile(0.25):.1f}, Q3={df[col].quantile(0.75):.1f}")
```

**Quy tắc EDA:**
- Mỗi plot = 1 cell riêng
- Luôn có `plt.title()` và label trục
- Dùng markdown ghi nhận insight ngay bên dưới plot

---

### 3.4 Làm sạch & Tiền xử lý

```python
# ✅ Mỗi bước xử lý = 1 cell, có comment giải thích lý do
# Xử lý missing values
df["age"].fillna(df["age"].median(), inplace=True)
df["category"].fillna("Unknown", inplace=True)
print("Missing sau xử lý:", df.isnull().sum().sum())
```

```python
# Loại bỏ outlier bằng IQR
Q1, Q3 = df["income"].quantile([0.25, 0.75])
IQR = Q3 - Q1
df = df[df["income"].between(Q1 - 1.5*IQR, Q3 + 1.5*IQR)]
print(f"Shape sau lọc outlier: {df.shape}")
```

```python
# Encode biến categorical
df = pd.get_dummies(df, columns=["gender", "region"], drop_first=True)
print("Columns sau encode:", df.columns.tolist())
```

> ❌ **Tránh**: gộp fillna + encode + scale + split vào 1 cell duy nhất.

---

### 3.5 Feature Engineering

```python
# ✅ Tạo feature mới — mỗi nhóm feature liên quan = 1 cell
df["age_group"]       = pd.cut(df["age"], bins=[0,25,45,65,100], labels=["youth","adult","middle","senior"])
df["income_per_age"]  = df["income"] / (df["age"] + 1)
df["high_value"]      = (df["income"] > df["income"].median()).astype(int)

print("Features mới:", ["age_group", "income_per_age", "high_value"])
df[["age", "income", "age_group", "income_per_age", "high_value"]].head()
```

---

### 3.6 Chia tập & Scale

```python
# Tách feature và target
X = df.drop(columns=["target"])
y = df["target"]

# Chia train/test
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED, stratify=y
)
print(f"Train: {X_train.shape}, Test: {X_test.shape}")
```

```python
# Scale — fit trên train, transform cả hai
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)   # ← KHÔNG fit lại trên test!
```

> ⚠️ **Lỗi phổ biến**: `fit_transform` cả trên test → data leakage. Luôn chỉ `transform` test.

---

### 3.7 Xây dựng & Huấn luyện mô hình

```python
# ✅ Mỗi mô hình = 1 cell riêng để dễ so sánh
from sklearn.ensemble import RandomForestClassifier

rf_model = RandomForestClassifier(n_estimators=100, random_state=RANDOM_SEED)
rf_model.fit(X_train_scaled, y_train)
print("✓ Random Forest trained")
```

```python
from sklearn.linear_model import LogisticRegression

lr_model = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
lr_model.fit(X_train_scaled, y_train)
print("✓ Logistic Regression trained")
```

---

### 3.8 Đánh giá mô hình

```python
# ✅ Hàm đánh giá tái sử dụng — định nghĩa 1 lần
from sklearn.metrics import classification_report, roc_auc_score, ConfusionMatrixDisplay

def evaluate_model(name, model, X, y):
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]
    print(f"\n{'='*40}")
    print(f"Model: {name}")
    print(classification_report(y, y_pred))
    print(f"AUC-ROC: {roc_auc_score(y, y_prob):.4f}")
    ConfusionMatrixDisplay.from_predictions(y, y_pred, display_labels=["No","Yes"])
    plt.title(f"Confusion Matrix — {name}")
    plt.show()
```

```python
# Gọi hàm đánh giá cho từng mô hình
evaluate_model("Random Forest",      rf_model, X_test_scaled, y_test)
evaluate_model("Logistic Regression", lr_model, X_test_scaled, y_test)
```

---

## 4. Quy Tắc Markdown Trong Notebook

### Khi nào cần thêm markdown cell?

| Tình huống | Markdown cần viết |
|---|---|
| Bắt đầu phần mới | `## 3. Làm sạch dữ liệu` + 1-2 câu mục tiêu |
| Sau EDA plot | Insight rút ra: *"Phân phối lệch phải, cần log-transform"* |
| Trước bước quan trọng | Giải thích lý do chọn kỹ thuật |
| Kết thúc notebook | Tóm tắt kết quả & bước tiếp theo |

### Template markdown chuẩn cho mỗi section:

```markdown
## 4. Feature Engineering

**Mục tiêu**: Tạo các biến mới có khả năng dự đoán cao hơn từ dữ liệu thô.

**Các feature sẽ tạo**:
- `income_per_age`: thu nhập tương đối theo tuổi
- `age_group`: nhóm tuổi để nắm bắt phi tuyến tính
- `high_value`: nhãn nhị phân dựa trên ngưỡng thu nhập trung vị
```

---

## 5. Anti-patterns Cần Tránh

### ❌ Cell quá dài (God Cell)

```python
# KHÔNG NÊN — 1 cell làm quá nhiều việc
df = pd.read_csv("data.csv")
df.dropna(inplace=True)
df["new_col"] = df["a"] / df["b"]
X = df.drop("target", axis=1)
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)
model = RandomForestClassifier().fit(X_train, y_train)
print(model.score(X_test, y_test))
```

### ✅ Tách đúng cách

Chia cell trên thành **7 cell riêng biệt**, mỗi cell có comment tiêu đề.

---

### ❌ Không có output kiểm chứng

```python
# Xử lý xong nhưng không in gì → không biết có lỗi không
df.fillna(0, inplace=True)
df.drop_duplicates(inplace=True)
```

### ✅ Luôn kiểm chứng

```python
df.fillna(0, inplace=True)
df.drop_duplicates(inplace=True)
print(f"Shape: {df.shape} | Missing: {df.isnull().sum().sum()} | Dups: {df.duplicated().sum()}")
```

---

### ❌ Magic numbers rải rác

```python
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
```

### ✅ Dùng hằng số đã định nghĩa

```python
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED)
```

---

## 6. Checklist Trước Khi Submit Notebook

- [ ] Chạy **Kernel → Restart & Run All** không có lỗi
- [ ] Tất cả cell đều có output có ý nghĩa
- [ ] Không có cell nào vượt quá ~30 dòng code
- [ ] Mỗi section lớn có markdown giải thích
- [ ] Không có data leakage (fit trên train, transform trên test)
- [ ] Đường dẫn file dùng hằng số, không hardcode
- [ ] Random seed cố định để kết quả reproducible
- [ ] Plot có title, axis label, legend đầy đủ
- [ ] Kết quả mô hình được in ra rõ ràng với tên mô hình

---

## 7. Cấu Trúc Thư Mục Khuyến Nghị

```
project/
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_preprocessing.ipynb
│   ├── 03_modeling.ipynb
│   └── 04_evaluation.ipynb
├── src/
│   ├── features.py      # Hàm feature engineering tái sử dụng
│   ├── train.py         # Script training chính
│   └── evaluate.py      # Hàm đánh giá
├── data/
│   ├── raw/             # Dữ liệu gốc, KHÔNG chỉnh sửa
│   └── processed/       # Dữ liệu đã xử lý
├── models/              # Mô hình đã lưu
├── reports/             # Kết quả, biểu đồ
└── README.md
```

> **Nguyên tắc**: Notebook dùng để **khám phá & trình bày**. Logic lặp lại → chuyển vào `src/` dưới dạng hàm Python.

---

*Tài liệu này được tối ưu cho Jupyter Notebook và VS Code Notebook với kernel Python 3.10+.*
