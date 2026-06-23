from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SELECTED_FEATURES_PATH = PROJECT_ROOT / "outputs" / "feature_analysis_focused" / "selected_features_final.csv"
DEFAULT_FINAL_FEATURE_LIST_PATH = (
    PROJECT_ROOT / "report_2026_06_08" / "model_outputs" / "tables" / "phase10_final_feature_list.csv"
)
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "report_2026_06_18" / "outputs" / "selected_features_sample.csv"

LAG_PATTERN = re.compile(r"^(?P<base>.+)_lag_(?P<days>\d+)d$")
ROLLING_PATTERN = re.compile(r"^(?P<base>.+)_rolling_(?P<days>\d+)d_(?P<stat>mean|sum|std|min|max)$")
PCT_CHANGE_PATTERN = re.compile(r"^(?P<base>.+)_pct_change_(?P<days>\d+)d$")
DIFF_PATTERN = re.compile(r"^(?P<base>.+)_diff_(?P<days>\d+)d$")


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return PROJECT_ROOT / candidate


def _read_feature_file(path: Path) -> list[str]:
    df = pd.read_csv(path)
    if "selected_order" in df.columns:
        df = df.sort_values("selected_order")
    if "feature" not in df.columns:
        first_col = df.columns[0]
        values = df[first_col]
    else:
        values = df["feature"]
    return values.dropna().astype(str).tolist()


def load_feature_columns(
    path: str | Path | None = None,
    selected_features_path: str | Path | None = None,
) -> list[str]:
    candidates: list[Path] = []
    if path:
        candidates.append(_resolve_path(path))
    if selected_features_path:
        candidates.append(_resolve_path(selected_features_path))
    candidates.extend([DEFAULT_FINAL_FEATURE_LIST_PATH, DEFAULT_SELECTED_FEATURES_PATH])

    for candidate in candidates:
        if candidate.exists():
            features = _read_feature_file(candidate)
            if features:
                return features

    raise FileNotFoundError("No selected feature file found.")


