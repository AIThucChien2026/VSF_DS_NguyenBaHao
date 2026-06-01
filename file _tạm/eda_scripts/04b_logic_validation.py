"""
Muc tieu:
    Kiem tra cac rule logic nghiep vu tren tung bang va giua cac bang de
    phat hien nhung dong du lieu bat thuong hoac khong hop le.

Input:
    - Cac bang du lieu duoc nap bang load_tables() tu cau hinh trong config.py.
    - Khoang ngay hop le DATE_MIN, DATE_MAX.

Quy trinh:
    - Chay cac rule logic tren tung bang, vi du gia tri duong, ngay hop le,
      discount khong vuot qua gia tri hang, rating nam trong [1, 5].
    - Chay cac cross-table check can noi nhieu bang, vi du payments so voi
      order_items va shipments so voi orders.
    - Tong hop danh sach dong vi pham va summary PASS/FAIL cho tung rule.

Output:
    - outputs/tables/04b_logic_violations.csv
    - outputs/tables/04b_logic_summary.csv
"""

import pandas as pd

from config import DATE_MAX, DATE_MIN, load_tables, save_table


DATE_MIN_TS = pd.to_datetime(DATE_MIN, dayfirst=True)
DATE_MAX_TS = pd.to_datetime(DATE_MAX, dayfirst=True)
PAYMENT_MATCH_TOLERANCE_PCT = 0.01
PAYMENT_MATCH_TOLERANCE_ABS = 1.0


# Giai thich nhanh:
# - Assumption: gia dinh nghiep vu minh dat ra khi dataset khong noi ro cach luu du lieu.
# - Tolerance: nguong sai lech chap nhan duoc de tranh bat loi do lam tron so nho.
# - Cross-table check: rule can noi nhieu bang, vi du payments so voi order_items.
# Each rule: table, rule_name, condition_fn, description.
# condition_fn returns True for rows that violate the rule.
LOGIC_RULES = [
    (
        "order_items",
        "quantity > 0",
        lambda df: df["quantity"] <= 0,
        "Quantity must be greater than 0.",
    ),
    (
        "order_items",
        "unit_price > 0",
        lambda df: df["unit_price"] <= 0,
        "Unit price must be greater than 0.",
    ),
    (
        "order_items",
        "discount_amount >= 0",
        lambda df: df["discount_amount"] < 0,
        "Discount amount cannot be negative.",
    ),
    (
        "order_items",
        "discount_amount <= quantity * unit_price",
        lambda df: df["discount_amount"] > df["quantity"] * df["unit_price"] + 0.01,
        "Discount amount cannot exceed gross item value.",
    ),
    (
        "orders",
        f"order_date in [{DATE_MIN}, {DATE_MAX}]",
        lambda df: (df["order_date"] < DATE_MIN_TS) | (df["order_date"] > DATE_MAX_TS),
        "Order date must be within the configured valid data range.",
    ),
    (
        "products",
        "price > 0",
        lambda df: df["price"] <= 0,
        "Product price must be greater than 0.",
    ),
    (
        "products",
        "cogs >= 0",
        lambda df: df["cogs"] < 0,
        "Product COGS cannot be negative.",
    ),
    (
        "products",
        "price >= cogs",
        lambda df: df["price"] + 0.01 < df["cogs"],
        "Product price should not be lower than COGS.",
    ),
    (
        "payments",
        "payment_value > 0",
        lambda df: df["payment_value"] <= 0,
        "Payment value must be greater than 0.",
    ),
    (
        "promotions",
        "end_date >= start_date",
        lambda df: df["end_date"] < df["start_date"],
        "Promotion end date must be greater than or equal to start date.",
    ),
    (
        "promotions",
        "discount_value > 0",
        lambda df: df["discount_value"] <= 0,
        "Promotion discount value must be greater than 0.",
    ),
    (
        "promotions",
        "percentage discount_value in (0, 1]",
        lambda df: df["promo_type"].astype(str).str.lower().str.contains(
            "percent|percentage|rate", na=False
        )
        & (((df["discount_value"] / 100) <= 0) | ((df["discount_value"] / 100) > 1)),
        "Assumption: rate/percentage discounts are stored as decimal values, so discount_value should be in (0, 1].",
    ),
    (
        "promotions",
        "min_order_value >= 0",
        lambda df: df["min_order_value"] < 0,
        "Minimum order value cannot be negative.",
    ),
    (
        "returns",
        "refund_amount >= 0",
        lambda df: df["refund_amount"] < 0,
        "Refund amount cannot be negative.",
    ),
    (
        "returns",
        "return_quantity > 0",
        lambda df: df["return_quantity"] <= 0,
        "Return quantity must be greater than 0.",
    ),
    (
        "reviews",
        "rating in [1, 5]",
        lambda df: (df["rating"] < 1) | (df["rating"] > 5),
        "Review rating must be between 1 and 5.",
    ),
    (
        "shipments",
        "delivery_date >= ship_date",
        lambda df: df["delivery_date"].notna()
        & df["ship_date"].notna()
        & (df["delivery_date"] < df["ship_date"]),
        "Delivery date must be greater than or equal to ship date.",
    ),
    (
        "inventory",
        "stock_on_hand >= 0",
        lambda df: df["stock_on_hand"] < 0,
        "Stock on hand cannot be negative.",
    ),
    (
        "inventory",
        "units_sold >= 0",
        lambda df: df["units_sold"] < 0,
        "Units sold cannot be negative.",
    ),
    (
        "web_traffic",
        "sessions >= unique_visitors",
        lambda df: df["sessions"] < df["unique_visitors"],
        "Sessions must be greater than or equal to unique visitors.",
    ),
    (
        "web_traffic",
        "page_views >= sessions",
        lambda df: df["page_views"] < df["sessions"],
        "Page views must be greater than or equal to sessions.",
    ),
    (
        "web_traffic",
        "bounce_rate in [0, 1] or [0, 100]",
        lambda df: (df["bounce_rate"] < 0) | (df["bounce_rate"] > 100),
        "Bounce rate must be within [0, 1] or [0, 100], depending on data format.",
    ),
]


