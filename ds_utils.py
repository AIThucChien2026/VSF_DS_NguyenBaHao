"""
Reusable utilities for Data Science notebooks.

Keep this module generic:
- no dataset-specific column names
- no notebook-specific feature-selection or modeling workflow
- no business rules tied to one project step

Typical notebook usage:

    from pathlib import Path
    import sys

    PROJECT_ROOT = Path.cwd()
    while not (PROJECT_ROOT / "data").exists() and PROJECT_ROOT.parent != PROJECT_ROOT:
        PROJECT_ROOT = PROJECT_ROOT.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    import ds_utils as du
    du.setup_notebook()

    df = du.read_csv(PROJECT_ROOT / "data" / "your_table.csv")
    du.show(du.schema_report(df), title="Schema")
    du.plot_missing_bar(df)

The module intentionally depends only on pandas, numpy, matplotlib and seaborn.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence
import math
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

try:
    from IPython.display import Markdown, display
except Exception:  # pragma: no cover - only used outside notebooks.
    Markdown = None

    def display(obj):
        print(obj.to_string() if hasattr(obj, "to_string") else obj)


MONEY_FORMATTER = FuncFormatter(
    lambda x, _: (
        f"{x / 1e9:.1f}B"
        if abs(x) >= 1e9
        else f"{x / 1e6:.1f}M"
        if abs(x) >= 1e6
        else f"{x / 1e3:.1f}K"
        if abs(x) >= 1e3
        else f"{x:.0f}"
    )
)
PCT_FORMATTER = FuncFormatter(lambda x, _: f"{x:.0%}" if abs(x) <= 1 else f"{x:.1f}%")
COUNT_FORMATTER = FuncFormatter(lambda x, _: f"{x:,.0f}")


def setup_notebook(
    max_columns: int = 80,
    max_rows: int = 120,
    style: str = "whitegrid",
    figsize: tuple[float, float] = (10, 5),
    warn: bool = False,
) -> None:
    """Apply notebook-friendly pandas/matplotlib defaults."""
    pd.set_option("display.max_columns", max_columns)
    pd.set_option("display.max_rows", max_rows)
    pd.set_option("display.width", 160)
    sns.set_theme(style=style)
    plt.rcParams.update(
        {
            "figure.figsize": figsize,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    if not warn:
        warnings.filterwarnings("ignore")


def find_project_root(start: str | Path | None = None, markers: Sequence[str] = ("data", "requirements.txt")) -> Path:
    """Walk upward from start until a directory contains any marker."""
    root = Path(start or Path.cwd()).resolve()
    for candidate in [root, *root.parents]:
        if any((candidate / marker).exists() for marker in markers):
            return candidate
    return root


def show(df, n: int = 20, title: str | None = None, sort_by: str | None = None, ascending: bool = False):
    """Display the first n rows of a dataframe with an optional title."""
    if title:
        print(f"\n{title}")
    if df is None:
        print("No data")
        return None
    if not hasattr(df, "head"):
        display(df)
        return df
    out = df.copy()
    if sort_by and sort_by in out.columns:
        out = out.sort_values(sort_by, ascending=ascending)
    display(out.head(n))
    return out.head(n)


def note(title: str, bullets: Sequence[str]) -> None:
    """Render a short markdown note in notebooks, with text fallback."""
    text = "**" + title + "**\n" + "\n".join(f"- {item}" for item in bullets)
    if Markdown is not None:
        display(Markdown(text))
    else:
        print(text)


def read_csv(path: str | Path, **kwargs) -> pd.DataFrame:
    """Read a CSV with project-friendly defaults and stripped column names."""
    options = {"encoding": "utf-8-sig", "low_memory": False}
    options.update(kwargs)
    df = pd.read_csv(path, **options)
    return clean_column_names(df)


def read_csvs(files: Mapping[str, str | Path], base_dir: str | Path = ".") -> dict[str, pd.DataFrame]:
    """Read many CSV files into a dict keyed by logical table name."""
    base_dir = Path(base_dir)
    tables = {}
    for name, file_name in files.items():
        path = base_dir / file_name
        if path.exists():
            tables[name] = read_csv(path)
    return tables


def clean_column_names(df: pd.DataFrame, lower: bool = False) -> pd.DataFrame:
    """Strip whitespace from column names; optionally lower-case them."""
    out = df.copy()
    cols = [str(c).strip() for c in out.columns]
    if lower:
        cols = [c.lower() for c in cols]
    out.columns = cols
    return out


def convert_columns(
    df: pd.DataFrame,
    date_cols: Sequence[str] = (),
    numeric_cols: Sequence[str] = (),
    normalize_dates: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convert selected columns and return (converted_df, conversion_report)."""
    out = df.copy()
    rows = []
    for col in date_cols:
        if col not in out.columns:
            rows.append([col, "date", "missing_column", np.nan])
            continue
        before_na = out[col].isna().sum()
        parsed = pd.to_datetime(out[col], errors="coerce")
        if normalize_dates:
            parsed = parsed.dt.normalize()
        out[col] = parsed
        rows.append([col, "date", "converted", int(out[col].isna().sum() - before_na)])
    for col in numeric_cols:
        if col not in out.columns:
            rows.append([col, "numeric", "missing_column", np.nan])
            continue
        before_na = out[col].isna().sum()
        out[col] = pd.to_numeric(out[col], errors="coerce")
        rows.append([col, "numeric", "converted", int(out[col].isna().sum() - before_na)])
    report = pd.DataFrame(rows, columns=["column", "target_type", "status", "invalid_after_convert"])
    return out, report


