from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "report_2026_06_18" / "outputs" / "cleaned_sample.csv"

REQUIRED_TABLES = ["sales.csv"]
OPTIONAL_TABLES = ["web_traffic.csv"]


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _clean_column_name(value: str) -> str:
    return value.strip()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input table: {path}")
    df = pd.read_csv(path)
    df.columns = [_clean_column_name(str(col)) for col in df.columns]
    return df


def load_required_tables(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    required_tables: list[str] | None = None,
    optional_tables: list[str] | None = None,
) -> dict[str, pd.DataFrame]:
    data_path = _resolve_path(data_dir)
    if not data_path.exists():
        raise FileNotFoundError(f"data_dir does not exist: {data_path}")

    required = required_tables or REQUIRED_TABLES
    optional = optional_tables or OPTIONAL_TABLES
    tables: dict[str, pd.DataFrame] = {}

    for table_name in required:
        tables[table_name] = _read_csv(data_path / table_name)

    for table_name in optional:
        table_path = data_path / table_name
        if table_path.exists():
            tables[table_name] = _read_csv(table_path)

    return tables


def _clean_sales(sales: pd.DataFrame) -> pd.DataFrame:
    required_cols = {"Date", "Revenue", "COGS"}
    missing = sorted(required_cols - set(sales.columns))
    if missing:
        raise ValueError(f"sales.csv is missing required columns: {missing}")

    cleaned = sales.loc[:, ["Date", "Revenue", "COGS"]].copy()
    cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")
    cleaned["Revenue"] = pd.to_numeric(cleaned["Revenue"], errors="coerce")
    cleaned["COGS"] = pd.to_numeric(cleaned["COGS"], errors="coerce")
    cleaned = cleaned.dropna(subset=["Date"])
    cleaned = cleaned.sort_values("Date")
    cleaned = cleaned.drop_duplicates(subset=["Date"], keep="last")
    cleaned["Revenue"] = cleaned["Revenue"].fillna(0.0).clip(lower=0.0)
    cleaned["COGS"] = cleaned["COGS"].fillna(0.0).clip(lower=0.0)
    cleaned["Gross_Profit"] = cleaned["Revenue"] - cleaned["COGS"]
    cleaned["Gross_Margin"] = np.where(
        cleaned["Revenue"].abs() > 0,
        cleaned["Gross_Profit"] / cleaned["Revenue"],
        0.0,
    )
    return cleaned


def _clean_web_traffic(web_traffic: pd.DataFrame) -> pd.DataFrame:
    if "date" not in web_traffic.columns:
        raise ValueError("web_traffic.csv is missing required column: date")

    cleaned = web_traffic.copy()
    cleaned["Date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["Date"])

    numeric_cols = [
        "sessions",
        "unique_visitors",
        "page_views",
        "bounce_rate",
        "avg_session_duration_sec",
    ]
    for col in numeric_cols:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    agg_map: dict[str, str] = {}
    for col in ["sessions", "unique_visitors", "page_views"]:
        if col in cleaned.columns:
            agg_map[col] = "sum"
    for col in ["bounce_rate", "avg_session_duration_sec"]:
        if col in cleaned.columns:
            agg_map[col] = "mean"

    if not agg_map:
        return cleaned[["Date"]].drop_duplicates()

    return cleaned.groupby("Date", as_index=False).agg(agg_map)


def clean_tables(tables: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, Any]]:
    if "sales.csv" not in tables:
        raise ValueError("sales.csv is required to build the selected daily features.")

    sales_raw = tables["sales.csv"]
    cleaned = _clean_sales(sales_raw)
    source_tables = ["sales.csv"]

    if "web_traffic.csv" in tables:
        web = _clean_web_traffic(tables["web_traffic.csv"])
        cleaned = cleaned.merge(web, on="Date", how="left")
        source_tables.append("web_traffic.csv")

    numeric_cols = cleaned.select_dtypes(include=["number"]).columns
    cleaned[numeric_cols] = cleaned[numeric_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    cleaned = cleaned.sort_values("Date").reset_index(drop=True)

    summary = {
        "source_tables": source_tables,
        "input_rows": {name: int(len(df)) for name, df in tables.items()},
        "cleaned_rows": int(len(cleaned)),
        "date_min": cleaned["Date"].min().date().isoformat() if not cleaned.empty else None,
        "date_max": cleaned["Date"].max().date().isoformat() if not cleaned.empty else None,
        "columns": cleaned.columns.tolist(),
        "dropped_duplicate_dates": int(len(sales_raw) - sales_raw["Date"].nunique()),
    }
    return cleaned, summary


def clean_data_dir(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    tables = load_required_tables(data_dir)
    cleaned, summary = clean_tables(tables)

    if output_path:
        output = _resolve_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(output, index=False)
        summary_path = output.with_suffix(".summary.json")
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return cleaned


def clean_data_dir_with_summary(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    output_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    tables = load_required_tables(data_dir)
    cleaned, summary = clean_tables(tables)

    if output_path:
        output = _resolve_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(output, index=False)
        output.with_suffix(".summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

    return cleaned, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean source tables from data/ for inference.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing source CSV tables.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Output CSV path for cleaned data.")
    args = parser.parse_args()

    cleaned, summary = clean_data_dir_with_summary(args.data_dir, args.output)
    print(json.dumps({"rows": len(cleaned), **summary}, indent=2))


if __name__ == "__main__":
    main()

