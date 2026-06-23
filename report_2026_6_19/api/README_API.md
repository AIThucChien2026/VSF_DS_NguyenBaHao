# API README

FastAPI entrypoint:

```bash
uvicorn api.app:app --reload --port 8000
```

Endpoints:

- `GET /health`
- `GET /model-info`
- `POST /clean`
- `POST /features`
- `POST /predict`

Sample request:

```json
{
  "data_dir": "data/"
}
```

Notes:

- The API expects the five input CSV files in `report_2026_6_19/data/`.
- `returns.csv` is intentionally excluded from inference.
- The preprocessor artifact should be available in `report_2026_6_19/artifacts/`.
