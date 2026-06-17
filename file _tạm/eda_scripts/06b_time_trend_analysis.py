"""
Goal:
    Explore time-based coverage and trends after the initial data-quality checks.

Input:
    - sales.csv as the central analytical table for Revenue/COGS.
    - Other dated tables for operational and behavioral trend summaries.

Process:
    - Parse date columns.
    - Build date coverage and missing-date checks.
    - Summarize sales by daily, weekly, monthly, and yearly levels.
    - Add rolling Revenue/COGS/Gross Profit averages for daily sales.
    - Summarize orders, returns, reviews, web traffic, and inventory over time.
    - Save focused charts for visual inspection.

Output:
    - outputs/tables/06b_date_coverage.csv
    - outputs/tables/06b_sales_daily.csv
    - outputs/tables/06b_sales_weekly.csv
    - outputs/tables/06b_sales_monthly.csv
    - outputs/tables/06b_sales_yearly.csv
    - outputs/tables/06b_order_status_monthly.csv
    - outputs/tables/06b_returns_monthly.csv
    - outputs/tables/06b_return_rate_monthly.csv
    - outputs/tables/06b_reviews_monthly.csv
    - outputs/tables/06b_web_traffic_daily.csv
    - outputs/tables/06b_web_traffic_monthly.csv
    - outputs/tables/06b_inventory_monthly.csv
    - outputs/reports/06b_time_trend_summary.md
    - outputs/figures/06b_sales_daily_rolling.png
    - outputs/figures/06b_sales_monthly.png
    - outputs/figures/06b_orders_monthly.png
    - outputs/figures/06b_returns_monthly.png
    - outputs/figures/06b_web_sessions_daily.png
    - outputs/figures/06b_web_sessions_monthly.png
    - outputs/figures/06b_inventory_monthly.png
"""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

from config import DATE_COLUMNS, load_tables, save_figure, save_report, save_table


DATE_CHECKS = {
    "sales": "Date",
    "sample_submission": "Date",
    "orders": "order_date",
    "returns": "return_date",
    "reviews": "review_date",
    "web_traffic": "date",
    "inventory": "snapshot_date",
}


def add_sales_metrics(sales):
    sales = sales.copy()
    sales["Gross Profit"] = sales["Revenue"] - sales["COGS"]
    sales["Margin"] = sales["Gross Profit"] / sales["Revenue"].replace(0, pd.NA)
    return sales


def month_start(series):
    return series.dt.to_period("M").dt.to_timestamp()


def week_start(series):
    return series.dt.to_period("W-SUN").dt.start_time


def summarize_coverage(tables):
    rows = []

    for table, date_col in DATE_CHECKS.items():
        if table not in tables or date_col not in tables[table].columns:
            continue

        df = tables[table]
        dates = df[date_col].dropna()
        min_date = dates.min() if not dates.empty else pd.NaT
        max_date = dates.max() if not dates.empty else pd.NaT
        unique_dates = int(dates.dt.normalize().nunique()) if not dates.empty else 0

        expected_days = 0
        missing_days = 0
        missing_months = 0
        if not pd.isna(min_date) and not pd.isna(max_date):
            all_days = pd.date_range(min_date.normalize(), max_date.normalize(), freq="D")
            present_days = pd.Index(dates.dt.normalize().unique())
            missing_days = int(len(all_days.difference(present_days)))
            expected_days = int(len(all_days))

            all_months = pd.period_range(min_date, max_date, freq="M")
            present_months = dates.dt.to_period("M").unique()
            missing_months = int(len(all_months.difference(pd.PeriodIndex(present_months))))

        rows.append(
            {
                "table": table,
                "date_column": date_col,
                "rows": len(df),
                "missing_date_rows": int(df[date_col].isna().sum()),
                "min_date": min_date,
                "max_date": max_date,
                "unique_dates": unique_dates,
                "expected_days_between_min_max": expected_days,
                "missing_days_between_min_max": missing_days,
                "missing_months_between_min_max": missing_months,
            }
        )

    out = pd.DataFrame(rows)
    save_table(out, "06b_date_coverage.csv")
    return out


