"""
Muc tieu:
    Tao bao cao Markdown de tom tat ket qua kiem tra logic nghiep vu tu script
    04b, giup doc nhanh cac rule PASS/FAIL va cac dong vi pham tieu bieu.

Input:
    - outputs/tables/04b_logic_summary.csv
    - outputs/tables/04b_logic_violations.csv

Quy trinh:
    - Doc file summary va file violations tu thu muc outputs/tables.
    - Tinh tong so rule, so rule PASS/FAIL va tong so dong vi pham.
    - Tao bang Markdown cho failed rules, sample violations va passed rules.
    - Ghi chu cac assumption, tolerance va thuat ngu can luu y khi doc bao cao.

Output:
    - outputs/reports/04b_logic_summary.md
"""

import pandas as pd

from config import TABLE_DIR, save_report


PAYMENT_MATCH_TOLERANCE_PCT = 0.01
PAYMENT_MATCH_TOLERANCE_ABS = 1.0


def dataframe_to_markdown(df):
    if df.empty:
        return "*No rows.*"

    cols = list(df.columns)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join(["---"] * len(cols)) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row[col]).replace("|", "\\|") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def load_csv(filename):
    path = TABLE_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return pd.read_csv(path)


def generate_markdown_report(df_summary, df_violations):
    total_rules = len(df_summary)
    passed_rules = int((df_summary["status"] == "PASS").sum())
    failed_rules = int((df_summary["status"] == "FAIL").sum())
    total_violated = int(df_summary["violated_rows"].sum())

    fail_df = df_summary[df_summary["status"] == "FAIL"].copy()
    pass_df = df_summary[df_summary["status"] == "PASS"][
        ["table", "rule_name", "checked_rows", "description"]
    ].copy()

    fail_md = (
        dataframe_to_markdown(fail_df)
        if failed_rules > 0
        else "*All rules passed; no logic violations found.*"
    )
    pass_md = dataframe_to_markdown(pass_df)

    if df_violations.empty:
        sample_md = "*No violating rows.*"
    else:
        sample_cols = [c for c in ["_table", "_violated_rule", "order_id", "product_id"] if c in df_violations.columns]
        sample_df = df_violations[sample_cols].head(20) if sample_cols else df_violations.head(20)
        sample_md = dataframe_to_markdown(sample_df)

    return f"""# Logic Validation Report (04b)

## Overview

| Metric | Value |
|---|---:|
| Total rules checked | {total_rules} |
| Rules PASS | {passed_rules} |
| Rules FAIL | {failed_rules} |
| Total violating rows | {total_violated:,} |

## Failed Rules

{fail_md}

## Sample Violations

{sample_md}

## Passed Rules

{pass_md}

## Notes

- Detailed violating rows are saved in `04b_logic_violations.csv`.
- `payment_value roughly matches order item total` uses net item value: `quantity * unit_price - discount_amount`.
- Payment matching tolerance: {PAYMENT_MATCH_TOLERANCE_PCT:.2%} and absolute tolerance {PAYMENT_MATCH_TOLERANCE_ABS}.
- `max_discount_amount >= 0` was not added because the current promotions table does not contain `max_discount_amount`; it contains `min_order_value`.

## Giai Thich Thuat Ngu

- `Assumption`: gia dinh nghiep vu minh dat ra khi dataset khong noi ro cach luu du lieu. Vi du: rule percentage discount dang gia dinh `20%` duoc luu la `0.2`, khong phai `20`.
- `Tolerance`: nguong sai lech chap nhan duoc. Dung de tranh bat loi do lam tron so nho, vi du chenh lech thanh toan vai dong/cent.
- `Cross-table check`: rule phai noi nhieu bang moi kiem tra duoc. Vi du `ship_date >= order_date` can noi `shipments` voi `orders`.
- `Net item value`: gia tri sau giam gia cua dong san pham, tinh bang `quantity * unit_price - discount_amount`.
- `Violation`: dong du lieu vi pham rule. Vi pham khong luon co nghia la data sai; doi khi la rule dang dung assumption chua khop voi format that cua data.
"""


def main():
    print("Loading 04b logic validation outputs...")
    df_summary = load_csv("04b_logic_summary.csv")
    df_violations = load_csv("04b_logic_violations.csv")

    print("Generating 04b logic validation report...")
    report = generate_markdown_report(df_summary, df_violations)
    save_report(report, "04c_logic_summary.md")
    print("04c logic validation report done!")


if __name__ == "__main__":
    main()
