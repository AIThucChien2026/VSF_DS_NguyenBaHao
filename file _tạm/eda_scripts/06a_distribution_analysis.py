"""
Goal:
    Explore data distributions for the main numeric and categorical fields.

Input:
    - Selected CSV files from data/.

Process:
    - Build descriptive statistics for important numeric columns.
    - Add derived sales metrics: Gross Profit and Margin.
    - Summarize zero values, skewness, and mean-vs-median gap.
    - Summarize top categories with counts and percentages.
    - Summarize revenue contribution by order/customer and product groups.
    - Save compact charts for quick review.

Output:
    - outputs/tables/06a_numeric_describe.csv
    - outputs/tables/06a_categorical_top_values.csv
    - outputs/tables/06a_revenue_by_order_group.csv
    - outputs/tables/06a_revenue_by_product_group.csv
    - outputs/reports/06a_distribution_summary.md
    - outputs/figures/06a_numeric_distribution_grid.png
    - outputs/figures/06a_categorical_top_values.png
    - outputs/figures/06a_sales_revenue_distribution_detail.png
    - outputs/figures/06a_revenue_by_order_groups.png
    - outputs/figures/06a_revenue_by_product_groups.png
"""

import math

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from config import load_tables, save_figure, save_report, save_table


NUMERIC_COLUMNS = {
    "sales": ["Revenue", "COGS", "Gross Profit", "Margin"],
    "payments": ["payment_value", "installments"],
    "order_items": ["quantity", "unit_price", "discount_amount"],
    "products": ["price", "cogs"],
    "returns": ["refund_amount", "return_quantity"],
    "reviews": ["rating"],
    "web_traffic": [
        "sessions",
        "unique_visitors",
        "page_views",
        "bounce_rate",
        "avg_session_duration_sec",
    ],
    "inventory": [
        "stock_on_hand",
        "units_sold",
        "stockout_days",
        "fill_rate",
        "sell_through_rate",
    ],
}

CATEGORICAL_COLUMNS = {
    "orders": ["order_status", "payment_method", "device_type", "order_source"],
    "customers": ["gender", "age_group", "acquisition_channel", "city"],
    "products": ["category", "segment", "size", "color"],
    "returns": ["return_reason"],
    "web_traffic": ["traffic_source"],
}

PERCENTILES = [0.25, 0.75, 0.95, 0.99]
TOP_N = 10

ORDER_REVENUE_GROUPS = ["order_status", "payment_method", "device_type", "order_source"]
CUSTOMER_REVENUE_GROUPS = ["gender", "age_group", "acquisition_channel", "city"]
PRODUCT_REVENUE_GROUPS = ["category", "segment", "size", "color", "product_name"]


def add_derived_metrics(tables):
    if "sales" not in tables:
        return

    sales = tables["sales"].copy()
    if {"Revenue", "COGS"}.issubset(sales.columns):
        sales["Gross Profit"] = sales["Revenue"] - sales["COGS"]
        sales["Margin"] = sales["Gross Profit"] / sales["Revenue"].replace(0, pd.NA)
    tables["sales"] = sales


def classify_skew(skew_value):
    if pd.isna(skew_value):
        return "unknown"
    if skew_value >= 1:
        return "right_skewed_strong"
    if skew_value >= 0.5:
        return "right_skewed_moderate"
    if skew_value <= -1:
        return "left_skewed_strong"
    if skew_value <= -0.5:
        return "left_skewed_moderate"
    return "roughly_symmetric"