def summarize_rule(table, rule_name, description, checked_rows, violated_rows):
    return {
        "table": table,
        "rule_name": rule_name,
        "description": description,
        "checked_rows": checked_rows,
        "violated_rows": violated_rows,
        "violation_pct": round(violated_rows / checked_rows * 100, 4) if checked_rows else 0,
        "status": "FAIL" if violated_rows > 0 else "PASS",
    }


def run_single_table_checks(tables):
    all_violations = []
    summary_rows = []

    for table, rule_name, condition_fn, description in LOGIC_RULES:
        if table not in tables:
            print(f"  [SKIP] {table} not found.")
            continue

        df = tables[table].copy()
        try:
            mask = condition_fn(df).fillna(False)
        except KeyError as e:
            print(f"  [WARN] {table} / {rule_name}: missing column {e}; skipped.")
            continue

        violated_df = df[mask].copy()
        violated_df["_table"] = table
        violated_df["_violated_rule"] = rule_name

        if not violated_df.empty:
            all_violations.append(violated_df)

        summary_rows.append(
            summarize_rule(table, rule_name, description, len(df), int(mask.sum()))
        )

    return all_violations, summary_rows


def add_cross_table_violation(all_violations, summary_rows, df, table, rule_name, description, mask):
    mask = mask.fillna(False)
    violated_df = df[mask].copy()
    violated_df["_table"] = table
    violated_df["_violated_rule"] = rule_name

    if not violated_df.empty:
        all_violations.append(violated_df)

    summary_rows.append(
        summarize_rule(table, rule_name, description, len(df), int(mask.sum()))
    )