def build_sales_time_tables(tables):
    if "sales" not in tables:
        return None, None, None, None

    sales = tables["sales"].copy()
    required = {"Date", "Revenue", "COGS"}
    if not required.issubset(sales.columns):
        return None, None, None, None

    sales = add_sales_metrics(sales)
    sales = sales.sort_values("Date")

    daily = sales.groupby("Date", as_index=False).agg(
        Revenue=("Revenue", "sum"),
        COGS=("COGS", "sum"),
        Gross_Profit=("Gross Profit", "sum"),
        Margin=("Margin", "mean"),
    )
    daily = daily.sort_values("Date")
    daily["Revenue_rolling_7d"] = daily["Revenue"].rolling(7, min_periods=1).mean()
    daily["Revenue_rolling_30d"] = daily["Revenue"].rolling(30, min_periods=1).mean()
    daily["COGS_rolling_30d"] = daily["COGS"].rolling(30, min_periods=1).mean()
    daily["Gross_Profit_rolling_30d"] = daily["Gross_Profit"].rolling(30, min_periods=1).mean()
    save_table(daily, "06b_sales_daily.csv")

    weekly = daily.copy()
    weekly["week_start"] = week_start(weekly["Date"])
    weekly = weekly.groupby("week_start", as_index=False).agg(
        Revenue=("Revenue", "sum"),
        COGS=("COGS", "sum"),
        Gross_Profit=("Gross_Profit", "sum"),
        Margin=("Margin", "mean"),
        days_observed=("Date", "nunique"),
    )
    save_table(weekly, "06b_sales_weekly.csv")

    monthly = daily.copy()
    monthly["month"] = month_start(monthly["Date"])
    monthly = monthly.groupby("month", as_index=False).agg(
        Revenue=("Revenue", "sum"),
        COGS=("COGS", "sum"),
        Gross_Profit=("Gross_Profit", "sum"),
        Margin=("Margin", "mean"),
        days_observed=("Date", "nunique"),
    )
    monthly["Revenue_mom_pct"] = monthly["Revenue"].pct_change() * 100
    monthly["Gross_Profit_mom_pct"] = monthly["Gross_Profit"].pct_change() * 100
    save_table(monthly, "06b_sales_monthly.csv")

    yearly = daily.copy()
    yearly["year"] = yearly["Date"].dt.year
    yearly = yearly.groupby("year", as_index=False).agg(
        Revenue=("Revenue", "sum"),
        COGS=("COGS", "sum"),
        Gross_Profit=("Gross_Profit", "sum"),
        Margin=("Margin", "mean"),
        days_observed=("Date", "nunique"),
    )
    yearly["Revenue_yoy_pct"] = yearly["Revenue"].pct_change() * 100
    yearly["Gross_Profit_yoy_pct"] = yearly["Gross_Profit"].pct_change() * 100
    save_table(yearly, "06b_sales_yearly.csv")

    return daily, weekly, monthly, yearly


def build_orders_monthly(tables):
    if "orders" not in tables or "order_date" not in tables["orders"].columns:
        return pd.DataFrame()

    orders = tables["orders"].copy()
    orders["month"] = month_start(orders["order_date"])
    monthly = orders.groupby(["month", "order_status"], as_index=False).agg(
        orders=("order_id", "nunique")
    )
    save_table(monthly, "06b_order_status_monthly.csv")
    return monthly


def build_returns_monthly(tables):
    if "returns" not in tables or "return_date" not in tables["returns"].columns:
        return pd.DataFrame()

    returns = tables["returns"].copy()
    returns["month"] = month_start(returns["return_date"])
    monthly = returns.groupby("month", as_index=False).agg(
        return_rows=("return_id", "nunique"),
        returned_quantity=("return_quantity", "sum"),
        refund_amount=("refund_amount", "sum"),
    )
    save_table(monthly, "06b_returns_monthly.csv")
    return monthly


