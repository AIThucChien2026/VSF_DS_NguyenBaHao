"""
Goal:
    Explore relationships between variables that can inform forecasting features.

Input:
    - sales.csv, web_traffic.csv
    - order_items.csv, products.csv
    - orders.csv, shipments.csv, reviews.csv
    - Optional existing 06b return-rate output for feature-candidate notes

Process:
    1. Revenue vs traffic at daily grain.
    2. Discount vs estimated profit at item grain.
    3. Lead time vs rating at order grain.
    4. Category/segment margin at item grain.
    5. Feature-candidate table with leakage notes.

Output:
    - outputs/tables/07a_daily_sales_traffic_relationship.csv
    - outputs/tables/07b_discount_profit_relationship.csv
    - outputs/tables/07c_leadtime_rating_relationship.csv
    - outputs/tables/07d_category_margin_relationship.csv
    - outputs/tables/07e_feature_candidates.csv
    - outputs/reports/07_relationship_summary.md
    - outputs/figures/07_*.png
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.ticker import FuncFormatter

from config import TABLE_DIR, load_tables, save_figure, save_report, save_table


TRAFFIC_METRICS = [
    "sessions",
    "unique_visitors",
    "page_views",
    "bounce_rate",
    "avg_session_duration_sec",
    "sessions_lag_1d",
    "sessions_lag_7d",
    "sessions_rolling_7d",
    "sessions_rolling_30d",
]

SALES_METRICS = ["Revenue", "COGS", "Gross_Profit", "Margin"]
GROUP_FIELDS = ["category", "segment", "size", "color"]
LEAD_BINS = [-0.01, 2, 5, 8, float("inf")]
LEAD_LABELS = ["0-2", "3-5", "6-8", "9+"]


def compact_number(value, _position=None):
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.0f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def pct_label(value, _position=None):
    return f"{value:.0f}%"


def dataframe_to_markdown(df):
    if df is None or df.empty:
        return "*No rows.*"
    return df.to_markdown(index=False)


def add_sales_metrics(sales):
    sales = sales.copy()
    sales["Gross_Profit"] = sales["Revenue"] - sales["COGS"]
    sales["Margin"] = sales["Gross_Profit"] / sales["Revenue"].replace(0, pd.NA)
    return sales


def build_daily_sales_traffic(tables):
    if not {"sales", "web_traffic"}.issubset(tables):
        out = pd.DataFrame()
        save_table(out, "07a_daily_sales_traffic_relationship.csv")
        return out, pd.DataFrame(), {}

    sales = add_sales_metrics(tables["sales"])
    web = tables["web_traffic"].copy()

    web_daily = web.groupby("date", as_index=False).agg(
        sessions=("sessions", "sum"),
        unique_visitors=("unique_visitors", "sum"),
        page_views=("page_views", "sum"),
        bounce_rate=("bounce_rate", "mean"),
        avg_session_duration_sec=("avg_session_duration_sec", "mean"),
    )
    web_daily = web_daily.sort_values("date")
    web_daily["sessions_lag_1d"] = web_daily["sessions"].shift(1)
    web_daily["sessions_lag_7d"] = web_daily["sessions"].shift(7)
    web_daily["sessions_rolling_7d"] = web_daily["sessions"].rolling(7, min_periods=1).mean()
    web_daily["sessions_rolling_30d"] = web_daily["sessions"].rolling(30, min_periods=1).mean()

    merged = sales[["Date"] + SALES_METRICS].merge(
        web_daily,
        left_on="Date",
        right_on="date",
        how="left",
    )
    merged = merged.drop(columns=["date"])

    corr_cols = [col for col in SALES_METRICS + TRAFFIC_METRICS if col in merged.columns]
    corr_matrix = merged[corr_cols].corr(numeric_only=True)
    corr_rows = []
    for sales_col in SALES_METRICS:
        for traffic_col in TRAFFIC_METRICS:
            if sales_col in corr_matrix.index and traffic_col in corr_matrix.columns:
                corr_rows.append(
                    {
                        "sales_metric": sales_col,
                        "traffic_metric": traffic_col,
                        "pearson_corr": corr_matrix.loc[sales_col, traffic_col],
                        "non_null_pairs": int(merged[[sales_col, traffic_col]].dropna().shape[0]),
                    }
                )
    corr_df = pd.DataFrame(corr_rows).sort_values(
        "pearson_corr", key=lambda s: s.abs(), ascending=False
    )

    validation = {
        "sales_rows": len(sales),
        "web_daily_rows": len(web_daily),
        "merged_rows": len(merged),
        "missing_web_rows_after_left_join": int(merged["sessions"].isna().sum()),
        "sales_date_min": sales["Date"].min(),
        "sales_date_max": sales["Date"].max(),
        "web_date_min": web_daily["date"].min(),
        "web_date_max": web_daily["date"].max(),
    }

    save_table(merged, "07a_daily_sales_traffic_relationship.csv")
    return merged, corr_df, validation


def build_item_profit_base(tables):
    if not {"order_items", "products"}.issubset(tables):
        return pd.DataFrame(), {}

    items = tables["order_items"].copy()
    products = tables["products"].copy()
    product_cols = ["product_id", "category", "segment", "size", "color", "cogs"]
    item_base = items.merge(products[product_cols], on="product_id", how="left")

    item_base["gross_item_value"] = item_base["quantity"] * item_base["unit_price"]
    item_base["net_item_revenue"] = item_base["gross_item_value"] - item_base["discount_amount"]
    item_base["discount_rate"] = item_base["discount_amount"] / item_base["gross_item_value"].replace(0, pd.NA)
    item_base["estimated_item_cogs"] = item_base["quantity"] * item_base["cogs"]
    item_base["estimated_item_profit"] = item_base["net_item_revenue"] - item_base["estimated_item_cogs"]
    item_base["estimated_margin"] = item_base["estimated_item_profit"] / item_base["net_item_revenue"].replace(0, pd.NA)

    validation = {
        "order_items_rows": len(items),
        "item_base_rows": len(item_base),
        "missing_product_rows": int(item_base["category"].isna().sum()),
        "negative_net_item_revenue_rows": int((item_base["net_item_revenue"] < 0).sum()),
        "non_positive_gross_item_value_rows": int((item_base["gross_item_value"] <= 0).sum()),
    }
    return item_base, validation


def build_discount_profit_relationship(item_base):
    if item_base.empty:
        out = pd.DataFrame()
        save_table(out, "07b_discount_profit_relationship.csv")
        return out

    discount_bins = [-0.01, 0, 0.05, 0.10, 0.20, float("inf")]
    discount_labels = ["0", "0-5%", "5-10%", "10-20%", "20%+"]
    df = item_base.copy()
    df["discount_bin"] = pd.cut(
        df["discount_rate"].fillna(0),
        bins=discount_bins,
        labels=discount_labels,
        include_lowest=True,
    )

    grouped = df.groupby(["discount_bin", "category"], dropna=False, observed=False).agg(
        item_rows=("order_id", "size"),
        quantity=("quantity", "sum"),
        revenue=("net_item_revenue", "sum"),
        estimated_profit=("estimated_item_profit", "sum"),
        avg_discount_rate=("discount_rate", "mean"),
        avg_margin=("estimated_margin", "mean"),
    ).reset_index()
    grouped["profit_margin_weighted"] = grouped["estimated_profit"] / grouped["revenue"].replace(0, pd.NA)

    save_table(grouped, "07b_discount_profit_relationship.csv")
    return grouped


def build_leadtime_rating_relationship(tables):
    if not {"orders", "shipments", "reviews"}.issubset(tables):
        out = pd.DataFrame()
        save_table(out, "07c_leadtime_rating_relationship.csv")
        return out, pd.DataFrame(), {}

    orders = tables["orders"].copy()
    shipments = tables["shipments"].copy()
    reviews = tables["reviews"].copy()

    review_order = reviews.groupby("order_id", as_index=False).agg(
        avg_rating=("rating", "mean"),
        review_count=("review_id", "nunique"),
        first_review_date=("review_date", "min"),
    )
    base = (
        orders[["order_id", "order_date"]]
        .merge(shipments[["order_id", "ship_date", "delivery_date"]], on="order_id", how="left")
        .merge(review_order, on="order_id", how="inner")
    )
    base["ship_lead_days"] = (base["ship_date"] - base["order_date"]).dt.days
    base["delivery_lead_days"] = (base["delivery_date"] - base["order_date"]).dt.days
    base["review_delay_days"] = (base["first_review_date"] - base["order_date"]).dt.days
    base["delivery_lead_bin"] = pd.cut(
        base["delivery_lead_days"],
        bins=LEAD_BINS,
        labels=LEAD_LABELS,
        include_lowest=True,
    )

    grouped = base.groupby("delivery_lead_bin", dropna=False, observed=False).agg(
        orders=("order_id", "nunique"),
        avg_rating=("avg_rating", "mean"),
        median_rating=("avg_rating", "median"),
        avg_delivery_lead_days=("delivery_lead_days", "mean"),
        avg_review_delay_days=("review_delay_days", "mean"),
    ).reset_index()

    corr = base[["avg_rating", "ship_lead_days", "delivery_lead_days", "review_delay_days"]].corr(
        numeric_only=True
    )
    corr_rows = []
    for metric in ["ship_lead_days", "delivery_lead_days", "review_delay_days"]:
        corr_rows.append(
            {
                "relationship": f"{metric} vs avg_rating",
                "pearson_corr": corr.loc["avg_rating", metric] if metric in corr.columns else pd.NA,
                "non_null_pairs": int(base[["avg_rating", metric]].dropna().shape[0]),
            }
        )
    corr_df = pd.DataFrame(corr_rows)

    validation = {
        "orders_rows": len(orders),
        "shipments_rows": len(shipments),
        "review_orders": len(review_order),
        "leadtime_base_rows": len(base),
        "negative_ship_lead_rows": int((base["ship_lead_days"] < 0).sum()),
        "negative_delivery_lead_rows": int((base["delivery_lead_days"] < 0).sum()),
        "ratings_outside_1_5_rows": int(((base["avg_rating"] < 1) | (base["avg_rating"] > 5)).sum()),
    }

    save_table(grouped, "07c_leadtime_rating_relationship.csv")
    return grouped, corr_df, validation


def build_category_margin_relationship(item_base):
    if item_base.empty:
        out = pd.DataFrame()
        save_table(out, "07d_category_margin_relationship.csv")
        return out

    rows = []
    for field in GROUP_FIELDS:
        grouped = item_base.groupby(field, dropna=False).agg(
            item_rows=("order_id", "size"),
            quantity=("quantity", "sum"),
            revenue=("net_item_revenue", "sum"),
            estimated_profit=("estimated_item_profit", "sum"),
            avg_margin=("estimated_margin", "mean"),
            products=("product_id", "nunique"),
        ).reset_index().rename(columns={field: "group_value"})
        grouped["group_field"] = field
        grouped["profit_margin_weighted"] = grouped["estimated_profit"] / grouped["revenue"].replace(0, pd.NA)
        rows.append(grouped)

    out = pd.concat(rows, ignore_index=True)
    out = out[
        [
            "group_field",
            "group_value",
            "item_rows",
            "quantity",
            "products",
            "revenue",
            "estimated_profit",
            "avg_margin",
            "profit_margin_weighted",
        ]
    ].sort_values(["group_field", "revenue"], ascending=[True, False])
    save_table(out, "07d_category_margin_relationship.csv")
    return out


def build_feature_candidates(return_rate_exists):
    rows = [
        {
            "feature_name": "sessions_lag_1d / sessions_lag_7d",
            "source_tables": "web_traffic",
            "grain": "daily",
            "why_useful": "Captures recent demand/traffic signal before revenue is observed.",
            "leakage_risk": "LOW if only past traffic is used.",
            "recommended_use": "Use lagged traffic features for daily revenue/COGS forecasting.",
        },
        {
            "feature_name": "sessions_rolling_7d / sessions_rolling_30d",
            "source_tables": "web_traffic",
            "grain": "daily",
            "why_useful": "Smooths noisy traffic and captures short/medium-term demand trend.",
            "leakage_risk": "LOW if rolling window excludes future days.",
            "recommended_use": "Use rolling features computed up to prediction date.",
        },
        {
            "feature_name": "discount_rate_bin_share",
            "source_tables": "order_items, products",
            "grain": "item/monthly aggregate",
            "why_useful": "Discount intensity may explain revenue lift and margin pressure.",
            "leakage_risk": "MEDIUM; future discounts are only usable if promotion calendar is known.",
            "recommended_use": "Aggregate by month/category and use known planned discounts or lagged discount mix.",
        },
        {
            "feature_name": "category_revenue_share / segment_revenue_share",
            "source_tables": "order_items, products",
            "grain": "item/monthly aggregate",
            "why_useful": "Product mix can explain revenue, COGS, and margin movements.",
            "leakage_risk": "MEDIUM if computed from same-period realized sales.",
            "recommended_use": "Use lagged category mix or planned assortment/category indicators.",
        },
        {
            "feature_name": "return_rate_lag_1m / return_rate_rolling_3m",
            "source_tables": "06b_return_rate_monthly.csv",
            "grain": "monthly",
            "why_useful": "Return pressure can signal weak revenue quality and future margin risk.",
            "leakage_risk": "LOW when lagged; HIGH if same-month full cohort return rate is used.",
            "recommended_use": "Use lagged/rolling return metrics only.",
        },
        {
            "feature_name": "delivery_lead_days_lagged_summary",
            "source_tables": "orders, shipments, reviews",
            "grain": "order/monthly aggregate",
            "why_useful": "Fulfillment delay may affect satisfaction and repeat demand.",
            "leakage_risk": "MEDIUM; same-order delivery outcome may not be known at forecast time.",
            "recommended_use": "Use historical monthly averages or operational SLA features.",
        },
        {
            "feature_name": "rating_lagged_average",
            "source_tables": "reviews",
            "grain": "monthly",
            "why_useful": "Customer satisfaction trend can signal future demand and return risk.",
            "leakage_risk": "LOW when lagged; HIGH if using future reviews.",
            "recommended_use": "Use lagged average rating and review volume.",
        },
    ]

    if not return_rate_exists:
        rows.append(
            {
                "feature_name": "return_rate_lag_1m / return_rate_rolling_3m",
                "source_tables": "06b_return_rate_monthly.csv",
                "grain": "monthly",
                "why_useful": "Feature candidate requires running 06b first.",
                "leakage_risk": "UNKNOWN until source table exists.",
                "recommended_use": "Run 06b_time_trend_analysis.py before building return features.",
            }
        )

    out = pd.DataFrame(rows)
    save_table(out, "07e_feature_candidates.csv")
    return out


def plot_sales_traffic_scatter(df):
    required = {"sessions", "Revenue"}
    if df.empty or not required.issubset(df.columns):
        return None
    plot_df = df.dropna(subset=["sessions", "Revenue"])
    if plot_df.empty:
        return None

    fig, ax = plt.subplots(figsize=(8, 5.5))
    sns.regplot(
        data=plot_df,
        x="sessions",
        y="Revenue",
        scatter_kws={"alpha": 0.25, "s": 14},
        line_kws={"color": "#dc2626", "linewidth": 1.5},
        ax=ax,
    )
    ax.set_title("Daily Revenue vs Web Sessions", weight="bold")
    ax.set_xlabel("Sessions")
    ax.set_ylabel("Revenue")
    ax.xaxis.set_major_formatter(FuncFormatter(compact_number))
    ax.yaxis.set_major_formatter(FuncFormatter(compact_number))
    return save_figure(fig, "07_revenue_vs_sessions_scatter.png")


def plot_sales_traffic_normalized(df):
    required = {"Date", "Revenue", "sessions_rolling_30d"}
    if df.empty or not required.issubset(df.columns):
        return None
    plot_df = df.dropna(subset=["Revenue", "sessions_rolling_30d"]).copy()
    if plot_df.empty:
        return None

    plot_df["Revenue_index"] = plot_df["Revenue"] / plot_df["Revenue"].mean() * 100
    plot_df["sessions_rolling_30d_index"] = (
        plot_df["sessions_rolling_30d"] / plot_df["sessions_rolling_30d"].mean() * 100
    )

    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.plot(plot_df["Date"], plot_df["Revenue_index"], label="Revenue index", linewidth=1.2, alpha=0.65)
    ax.plot(
        plot_df["Date"],
        plot_df["sessions_rolling_30d_index"],
        label="Sessions 30d rolling index",
        linewidth=2.0,
        color="#f97316",
    )
    ax.axhline(100, color="#64748b", linewidth=0.8, alpha=0.8)
    ax.set_title("Revenue and Traffic Trend, Indexed to Average = 100", weight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Index")
    ax.legend(loc="upper left", ncol=2, frameon=True)
    return save_figure(fig, "07_revenue_traffic_indexed_trend.png")


def plot_discount_profit(df):
    if df.empty:
        return None
    plot_df = (
        df.groupby("discount_bin", observed=False)
        .agg(
            estimated_profit=("estimated_profit", "sum"),
            profit_margin_weighted=("profit_margin_weighted", "mean"),
            revenue=("revenue", "sum"),
        )
        .reset_index()
    )

    fig, ax_profit = plt.subplots(figsize=(9, 5.2))
    sns.barplot(data=plot_df, x="discount_bin", y="estimated_profit", ax=ax_profit, color="#4c78a8")
    ax_profit.set_title("Estimated Profit and Margin by Discount Bin", weight="bold")
    ax_profit.set_xlabel("Discount bin")
    ax_profit.set_ylabel("Estimated profit")
    ax_profit.yaxis.set_major_formatter(FuncFormatter(compact_number))

    ax_margin = ax_profit.twinx()
    ax_margin.plot(
        plot_df["discount_bin"].astype(str),
        plot_df["profit_margin_weighted"] * 100,
        color="#f97316",
        marker="o",
        linewidth=2.0,
        label="Weighted margin",
    )
    ax_margin.set_ylabel("Weighted margin (%)")
    ax_margin.yaxis.set_major_formatter(FuncFormatter(pct_label))
    return save_figure(fig, "07_discount_profit_by_bin.png")


def plot_leadtime_rating(df):
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    sns.barplot(data=df, x="delivery_lead_bin", y="avg_rating", ax=ax, color="#4c78a8")
    ax.set_title("Average Rating by Delivery Lead Time", weight="bold")
    ax.set_xlabel("Delivery lead time bin (days)")
    ax.set_ylabel("Average rating")
    ax.set_ylim(1, 5)
    return save_figure(fig, "07_leadtime_rating_by_bin.png")


def plot_category_margin(df):
    if df.empty:
        return None

    category = df[df["group_field"] == "category"].copy()
    if category.empty:
        return None

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    scatter = ax.scatter(
        category["revenue"],
        category["profit_margin_weighted"] * 100,
        s=category["item_rows"] / category["item_rows"].max() * 500 + 80,
        alpha=0.75,
        color="#4c78a8",
    )
    for _, row in category.iterrows():
        ax.annotate(str(row["group_value"]), (row["revenue"], row["profit_margin_weighted"] * 100), fontsize=9)
    ax.set_title("Category Revenue vs Estimated Margin", weight="bold")
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Weighted margin (%)")
    ax.xaxis.set_major_formatter(FuncFormatter(compact_number))
    ax.yaxis.set_major_formatter(FuncFormatter(pct_label))
    return save_figure(fig, "07_category_revenue_margin_scatter.png")


def plot_segment_profit_margin(df):
    if df.empty:
        return None
    segment = df[df["group_field"] == "segment"].sort_values("estimated_profit", ascending=False).head(10)
    if segment.empty:
        return None

    fig, ax = plt.subplots(figsize=(10, 5.6))
    sns.barplot(data=segment, x="estimated_profit", y="group_value", ax=ax, color="#4c78a8")
    ax.set_title("Top Segments by Estimated Profit", weight="bold")
    ax.set_xlabel("Estimated profit")
    ax.set_ylabel("Segment")
    ax.xaxis.set_major_formatter(FuncFormatter(compact_number))
    return save_figure(fig, "07_segment_estimated_profit.png")


def generate_report(
    traffic_corr,
    traffic_validation,
    item_validation,
    lead_validation,
    lead_corr,
    discount_summary,
    category_margin,
    feature_candidates,
):
    top_traffic = traffic_corr.head(12) if not traffic_corr.empty else pd.DataFrame()
    discount_overall = (
        discount_summary.groupby("discount_bin", observed=False)
        .agg(
            item_rows=("item_rows", "sum"),
            revenue=("revenue", "sum"),
            estimated_profit=("estimated_profit", "sum"),
            avg_margin=("avg_margin", "mean"),
            profit_margin_weighted=("profit_margin_weighted", "mean"),
        )
        .reset_index()
        if not discount_summary.empty
        else pd.DataFrame()
    )
    category_top = (
        category_margin[category_margin["group_field"].isin(["category", "segment"])]
        .sort_values(["group_field", "estimated_profit"], ascending=[True, False])
        .groupby("group_field")
        .head(5)
        if not category_margin.empty
        else pd.DataFrame()
    )

    validation_df = pd.DataFrame(
        [
            {"check": key, "value": value}
            for block in [traffic_validation, item_validation, lead_validation]
            for key, value in block.items()
        ]
    )

    report = f"""# Relationship Analysis (07)

