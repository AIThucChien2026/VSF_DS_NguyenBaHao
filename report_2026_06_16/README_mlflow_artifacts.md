# MLflow / MLruns Artifacts

## Thu muc nay chua gi?

- `mlflow/`
  - Backend SQLite database: `mlflow/mlflow.db`.
  - Artifact store: `mlflow/artifacts`.
  - Nen dung thu muc nay khi mo MLflow UI.

- `mlruns/`
  - File-store style run artifacts tu lan track truoc.
  - Co the doc truc tiep model/artifact, nhung UI hien tai nen tro vao `mlflow/mlflow.db`.

- `code/`
  - Snapshot code de review:
    - `4_Modeling.ipynb`
    - `mlflow_track_and_register.py`
    - `README_mlflow.md`
    - `requirements-mlflow.txt`

## Vi sao truoc do khong thay code trong MLflow?

MLflow khong tu dong log notebook hoac script neu code khong goi `mlflow.log_artifact(...)`
cho cac file do. Lan track truoc chi log model, metrics, params, figures va metadata
CSV/MD. Hien tai da bo sung code snapshot vao artifact path `code` cua champion runs.

## Mo MLflow UI

```powershell
.\venv\Scripts\mlflow.exe server `
  --backend-store-uri sqlite:///B:/DA_VSF/customer_churn_PL/report_16_6_2026/mlflow/mlflow.db `
  --default-artifact-root file:///B:/DA_VSF/customer_churn_PL/report_16_6_2026/mlflow/artifacts `
  --port 5000
```

Sau do mo: `http://127.0.0.1:5000`.

## Ghi chu khi move thu muc

Co the move `mlflow` va `mlruns` vao `report_16_6_2026`, nhung can sua artifact URI
trong SQLite database va metadata. Hien tai URI da duoc sua ve:

- `file:///B:/DA_VSF/customer_churn_PL/report_16_6_2026/mlflow/artifacts`
- `file:///B:/DA_VSF/customer_churn_PL/report_16_6_2026/mlruns/0`