def summarize_numeric(tables):
    rows = []

    for table, columns in NUMERIC_COLUMNS.items():
        if table not in tables:
            continue

        df = tables[table]
        for column in columns:
            if column not in df.columns:
                continue

            s = pd.to_numeric(df[column], errors="coerce")
            non_null = s.dropna()
            count = int(non_null.count())
            zero_count = int((non_null == 0).sum())
            mean = non_null.mean() if count else pd.NA
            median = non_null.median() if count else pd.NA
            mean_median_gap_pct = (
                abs(mean - median) / abs(median) * 100
                if count and not pd.isna(median) and median != 0
                else pd.NA
            )

            quantiles = non_null.quantile(PERCENTILES) if count else pd.Series(dtype=float)

            rows.append(
                {
                    "table": table,
                    "column": column,
                    "rows": len(df),
                    "count": count,
                    "missing": int(s.isna().sum()),
                    "missing_pct": round(s.isna().mean() * 100, 3) if len(s) else 0,
                    "mean": round(mean, 4) if count else pd.NA,
                    "median": round(median, 4) if count else pd.NA,
                    "std": round(non_null.std(), 4) if count else pd.NA,
                    "min": round(non_null.min(), 4) if count else pd.NA,
                    "p25": round(quantiles.get(0.25, pd.NA), 4) if count else pd.NA,
                    "p75": round(quantiles.get(0.75, pd.NA), 4) if count else pd.NA,
                    "p95": round(quantiles.get(0.95, pd.NA), 4) if count else pd.NA,
                    "p99": round(quantiles.get(0.99, pd.NA), 4) if count else pd.NA,
                    "max": round(non_null.max(), 4) if count else pd.NA,
                    "zero_count": zero_count,
                    "zero_pct": round(zero_count / count * 100, 3) if count else 0,
                    "skew": round(non_null.skew(), 4) if count > 2 else pd.NA,
                    "skew_flag": classify_skew(non_null.skew() if count > 2 else pd.NA),
                    "mean_median_gap_pct": (
                        round(mean_median_gap_pct, 3)
                        if not pd.isna(mean_median_gap_pct)
                        else pd.NA
                    ),
                }
            )

    out = pd.DataFrame(rows)
    save_table(out, "06a_numeric_describe.csv")
    return out


def summarize_categorical(tables):
    rows = []

    for table, columns in CATEGORICAL_COLUMNS.items():
        if table not in tables:
            continue

        df = tables[table]
        for column in columns:
            if column not in df.columns:
                continue

            counts = df[column].value_counts(dropna=False).head(TOP_N)
            for rank, (value, count) in enumerate(counts.items(), start=1):
                rows.append(
                    {
                        "table": table,
                        "column": column,
                        "rank": rank,
                        "value": value,
                        "count": int(count),
                        "pct": round(count / len(df) * 100, 3) if len(df) else 0,
                        "unique_values": int(df[column].nunique(dropna=False)),
                        "rows": len(df),
                    }
                )

    out = pd.DataFrame(rows)
    save_table(out, "06a_categorical_top_values.csv")
    return out


def summarize_revenue_by_order_groups(tables):
    required = {"orders", "payments"}
    if not required.issubset(tables):
        out = pd.DataFrame()
        save_table(out, "06a_revenue_by_order_group.csv")
        return out

    orders = tables["orders"].copy()
    payments = tables["payments"].copy()
    if "order_id" not in orders.columns or not {"order_id", "payment_value"}.issubset(payments.columns):
        out = pd.DataFrame()
        save_table(out, "06a_revenue_by_order_group.csv")
        return out

    order_revenue = payments.groupby("order_id", as_index=False).agg(
        revenue=("payment_value", "sum")
    )
    order_base_cols = ["order_id", "customer_id"] + [
        col for col in ORDER_REVENUE_GROUPS if col in orders.columns
    ]
    order_base = orders[order_base_cols].merge(order_revenue, on="order_id", how="left")
    order_base["revenue"] = order_base["revenue"].fillna(0)

    rows = []
    rows.extend(build_group_revenue_rows(order_base, ORDER_REVENUE_GROUPS, "order_level"))

    if "customers" in tables and "customer_id" in order_base.columns:
        customer_cols = ["customer_id"] + [
            col for col in CUSTOMER_REVENUE_GROUPS if col in tables["customers"].columns
        ]
        customer_base = order_base[["order_id", "customer_id", "revenue"]].merge(
            tables["customers"][customer_cols],
            on="customer_id",
            how="left",
        )
        rows.extend(build_group_revenue_rows(customer_base, CUSTOMER_REVENUE_GROUPS, "customer_level"))

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    save_table(out, "06a_revenue_by_order_group.csv")
    return out


