"""
Check whether any date column has values after 31/12/2021.

Output:
    - outputs/tables/check_dates_after_2021.csv
"""

import pandas as pd

from config import DATE_COLUMNS, load_tables, save_table


def check_dates_after_cutoff(tables, cutoff_date="31/12/2022"):
    cutoff = pd.to_datetime(cutoff_date, dayfirst=True, errors="coerce")
    rows = []

    for table, columns in DATE_COLUMNS.items():
        if table not in tables:
            continue

        df = tables[table]
        for col in columns:
            if col not in df.columns:
                continue

            after_cutoff = df[col] > cutoff
            rows.append(
                {
                    "table": table,
                    "date_column": col,
                    "cutoff_date": cutoff,
                    "min_date": df[col].min(),
                    "max_date": df[col].max(),
                    "rows_after_cutoff": int(after_cutoff.sum()),
                    "has_date_after_cutoff": bool(after_cutoff.any()),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    return result.sort_values(
        ["has_date_after_cutoff", "rows_after_cutoff", "table", "date_column"],
        ascending=[False, False, True, True],
    )


def main():
    tables = load_tables(parse_dates=True)
    result = check_dates_after_cutoff(tables, cutoff_date="31/12/2021")
    save_table(result, "check_dates_after_2021.csv")

    total_rows = int(result["rows_after_cutoff"].sum()) if not result.empty else 0
    total_columns = int(result["has_date_after_cutoff"].sum()) if not result.empty else 0

    print(f"Columns with date after 2021-12-31: {total_columns}")
    print(f"Rows with date after 2021-12-31: {total_rows}")
    print("Saved: outputs/tables/check_dates_after_2021.csv")


if __name__ == "__main__":
    main()