def schema_report(df: pd.DataFrame) -> pd.DataFrame:
    """Column-level schema summary."""
    rows = []
    for col in df.columns:
        s = df[col]
        rows.append(
            {
                "column": col,
                "dtype": str(s.dtype),
                "non_null": int(s.notna().sum()),
                "missing": int(s.isna().sum()),
                "missing_pct": round(s.isna().mean() * 100, 2),
                "nunique": int(s.nunique(dropna=True)),
                "example": next((x for x in s.dropna().head(3).tolist()), np.nan),
            }
        )
    return pd.DataFrame(rows)


def missing_report(df: pd.DataFrame, only_missing: bool = True) -> pd.DataFrame:
    """Missing-value report sorted by missing percentage."""
    out = pd.DataFrame(
        {
            "column": df.columns,
            "missing": df.isna().sum().to_numpy(),
            "missing_pct": (df.isna().mean() * 100).round(2).to_numpy(),
            "dtype": [str(df[c].dtype) for c in df.columns],
        }
    ).sort_values("missing_pct", ascending=False)
    if only_missing:
        out = out.query("missing > 0")
    return out.reset_index(drop=True)


def duplicate_report(df: pd.DataFrame, keys: Sequence[str] | None = None) -> pd.DataFrame:
    """Duplicate summary for full rows and optional key columns."""
    rows = [{"scope": "full_row", "duplicate_rows": int(df.duplicated().sum()), "rows": len(df)}]
    if keys:
        valid_keys = [c for c in keys if c in df.columns]
        if valid_keys:
            rows.append(
                {
                    "scope": ", ".join(valid_keys),
                    "duplicate_rows": int(df.duplicated(subset=valid_keys).sum()),
                    "rows": len(df),
                }
            )
    return pd.DataFrame(rows)


def numeric_summary(df: pd.DataFrame, cols: Sequence[str] | None = None) -> pd.DataFrame:
    """Describe numeric columns with skew and missing percentage."""
    cols = list(cols) if cols else df.select_dtypes(include=np.number).columns.tolist()
    if not cols:
        return pd.DataFrame()
    desc = df[cols].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).T
    desc["missing_pct"] = df[cols].isna().mean().mul(100).round(2)
    desc["skew"] = df[cols].skew(numeric_only=True)
    return desc.reset_index(names="column")


def outlier_iqr_report(df: pd.DataFrame, cols: Sequence[str] | None = None, k: float = 1.5) -> pd.DataFrame:
    """IQR outlier summary for numeric columns."""
    cols = list(cols) if cols else df.select_dtypes(include=np.number).columns.tolist()
    rows = []
    for col in cols:
        s = df[col].dropna()
        if s.empty:
            rows.append({"column": col, "outlier_count": 0, "outlier_pct": 0.0, "lower_bound": np.nan, "upper_bound": np.nan})
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        lower = q1 - k * iqr
        upper = q3 + k * iqr
        mask = df[col].lt(lower) | df[col].gt(upper)
        rows.append(
            {
                "column": col,
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": lower,
                "upper_bound": upper,
                "outlier_count": int(mask.sum()),
                "outlier_pct": round(mask.mean() * 100, 2),
            }
        )
    return pd.DataFrame(rows).sort_values("outlier_pct", ascending=False)