def summarize_revenue_by_product_groups(tables):
    if "order_items" not in tables or "products" not in tables:
        out = pd.DataFrame()
        save_table(out, "06a_revenue_by_product_group.csv")
        return out

    items = tables["order_items"].copy()
    products = tables["products"].copy()
    required_item_cols = {"product_id", "quantity", "unit_price", "discount_amount"}
    if not required_item_cols.issubset(items.columns) or "product_id" not in products.columns:
        out = pd.DataFrame()
        save_table(out, "06a_revenue_by_product_group.csv")
        return out

    items["net_item_revenue"] = items["quantity"] * items["unit_price"] - items["discount_amount"]
    product_cols = ["product_id"] + [col for col in PRODUCT_REVENUE_GROUPS if col in products.columns]
    item_base = items[["product_id", "quantity", "net_item_revenue"]].merge(
        products[product_cols],
        on="product_id",
        how="left",
    )

    total_revenue = item_base["net_item_revenue"].sum()
    rows = []
    for group_col in PRODUCT_REVENUE_GROUPS:
        if group_col not in item_base.columns:
            continue
        grouped = (
            item_base.groupby(group_col, dropna=False)
            .agg(
                revenue=("net_item_revenue", "sum"),
                item_rows=("net_item_revenue", "size"),
                quantity=("quantity", "sum"),
                products=("product_id", "nunique"),
            )
            .reset_index()
            .rename(columns={group_col: "group_value"})
        )
        grouped["group_field"] = group_col
        grouped["analysis_level"] = "product_item_level"
        grouped["revenue_pct"] = (
            grouped["revenue"] / total_revenue * 100 if total_revenue else 0
        )
        grouped["avg_revenue_per_item_row"] = grouped["revenue"] / grouped["item_rows"]
        grouped = grouped.sort_values("revenue", ascending=False).head(TOP_N)
        rows.append(grouped)

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    save_table(out, "06a_revenue_by_product_group.csv")
    return out


def build_group_revenue_rows(df, group_columns, analysis_level):
    total_revenue = df["revenue"].sum()
    rows = []

    for group_col in group_columns:
        if group_col not in df.columns:
            continue

        grouped = (
            df.groupby(group_col, dropna=False)
            .agg(
                revenue=("revenue", "sum"),
                orders=("order_id", "nunique"),
            )
            .reset_index()
            .rename(columns={group_col: "group_value"})
        )
        grouped["group_field"] = group_col
        grouped["analysis_level"] = analysis_level
        grouped["revenue_pct"] = grouped["revenue"] / total_revenue * 100 if total_revenue else 0
        grouped["avg_revenue_per_order"] = grouped["revenue"] / grouped["orders"]
        grouped = grouped.sort_values("revenue", ascending=False).head(TOP_N)
        rows.append(grouped)

    return rows


def plot_numeric_distributions(tables):
    plot_specs = [
        ("sales", "Revenue"),
        ("sales", "Gross Profit"),
        ("payments", "payment_value"),
        ("order_items", "unit_price"),
        ("order_items", "discount_amount"),
        ("products", "price"),
        ("returns", "refund_amount"),
        ("reviews", "rating"),
        ("web_traffic", "sessions"),
        ("inventory", "fill_rate"),
    ]
    available = [
        (table, column)
        for table, column in plot_specs
        if table in tables and column in tables[table].columns
    ]
    if not available:
        return None

    ncols = 2
    nrows = math.ceil(len(available) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 3.3 * nrows))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for ax, (table, column) in zip(axes, available):
        s = pd.to_numeric(tables[table][column], errors="coerce").dropna()
        sns.histplot(s, bins=40, ax=ax, color="#4c78a8")
        ax.set_title(f"{table}.{column}")
        ax.set_xlabel(column)
        ax.set_ylabel("Rows")

    for ax in axes[len(available):]:
        ax.axis("off")

    fig.suptitle("Key numeric distributions", fontsize=13, weight="bold")
    return save_figure(fig, "06a_numeric_distribution_grid.png")


