# Ke Hoach Report 18/6/2026 - Data Cleaning, Feature Selection, Model Prediction va FastAPI

Tai lieu nay lap ke hoach trien khai bo script phuc vu inference cho du an du doan tra hang. Muc tieu cua ngay 18/6 la bien cac buoc dang nam rai rac trong notebook/script thanh pipeline co the goi lai duoc: chon cac bang can thiet tu thu muc `data/`, clean data theo luong da co, tao lai dung cac feature da duoc chon truoc do, du doan bang model champion, va mot file FastAPI de goi cac buoc nay qua API.

---

## 1. Muc tieu

1. Viet script clean data de chon cac bang can dung trong `data/` va xu ly thanh bang du lieu sach, co schema on dinh.
2. Viet script tao lai/chon dung cac feature da duoc chot truoc do, khong lam EDA va khong tao FE moi ngoai contract.
3. Viet script predict model de load model champion, can chinh cot feature, tinh probability va label.
4. Viet mot file FastAPI de cung cap endpoint cho clean, feature selection va predict.
5. Tao sample request va README ngan de team co the chay thu bang `uvicorn`.

---

## 2. Cau truc thu muc de xuat

```text
report_2026_06_18/
  plan.md
  scripts/
    __init__.py
    clean_data.py
    select_features.py
    predict_model.py
  api/
    __init__.py
    app.py
    sample_request.json
    README_API.md
  outputs/
    cleaned_sample.csv
    selected_features_sample.csv
    prediction_sample.csv
```

Trong do:

- `scripts/clean_data.py`: chon bang nguon trong `data/`, lam sach va chuan hoa du lieu theo luong da co.
- `scripts/select_features.py`: tao lai dung cac feature da duoc chon truoc do va can chinh theo schema model.
- `scripts/predict_model.py`: load model va sinh du doan.
- `api/app.py`: FastAPI app goi lai cac ham trong 3 script tren.

---

## 3. Dau vao va dau ra chuan

### Dau vao

- Du lieu nguon nam trong thu muc `data/`, gom nhieu bang CSV nhu `orders.csv`, `order_items.csv`, `returns.csv`, `shipments.csv`, `payments.csv`, `customers.csv`, `products.csv` va cac bang lien quan neu feature contract can.
- Script clean se chon dung cac bang can dung theo luong pipeline; khong can doc tat ca bang neu bang do khong phuc vu feature da chot.
- Cac cot co the sai kieu du lieu, thieu gia tri, hoac co cot thua.
- Model champion da duoc luu tu phase modeling/MLflow.
- File danh sach feature da chot, vi du `outputs/feature_analysis_focused/selected_features_final.csv`, `feature_cols_v1.csv` hoac artifact tu MLflow.

### Dau ra trung gian

- `cleaned_sample.csv`: du lieu sau khi chon bang nguon, merge theo khoa can thiet, xu ly missing values, kieu du lieu, duplicate, ngay thang, cot tien/so luong.
- `selected_features_sample.csv`: bang feature duoc tao lai dung cong thuc/ten cot da chot truoc do va can chinh dung thu tu cot model.

### Dau ra cuoi

- `prediction_sample.csv`: moi dong co `return_probability`, `prediction`, `threshold`, va thong tin dinh danh neu co.
- API response dang JSON cho endpoint `/predict`.

---

## 4. Script 1 - `clean_data.py`

### Nhiem vu

Script nay nhan `data_dir`, chon cac bang CSV can dung trong thu muc `data/`, merge theo luong pipeline da co va tra ve DataFrame sach. Khong duoc dua logic model prediction, EDA hay feature engineering moi vao day. Script nay cung khong can lam mot phase check quality rieng; chi ghi metadata clean toi thieu de truy vet loi neu co.

### Xu ly chinh

1. Xac dinh cac bang nguon can doc:
   - bang bat buoc theo feature da chot: `orders.csv`, `order_items.csv`, `returns.csv`, `shipments.csv`, `payments.csv`;
   - bang bo sung neu feature contract can: `customers.csv`, `products.csv`, `geography.csv`, `reviews.csv`, `web_traffic.csv`, `promotions.csv`, `inventory.csv`, `sales.csv`;
   - khong doc cac bang khong lien quan den selected features.
2. Doc cac bang tu `data_dir` va giu lai cac cot can dung.
3. Merge cac bang theo khoa da xac dinh trong pipeline cu:
   - `order_id` cho order-level;
   - `customer_id`, `product_id`, `geo_id` hoac cac khoa tuong ung neu can enrich;
   - aggregate truoc khi merge neu bang co nhieu dong tren mot order.
