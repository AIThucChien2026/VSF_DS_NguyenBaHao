"""
Mục tiêu:
    Vẽ ERD sơ khởi để nhìn nhanh quan hệ giữa các bảng trong bộ dữ liệu.

Input:
    - Cấu trúc quan hệ được khai báo trực tiếp trong script dựa trên đề bài.
    - Không đọc dữ liệu chi tiết; chỉ dùng tên bảng, nhóm bảng và quan hệ khóa.

Quy trình:
    - Đặt vị trí các bảng theo 4 nhóm: master, transaction, analytical, operational.
    - Vẽ mỗi bảng thành một box có tên bảng và một số khóa/cột chính.
    - Vẽ mũi tên thể hiện quan hệ join giữa các bảng.
    - Lưu hình ERD ra thư mục figures và mô tả quan hệ ra tables/reports.

Output:
    - outputs/eda_initial/figures/10_erd_relationships.png
    - outputs/eda_initial/figures/10_erd_relationships.svg
    - outputs/eda_initial/tables/10_erd_relationships.csv
    - outputs/eda_initial/reports/10_erd_notes.md
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd

from config import FIGURE_DIR, REPORT_DIR, save_table


TABLES = {
    "products": {
        "group": "Master",
        "fields": ["PK product_id", "category", "segment", "price", "cogs"],
        "xy": (0.05, 0.72),
    },
    "customers": {
        "group": "Master",
        "fields": ["PK customer_id", "zip", "signup_date", "age_group"],
        "xy": (0.05, 0.48),
    },
    "promotions": {
        "group": "Master",
        "fields": ["PK promo_id", "promo_type", "discount_value"],
        "xy": (0.05, 0.24),
    },
    "geography": {
        "group": "Master",
        "fields": ["PK zip", "city", "region", "district"],
        "xy": (0.05, 0.02),
    },
    "orders": {
        "group": "Transaction",
        "fields": ["PK order_id", "FK customer_id", "FK zip", "order_date"],
        "xy": (0.38, 0.50),
    },
    "order_items": {
        "group": "Transaction",
        "fields": ["FK order_id", "FK product_id", "quantity", "promo_id"],
        "xy": (0.38, 0.75),
    },
    "payments": {
        "group": "Transaction",
        "fields": ["FK order_id", "payment_value", "installments"],
        "xy": (0.68, 0.78),
    },
    "shipments": {
        "group": "Transaction",
        "fields": ["FK order_id", "ship_date", "delivery_date"],
        "xy": (0.68, 0.57),
    },
    "returns": {
        "group": "Transaction",
        "fields": ["PK return_id", "FK order_id", "FK product_id"],
        "xy": (0.68, 0.35),
    },
    "reviews": {
        "group": "Transaction",
        "fields": ["PK review_id", "FK order_id", "FK product_id", "rating"],
        "xy": (0.68, 0.13),
    },
    "sales": {
        "group": "Analytical",
        "fields": ["Date", "Revenue", "COGS"],
        "xy": (0.38, 0.08),
    },
    "sample_submission": {
        "group": "Analytical",
        "fields": ["Date", "Revenue", "COGS"],
        "xy": (0.38, -0.12),
    },
    "inventory": {
        "group": "Operational",
        "fields": ["snapshot_date", "FK product_id", "stock_on_hand"],
        "xy": (0.05, -0.20),
    },
    "web_traffic": {
        "group": "Operational",
        "fields": ["date", "sessions", "traffic_source"],
        "xy": (0.68, -0.10),
    },
}

RELATIONSHIPS = [
    ("customers", "orders", "customer_id"),
    ("geography", "customers", "zip"),
    ("geography", "orders", "zip"),
    ("orders", "order_items", "order_id"),
    ("products", "order_items", "product_id"),
    ("promotions", "order_items", "promo_id / promo_id_2"),
    ("orders", "payments", "order_id"),
    ("orders", "shipments", "order_id"),
    ("orders", "returns", "order_id"),
    ("products", "returns", "product_id"),
    ("orders", "reviews", "order_id"),
    ("products", "reviews", "product_id"),
    ("customers", "reviews", "customer_id"),
    ("products", "inventory", "product_id"),
    ("sales", "sample_submission", "same format"),
]

GROUP_COLORS = {
    "Master": "#dbeafe",
    "Transaction": "#dcfce7",
    "Analytical": "#fef3c7",
    "Operational": "#fee2e2",
}


def box_center(table):
    x, y = TABLES[table]["xy"]
    return x + 0.12, y + 0.07


def draw_box(ax, table, spec):
    x, y = spec["xy"]
    width = 0.24
    height = 0.16
    color = GROUP_COLORS.get(spec["group"], "#f3f4f6")
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.01,rounding_size=0.012",
        linewidth=1.2,
        edgecolor="#334155",
        facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(x + 0.012, y + height - 0.028, table, fontsize=10, weight="bold", color="#0f172a")
    ax.text(x + 0.012, y + height - 0.052, spec["group"], fontsize=7.5, color="#475569")
    for i, field in enumerate(spec["fields"][:5]):
        ax.text(x + 0.012, y + height - 0.078 - i * 0.021, field, fontsize=7.5, color="#1e293b")


def draw_arrow(ax, source, target, label):
    start = box_center(source)
    end = box_center(target)
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=9,
        linewidth=0.9,
        color="#64748b",
        alpha=0.75,
        connectionstyle="arc3,rad=0.08",
    )
    ax.add_patch(arrow)
    mx = (start[0] + end[0]) / 2
    my = (start[1] + end[1]) / 2
    ax.text(mx, my, label, fontsize=6.5, color="#334155", ha="center", va="center", alpha=0.9)


def main():
    relationship_df = pd.DataFrame(RELATIONSHIPS, columns=["source_table", "target_table", "join_key"])
    save_table(relationship_df, "10_erd_relationships.csv")

    fig, ax = plt.subplots(figsize=(16, 10))
    ax.set_xlim(0, 1)
    ax.set_ylim(-0.28, 0.94)
    ax.axis("off")
    ax.set_title("Initial ERD / Relationship Map", fontsize=18, weight="bold", pad=16)

    for table, spec in TABLES.items():
        draw_box(ax, table, spec)

    for source, target, label in RELATIONSHIPS:
        draw_arrow(ax, source, target, label)

    legend_x = 0.02
    legend_y = 0.90
    ax.text(legend_x, legend_y, "Groups", fontsize=10, weight="bold", color="#0f172a")
    for i, (group, color) in enumerate(GROUP_COLORS.items()):
        y = legend_y - 0.035 - i * 0.03
        ax.add_patch(FancyBboxPatch((legend_x, y), 0.018, 0.018, boxstyle="round,pad=0.002", facecolor=color, edgecolor="#334155"))
        ax.text(legend_x + 0.025, y + 0.002, group, fontsize=8.5, color="#334155")

    png_path = FIGURE_DIR / "10_erd_relationships.png"
    svg_path = FIGURE_DIR / "10_erd_relationships.svg"
    fig.tight_layout()
    fig.savefig(png_path, dpi=180, bbox_inches="tight")
    fig.savefig(svg_path, bbox_inches="tight")
    plt.close(fig)

    notes = """# ERD Notes

File này là ERD sơ khởi để định hướng join khi làm EDA.

## Lưu ý quan trọng

- `orders` là bảng trung tâm cho phân tích đơn hàng.
- `order_items` là bảng trung tâm cho phân tích sản phẩm trong đơn.
- Join `orders` với `order_items` sẽ đổi granularity từ order-level sang item-level.
- `sales` và `sample_submission` có cùng format cho bài forecasting nhưng không join trực tiếp với từng order nếu chưa đối soát.
- `inventory` là snapshot theo tháng/sản phẩm, khác granularity với sales theo ngày.
- `web_traffic` là dữ liệu theo ngày/traffic_source, cần aggregate trước khi so với sales.
"""
    (REPORT_DIR / "9_erd_notes.md").write_text(notes, encoding="utf-8")


if __name__ == "__main__":
    main()