def _ensure_base_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "Date" not in out.columns:
        if "date" in out.columns:
            out = out.rename(columns={"date": "Date"})
        else:
            raise ValueError("Input data must contain Date or date column.")

    out["Date"] = pd.to_datetime(out["Date"], errors="coerce")
    out = out.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)

    for col in ["Revenue", "COGS", "Gross_Profit", "Gross_Margin", "page_views"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "Gross_Profit" not in out.columns and {"Revenue", "COGS"}.issubset(out.columns):
        out["Gross_Profit"] = out["Revenue"] - out["COGS"]

    if "Gross_Margin" not in out.columns and {"Gross_Profit", "Revenue"}.issubset(out.columns):
        out["Gross_Margin"] = np.where(
            out["Revenue"].abs() > 0,
            out["Gross_Profit"] / out["Revenue"],
            0.0,
        )

    return out


def _calendar_feature(df: pd.DataFrame, feature: str) -> pd.Series | None:
    date_col = df["Date"]
    if feature == "year":
        return date_col.dt.year
    if feature == "quarter":
        return date_col.dt.quarter
    if feature == "month":
        return date_col.dt.month
    if feature == "day_of_month":
        return date_col.dt.day
    if feature == "day_of_week":
        return date_col.dt.dayofweek
    if feature == "is_month_start":
        return date_col.dt.is_month_start.astype(int)
    if feature == "is_month_end":
        return date_col.dt.is_month_end.astype(int)
    if feature == "sin_month":
        return np.sin(2 * np.pi * date_col.dt.month / 12)
    if feature == "cos_month":
        return np.cos(2 * np.pi * date_col.dt.month / 12)
    if feature == "sin_day_of_week":
        return np.sin(2 * np.pi * date_col.dt.dayofweek / 7)
    if feature == "cos_day_of_week":
        return np.cos(2 * np.pi * date_col.dt.dayofweek / 7)
    return None


def _base_series(df: pd.DataFrame, base: str) -> pd.Series:
    if base not in df.columns:
        raise KeyError(base)
    return pd.to_numeric(df[base], errors="coerce")


def _build_one_feature(df: pd.DataFrame, feature: str) -> pd.Series:
    if feature in df.columns:
        return pd.to_numeric(df[feature], errors="coerce")

    calendar = _calendar_feature(df, feature)
    if calendar is not None:
        return pd.Series(calendar, index=df.index)

    lag_match = LAG_PATTERN.match(feature)
    if lag_match:
        base = lag_match.group("base")
        days = int(lag_match.group("days"))
        return _base_series(df, base).shift(days)

    rolling_match = ROLLING_PATTERN.match(feature)
    if rolling_match:
        base = rolling_match.group("base")
        days = int(rolling_match.group("days"))
        stat = rolling_match.group("stat")
        rolling = _base_series(df, base).shift(1).rolling(window=days, min_periods=days)
        return getattr(rolling, stat)()

    pct_match = PCT_CHANGE_PATTERN.match(feature)
    if pct_match:
        base = pct_match.group("base")
        days = int(pct_match.group("days"))
        return _base_series(df, base).pct_change(periods=days).shift(1)

    diff_match = DIFF_PATTERN.match(feature)
    if diff_match:
        base = diff_match.group("base")
        days = int(diff_match.group("days"))
        return _base_series(df, base).diff(periods=days).shift(1)

    raise KeyError(feature)


def recreate_selected_features(
    cleaned_df: pd.DataFrame,
    feature_cols: list[str],
    drop_na: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    base_df = _ensure_base_columns(cleaned_df)
    feature_frame = pd.DataFrame({"Date": base_df["Date"]})

    for target_col in ["Revenue", "COGS"]:
        if target_col in base_df.columns:
            feature_frame[target_col] = base_df[target_col]

    missing_features: list[str] = []
    for feature in feature_cols:
        try:
            feature_frame[feature] = _build_one_feature(base_df, feature)
        except KeyError:
            feature_frame[feature] = 0.0
            missing_features.append(feature)

    feature_frame[feature_cols] = feature_frame[feature_cols].replace([np.inf, -np.inf], np.nan)
    rows_before_drop = len(feature_frame)
    if drop_na:
        feature_frame = feature_frame.dropna(subset=feature_cols)
    feature_frame[feature_cols] = feature_frame[feature_cols].fillna(0.0)
    feature_frame = feature_frame.reset_index(drop=True)

    metadata = {
        "feature_count": len(feature_cols),
        "feature_columns": feature_cols,
        "missing_features_filled": missing_features,
        "rows_before_drop": int(rows_before_drop),
        "rows_after_drop": int(len(feature_frame)),
        "dropped_rows_due_to_lag_window": int(rows_before_drop - len(feature_frame)),
    }
    return feature_frame, metadata


def select_model_features(
    features_df: pd.DataFrame,
    feature_cols: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    output = features_df.copy()
    extra_columns = [col for col in output.columns if col not in {"Date", "Revenue", "COGS", *feature_cols}]
    for feature in feature_cols:
        if feature not in output.columns:
            output[feature] = 0.0
    ordered_cols = [col for col in ["Date", "Revenue", "COGS"] if col in output.columns] + feature_cols
    return output.loc[:, ordered_cols], {
        "feature_count": len(feature_cols),
        "extra_columns_removed": extra_columns,
        "feature_columns": feature_cols,
    }


def build_feature_file(
    input_path: str | Path,
    output_path: str | Path | None = None,
    feature_cols_path: str | Path | None = None,
    selected_features_path: str | Path | None = None,
    drop_na: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    input_file = _resolve_path(input_path)
    cleaned = pd.read_csv(input_file)
    feature_cols = load_feature_columns(feature_cols_path, selected_features_path)
    features, metadata = recreate_selected_features(cleaned, feature_cols, drop_na=drop_na)
    selected, schema = select_model_features(features, feature_cols)
    metadata.update(schema)
    metadata["selected_feature_source"] = str(feature_cols_path or selected_features_path or DEFAULT_FINAL_FEATURE_LIST_PATH)

    if output_path:
        output = _resolve_path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        selected.to_csv(output, index=False)
        output.with_suffix(".summary.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

    return selected, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Recreate the selected feature contract from cleaned data.")
    parser.add_argument("--input", required=True, help="Cleaned CSV input path.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH), help="Selected feature CSV output path.")
    parser.add_argument("--feature-cols", default=None, help="Optional feature_cols_v1.csv path.")
    parser.add_argument("--selected-features", default=None, help="Optional selected_features_final.csv path.")
    parser.add_argument("--keep-na", action="store_true", help="Keep initial rows with lag/rolling NaN values.")
    args = parser.parse_args()

    features, metadata = build_feature_file(
        args.input,
        args.output,
        feature_cols_path=args.feature_cols,
        selected_features_path=args.selected_features,
        drop_na=not args.keep_na,
    )
    print(json.dumps({"rows": len(features), **metadata}, indent=2))


if __name__ == "__main__":
    main()

