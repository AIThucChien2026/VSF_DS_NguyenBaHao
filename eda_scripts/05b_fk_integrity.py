"""
Mục tiêu:
    Kiểm tra referential integrity giữa các bảng — FK có trỏ đúng sang PK không.
    Phát hiện orphan records: các row có FK không tồn tại trong bảng tham chiếu.

Input:
    - data/order_items.csv
    - data/orders.csv
    - data/products.csv
    - data/customers.csv
    - data/promotions.csv
    - data/geography.csv
    - data/returns.csv
    - data/reviews.csv
    - data/payments.csv
    - data/shipments.csv
    - data/inventory.csv

Quy trình:
    - Định nghĩa danh sách FK_CHECKS: mỗi entry gồm
      (child_table, fk_column, parent_table, pk_column, nullable).
    - Với mỗi entry: tìm các giá trị FK không có trong tập PK tương ứng.
    - Tính orphan_count và orphan_pct cho từng relationship.
    - Lưu chi tiết các row orphan và bảng tổng hợp.
    - Đặc biệt lưu ý: order_items.promo_id và promo_id_2 là nullable,
      chỉ check các row không null.

Output:
    - outputs/tables/05b_fk_violations.csv        ← chi tiết row orphan theo relationship
    - outputs/tables/05b_fk_summary.csv           ← orphan_count + orphan_pct mỗi FK
    - outputs/reports/05b_fk_summary.md           ← tóm tắt dạng text
"""

import pandas as pd

from config import load_tables, save_report, save_table


# (child_table, fk_column, parent_table, pk_column, nullable)
FK_CHECKS = [
    ("orders",      "customer_id", "customers",  "customer_id", False),
    ("orders",      "zip",         "geography",   "zip",         False),
    ("order_items", "order_id",    "orders",      "order_id",    False),
    ("order_items", "product_id",  "products",    "product_id",  False),
    ("order_items", "promo_id",    "promotions",  "promo_id",    True),   # nullable
    ("order_items", "promo_id_2",  "promotions",  "promo_id",    True),   # nullable
    ("payments",    "order_id",    "orders",      "order_id",    False),
    ("shipments",   "order_id",    "orders",      "order_id",    False),
    ("returns",     "order_id",    "orders",      "order_id",    False),
    ("returns",     "product_id",  "products",    "product_id",  False),
    ("reviews",     "order_id",    "orders",      "order_id",    False),
    ("reviews",     "product_id",  "products",    "product_id",  False),
    ("inventory",   "product_id",  "products",    "product_id",  False),
]


def run_fk_checks(tables):
    all_orphans  = []
    summary_rows = []

    for child_t, fk_col, parent_t, pk_col, nullable in FK_CHECKS:
        if child_t not in tables or parent_t not in tables:
            print(f"  [SKIP] {child_t} hoặc {parent_t} không có trong dữ liệu.")
            continue

        if fk_col not in tables[child_t].columns:
            print(f"  [WARN] Cột {fk_col} không tồn tại trong {child_t} — bỏ qua.")
            continue

        child_df  = tables[child_t].copy()
        parent_pk = set(tables[parent_t][pk_col].dropna())

        # Nullable FK: chỉ check các row không null
        check_df = child_df[child_df[fk_col].notna()].copy() if nullable else child_df.copy()
        n_checked = len(check_df)

        if n_checked == 0:
            orphan_df         = pd.DataFrame()
            n_orphan          = 0
            unique_orphan_keys = 0
        else:
            is_orphan          = ~check_df[fk_col].isin(parent_pk)
            orphan_df          = check_df[is_orphan].copy()
            n_orphan           = int(is_orphan.sum())
            unique_orphan_keys = int(orphan_df[fk_col].nunique()) if not orphan_df.empty else 0

        # Gắn meta vào orphan rows
        if not orphan_df.empty:
            orphan_df["_child_table"]  = child_t
            orphan_df["_fk_column"]    = fk_col
            orphan_df["_parent_table"] = parent_t
            orphan_df["_pk_column"]    = pk_col
            all_orphans.append(orphan_df)

        summary_rows.append({
            "child_table":         child_t,
            "fk_column":           fk_col,
            "parent_table":        parent_t,
            "pk_column":           pk_col,
            "nullable":            nullable,
            "checked_rows":        n_checked,
            "orphan_rows":         n_orphan,
            "unique_orphan_keys":  unique_orphan_keys,
            "orphan_pct":          round(n_orphan / n_checked * 100, 4) if n_checked else 0,
            "percent_valid":       round((n_checked - n_orphan) / n_checked * 100, 4) if n_checked else 100.0,
            "status":              "FAIL" if n_orphan > 0 else "PASS",
        })

    # Ghép toàn bộ orphan rows, đưa meta lên đầu
    if all_orphans:
        df_violations = pd.concat(all_orphans, ignore_index=True)
        meta_cols  = ["_child_table", "_fk_column", "_parent_table", "_pk_column"]
        other_cols = [c for c in df_violations.columns if c not in meta_cols]
        df_violations = df_violations[meta_cols + other_cols]
    else:
        df_violations = pd.DataFrame()

    df_summary = pd.DataFrame(summary_rows)
    return df_violations, df_summary