4. Chuan hoa ten cot:
   - strip khoang trang;
   - dua ve snake_case neu can;
   - map alias ve ten cot chuan.
5. Chuan hoa kieu du lieu:
   - cot ngay thang -> `datetime`;
   - cot so tien/so luong -> numeric;
   - cot category -> string/category;
   - cot boolean -> 0/1 neu model can.
6. Xu ly missing values:
   - cot numeric: dien median/0 theo contract da chot;
   - cot category: dien `"unknown"`;
   - cot ngay thang quan trong: bao loi neu khong the suy luan.
7. Xu ly duplicate va ban ghi loi:
   - drop duplicate theo `order_id` neu co;
   - khong tao phase check quality rieng, chi luu `clean_summary` ngan gon.
8. Tra ve:
   - `cleaned_df`;
   - metadata: bang da dung, row count, dropped duplicate count, cac cot thieu bat buoc neu co.

### Ham can co

```python
def load_required_tables(data_dir: str, required_tables: list[str]) -> dict[str, pd.DataFrame]:
    ...

def clean_tables(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict]:
    ...

def clean_data_dir(data_dir: str, output_path: str | None = None) -> pd.DataFrame:
    ...
```

### CLI du kien

```powershell
.\venv\Scripts\python.exe report_2026_06_18\scripts\clean_data.py `
  --data-dir data `
  --output report_2026_06_18\outputs\cleaned_sample.csv
```

---

## 5. Script 2 - `select_features.py`

### Nhiem vu

Script nay nhan du lieu da clean va tao lai y nguyen cac feature da duoc chon truoc do. Khong lam EDA, khong tim feature moi, khong chay feature selection moi, khong train model va khong thay doi danh sach feature tuy tien.

### Xu ly chinh

1. Load danh sach feature da chot:
   - uu tien `outputs/feature_analysis_focused/selected_features_final.csv` neu can lay ten feature va ly do giu;
   - uu tien artifact `feature_cols_v1.csv` neu can dung dung thu tu cot model;
   - neu model bundle co `feature_cols` thi dung truc tiep tu bundle;
   - neu thieu thi dung constant `FEATURE_COLS`.
2. Tao lai cac feature dung cong thuc da co trong pipeline cu:
   - chi tao feature nam trong selected feature list;
   - neu feature la lag/rolling thi tinh dung theo time-safe logic da chot;
   - neu feature la calendar thi tao tu ngay don hang theo cong thuc cu;
   - neu feature la aggregate theo order/customer/product/shipment/return/review thi aggregate dung muc hat da chot.
3. Khong lam feature engineering moi:
   - khong sinh them cot ngoai selected feature list;
   - khong thu nghiem encoding moi;
   - khong tinh feature moi chi vi du lieu co san.
4. Loai bo cot leakage:
   - cot label/target;
   - cot biet sau thoi diem du doan;
   - cot ID khong dung cho model, tru khi da duoc encode co chu dich.
5. Can chinh schema:
   - them cot thieu voi gia tri mac dinh;
   - bo cot thua;
   - sap xep cot dung thu tu model;
   - dam bao toan bo feature numeric neu model yeu cau.
6. Tra ve:
   - `features_df`;
   - metadata: feature count, missing feature list, extra column list, selected feature source.

### Ham can co

```python
def load_feature_columns(path: str | None = None) -> list[str]:
    ...

def recreate_selected_features(cleaned_df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    ...

def select_model_features(features_df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, dict]:
    ...
```

### CLI du kien

```powershell
.\venv\Scripts\python.exe report_2026_06_18\scripts\select_features.py `
  --input report_2026_06_18\outputs\cleaned_sample.csv `
  --selected-features outputs\feature_analysis_focused\selected_features_final.csv `
  --feature-cols report_2026_06_16\mlruns\0\...\artifacts\project_metadata\feature_cols_v1.csv `
  --output report_2026_06_18\outputs\selected_features_sample.csv
```

---

## 6. Script 3 - `predict_model.py`

### Nhiem vu

Script nay load model champion va du doan tren bang feature da duoc can chinh. Day la noi duy nhat quan ly model path, threshold va output prediction.

### Xu ly chinh

1. Load model:
   - uu tien model local da dong goi bang `joblib`;
   - neu dung MLflow thi load tu `models:/customer-return-champion@champion`;
   - cache model de API khong load lai moi request.
2. Kiem tra schema:
   - so cot feature dung voi model;
   - thu tu cot dung;
   - khong con missing/NaN bat thuong.
3. Du doan:
   - neu model co `predict_proba`, lay xac suat lop tra hang;
   - ap dung threshold da chot;
   - neu model chi co `predict`, tra label va ghi ro probability khong kha dung.