def run_cross_table_checks(tables):
    all_violations = []
    summary_rows = []

    if {"orders", "order_items", "payments"}.issubset(tables):
        order_items = tables["order_items"].copy()
        payments = tables["payments"].copy()

        order_items["expected_order_total"] = (
            order_items["quantity"] * order_items["unit_price"] - order_items["discount_amount"]
        )
        expected = order_items.groupby("order_id", as_index=False).agg(
            expected_order_total=("expected_order_total", "sum")
        )
        paid = payments.groupby("order_id", as_index=False).agg(
            actual_payment_total=("payment_value", "sum")
        )
        payment_check = expected.merge(paid, on="order_id", how="outer")
        payment_check[["expected_order_total", "actual_payment_total"]] = payment_check[
            ["expected_order_total", "actual_payment_total"]
        ].fillna(0)
        payment_check["payment_diff"] = (
            payment_check["actual_payment_total"] - payment_check["expected_order_total"]
        )
        payment_check["payment_diff_pct"] = payment_check["payment_diff"].abs() / payment_check[
            "expected_order_total"
        ].replace(0, pd.NA)
        payment_mask = (
            payment_check["payment_diff"].abs() > PAYMENT_MATCH_TOLERANCE_ABS
        ) & (
            payment_check["payment_diff_pct"].fillna(1) > PAYMENT_MATCH_TOLERANCE_PCT
        )
        add_cross_table_violation(
            all_violations,
            summary_rows,
            payment_check,
            "payments",
            "payment_value roughly matches order item total",
            "Payment total per order should roughly match net order item total.",
            payment_mask,
        )

    if {"orders", "shipments"}.issubset(tables):
        ship_check = tables["shipments"].merge(
            tables["orders"][["order_id", "order_date"]], on="order_id", how="left"
        )
        ship_mask = (
            ship_check["ship_date"].notna()
            & ship_check["order_date"].notna()
            & (ship_check["ship_date"] < ship_check["order_date"])
        )
        add_cross_table_violation(
            all_violations,
            summary_rows,
            ship_check,
            "shipments",
            "ship_date >= order_date",
            "Ship date must be greater than or equal to order date.",
            ship_mask,
        )

    if {"orders", "returns"}.issubset(tables):
        return_check = tables["returns"].merge(
            tables["orders"][["order_id", "order_date"]], on="order_id", how="left"
        )
        return_mask = (
            return_check["return_date"].notna()
            & return_check["order_date"].notna()
            & (return_check["return_date"] < return_check["order_date"])
        )
        add_cross_table_violation(
            all_violations,
            summary_rows,
            return_check,
            "returns",
            "return_date >= order_date",
            "Return date must be greater than or equal to order date.",
            return_mask,
        )

    if {"orders", "reviews"}.issubset(tables):
        review_check = tables["reviews"].merge(
            tables["orders"][["order_id", "order_date"]], on="order_id", how="left"
        )
        review_mask = (
            review_check["review_date"].notna()
            & review_check["order_date"].notna()
            & (review_check["review_date"] < review_check["order_date"])
        )
        add_cross_table_violation(
            all_violations,
            summary_rows,
            review_check,
            "reviews",
            "review_date >= order_date",
            "Review date must be greater than or equal to order date.",
            review_mask,
        )

    return all_violations, summary_rows


def run_logic_checks(tables):
    single_violations, single_summary = run_single_table_checks(tables)
    cross_violations, cross_summary = run_cross_table_checks(tables)

    all_violations = single_violations + cross_violations
    summary_rows = single_summary + cross_summary

    if all_violations:
        df_violations = pd.concat(all_violations, ignore_index=True, sort=False)
        meta_cols = ["_table", "_violated_rule"]
        other_cols = [c for c in df_violations.columns if c not in meta_cols]
        df_violations = df_violations[meta_cols + other_cols]
    else:
        df_violations = pd.DataFrame(columns=["_table", "_violated_rule"])

    return df_violations, pd.DataFrame(summary_rows)


def main():
    print("Loading tables...")
    tables = load_tables(
        names=[
            "products",
            "order_items",
            "orders",
            "promotions",
            "returns",
            "reviews",
            "payments",
            "shipments",
            "inventory",
            "web_traffic",
        ],
        parse_dates=True,
    )
    print(f"Loaded {len(tables)} tables.")

    print("Running logic checks...")
    df_violations, df_summary = run_logic_checks(tables)

    print("Saving outputs...")
    save_table(df_violations, "04b_logic_violations.csv")
    save_table(df_summary, "04b_logic_summary.csv")

    n_fail = int((df_summary["status"] == "FAIL").sum())
    print(f"04b logic validation done! {n_fail}/{len(df_summary)} rules FAIL.")


if __name__ == "__main__":
    main()
    print("04b logic validation completed!")