def generate_markdown_report(df_summary):
    total     = len(df_summary)
    passed    = int((df_summary["status"] == "PASS").sum())
    failed    = int((df_summary["status"] == "FAIL").sum())
    total_orp = int(df_summary["orphan_rows"].sum())

    fail_md = (
        df_summary[df_summary["status"] == "FAIL"].to_markdown(index=False)
        if failed > 0
        else "*Tất cả FK relationships đều hợp lệ — không có orphan record.*"
    )
    pass_md = df_summary[df_summary["status"] == "PASS"][
        ["child_table", "fk_column", "parent_table", "pk_column", "checked_rows"]
    ].to_markdown(index=False)

    report = f"""# Báo cáo FK Integrity (05b)

Kiểm tra toàn vẹn tham chiếu (referential integrity) cho tất cả quan hệ FK → PK.
Nullable FK (`promo_id`, `promo_id_2`) chỉ check các row không null — null là hợp lệ nghiệp vụ.

---

## Tổng quan

| Chỉ số | Giá trị |
|---|---|
| Tổng số FK relationships kiểm tra | {total} |
| Relationships PASS | {passed} |
| Relationships FAIL | {failed} |
| Tổng orphan rows phát hiện | {total_orp:,} |

---

## FK vi phạm (FAIL) — Orphan records

{fail_md}

---

## FK hợp lệ (PASS)

{pass_md}

---

## Khuyến nghị xử lý

- Chi tiết orphan rows lưu trong `05b_fk_violations.csv` kèm `_child_table`, `_fk_column` để truy vết.
- Nếu `percent_valid < 100%`: kiểm tra ETL/nguồn dữ liệu trước khi join —
  orphan rows sẽ bị drop khi INNER JOIN.
- Nếu cần giữ orphan rows: dùng LEFT JOIN và xử lý null sau join.
- Nullable FK (`promo_id`, `promo_id_2`): null không tính là orphan, đây là hành vi đúng nghiệp vụ.
"""
    save_report(report, "05b_fk_summary.md")


def main():
    print("Loading tables...")
    tables = load_tables(
        names=[
            "order_items", "orders", "products", "customers",
            "promotions", "geography", "returns", "reviews",
            "payments", "shipments", "inventory",
        ],
        parse_dates=False,
    )
    print(f"Loaded {len(tables)} tables.")

    print("Running FK integrity checks...")
    df_violations, df_summary = run_fk_checks(tables)

    print("Saving outputs...")
    save_table(df_violations, "05b_fk_violations.csv")
    save_table(df_summary,    "05b_fk_summary.csv")

    print("Generating markdown report...")
    generate_markdown_report(df_summary)

    n_fail = int((df_summary["status"] == "FAIL").sum())
    print(f"05b FK integrity done! {n_fail}/{len(df_summary)} relationships FAIL.")


if __name__ == "__main__":
    main()

    print("05b FK integrity completed!")