# Customer Return Prediction API

FastAPI inference API for the 2026-06-16 report.

This API does not run EDA, train, tune, split data, draw charts, or log a new MLflow run. It only:

1. Cleans raw inference input.
2. Creates the 28 selected model features.
3. Loads the selected saved model.
4. Returns prediction probability and label.

## Files

- `transform.py`: raw order data -> 28 selected features.
- `predict.py`: saved model -> prediction.
- `app.py`: FastAPI endpoints.
- `sample_request.json`: example input.

## Run

From the project root:

```powershell
.\venv\Scripts\python.exe -m uvicorn report_16_6_2026.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## Endpoints

### GET /health

Checks whether the API can load the model.

### GET /model-info

Returns model source, threshold, feature count, and feature columns.

### POST /transform

Converts raw order data to the exact 28 selected features.

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/transform `
  -ContentType "application/json" `
  -InFile report_16_6_2026\api\sample_request.json
```

### POST /predict

Transforms raw order data and predicts return risk.

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/predict `
  -ContentType "application/json" `
  -InFile report_16_6_2026\api\sample_request.json
```

## Model

Default model path:

```text
report_14_6_2026/modeling_outputs/models/final_model.joblib
```

Default threshold:

```text
0.06335713951173381
```

To use a different MLflow `.pkl` model later, update `MODEL_PATH` in `predict.py`.