def categorical_summary(df: pd.DataFrame, cols: Sequence[str] | None = None, top_n: int = 5) -> pd.DataFrame:
    """Top values and cardinality for categorical-like columns."""
    if cols is None:
        cols = df.select_dtypes(exclude=np.number).columns.tolist()
    rows = []
    for col in cols:
        if col not in df.columns:
            continue
        vc = df[col].value_counts(dropna=False).head(top_n)
        rows.append(
            {
                "column": col,
                "dtype": str(df[col].dtype),
                "nunique": int(df[col].nunique(dropna=True)),
                "missing_pct": round(df[col].isna().mean() * 100, 2),
                "top_values": "; ".join(f"{idx}: {val}" for idx, val in vc.items()),
            }
        )
    return pd.DataFrame(rows)


def date_range_report(df: pd.DataFrame, date_cols: Sequence[str]) -> pd.DataFrame:
    """Min/max date and missing counts for date columns."""
    rows = []
    for col in date_cols:
        if col not in df.columns:
            rows.append({"column": col, "status": "missing_column"})
            continue
        s = pd.to_datetime(df[col], errors="coerce")
        rows.append(
            {
                "column": col,
                "status": "ok",
                "min_date": s.min(),
                "max_date": s.max(),
                "missing": int(s.isna().sum()),
                "unique_dates": int(s.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)


def infer_feature_type(s: pd.Series, low_cardinality_threshold: int = 12) -> str:
    """Classify a feature for plotting: binary, low_cardinality, continuous, other."""
    nunique = s.nunique(dropna=True)
    if nunique <= 2:
        return "binary"
    if nunique <= low_cardinality_threshold:
        return "low_cardinality"
    if pd.api.types.is_numeric_dtype(s):
        return "continuous"
    return "other"


def relation_label(abs_corr: float | None) -> str:
    """Label absolute correlation strength."""
    if abs_corr is None or pd.isna(abs_corr):
        return "unclear"
    if abs_corr >= 0.60:
        return "strong"
    if abs_corr >= 0.30:
        return "medium"
    if abs_corr >= 0.10:
        return "weak"
    return "unclear"


def safe_div(a, b):
    """Vectorized division that returns NaN when denominator is zero."""
    return np.where(np.asarray(b) != 0, np.asarray(a) / np.asarray(b), np.nan)


def make_lag_roll(
    df: pd.DataFrame,
    date_col: str,
    cols: Sequence[str],
    lags: Sequence[int] = (1, 7, 14, 28),
    windows: Sequence[int] = (7, 28),
    prefix: str | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Create time-series lag and rolling mean features using past values only."""
    out = df.sort_values(date_col).copy()
    made = []
    for col in cols:
        if col not in out.columns:
            continue
        base = prefix + col if prefix else col
        for lag in lags:
            name = f"{base}_lag_{lag}d"
            out[name] = out[col].shift(lag)
            made.append(name)
        past = out[col].shift(1)
        for window in windows:
            name = f"{base}_rolling_{window}d_mean"
            out[name] = past.rolling(window, min_periods=1).mean()
            made.append(name)
    return out, made


def target_relation_report(
    df: pd.DataFrame,
    features: Sequence[str],
    targets: Sequence[str],
    min_pairs: int = 30,
) -> pd.DataFrame:
    """Compute Pearson/Spearman relation between feature columns and targets."""
    rows = []
    for feature in features:
        if feature not in df.columns:
            continue
        row = {
            "feature": feature,
            "view_type": infer_feature_type(df[feature]),
            "missing_pct": round(df[feature].isna().mean() * 100, 2),
            "nunique": int(df[feature].nunique(dropna=True)),
        }
        max_abs = np.nan
        for target in targets:
            pair = df[[feature, target]].dropna()
            ok = len(pair) >= min_pairs and pair[feature].nunique(dropna=True) > 1
            row[f"{target}_pair_count"] = len(pair)
            row[f"{target}_pearson"] = pair[feature].corr(pair[target], method="pearson") if ok else np.nan
            row[f"{target}_spearman"] = pair[feature].corr(pair[target], method="spearman") if ok else np.nan
            row[f"{target}_abs_spearman"] = abs(row[f"{target}_spearman"]) if ok else np.nan
            if ok:
                max_abs = np.nanmax([max_abs, row[f"{target}_abs_spearman"]])
        row["max_abs_spearman"] = max_abs
        row["relation"] = relation_label(max_abs)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("max_abs_spearman", ascending=False)


def high_corr_pairs(df: pd.DataFrame, cols: Sequence[str] | None = None, threshold: float = 0.9, method: str = "spearman") -> pd.DataFrame:
    """Return feature pairs whose absolute correlation is at least threshold."""
    use_cols = list(cols) if cols else df.select_dtypes(include=np.number).columns.tolist()
    corr = df[use_cols].corr(method=method).abs()
    upper = corr.where(np.triu(np.ones(corr.shape), k=1).astype(bool))
    pairs = (
        upper.stack()
        .reset_index()
        .rename(columns={"level_0": "feature_a", "level_1": "feature_b", 0: "abs_corr"})
        .query("abs_corr >= @threshold")
        .sort_values("abs_corr", ascending=False)
        .reset_index(drop=True)
    )
    return pairs


def temporal_relation_report(
    df: pd.DataFrame,
    date_col: str,
    features: Sequence[str],
    target: str,
    period: str = "Y",
    min_pairs: int = 30,
) -> pd.DataFrame:
    """Spearman relation by time period, useful for feature stability checks."""
    tmp = df[[date_col, target] + list(features)].copy()
    tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
    tmp["_period"] = tmp[date_col].dt.to_period(period).astype(str)
    rows = []
    for feature in features:
        for period_value, g in tmp.groupby("_period"):
            pair = g[[feature, target]].dropna()
            corr = np.nan
            if len(pair) >= min_pairs and pair[feature].nunique(dropna=True) > 1:
                corr = pair[feature].corr(pair[target], method="spearman")
            rows.append({"feature": feature, "period": period_value, "spearman": corr, "abs_spearman": abs(corr) if pd.notna(corr) else np.nan})
    return pd.DataFrame(rows)


def wape(y_true, y_pred) -> float:
    """Weighted absolute percentage error."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.abs(y_true).sum()
    return np.nan if denom == 0 else float(np.abs(y_true - y_pred).sum() / denom)


def mae(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.abs(y_true - y_pred).mean())


def rmse(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return float(np.sqrt(((y_true - y_pred) ** 2).mean()))


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    """Common regression metrics for notebooks."""
    return {"mae": mae(y_true, y_pred), "rmse": rmse(y_true, y_pred), "wape": wape(y_true, y_pred)}


def time_split(
    df: pd.DataFrame,
    date_col: str,
    train_end: str | pd.Timestamp,
    valid_end: str | pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame] | tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split a dataframe by date into train/valid or train/valid/test."""
    d = df.copy()
    dates = pd.to_datetime(d[date_col], errors="coerce")
    train_end = pd.Timestamp(train_end)
    if valid_end is None:
        return d.loc[dates <= train_end].copy(), d.loc[dates > train_end].copy()
    valid_end = pd.Timestamp(valid_end)
    train = d.loc[dates <= train_end].copy()
    valid = d.loc[(dates > train_end) & (dates <= valid_end)].copy()
    test = d.loc[dates > valid_end].copy()
    return train, valid, test


def _ax(ax=None, figsize=(10, 5)):
    if ax is not None:
        return ax
    _, ax = plt.subplots(figsize=figsize)
    return ax


def plot_missing_bar(df: pd.DataFrame, top: int = 20, ax=None, title: str = "Top missing columns"):
    report = missing_report(df).head(top).sort_values("missing_pct")
    ax = _ax(ax, figsize=(9, max(4, top * 0.28)))
    if report.empty:
        ax.text(0.5, 0.5, "No missing values", ha="center", va="center")
        ax.set_axis_off()
        return ax
    sns.barplot(data=report, x="missing_pct", y="column", ax=ax, color="#4c78a8")
    ax.set_title(title)
    ax.set_xlabel("Missing (%)")
    ax.set_ylabel("Column")
    return ax


def plot_barh(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    top: int = 20,
    ax=None,
    formatter=None,
    color: str = "#4c78a8",
):
    """Generic horizontal bar chart for ranked dataframe rows."""
    d = df.dropna(subset=[x]).nlargest(top, x).sort_values(x)
    ax = _ax(ax, figsize=(9, max(4, top * 0.28)))
    if d.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        return ax
    sns.barplot(data=d, x=x, y=y, ax=ax, color=color)
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(y)
    if formatter:
        ax.xaxis.set_major_formatter(formatter)
    return ax


def plot_numeric_grid(df: pd.DataFrame, cols: Sequence[str] | None = None, bins: int = 40, max_cols: int = 12, kde: bool = True):
    cols = list(cols) if cols else df.select_dtypes(include=np.number).columns.tolist()
    cols = cols[:max_cols]
    if not cols:
        print("No numeric columns to plot.")
        return None
    n_cols = min(3, len(cols))
    n_rows = math.ceil(len(cols) / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 3.5 * n_rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, col in zip(axes, cols):
        sns.histplot(df[col].dropna(), bins=bins, kde=kde, ax=ax, color="#4c78a8")
        ax.set_title(col)
        ax.set_xlabel(col)
        ax.set_ylabel("Rows")
    for ax in axes[len(cols):]:
        ax.axis("off")
    plt.tight_layout()
    return fig


def plot_boxplot_grid(df: pd.DataFrame, cols: Sequence[str] | None = None, max_cols: int = 12):
    """Boxplots for numeric columns, useful for outlier scanning."""
    cols = list(cols) if cols else df.select_dtypes(include=np.number).columns.tolist()
    cols = cols[:max_cols]
    if not cols:
        print("No numeric columns to plot.")
        return None
    n_cols = min(3, len(cols))
    n_rows = math.ceil(len(cols) / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 3.3 * n_rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, col in zip(axes, cols):
        sns.boxplot(x=df[col], ax=ax, color="#4c78a8")
        ax.set_title(col)
        ax.set_xlabel(col)
    for ax in axes[len(cols):]:
        ax.axis("off")
    plt.tight_layout()
    return fig


def plot_category_counts(df: pd.DataFrame, col: str, top: int = 20, ax=None, title: str | None = None):
    counts = df[col].value_counts(dropna=False).head(top).reset_index()
    counts.columns = [col, "rows"]
    ax = _ax(ax, figsize=(9, max(4, top * 0.28)))
    sns.barplot(data=counts.sort_values("rows"), x="rows", y=col, ax=ax, color="#4c78a8")
    ax.set_title(title or f"Top {top} values of {col}")
    ax.set_xlabel("Rows")
    ax.set_ylabel(col)
    ax.xaxis.set_major_formatter(COUNT_FORMATTER)
    return ax


def plot_group_target(
    df: pd.DataFrame,
    group_col: str,
    target: str,
    agg: str = "mean",
    top: int | None = None,
    ax=None,
    money_axis: bool = False,
):
    """Plot aggregated target by a category or low-cardinality feature."""
    d = df[[group_col, target]].dropna()
    if top:
        keep = d[group_col].value_counts().head(top).index
        d = d[d[group_col].isin(keep)]
    summary = d.groupby(group_col, as_index=False).agg(target_value=(target, agg), rows=(target, "size"))
    summary = summary.sort_values("target_value")
    ax = _ax(ax, figsize=(9, max(4, len(summary) * 0.28)))
    sns.barplot(data=summary, x="target_value", y=group_col, ax=ax, color="#4c78a8")
    ax.set_title(f"{agg.title()} {target} by {group_col}")
    ax.set_xlabel(f"{agg.title()} {target}")
    ax.set_ylabel(group_col)
    if money_axis:
        ax.xaxis.set_major_formatter(MONEY_FORMATTER)
    return ax


def plot_time_series(
    df: pd.DataFrame,
    date_col: str,
    y_cols: Sequence[str],
    rolling: int | None = None,
    ax=None,
    title: str | None = None,
    money_axis: bool = False,
):
    d = df.sort_values(date_col).copy()
    ax = _ax(ax, figsize=(12, 5))
    for col in y_cols:
        if col not in d.columns:
            continue
        values = d[col].rolling(rolling, min_periods=1).mean() if rolling else d[col]
        label = f"{col} {rolling}d avg" if rolling else col
        ax.plot(d[date_col], values, label=label, linewidth=1.8)
    ax.set_title(title or "Time series")
    ax.set_xlabel(date_col)
    ax.set_ylabel("Value")
    if money_axis:
        ax.yaxis.set_major_formatter(MONEY_FORMATTER)
    ax.legend()
    return ax


def plot_temporal_relation(report: pd.DataFrame, top_features: Sequence[str] | None = None, ax=None):
    """Line plot for temporal_relation_report output."""
    d = report.copy()
    if top_features is not None:
        d = d[d["feature"].isin(top_features)]
    ax = _ax(ax, figsize=(12, 6))
    sns.lineplot(data=d, x="period", y="abs_spearman", hue="feature", marker="o", ax=ax)
    ax.set_title("Feature-target relation stability")
    ax.set_xlabel("Period")
    ax.set_ylabel("Absolute Spearman")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left")
    return ax


def plot_corr_heatmap(df: pd.DataFrame, cols: Sequence[str] | None = None, method: str = "spearman", ax=None, title: str | None = None):
    use_cols = list(cols) if cols else df.select_dtypes(include=np.number).columns.tolist()
    corr = df[use_cols].corr(method=method)
    ax = _ax(ax, figsize=(max(8, len(use_cols) * 0.45), max(6, len(use_cols) * 0.35)))
    sns.heatmap(corr, cmap="vlag", center=0, ax=ax)
    ax.set_title(title or f"{method.title()} correlation heatmap")
    return ax


def plot_feature_vs_target(
    df: pd.DataFrame,
    feature: str,
    target: str,
    feature_type: str | None = None,
    bins: int = 10,
    sample_n: int = 3000,
    ax=None,
    money_axis: bool = False,
):
    """Plot a feature against a target using a chart suitable for the feature type."""
    feature_type = feature_type or infer_feature_type(df[feature])
    pair = df[[feature, target]].dropna()
    ax = _ax(ax, figsize=(8, 5))
    if pair.empty:
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.set_axis_off()
        return ax

    if feature_type in {"binary", "low_cardinality", "other"}:
        summary = pair.groupby(feature, dropna=False, as_index=False).agg(
            target_mean=(target, "mean"),
            target_median=(target, "median"),
            rows=(target, "size"),
        )
        sns.barplot(data=summary, x=feature, y="target_mean", ax=ax, color="#4c78a8")
        ax.tick_params(axis="x", rotation=45)
        ax.set_ylabel(f"Mean {target}")
    else:
        sample = pair.sample(min(sample_n, len(pair)), random_state=42) if len(pair) > sample_n else pair
        sns.scatterplot(data=sample, x=feature, y=target, ax=ax, s=16, alpha=0.25, color="#4c78a8", edgecolor=None)
        if pair[feature].nunique(dropna=True) >= 5:
            try:
                binned = pair.assign(_bin=pd.qcut(pair[feature], q=min(bins, pair[feature].nunique()), duplicates="drop"))
                binned = binned.groupby("_bin", observed=False).agg(x=(feature, "median"), y=(target, "mean")).dropna()
                ax.plot(binned["x"], binned["y"], color="#dc2626", linewidth=2, marker="o", markersize=3, label="Binned mean")
                ax.legend()
            except ValueError:
                pass
        ax.set_ylabel(target)

    ax.set_title(f"{feature} vs {target}")
    ax.set_xlabel(feature)
    if money_axis:
        ax.yaxis.set_major_formatter(MONEY_FORMATTER)
    return ax


def plot_feature_grid(
    df: pd.DataFrame,
    features: Sequence[str],
    target: str,
    n_cols: int = 3,
    money_axis: bool = False,
):
    """Small-multiple feature-vs-target plots."""
    features = [f for f in features if f in df.columns]
    if not features:
        print("No valid features to plot.")
        return None
    n_rows = math.ceil(len(features) / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5.5 * n_cols, 4.2 * n_rows))
    axes = np.atleast_1d(axes).ravel()
    for ax, feature in zip(axes, features):
        plot_feature_vs_target(df, feature, target, ax=ax, money_axis=money_axis)
    for ax in axes[len(features):]:
        ax.axis("off")
    plt.tight_layout()
    return fig


def plot_target_relation_bars(report: pd.DataFrame, target: str, top: int = 20, ax=None):
    """Bar chart from target_relation_report output."""
    col = f"{target}_abs_spearman"
    d = report.dropna(subset=[col]).nlargest(top, col).sort_values(col)
    ax = _ax(ax, figsize=(9, max(4, top * 0.28)))
    sns.barplot(data=d, x=col, y="feature", ax=ax, color="#4c78a8")
    ax.set_title(f"Top feature relation with {target}")
    ax.set_xlabel("Absolute Spearman")
    ax.set_ylabel("Feature")
    return ax


def plot_actual_vs_pred(y_true, y_pred, ax=None, title: str = "Actual vs predicted", money_axis: bool = False):
    ax = _ax(ax, figsize=(6, 6))
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    sns.scatterplot(x=y_true, y=y_pred, ax=ax, s=20, alpha=0.45, color="#4c78a8", edgecolor=None)
    lo = np.nanmin([y_true.min(), y_pred.min()])
    hi = np.nanmax([y_true.max(), y_pred.max()])
    ax.plot([lo, hi], [lo, hi], color="#dc2626", linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    if money_axis:
        ax.xaxis.set_major_formatter(MONEY_FORMATTER)
        ax.yaxis.set_major_formatter(MONEY_FORMATTER)
    return ax


def plot_residuals(y_true, y_pred, ax=None, title: str = "Residual distribution"):
    ax = _ax(ax, figsize=(8, 4.5))
    resid = np.asarray(y_true, dtype=float) - np.asarray(y_pred, dtype=float)
    sns.histplot(resid, bins=40, kde=True, ax=ax, color="#4c78a8")
    ax.axvline(0, color="#dc2626", linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Residual")
    ax.set_ylabel("Rows")
    return ax


def save_table(df: pd.DataFrame, path: str | Path, index: bool = False) -> Path:
    """Create parent folder and save a CSV."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index)
    return path


def quick_eda(df: pd.DataFrame, target: str | None = None, top_missing: int = 15) -> dict[str, pd.DataFrame]:
    """Return common EDA tables in one call."""
    reports = {
        "schema": schema_report(df),
        "missing": missing_report(df).head(top_missing),
        "duplicates": duplicate_report(df),
        "numeric": numeric_summary(df),
        "categorical": categorical_summary(df),
    }
    if target and target in df.columns:
        features = [c for c in df.select_dtypes(include=np.number).columns if c != target]
        reports["target_relation"] = target_relation_report(df, features, [target])
    return reports


__all__ = [
    "COUNT_FORMATTER",
    "MONEY_FORMATTER",
    "PCT_FORMATTER",
    "categorical_summary",
    "clean_column_names",
    "convert_columns",
    "date_range_report",
    "duplicate_report",
    "find_project_root",
    "high_corr_pairs",
    "infer_feature_type",
    "mae",
    "make_lag_roll",
    "missing_report",
    "note",
    "numeric_summary",
    "outlier_iqr_report",
    "plot_actual_vs_pred",
    "plot_barh",
    "plot_boxplot_grid",
    "plot_category_counts",
    "plot_corr_heatmap",
    "plot_feature_grid",
    "plot_feature_vs_target",
    "plot_group_target",
    "plot_missing_bar",
    "plot_numeric_grid",
    "plot_residuals",
    "plot_target_relation_bars",
    "plot_temporal_relation",
    "plot_time_series",
    "quick_eda",
    "read_csv",
    "read_csvs",
    "regression_metrics",
    "relation_label",
    "rmse",
    "safe_div",
    "save_table",
    "schema_report",
    "setup_notebook",
    "show",
    "target_relation_report",
    "temporal_relation_report",
    "time_split",
    "wape",
]
