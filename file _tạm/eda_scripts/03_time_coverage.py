"""
Mục tiêu:
    Kiểm tra phạm vi thời gian của các bảng có cột ngày và vẽ timeline sơ khởi.

Input:
    - Các file CSV trong data/.
    - DATE_COLUMNS khai báo trong eda_scripts/config.py.

Quy trình:
    - Load dữ liệu và parse các cột ngày.
    - Tính min_date, max_date, missing_dates, unique_dates cho từng cột ngày.
    - Vẽ Revenue theo ngày từ sales.csv.
    - Vẽ sessions theo ngày từ web_traffic.csv nếu có.

Output:
    - outputs/eda_initial/tables/03_date_ranges.csv
    - outputs/eda_initial/figures/03_sales_revenue_timeline.png
    - outputs/eda_initial/figures/03_web_sessions_timeline.png
"""

import matplotlib.pyplot as plt
import pandas as pd

from config import DATE_COLUMNS, load_tables, save_figure, save_table


def main():
    tables = load_tables(parse_dates=True)
    rows = []

    for table, columns in DATE_COLUMNS.items():
        if table not in tables:
            continue
        df = tables[table]
        for col in columns:
            if col not in df.columns:
                continue
            rows.append(
                {
                    "table": table,
                    "date_column": col,
                    "min_date": df[col].min(),
                    "max_date": df[col].max(),
                    "missing_dates": int(df[col].isna().sum()),
                    "unique_dates": int(df[col].nunique(dropna=True)),
                }
            )

    save_table(pd.DataFrame(rows), "03_date_ranges.csv")

    if "sales" in tables and {"Date", "Revenue"}.issubset(tables["sales"].columns):
        sales = tables["sales"].sort_values("Date")
        fig, ax = plt.subplots(figsize=(14, 4))
        ax.plot(sales["Date"], sales["Revenue"], linewidth=1)
        ax.set_title("Daily Revenue over time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Revenue")
        save_figure(fig, "03_sales_revenue_timeline.png")

    if "web_traffic" in tables and {"date", "sessions"}.issubset(tables["web_traffic"].columns):
        web = tables["web_traffic"].copy()
        web_daily = web.groupby("date", as_index=False)["sessions"].sum().sort_values("date")
        fig, ax = plt.subplots(figsize=(14, 4))
        ax.plot(web_daily["date"], web_daily["sessions"], linewidth=1)
        ax.set_title("Daily web sessions over time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Sessions")
        save_figure(fig, "03_web_sessions_timeline.png")


if __name__ == "__main__":
    main()
    
    print("time coverage done!")