def plot_categorical_top_values(df_top):
    if df_top.empty:
        return None

    first_rank = df_top[df_top["rank"] == 1].copy()
    first_rank["field"] = first_rank["table"] + "." + first_rank["column"]
    first_rank = first_rank.sort_values("pct", ascending=True)

    fig, ax = plt.subplots(figsize=(10, max(5, len(first_rank) * 0.35)))
    sns.barplot(data=first_rank, x="pct", y="field", ax=ax, color="#59a14f")
    ax.set_title("Top category share by field")
    ax.set_xlabel("Top value share (%)")
    ax.set_ylabel("Field")
    return save_figure(fig, "06a_categorical_top_values.png")


def plot_sales_revenue_distribution_detail(tables):
    if "sales" not in tables or "Revenue" not in tables["sales"].columns:
        return None

    revenue = pd.to_numeric(tables["sales"]["Revenue"], errors="coerce").dropna()
    if revenue.empty:
        return None

    fig, axes = plt.subplots(2, 2, figsize=(13, 8))

    sns.histplot(revenue, bins=50, kde=True, ax=axes[0, 0], color="#4c78a8")
    axes[0, 0].axvline(revenue.mean(), color="#e15759", linestyle="--", label="mean")
    axes[0, 0].axvline(revenue.median(), color="#59a14f", linestyle="--", label="median")
    axes[0, 0].set_title("Daily Revenue distribution")
    axes[0, 0].set_xlabel("Revenue")
    axes[0, 0].legend()

    sns.boxplot(x=revenue, ax=axes[0, 1], color="#f28e2b")
    axes[0, 1].set_title("Daily Revenue boxplot")
    axes[0, 1].set_xlabel("Revenue")

    sns.ecdfplot(revenue, ax=axes[1, 0], color="#4c78a8")
    axes[1, 0].set_title("Daily Revenue cumulative distribution")
    axes[1, 0].set_xlabel("Revenue")
    axes[1, 0].set_ylabel("Cumulative share of days")

    sns.histplot(revenue, bins=50, log_scale=(True, False), ax=axes[1, 1], color="#76b7b2")
    axes[1, 1].set_title("Daily Revenue distribution - log x-axis")
    axes[1, 1].set_xlabel("Revenue, log scale")

    fig.suptitle("Revenue distribution shape", fontsize=13, weight="bold")
    return save_figure(fig, "06a_sales_revenue_distribution_detail.png")


def plot_revenue_group_grid(df, filename, title, value_col="revenue"):
    if df.empty:
        return None

    fields = list(df["group_field"].drop_duplicates())[:4]
    if not fields:
        return None

    ncols = 2
    nrows = math.ceil(len(fields) / ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(13, 4 * nrows))
    axes = axes.flatten() if hasattr(axes, "flatten") else [axes]

    for ax, field in zip(axes, fields):
        plot_df = df[df["group_field"] == field].sort_values(value_col, ascending=False).head(8)
        sns.barplot(data=plot_df, x=value_col, y="group_value", ax=ax, color="#4c78a8")
        ax.set_title(f"Revenue by {field}")
        ax.set_xlabel("Revenue")
        ax.set_ylabel("")

    for ax in axes[len(fields):]:
        ax.axis("off")

    fig.suptitle(title, fontsize=13, weight="bold")
    return save_figure(fig, filename)


def dataframe_to_markdown(df):
    if df.empty:
        return "*No rows.*"
    return df.to_markdown(index=False)


