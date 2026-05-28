"""
Mục tiêu:
    Kiểm tra missing values, duplicate và outlier ở mức tổng quan.

Input:
    - Tất cả file CSV trong data/.

Quy trình:
    1. Missing: tính missing_count và missing_pct mọi cột mọi bảng.
    2. Duplicate full rows: tính số dòng trùng hoàn toàn mọi bảng.
    3. Duplicate composite key: kiểm tra PK đơn và khóa ghép từng bảng.
    4. Outlier numeric: IQR method cho các cột số quan trọng + boxplot.
    5. Vẽ bar chart top missing columns.

Output:
    - outputs/tables/04a_missing_summary.csv
    - outputs/tables/04a_duplicate_full_summary.csv
    - outputs/tables/04a_duplicate_key_summary.csv
    - outputs/tables/04a_outlier_numeric_summary.csv
    - outputs/figures/04a_top_missing_columns.png
    - outputs/figures/04a_outlier_boxplots.png
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import FIGURE_DIR, load_tables, plot_bar, save_table

PRIMARY_KEYS = {
    "products":          ["product_id"],
    "customers":         ["customer_id"],
    "geography":         ["zip"],
    "promotions":        ["promo_id"],
    "orders":            ["order_id"],
    "order_items":       ["order_id", "product_id"],
    "payments":          ["order_id"],
    "shipments":         ["order_id"],
    "returns":           ["return_id"],
    "reviews":           ["review_id"],
    "inventory":         ["snapshot_date", "product_id"],
    "sales":             ["Date"],
    "sample_submission": ["Date"],
    "web_traffic":       ["date", "traffic_source"],
}

NUMERIC_OUTLIER_COLS = {
    "products":    ["price", "cogs"],
    "order_items": ["quantity", "unit_price", "discount_amount"],
    "payments":    ["payment_value", "installments"],
    "sales":       ["Revenue","COGS"],
    "returns":    ["refund_amount", "return_quantity"],
    "shipments"  : ["shipping_fee"],
    "inventory" : ["stock_on_hand", "units_received", "units_sold", ],
    "web_traffic" : ["sessions", "unique_visitors", "page_views"]
}

MISSING_RULES = {
    ("order_items", "promo_id"): {
        "missing_type": "business_valid",
        "severity": "LOW",
        "recommended_action": "keep_as_no_promo",
        "note": "Null means the item did not use a first promotion.",
    },
    ("order_items", "promo_id_2"): {
        "missing_type": "business_valid",
        "severity": "LOW",
        "recommended_action": "keep_as_no_second_promo",
        "note": "Null means the item did not use a stacked/second promotion.",
    },
    ("shipments", "delivery_date"): {
        "missing_type": "conditional_valid",
        "severity": "MEDIUM",
        "recommended_action": "check_order_status_before_imputing",
        "note": "May be valid for undelivered orders; invalid for completed deliveries.",
    },
    ("returns", "return_date"): {
        "missing_type": "conditional_valid",
        "severity": "MEDIUM",
        "recommended_action": "check_return_record_before_imputing",
        "note": "Return rows should usually have a return date.",
    },
    ("returns", "return_reason"): {
        "missing_type": "conditional_valid",
        "severity": "MEDIUM",
        "recommended_action": "label_unknown_if_needed",
        "note": "Missing reason limits return analysis but may not block revenue analysis.",
    },
    ("reviews", "review_title"): {
        "missing_type": "business_valid",
        "severity": "LOW",
        "recommended_action": "keep",
        "note": "Review title is optional text and not required for numeric analysis.",
    },
    ("reviews", "rating"): {
        "missing_type": "analysis_blocking",
        "severity": "HIGH",
        "recommended_action": "exclude_from_rating_analysis",
        "note": "Rating is required for satisfaction analysis.",
    },
    ("sample_submission", "Revenue"): {
        "missing_type": "target_placeholder",
        "severity": "LOW",
        "recommended_action": "keep",
        "note": "Missing target values can be expected in submission templates.",
    },
    ("sample_submission", "COGS"): {
        "missing_type": "target_placeholder",
        "severity": "LOW",
        "recommended_action": "keep",
        "note": "Missing target values can be expected in submission templates.",
    },
}

CRITICAL_COLUMNS = {
    "product_id", "customer_id", "order_id", "return_id", "review_id",
    "promo_id", "zip", "Date", "date", "snapshot_date",
}

CRITICAL_METRICS = {
    "quantity", "unit_price", "discount_amount", "payment_value",
    "price", "cogs", "Revenue", "COGS", "sessions", "unique_visitors",
    "page_views", "stock_on_hand", "units_received", "units_sold",
    "return_quantity", "refund_amount", "shipping_fee",
}

DATE_COLUMNS_FOR_ANALYSIS = {
    "signup_date", "order_date", "ship_date", "delivery_date",
    "return_date", "review_date", "start_date", "end_date",
}


def classify_missing(table, column, missing_count, missing_pct):
    if missing_count == 0:
        return {
            "missing_type": "complete",
            "severity": "NONE",
            "recommended_action": "none",
            "note": "No missing values detected.",
        }

    rule = MISSING_RULES.get((table, column))
    if rule is not None:
        return rule

    if column in CRITICAL_COLUMNS:
        return {
            "missing_type": "critical_key",
            "severity": "CRITICAL",
            "recommended_action": "investigate_or_drop_before_join",
            "note": "Missing key/date field can break joins, deduplication, or time analysis.",
        }

    if column in CRITICAL_METRICS:
        return {
            "missing_type": "critical_metric",
            "severity": "CRITICAL",
            "recommended_action": "investigate_before_revenue_or_quality_analysis",
            "note": "Missing metric can bias revenue, profit, traffic, inventory, or operations analysis.",
        }

    if column in DATE_COLUMNS_FOR_ANALYSIS:
        return {
            "missing_type": "analysis_blocking_date",
            "severity": "HIGH",
            "recommended_action": "investigate_or_exclude_from_time_analysis",
            "note": "Missing date limits time-based validation and trend analysis.",
        }

    if missing_pct >= 50:
        severity = "HIGH"
        action = "investigate_business_meaning"
    elif missing_pct >= 10:
        severity = "MEDIUM"
        action = "inspect_before_using_feature"
    else:
        severity = "LOW"
        action = "document_or_impute_if_needed"

    return {
        "missing_type": "needs_review",
        "severity": severity,
        "recommended_action": action,
        "note": "No custom missing rule defined for this field.",
    }


def check_missing(tables):
    rows = []
    for name, df in sorted(tables.items()):
        for col in df.columns:
            m = int(df[col].isna().sum())
            missing_pct = round(m / len(df) * 100, 3) if len(df) else 0
            missing_meta = classify_missing(name, col, m, missing_pct)
            rows.append({
                "table": name,
                "column": col,
                "missing_count": m,
                "missing_pct": missing_pct,
                **missing_meta,
            })
    df_out = pd.DataFrame(rows).sort_values(
        ["missing_pct", "missing_count"], ascending=False
    )
    save_table(df_out, "04a_missing_summary.csv")
    return df_out


def check_duplicate_full(tables):
    rows = []
    for name, df in sorted(tables.items()):
        full_dups = int(df.duplicated().sum())
        rows.append({
            "table": name,
            "rows": len(df),
            "duplicate_full_rows": full_dups,
            "duplicate_full_pct": round(full_dups / len(df) * 100, 3) if len(df) else 0,
        })
    df_out = pd.DataFrame(rows).sort_values("duplicate_full_rows", ascending=False)
    save_table(df_out, "04a_duplicate_full_summary.csv")
    return df_out


def check_duplicate_key(tables):
    rows = []
    for name, df in sorted(tables.items()):
        keys = PRIMARY_KEYS.get(name, [])
        cols = [c for c in keys if c in df.columns]
        if len(cols) != len(keys) or not cols:
            continue
        key_dups = int(df.duplicated(subset=cols).sum())
        rows.append({
            "table": name,
            "keys": ", ".join(cols),
            "total_rows": len(df),
            "key_duplicates": key_dups,
            "key_dup_pct": round(key_dups / len(df) * 100, 3) if len(df) else 0,
        })
    df_out = pd.DataFrame(rows).sort_values("key_duplicates", ascending=False)
    save_table(df_out, "04a_duplicate_key_summary.csv")
    return df_out


def check_outliers(tables):
    rows = []
    series_for_plot = {}

    for tname, cols in NUMERIC_OUTLIER_COLS.items():
        if tname not in tables:
            continue
        df = tables[tname]
        for col in cols:
            if col not in df.columns:
                continue
            s = df[col].dropna()
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lo = q1 - 1.5 * iqr
            hi = q3 + 1.5 * iqr
            n_out = int(((s < lo) | (s > hi)).sum())
            rows.append({
                "table": tname,
                "column": col,
                "count": len(s),
                "mean": round(s.mean(), 2),
                "median": round(s.median(), 2),
                "q1": round(q1, 2),
                "q3": round(q3, 2),
                "iqr": round(iqr, 2),
                "lower_fence": round(lo, 2),
                "upper_fence": round(hi, 2),
                "outlier_count": n_out,
                "outlier_pct": round(n_out / len(s) * 100, 3) if len(s) else 0,
            })
            series_for_plot[f"{tname}.{col}"] = s.values

    save_table(pd.DataFrame(rows), "04a_outlier_numeric_summary.csv")

    if series_for_plot:
        n = len(series_for_plot)
        fig, axes = plt.subplots(1, n, figsize=(3.5 * n, 4))
        if n == 1:
            axes = [axes]
        for ax, (label, vals) in zip(axes, series_for_plot.items()):
            ax.boxplot(
                vals,
                patch_artist=True,
                boxprops=dict(facecolor="#dbeafe", color="#334155"),
                medianprops=dict(color="#1d4ed8", linewidth=2),
                whiskerprops=dict(color="#64748b"),
                capprops=dict(color="#64748b"),
                flierprops=dict(marker=".", color="#ef4444", alpha=0.4, markersize=4),
            )
            ax.set_title(label, fontsize=8, pad=6)
            ax.set_xticks([])
            ax.tick_params(axis="y", labelsize=7)
        fig.suptitle("Outlier boxplots — IQR method", fontsize=11, weight="bold")
        fig.tight_layout()
        fig.savefig(FIGURE_DIR / "04a_outlier_boxplots.png", dpi=150, bbox_inches="tight")
        plt.close(fig)


def plot_missing(df_missing):
    plot_df = df_missing[df_missing["missing_count"] > 0].copy()
    if plot_df.empty:
        print("No missing values found — skipping chart.")
        return
    plot_df["field"] = plot_df["table"] + "." + plot_df["column"]
    plot_bar(
        plot_df.sort_values("missing_pct", ascending=False),
        x="missing_pct",
        y="field",
        title="Top missing columns",
        xlabel="Missing (%)",
        ylabel="Column",
        filename="04a_top_missing_columns.png",
        horizontal=True,
        max_items=30,
    )


def main():
    print("Loading tables...")
    tables = load_tables(parse_dates=False)
    print(f"Loaded {len(tables)} tables.")

    print("Checking missing values...")
    df_missing = check_missing(tables)

    print("Checking full-row duplicates...")
    check_duplicate_full(tables)

    print("Checking composite key duplicates...")
    check_duplicate_key(tables)

    print("Checking numeric outliers...")
    check_outliers(tables)

    print("Plotting missing columns chart...")
    plot_missing(df_missing)

    print("04a missing duplicates done!")


if __name__ == "__main__":
    main()