def build_return_rate_monthly(tables):
    if not {"orders", "returns"}.issubset(tables):
        out = pd.DataFrame()
        save_table(out, "06b_return_rate_monthly.csv")
        return out

    orders = tables["orders"].copy()
    returns = tables["returns"].copy()
    if "order_date" not in orders.columns or "return_date" not in returns.columns:
        out = pd.DataFrame()
        save_table(out, "06b_return_rate_monthly.csv")
        return out

    orders["month"] = month_start(orders["order_date"])
    orders_monthly = orders.groupby("month", as_index=False).agg(
        orders=("order_id", "nunique")
    )

    returns["return_month"] = month_start(returns["return_date"])
    returns_by_return_month = returns.groupby("return_month", as_index=False).agg(
        return_rows=("return_id", "nunique"),
        returned_orders=("order_id", "nunique"),
        returned_quantity=("return_quantity", "sum"),
        refund_amount=("refund_amount", "sum"),
    ).rename(columns={"return_month": "month"})

    returns_with_order_month = returns.merge(
        orders[["order_id", "month"]],
        on="order_id",
        how="left",
    )
    cohort_returns = returns_with_order_month.groupby("month", as_index=False).agg(
        cohort_return_rows=("return_id", "nunique"),
        cohort_returned_orders=("order_id", "nunique"),
        cohort_returned_quantity=("return_quantity", "sum"),
    )

    monthly = orders_monthly.merge(returns_by_return_month, on="month", how="left")
    monthly = monthly.merge(cohort_returns, on="month", how="left")
    fill_cols = [
        "return_rows",
        "returned_orders",
        "returned_quantity",
        "refund_amount",
        "cohort_return_rows",
        "cohort_returned_orders",
        "cohort_returned_quantity",
    ]
    monthly[fill_cols] = monthly[fill_cols].fillna(0)
    monthly["return_activity_rate_pct"] = monthly["returned_orders"] / monthly["orders"] * 100
    monthly["return_row_activity_rate_pct"] = monthly["return_rows"] / monthly["orders"] * 100
    monthly["cohort_return_rate_pct"] = monthly["cohort_returned_orders"] / monthly["orders"] * 100
    monthly["cohort_return_row_rate_pct"] = monthly["cohort_return_rows"] / monthly["orders"] * 100

    save_table(monthly, "06b_return_rate_monthly.csv")
    return monthly


def build_reviews_monthly(tables):
    if "reviews" not in tables or "review_date" not in tables["reviews"].columns:
        return pd.DataFrame()

    reviews = tables["reviews"].copy()
    reviews["month"] = month_start(reviews["review_date"])
    monthly = reviews.groupby("month", as_index=False).agg(
        reviews=("review_id", "nunique"),
        avg_rating=("rating", "mean"),
    )
    save_table(monthly, "06b_reviews_monthly.csv")
    return monthly


def build_web_daily(tables):
    if "web_traffic" not in tables or "date" not in tables["web_traffic"].columns:
        return pd.DataFrame()

    web = tables["web_traffic"].copy()
    daily = web.groupby("date", as_index=False).agg(
        sessions=("sessions", "sum"),
        unique_visitors=("unique_visitors", "sum"),
        page_views=("page_views", "sum"),
        bounce_rate=("bounce_rate", "mean"),
        avg_session_duration_sec=("avg_session_duration_sec", "mean"),
    )
    daily = daily.sort_values("date")
    daily["sessions_rolling_7d"] = daily["sessions"].rolling(7, min_periods=1).mean()
    daily["sessions_rolling_30d"] = daily["sessions"].rolling(30, min_periods=1).mean()
    daily["sessions_rolling_90d"] = daily["sessions"].rolling(90, min_periods=1).mean()
    save_table(daily, "06b_web_traffic_daily.csv")
    return daily


def build_web_monthly(web_daily):
    if web_daily is None or web_daily.empty:
        out = pd.DataFrame()
        save_table(out, "06b_web_traffic_monthly.csv")
        return out

    monthly = web_daily.copy()
    monthly["month"] = month_start(monthly["date"])
    monthly = monthly.groupby("month", as_index=False).agg(
        sessions=("sessions", "sum"),
        unique_visitors=("unique_visitors", "sum"),
        page_views=("page_views", "sum"),
        bounce_rate=("bounce_rate", "mean"),
        avg_session_duration_sec=("avg_session_duration_sec", "mean"),
        days_observed=("date", "nunique"),
    )
    monthly["sessions_mom_pct"] = monthly["sessions"].pct_change() * 100
    save_table(monthly, "06b_web_traffic_monthly.csv")
    return monthly


def build_inventory_monthly(tables):
    if "inventory" not in tables or "snapshot_date" not in tables["inventory"].columns:
        return pd.DataFrame()

    inventory = tables["inventory"].copy()
    inventory["month"] = month_start(inventory["snapshot_date"])
    monthly = inventory.groupby("month", as_index=False).agg(
        stock_on_hand=("stock_on_hand", "sum"),
        units_sold=("units_sold", "sum"),
        stockout_days=("stockout_days", "sum"),
        fill_rate=("fill_rate", "mean"),
        sell_through_rate=("sell_through_rate", "mean"),
    )
    save_table(monthly, "06b_inventory_monthly.csv")
    return monthly


def plot_line(df, x, y_columns, title, ylabel, filename):
    if df is None or df.empty:
        return None
    if any(col not in df.columns for col in [x] + y_columns):
        return None

    fig, ax = plt.subplots(figsize=(14, 4.5))
    for y in y_columns:
        ax.plot(df[x], df[y], label=y, linewidth=1.4)
    ax.set_title(title)
    ax.set_xlabel(x)
    ax.set_ylabel(ylabel)
    ax.legend()
    return save_figure(fig, filename)