def generate_report(df_numeric, df_categorical, df_order_revenue, df_product_revenue):
    skewed_all = df_numeric[
        df_numeric["skew_flag"].isin(["right_skewed_strong", "left_skewed_strong"])
    ]
    skewed = skewed_all[["table", "column", "skew", "skew_flag", "mean", "median"]].head(12)

    high_zero_all = df_numeric[df_numeric["zero_pct"] > 20]
    high_zero = high_zero_all[
        ["table", "column", "zero_pct", "mean", "median"]
    ].sort_values("zero_pct", ascending=False).head(12)

    dominant = df_categorical[df_categorical["rank"] == 1][
        ["table", "column", "value", "pct", "unique_values"]
    ].sort_values("pct", ascending=False).head(12)

    revenue_shape = df_numeric[
        (df_numeric["table"] == "sales") & (df_numeric["column"] == "Revenue")
    ][["mean", "median", "p95", "p99", "max", "skew", "mean_median_gap_pct"]]

    top_order_revenue = (
        df_order_revenue[
            df_order_revenue["group_field"].isin(["order_source", "payment_method", "device_type", "age_group"])
        ][["analysis_level", "group_field", "group_value", "revenue", "revenue_pct", "orders"]]
        .sort_values(["group_field", "revenue"], ascending=[True, False])
        .groupby("group_field")
        .head(3)
        if not df_order_revenue.empty
        else pd.DataFrame()
    )

    top_product_revenue = (
        df_product_revenue[
            df_product_revenue["group_field"].isin(["category", "segment", "product_name"])
        ][["group_field", "group_value", "revenue", "revenue_pct", "item_rows", "quantity"]]
        .sort_values(["group_field", "revenue"], ascending=[True, False])
        .groupby("group_field")
        .head(5)
        if not df_product_revenue.empty
        else pd.DataFrame()
    )

    report = f"""# Distribution Analysis (06a)

## Overview

| Metric | Value |
|---|---:|
| Numeric fields summarized | {len(df_numeric)} |
| Categorical top-value rows | {len(df_categorical)} |
| Strongly skewed numeric fields | {len(skewed_all)} |
| Numeric fields with >20% zero values | {len(high_zero_all)} |

## Revenue Distribution Shape

{dataframe_to_markdown(revenue_shape)}

## Top Revenue Groups - Order and Customer Level

{dataframe_to_markdown(top_order_revenue)}

## Top Revenue Groups - Product Item Level

{dataframe_to_markdown(top_product_revenue)}

## Strong Skew Candidates

{dataframe_to_markdown(skewed)}

## High Zero-Value Candidates

{dataframe_to_markdown(high_zero)}

## Dominant Categorical Values

{dataframe_to_markdown(dominant)}

## Notes

- This step describes distributions only; it does not infer causality.
- `sales` includes derived `Gross Profit = Revenue - COGS` and `Margin = Gross Profit / Revenue`.
- Revenue by order/customer groups uses a focused `orders` + order-level `payments` merge.
- Revenue by product groups uses a focused `order_items` + `products` merge and `quantity * unit_price - discount_amount`.
- Detailed outputs are saved in `06a_numeric_describe.csv`, `06a_categorical_top_values.csv`, `06a_revenue_by_order_group.csv`, and `06a_revenue_by_product_group.csv`.
"""
    save_report(report, "06a_distribution_summary.md")


def main():
    print("Loading tables for distribution analysis...")
    tables = load_tables(
        names=set(NUMERIC_COLUMNS) | set(CATEGORICAL_COLUMNS),
        parse_dates=False,
    )
    print(f"Loaded {len(tables)} tables.")

    print("Adding derived metrics...")
    add_derived_metrics(tables)

    print("Summarizing numeric distributions...")
    df_numeric = summarize_numeric(tables)

    print("Summarizing categorical distributions...")
    df_categorical = summarize_categorical(tables)

    print("Summarizing revenue contribution by groups...")
    df_order_revenue = summarize_revenue_by_order_groups(tables)
    df_product_revenue = summarize_revenue_by_product_groups(tables)

    print("Creating figures...")
    plot_numeric_distributions(tables)
    plot_categorical_top_values(df_categorical)
    plot_sales_revenue_distribution_detail(tables)
    plot_revenue_group_grid(
        df_order_revenue[df_order_revenue["group_field"].isin(ORDER_REVENUE_GROUPS)]
        if not df_order_revenue.empty
        else df_order_revenue,
        "06a_revenue_by_order_groups.png",
        "Order-level revenue contribution",
    )
    plot_revenue_group_grid(
        df_product_revenue[df_product_revenue["group_field"].isin(["category", "segment", "size", "color"])]
        if not df_product_revenue.empty
        else df_product_revenue,
        "06a_revenue_by_product_groups.png",
        "Product-level revenue contribution",
    )

    print("Generating markdown report...")
    generate_report(df_numeric, df_categorical, df_order_revenue, df_product_revenue)

    print("06a distribution analysis done!")


if __name__ == "__main__":
    main()
