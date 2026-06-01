"""
Mục tiêu:
    Cấu hình dùng chung cho pipeline EDA sơ khởi.

Input:
    Thư mục data/ chứa các file CSV của cuộc thi.

Quy trình:
    - Khai báo đường dẫn gốc, data, output.
    - Tạo các thư mục outputs/eda_initial/tables, figures, reports.
    - Khai báo danh sách bảng kỳ vọng và cột ngày cần parse.
    - Cung cấp helper load_tables, save_table, save_figure, save_report.

Output:
    - Tạo thư mục outputs/eda_initial/ nếu chưa tồn tại.
    - Không sinh bảng/biểu đồ riêng; các script khác sẽ dùng helper trong file này.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_DIR = OUTPUT_DIR / "reports"

for path in [OUTPUT_DIR, TABLE_DIR, FIGURE_DIR, REPORT_DIR]:
    path.mkdir(parents=True, exist_ok=True)

pd.set_option("display.max_columns", 200)
pd.set_option("display.width", 200)
sns.set_theme(style="whitegrid")

# Mốc thời gian dữ liệu
DATE_MIN = "04-07-2012"
DATE_MAX = "31-12-2022"

# Danh sách 14 bảng CSV chính theo đề bài. Đây mới là registry đầy đủ của dataset.
EXPECTED_TABLES = [
    "products",
    "customers",
    "promotions",
    "geography",
    "orders",
    "order_items",
    "payments",
    "shipments",
    "returns",
    "reviews",
    "sales",
    "sample_submission",
    "inventory",
    "web_traffic",
]

# Chỉ khai báo các bảng có cột ngày để parse datetime.
# Vì vậy DATE_COLUMNS có ít bảng hơn EXPECTED_TABLES là đúng.
DATE_COLUMNS = {
    "customers": ["signup_date"],
    "promotions": ["start_date", "end_date"],
    "orders": ["order_date"],
    "shipments": ["ship_date", "delivery_date"],
    "returns": ["return_date"],
    "reviews": ["review_date"],
    "sales": ["Date"],
    "sample_submission": ["Date"],
    "inventory": ["snapshot_date"],
    "web_traffic": ["date"],
}

EXPECTED_TABLE_GROUPS = {
    "master": ["products", "customers", "promotions", "geography"],
    "transaction": ["orders", "order_items", "payments", "shipments", "returns", "reviews"],
    "analytical": ["sales", "sample_submission"],
    "operational": ["inventory", "web_traffic"],
}


def load_tables(names=None, parse_dates=False):
    selected_names = set(names) if names is not None else None
    tables = {}
    for path in sorted(DATA_DIR.glob("*.csv")):
        name = path.stem
        if selected_names is not None and name not in selected_names:
            continue
        df = pd.read_csv(path, low_memory=False)
        if parse_dates:
            for col in DATE_COLUMNS.get(name, []):
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        tables[name] = df
    return tables


def save_table(df, filename):
    output_path = TABLE_DIR / filename
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def save_report(text, filename):
    output_path = REPORT_DIR / filename
    output_path.write_text(text, encoding="utf-8")
    return output_path


def save_figure(fig, filename):
    output_path = FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path


def safe_value_counts(df, column, top_n=None):
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "count", "pct"])
    counts = df[column].value_counts(dropna=False)
    if top_n is not None:
        counts = counts.head(top_n)
    out = counts.rename_axis(column).reset_index(name="count")
    out["pct"] = out["count"] / len(df) if len(df) else 0
    return out


def numeric_summary(df, columns):
    available = [col for col in columns if col in df.columns]
    if not available:
        return pd.DataFrame(columns=["column", "count", "mean", "std", "min", "median", "max"])
    summary = df[available].describe().T.reset_index().rename(columns={"index": "column", "50%": "median"})
    return summary


def plot_bar(df, x, y, title, xlabel, ylabel, filename, horizontal=False, max_items=20):
    if df.empty or x not in df.columns or y not in df.columns:
        return None
    plot_df = df.head(max_items).copy()
    fig, ax = plt.subplots(figsize=(10, max(4, min(9, len(plot_df) * 0.4))))
    if horizontal:
        sns.barplot(data=plot_df, x=x, y=y, ax=ax, color="#4c78a8")
    else:
        sns.barplot(data=plot_df, x=x, y=y, ax=ax, color="#4c78a8")
        ax.tick_params(axis="x", rotation=35)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return save_figure(fig, filename)


def table_group(table_name):
    for group, names in EXPECTED_TABLE_GROUPS.items():
        if table_name in names:
            return group
    return "unknown"