def compact_number(value, _position=None):
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.0f}M"
    if abs_value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def plot_sales_daily_rolling(df):
    required = {"Date", "Revenue", "Revenue_rolling_7d", "Revenue_rolling_30d"}
    if df is None or df.empty or not required.issubset(df.columns):
        return None

    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.plot(
        df["Date"],
        df["Revenue"],
        label="Daily Revenue",
        linewidth=0.55,
        alpha=0.18,
        color="#64748b",
    )
    ax.plot(
        df["Date"],
        df["Revenue_rolling_7d"],
        label="7d rolling avg",
        linewidth=1.15,
        alpha=0.85,
        color="#f97316",
    )
    ax.plot(
        df["Date"],
        df["Revenue_rolling_30d"],
        label="30d rolling avg",
        linewidth=2.2,
        color="#2563eb",
    )

    ax.set_title("Daily Revenue Trend with 7d and 30d Rolling Averages", weight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax.legend(loc="upper left", ncol=3, frameon=True)
    return save_figure(fig, "06b_sales_daily_rolling.png")


def plot_sales_monthly(df):
    required = {"month", "Revenue", "COGS", "Gross_Profit", "Margin"}
    if df is None or df.empty or not required.issubset(df.columns):
        return None

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(14, 7),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.4], "hspace": 0.08},
    )

    ax_top.plot(df["month"], df["Revenue"], label="Revenue", linewidth=2.0, color="#2563eb")
    ax_top.plot(df["month"], df["COGS"], label="COGS", linewidth=1.8, color="#f97316")
    ax_top.fill_between(
        df["month"],
        df["COGS"],
        df["Revenue"],
        where=df["Revenue"] >= df["COGS"],
        color="#22c55e",
        alpha=0.12,
        interpolate=True,
    )
    ax_top.fill_between(
        df["month"],
        df["COGS"],
        df["Revenue"],
        where=df["Revenue"] < df["COGS"],
        color="#ef4444",
        alpha=0.12,
        interpolate=True,
    )
    ax_top.set_title("Monthly Sales: Revenue, COGS, Profit, and Margin", weight="bold")
    ax_top.set_ylabel("Revenue / COGS")
    ax_top.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax_top.legend(loc="upper left", ncol=2, frameon=True)

    profit_colors = ["#16a34a" if value >= 0 else "#dc2626" for value in df["Gross_Profit"]]
    ax_bottom.bar(
        df["month"],
        df["Gross_Profit"],
        width=22,
        color=profit_colors,
        alpha=0.75,
        label="Gross Profit",
    )
    ax_bottom.axhline(0, color="#334155", linewidth=0.9)
    ax_bottom.set_ylabel("Gross Profit")
    ax_bottom.yaxis.set_major_formatter(FuncFormatter(compact_number))

    ax_margin = ax_bottom.twinx()
    ax_margin.plot(
        df["month"],
        df["Margin"] * 100,
        label="Margin %",
        linewidth=1.8,
        color="#7c3aed",
    )
    ax_margin.set_ylabel("Margin (%)")
    ax_margin.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}%"))

    lines_1, labels_1 = ax_bottom.get_legend_handles_labels()
    lines_2, labels_2 = ax_margin.get_legend_handles_labels()
    ax_bottom.legend(
        lines_1 + lines_2,
        labels_1 + labels_2,
        loc="upper left",
        ncol=2,
        frameon=True,
        fontsize=9,
    )
    ax_bottom.set_xlabel("Month")

    return save_figure(fig, "06b_sales_monthly.png")


def plot_orders_monthly(df):
    if df.empty:
        return None
    pivot = df.pivot(index="month", columns="order_status", values="orders").fillna(0)
    delivered = pivot["delivered"] if "delivered" in pivot.columns else None
    other_cols = [col for col in pivot.columns if col != "delivered"]

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(14, 6.5),
        sharex=True,
        gridspec_kw={"height_ratios": [2.2, 1.4], "hspace": 0.08},
    )

    if delivered is not None:
        ax_top.plot(
            pivot.index,
            delivered,
            color="#16a34a",
            linewidth=2.0,
            label="delivered",
        )
        ax_top.fill_between(pivot.index, delivered, color="#16a34a", alpha=0.12)
    ax_top.set_title("Monthly Orders by Status", weight="bold")
    ax_top.set_ylabel("Delivered orders")
    ax_top.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax_top.legend(loc="upper left", frameon=True)

    colors = ["#2563eb", "#f97316", "#7c3aed", "#dc2626", "#64748b"]
    for color, col in zip(colors, other_cols):
        ax_bottom.plot(pivot.index, pivot[col], linewidth=1.5, label=col, color=color)
    ax_bottom.set_ylabel("Other statuses")
    ax_bottom.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax_bottom.legend(loc="upper left", ncol=3, frameon=True, fontsize=9)
    ax_bottom.set_xlabel("Month")
    return save_figure(fig, "06b_orders_monthly.png")