4. Tra ve:
   - probability;
   - prediction label;
   - threshold;
   - model source/version;
   - row id/order id neu co.

### Ham can co

```python
def load_model_bundle(model_path: str | None = None) -> dict:
    ...

def predict_features(features_df: pd.DataFrame) -> list[dict]:
    ...

def predict_file(input_path: str, output_path: str) -> pd.DataFrame:
    ...
```

### CLI du kien

```powershell
.\venv\Scripts\python.exe report_2026_06_18\scripts\predict_model.py `
  --input report_2026_06_18\outputs\selected_features_sample.csv `
  --model-path report_2026_06_16\modeling_outputs\models\final_model.joblib `
  --output report_2026_06_18\outputs\prediction_sample.csv
```

---

## 7. FastAPI - `api/app.py`

### Muc tieu

File `app.py` chi dong vai tro API orchestration: nhan `data_dir` hoac dung mac dinh `data/`, goi `clean_data.py`, goi `select_features.py`, goi `predict_model.py`, va tra response. Khong viet lai logic clean/feature/predict trong API.

### Endpoint can co

#### `GET /health`

Kiem tra API song va model co load duoc hay khong.

Response:

```json
{
  "status": "ok",
  "model_loaded": true,
  "feature_count": 28,
  "threshold": 0.063357
}
```

#### `GET /model-info`

Tra thong tin model source, threshold, danh sach feature va version neu co.

#### `POST /clean`

Nhan `data_dir` va danh sach bang tuy chon, tra du lieu da clean va `clean_summary`.

#### `POST /features`

Nhan `data_dir` hoac cleaned records, tra selected feature records va schema report.

#### `POST /predict`

Chay full pipeline:

1. chon bang trong `data_dir` va clean;
2. tao lai selected features da chot;
3. predict model;
4. tra ket qua.

Response du kien:

```json
{
  "count": 1,
  "model_source": "models:/customer-return-champion@champion",
  "results": [
    {
      "order_id": "ORD001",
      "return_probability": 0.0812,
      "prediction": 1,
      "threshold": 0.063357
    }
  ],
  "clean_summary": {
    "input_rows": 1,
    "cleaned_rows": 1,
    "dropped_duplicates": 0
  },
  "feature_schema": {
    "feature_count": 28,
    "missing_features_filled": [],
    "extra_columns_removed": []
  }
}
```

### Chay API

```powershell
.\venv\Scripts\python.exe -m uvicorn report_2026_06_18.api.app:app `
  --host 127.0.0.1 `
  --port 8000 `
  --reload
```

Mo Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

## 8. Kiem thu toi thieu

1. Test `clean_data.py` voi `--data-dir data` va xac nhan script chi doc cac bang can dung.
2. Test `select_features.py` de dam bao output dung danh sach feature da chot, dung so cot va thu tu feature.
3. Test `predict_model.py` voi selected features sample va xac nhan output co probability/label.
4. Test API:
   - `GET /health`;
   - `POST /clean`;
   - `POST /features`;
   - `POST /predict`.
5. Kiem tra loi dau vao:
   - `data_dir` khong ton tai;
   - bang bat buoc khong ton tai;
   - thieu cot bat buoc;
   - ngay thang sai format;
   - model path khong ton tai.

---

## 9. Checklist thuc hien

- [ ] Tao thu muc `report_2026_06_18/scripts`.
- [ ] Tao thu muc `report_2026_06_18/api`.
- [ ] Viet `clean_data.py`.
- [ ] Viet `select_features.py`.
- [ ] Viet `predict_model.py`.
- [ ] Viet `api/app.py`.
- [ ] Tao `sample_request.json` voi `data_dir` mac dinh la `data`.
- [ ] Tao `README_API.md` kem lenh chay va vi du request.
- [ ] Chay thu tung script bang CLI.
- [ ] Chay FastAPI va test tren Swagger UI.
- [ ] Luu sample output vao `report_2026_06_18/outputs`.

---

## 10. Nguyen tac trien khai

1. Tach ro logic business/pipeline khoi FastAPI.
2. Moi script phai import duoc nhu module va cung co CLI de debug doc lap.
3. Khong train lai model trong API.
4. Khong lam EDA, khong lam check quality rieng, khong tim feature moi trong ngay 18/6.
5. Khong thay doi feature schema khi inference neu chua co ly do va ghi chu ro.
6. Neu co loi dau vao, API tra loi ro bang/cot nao loi thay vi crash im lang.
7. Moi output can co metadata de truy vet: source tables, input rows, cleaned rows, feature count, model source, threshold.