## Overview

Step 5 explores relationships that may inform forecasting features. Each analysis uses only the tables needed for that relationship and keeps a clear grain.

## Validation Checks

{dataframe_to_markdown(validation_df)}

## Revenue vs Traffic: Strongest Correlations

{dataframe_to_markdown(top_traffic)}

## Discount vs Estimated Profit

{dataframe_to_markdown(discount_overall)}

## Lead Time vs Rating Correlation

{dataframe_to_markdown(lead_corr)}

## Category and Segment Margin Highlights

{dataframe_to_markdown(category_top)}

## Feature Candidates

{dataframe_to_markdown(feature_candidates)}

## Notes

- `sales.csv` is the source of daily Revenue/COGS.
- Item-level profit is estimated as `quantity * unit_price - discount_amount - quantity * products.cogs`.
- Traffic features should be lagged or rolling features computed only from past dates.
- Return-rate features should come from lagged/rolling values, not same-period future-complete cohorts.
- Correlation is directional guidance for feature exploration, not causal proof.
"""
    save_report(report, "07_relationship_summary.md")


def main():
    print("Loading tables for relationship analysis...")
    tables = load_tables(
        names=[
            "sales",
            "web_traffic",
            "order_items",
            "products",
            "orders",
            "shipments",
            "reviews",
        ],
        parse_dates=True,
    )
    print(f"Loaded {len(tables)} tables.")

    print("Building daily sales/traffic relationship...")
    daily_sales_traffic, traffic_corr, traffic_validation = build_daily_sales_traffic(tables)

    print("Building item-level profit base...")
    item_base, item_validation = build_item_profit_base(tables)

    print("Building discount/profit relationship...")
    discount_summary = build_discount_profit_relationship(item_base)

    print("Building lead-time/rating relationship...")
    lead_summary, lead_corr, lead_validation = build_leadtime_rating_relationship(tables)

    print("Building category/segment margin relationship...")
    category_margin = build_category_margin_relationship(item_base)

    print("Building feature candidate table...")
    return_rate_exists = (TABLE_DIR / "06b_return_rate_monthly.csv").exists()
    feature_candidates = build_feature_candidates(return_rate_exists)

    print("Creating figures...")
    plot_sales_traffic_scatter(daily_sales_traffic)
    plot_sales_traffic_normalized(daily_sales_traffic)
    plot_discount_profit(discount_summary)
    plot_leadtime_rating(lead_summary)
    plot_category_margin(category_margin)
    plot_segment_profit_margin(category_margin)

    print("Generating markdown report...")
    generate_report(
        traffic_corr,
        traffic_validation,
        item_validation,
        lead_validation,
        lead_corr,
        discount_summary,
        category_margin,
        feature_candidates,
    )

    print("07 relationship analysis done!")


if __name__ == "__main__":
    main()