def plot_web_sessions_daily(df):
    if df is None or df.empty:
        return None

    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(
        df["date"],
        df["sessions"],
        label="daily sessions",
        linewidth=0.55,
        alpha=0.18,
        color="#4c78a8",
    )
    ax.plot(
        df["date"],
        df["sessions_rolling_7d"],
        label="7d rolling avg",
        linewidth=1.15,
        alpha=0.85,
        color="#f28e2b",
    )
    ax.plot(
        df["date"],
        df["sessions_rolling_30d"],
        label="30d rolling avg",
        linewidth=2.2,
        color="#2563eb",
    )
    ax.set_title("Daily Web Sessions Trend with 7d and 30d Rolling Averages", weight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Sessions")
    ax.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax.legend(loc="upper left", ncol=3, frameon=True)
    return save_figure(fig, "06b_web_sessions_daily.png")


def plot_web_sessions_monthly(df):
    if df is None or df.empty:
        return None

    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.plot(df["month"], df["sessions"], linewidth=1.6, color="#4c78a8")
    ax.scatter(df["month"], df["sessions"], s=16, color="#4c78a8", alpha=0.75)
    ax.set_title("Monthly web sessions")
    ax.set_xlabel("Month")
    ax.set_ylabel("Sessions")
    return save_figure(fig, "06b_web_sessions_monthly.png")


def plot_return_rates_monthly(df):
    if df.empty:
        return None

    fig, ax = plt.subplots(figsize=(14, 4.8))
    ax.plot(
        df["month"],
        df["cohort_return_rate_pct"],
        label="Cohort return rate",
        linewidth=2.2,
        color="#2563eb",
    )
    ax.scatter(
        df["month"],
        df["cohort_return_rate_pct"],
        s=14,
        color="#2563eb",
        alpha=0.75,
    )
    ax.plot(
        df["month"],
        df["return_activity_rate_pct"],
        label="Return activity rate",
        linewidth=1.3,
        alpha=0.65,
        linestyle="--",
        color="#f97316",
    )
    ax.set_title("Monthly Return Rates", weight="bold")
    ax.set_xlabel("Month")
    ax.set_ylabel("Returned orders / orders (%)")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}%"))
    ax.legend(loc="upper left", ncol=2, frameon=True)
    return save_figure(fig, "06b_returns_monthly.png")


def plot_inventory_rates(df):
    required = {"month", "fill_rate", "sell_through_rate"}
    if df is None or df.empty or not required.issubset(df.columns):
        return None

    fig, (ax_top, ax_bottom) = plt.subplots(
        2,
        1,
        figsize=(14, 6.2),
        sharex=True,
        gridspec_kw={"height_ratios": [1.5, 1.5], "hspace": 0.08},
    )

    ax_top.plot(df["month"], df["fill_rate"] * 100, linewidth=2.0, color="#2563eb")
    ax_top.scatter(df["month"], df["fill_rate"] * 100, s=12, color="#2563eb", alpha=0.7)
    ax_top.set_title("Monthly Inventory Rates", weight="bold")
    ax_top.set_ylabel("Fill rate (%)")
    ax_top.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}%"))

    fill_min = df["fill_rate"].min() * 100
    fill_max = df["fill_rate"].max() * 100
    padding = max((fill_max - fill_min) * 0.35, 1.0)
    ax_top.set_ylim(fill_min - padding, fill_max + padding)

    ax_bottom.plot(
        df["month"],
        df["sell_through_rate"] * 100,
        linewidth=1.8,
        color="#f97316",
    )
    ax_bottom.scatter(
        df["month"],
        df["sell_through_rate"] * 100,
        s=12,
        color="#f97316",
        alpha=0.7,
    )
    ax_bottom.set_ylabel("Sell-through (%)")
    ax_bottom.set_xlabel("Month")
    ax_bottom.yaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:.0f}%"))
    return save_figure(fig, "06b_inventory_monthly.png")


