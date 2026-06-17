"""
Mục tiêu:
    Hiểu nhanh các key candidate và bản đồ join giữa các bảng.

Input:
    - Tất cả file CSV trong data/.
    - Danh sách KEY_CANDIDATES khai báo trong file này.

Quy trình:
    - Tính rows, non_null, unique cho các cột khóa tiềm năng.
    - Tính duplicate_count_if_key để nhận diện cột nào không phải primary key đơn.
    - Lưu relationship notes và join map dạng Markdown.

Output:
    - outputs/tables/05a_key_summary.csv
    - outputs/tables/05a_relationship_notes.csv
    - outputs/reports/05a_join_map.md
"""

import pandas as pd

from config import REPORT_DIR, load_tables, save_report, save_table


KEY_CANDIDATES = {
    "products": ["product_id"],
    "customers": ["customer_id"],
    "geography": ["zip"],
    "promotions": ["promo_id"],
    "orders": ["order_id", "customer_id", "zip"],
    "order_items": ["order_id", "product_id", "promo_id", "promo_id_2"],
    "payments": ["order_id"],
    "shipments": ["order_id"],
    "returns": ["return_id", "order_id", "product_id"],
    "reviews": ["review_id", "order_id", "product_id", "customer_id"],
    "inventory": ["snapshot_date", "product_id"],
    "sales": ["Date"],
    "sample_submission": ["Date"],
    "web_traffic": ["date", "traffic_source"],
}

RELATIONSHIP_NOTES = [
    {"from": "products.product_id", "to": "order_items.product_id", "note": "product-level to item-level"},
    {"from": "products.product_id", "to": "returns.product_id", "note": "product-level to return records"},
    {"from": "products.product_id", "to": "reviews.product_id", "note": "product-level to review records"},
    {"from": "products.product_id", "to": "inventory.product_id", "note": "product-level to monthly inventory"},
    {"from": "customers.customer_id", "to": "orders.customer_id", "note": "customer-level to orders"},
    {"from": "customers.customer_id", "to": "reviews.customer_id", "note": "customer-level to reviews"},
    {"from": "geography.zip", "to": "customers.zip", "note": "zip to customer city/region"},
    {"from": "geography.zip", "to": "orders.zip", "note": "zip to delivery region"},
    {"from": "orders.order_id", "to": "order_items.order_id", "note": "order-level to item-level; can multiply rows"},
    {"from": "orders.order_id", "to": "payments.order_id", "note": "expected order-level payment"},
    {"from": "orders.order_id", "to": "shipments.order_id", "note": "shipping information"},
    {"from": "orders.order_id", "to": "returns.order_id", "note": "returns can be multiple per order"},
    {"from": "orders.order_id", "to": "reviews.order_id", "note": "reviews can be multiple per order"},
    {"from": "promotions.promo_id", "to": "order_items.promo_id", "note": "first promotion on item line"},
    {"from": "promotions.promo_id", "to": "order_items.promo_id_2", "note": "second promotion on item line"},
]


def main():
    tables = load_tables(parse_dates=False)
    rows = []

    for table, columns in KEY_CANDIDATES.items():
        if table not in tables:
            continue
        df = tables[table]
        for col in columns:
            if col not in df.columns:
                continue
            rows.append(
                {
                    "table": table,
                    "column": col,
                    "rows": len(df),
                    "non_null": int(df[col].notna().sum()),
                    "unique": int(df[col].nunique(dropna=True)),
                    "duplicate_count_if_key": int(df.duplicated(subset=[col]).sum()),
                }
            )

    save_table(pd.DataFrame(rows), "05a_key_summary.csv")
    save_table(pd.DataFrame(RELATIONSHIP_NOTES), "05a_relationship_notes.csv")

    report = """# Join map

products.product_id -> order_items.product_id, returns.product_id, reviews.product_id, inventory.product_id
customers.customer_id -> orders.customer_id, reviews.customer_id
geography.zip -> customers.zip, orders.zip
orders.order_id -> order_items.order_id, payments.order_id, shipments.order_id, returns.order_id, reviews.order_id
promotions.promo_id -> order_items.promo_id, order_items.promo_id_2

## Notes

- Do not join every table at once.
- Joining orders to order_items changes granularity from order-level to item-level.
- Aggregate many-row tables before order-level analysis.
- Use sales.csv as the central table for forecasting exploration.
"""
    save_report(report, "05a_join_map.md")


if __name__ == "__main__":
    main()

    print("05a key join overview completed!")
