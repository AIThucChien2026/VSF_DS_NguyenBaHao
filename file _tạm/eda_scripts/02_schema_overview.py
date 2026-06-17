"""
Mục tiêu:
    Kiểm tra schema sơ khởi: cột nào có trong từng bảng, dtype, missing, unique.

Input:
    - Tất cả file CSV trong data/.

Quy trình:
    - Load toàn bộ bảng.
    - Với từng cột, tính dtype, non_null, missing, missing_pct, unique_values.

Output:
    - outputs/eda_initial/tables/02_schema_overview.csv
"""

import pandas as pd

from config import load_tables, save_table, table_group


def sample_values(series, n=3):
    values = series.dropna().astype(str).head(n).tolist()
    return " | ".join(values)


def main():
    tables = load_tables(parse_dates=False)
    dtype_rows = []

    for name, df in sorted(tables.items()):
        for col in df.columns:
            missing = int(df[col].isna().sum())
            dtype_rows.append(
                {
                    "table": name,
                    "group": table_group(name),
                    "column": col,
                    "dtype": str(df[col].dtype),
                    "non_null": int(df[col].notna().sum()),
                    "missing": missing,
                    "missing_pct": round(missing / len(df) * 100, 3) if len(df) else 0,
                    "unique_values": int(df[col].nunique(dropna=True)),
                    "sample_values": sample_values(df[col]),
                }
            )

    save_table(pd.DataFrame(dtype_rows), "02_schema_overview.csv")


if __name__ == "__main__":
    main()
    print("schema overview done!")