def dataframe_to_markdown(df):
    if df is None or df.empty:
        return "*No rows.*"
    return df.to_markdown(index=False)


def generate_report(coverage, sales_daily, sales_monthly, sales_yearly, return_rate_monthly):
    sales_row = coverage[coverage["table"] == "sales"].head(1)
    sample_row = coverage[coverage["table"] == "sample_submission"].head(1)

    if not sales_row.empty:
        sales_start = sales_row.iloc[0]["min_date"]
        sales_end = sales_row.iloc[0]["max_date"]
        sales_missing_days = sales_row.iloc[0]["missing_days_between_min_max"]
    else:
        sales_start = "N/A"
        sales_end = "N/A"
        sales_missing_days = "N/A"

    if not sample_row.empty:
        sample_start = sample_row.iloc[0]["min_date"]
        sample_end = sample_row.iloc[0]["max_date"]
    else:
        sample_start = "N/A"
        sample_end = "N/A"

    monthly_tail = (
        sales_monthly[["month", "Revenue", "COGS", "Gross_Profit", "Margin", "Revenue_mom_pct"]]
        .tail(12)
        if sales_monthly is not None and not sales_monthly.empty
        else pd.DataFrame()
    )
    yearly_summary = (
        sales_yearly[["year", "Revenue", "COGS", "Gross_Profit", "Margin", "Revenue_yoy_pct"]]
        if sales_yearly is not None and not sales_yearly.empty
        else pd.DataFrame()
    )
    recent_return_rates = (
        return_rate_monthly[
            [
                "month",
                "orders",
                "returned_orders",
                "return_activity_rate_pct",
                "cohort_returned_orders",
                "cohort_return_rate_pct",
            ]
        ].tail(12)
        if return_rate_monthly is not None and not return_rate_monthly.empty
        else pd.DataFrame()
    )

    report = f"""# Time Trend Analysis (06b)

## Overview

| Metric | Value |
|---|---|
| Sales date range | {sales_start} to {sales_end} |
| Sales missing days between min/max | {sales_missing_days} |
| Sample submission date range | {sample_start} to {sample_end} |
| Sales daily rows | {0 if sales_daily is None else len(sales_daily)} |

## Recent Monthly Sales

{dataframe_to_markdown(monthly_tail)}

## Yearly Sales

{dataframe_to_markdown(yearly_summary)}

## Recent Monthly Return Rates

{dataframe_to_markdown(recent_return_rates)}

## Notes

- `sales.csv` is the central table for Revenue/COGS trend analysis.
- Daily, weekly, monthly, and yearly summaries are saved separately.
- Other dated tables are summarized at their own grain; no broad joins are used.
- Return rate uses two views: `return_activity_rate_pct` by return month, and `cohort_return_rate_pct` by original order month.
- `refund_amount` remains in `06b_returns_monthly.csv` as financial impact, but the return trend chart uses rates.
- This step describes trend and seasonality candidates only; it does not build forecasts.
"""
    save_report(report, "06b_time_trend_summary.md")


def main():
    print("Loading tables for time trend analysis...")
    tables = load_tables(names=list(DATE_CHECKS), parse_dates=True)
    print(f"Loaded {len(tables)} tables.")

    print("Summarizing date coverage...")
    coverage = summarize_coverage(tables)

    print("Building sales time tables...")
    sales_daily, sales_weekly, sales_monthly, sales_yearly = build_sales_time_tables(tables)

    print("Building non-sales time summaries...")
    orders_monthly = build_orders_monthly(tables)
    returns_monthly = build_returns_monthly(tables)
    return_rate_monthly = build_return_rate_monthly(tables)
    build_reviews_monthly(tables)
    web_daily = build_web_daily(tables)
    web_monthly = build_web_monthly(web_daily)
    inventory_monthly = build_inventory_monthly(tables)

    print("Creating figures...")
    plot_sales_daily_rolling(sales_daily)
    plot_sales_monthly(sales_monthly)
    plot_orders_monthly(orders_monthly)
    plot_return_rates_monthly(return_rate_monthly)
    plot_web_sessions_daily(web_daily)
    plot_web_sessions_monthly(web_monthly)
    plot_inventory_rates(inventory_monthly)

    print("Generating markdown report...")
    generate_report(coverage, sales_daily, sales_monthly, sales_yearly, return_rate_monthly)

    print("06b time trend analysis done!")


if __name__ == "__main__":
    main()
