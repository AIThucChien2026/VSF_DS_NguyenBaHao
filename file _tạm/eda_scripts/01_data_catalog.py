"""
Mục tiêu:
    Lập catalog tổng quan để biết bộ dữ liệu đang có những bảng nào.

Input:
    - Tất cả file CSV trong data/.

Quy trình:
    - Load toàn bộ CSV bằng load_tables().
    - Lấy số dòng, số cột, memory_mb, danh sách cột.
    - Ghi thêm file text liệt kê nhanh các bảng.

Output:
    - outputs/eda_initial/tables/01_data_catalog.csv
    - outputs/eda_initial/reports/01_file_list.txt
"""

import pandas as pd

from config import DATA_DIR, EXPECTED_TABLES, REPORT_DIR, table_group, load_tables, save_table


def main():
    tables = load_tables(parse_dates=False)
    rows = []
    for name, df in tables.items():
        rows.append(
            {
                "table": name,
                "group": table_group(name),
                "rows": len(df),
                "columns": df.shape[1],
                "columns_names": ", ".join(df.columns),
            }
        )

    catalog = sorted(rows, key=lambda row: row["table"])
    save_table(pd.DataFrame(catalog), "01_data_catalog.csv")

    file_list = ["# File list", ""]
    for row in catalog:
        file_list.append(f"- {row['table']}: {row['rows']} rows, {row['columns']} columns")
    (REPORT_DIR / "01_file_list.txt").write_text("\n".join(file_list), encoding="utf-8")


if __name__ == "__main__":
    main()
    print("data catalog done!")
