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
    - outputs/tables/06b_reviews_monthly.csv
    - outputs/tables/06b_web_traffic_daily.csv
    - outputs/tables/06b_inventory_monthly.csv
    - outputs/reports/06b_time_trend_summary.md
    - outputs/figures/06b_sales_daily_rolling.png
    - outputs/figures/06b_sales_monthly.png
    - outputs/figures/06b_orders_monthly.png
    - outputs/figures/06b_returns_monthly.png
    - outputs/figures/06b_web_sessions_daily.png
    - outputs/figures/06b_inventory_monthly.png
"""

import matplotlib.pyplot as plt
import pandas as pd

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
    save_table(daily, "06b_web_traffic_daily.csv")
    return daily


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


def plot_orders_monthly(df):
    if df.empty:
        return None
    pivot = df.pivot(index="month", columns="order_status", values="orders").fillna(0)
    fig, ax = plt.subplots(figsize=(14, 4.5))
    pivot.plot(ax=ax, linewidth=1.3)
    ax.set_title("Monthly orders by status")
    ax.set_xlabel("Month")
    ax.set_ylabel("Orders")
    return save_figure(fig, "06b_orders_monthly.png")


def dataframe_to_markdown(df):
    if df is None or df.empty:
        return "*No rows.*"
    return df.to_markdown(index=False)


def generate_report(coverage, sales_daily, sales_monthly, sales_yearly):
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

## Notes

- `sales.csv` is the central table for Revenue/COGS trend analysis.
- Daily, weekly, monthly, and yearly summaries are saved separately.
- Other dated tables are summarized at their own grain; no broad joins are used.
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
    build_reviews_monthly(tables)
    web_daily = build_web_daily(tables)
    inventory_monthly = build_inventory_monthly(tables)

    print("Creating figures...")
    plot_line(
        sales_daily,
        "Date",
        ["Revenue", "Revenue_rolling_7d", "Revenue_rolling_30d"],
        "Daily sales revenue with rolling averages",
        "Revenue",
        "06b_sales_daily_rolling.png",
    )
    plot_line(
        sales_monthly,
        "month",
        ["Revenue", "COGS", "Gross_Profit"],
        "Monthly sales metrics",
        "Value",
        "06b_sales_monthly.png",
    )
    plot_orders_monthly(orders_monthly)
    plot_line(
        returns_monthly,
        "month",
        ["return_rows", "refund_amount"],
        "Monthly returns",
        "Count / amount",
        "06b_returns_monthly.png",
    )
    plot_line(
        web_daily,
        "date",
        ["sessions", "sessions_rolling_7d", "sessions_rolling_30d"],
        "Daily web sessions with rolling averages",
        "Sessions",
        "06b_web_sessions_daily.png",
    )
    plot_line(
        inventory_monthly,
        "month",
        ["fill_rate", "sell_through_rate"],
        "Monthly inventory rates",
        "Rate",
        "06b_inventory_monthly.png",
    )

    print("Generating markdown report...")
    generate_report(coverage, sales_daily, sales_monthly, sales_yearly)

    print("06b time trend analysis done!")


if __name__ == "__main__":
    main()
