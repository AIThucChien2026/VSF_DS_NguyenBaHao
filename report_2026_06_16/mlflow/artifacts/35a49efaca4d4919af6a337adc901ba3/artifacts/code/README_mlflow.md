# MLflow experiment tracking and Model Registry

The script `mlflow_track_and_register.py` reuses the trained artifacts from
`report_14_6_2026`. It does not retrain any model.

## Install

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements-mlflow.txt
```

## Track experiments and register the champion

```powershell
.\venv\Scripts\python.exe scripts\mlflow_track_and_register.py
```

The default local setup uses:

- Backend store: `report_16_6_2026/mlflow/mlflow.db`
- Artifact store: `report_16_6_2026/mlflow/artifacts`
- Experiment: `customer-return-prediction`
- Registered model: `customer-return-champion`
- Alias: `champion`

The registered model applies the validation-locked threshold when `predict()`
is called. Use `predict_proba()` when probabilities are required.

## Open the MLflow UI

```powershell
.\venv\Scripts\mlflow.exe server `
  --backend-store-uri sqlite:///B:/DA_VSF/customer_churn_PL/report_16_6_2026/mlflow/mlflow.db `
  --default-artifact-root file:///B:/DA_VSF/customer_churn_PL/report_16_6_2026/mlflow/artifacts `
  --port 5000
```

Then open `http://127.0.0.1:5000`.

## Remote tracking server

```powershell
.\venv\Scripts\python.exe scripts\mlflow_track_and_register.py `
  --tracking-uri http://mlflow-server:5000 `
  --experiment-name customer-return-production `
  --registered-model-name customer-return-model
```

Use `--skip-registration` when only experiment tracking is needed.
