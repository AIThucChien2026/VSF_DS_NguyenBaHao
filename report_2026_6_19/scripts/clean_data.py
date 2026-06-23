# scripts/clean_data.py
"""
Bước 1 của inference pipeline.
Nhiệm vụ: load 5 bảng CSV → clean → merge → validate → trả về cleaned_df.

Không làm gì ngoài phạm vi này:
  - Không tạo features (công việc của FeatureBuilder)
  - Không preprocess / scale (công việc của ColumnTransformer)
  - Không load returns.csv (leakage)
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path

# Thiết lập logger — thay vì dùng print(), dùng logging để có timestamp và level
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
#  CONSTANTS — đặt ở đầu file để dễ tìm và sửa
# ─────────────────────────────────────────────────────────

# Schema bắt buộc phải có ở output — nếu thiếu bất kỳ cột nào → raise ValueError
REQUIRED_OUTPUT_COLS = [
    # IDs và datetime (không dùng trực tiếp làm feature nhưng cần để tính)
    "order_id",
    "customer_id",
    "order_date",
    "signup_date",

    # Cột raw từ orders (sẽ dùng làm feature categorical)
    "payment_method",
    "device_type",
    "order_source",

    # Cột raw từ payments
    "payment_value",

    # Binary flag
    "is_cod",                     # = 1 nếu payment_method == "COD"

    # Từ customers
    "customer_tenure_days",       # = (order_date - signup_date).dt.days
    "age_group",
    "gender",

    # Aggregate từ order_items
    "total_quantity",
    "unique_product_count",
    "total_discount_amount",
    "total_gross_value",
    "discount_ratio",             # = total_discount / total_gross_value
    "is_discounted",              # = 1 nếu discount_ratio > 0

    # Multi-hot từ products (4 + 6 + 4 = 14 cột)
    "category_Casual",
    "category_GenZ",
    "category_Outdoor",
    "category_Streetwear",
    "segment_Activewear",
    "segment_Balanced",
    "segment_Everyday",
    "segment_Performance",
    "segment_Premium",
    "segment_Standard",
    "size_L",
    "size_M",
    "size_S",
    "size_XL",
]


# ─────────────────────────────────────────────────────────
#  HÀM PHỤ TRỢ (helper functions)
# ─────────────────────────────────────────────────────────

def load_tables(data_dir: str) -> dict[str, pd.DataFrame]:
    """
    Load đúng 5 bảng từ data_dir.

    Tại sao có low_memory=False cho order_items?
    → order_items.csv có nhiều cột kiểu mixed (string + số),
      pandas cần đọc cả file để xác định dtype đúng.

    Returns:
        dict với key = tên bảng, value = DataFrame
    """
    data_dir = Path(data_dir)
    tables = {}

    table_configs = {
        "orders":      {"low_memory": True},
        "order_items": {"low_memory": False},   # Mixed types → cần False
        "customers":   {"low_memory": True},
        "products":    {"low_memory": True},
        "payments":    {"low_memory": True},
    }

    for name, kwargs in table_configs.items():
        path = data_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {path}\n"
                f"Kiểm tra lại đường dẫn data_dir='{data_dir}'"
            )
        tables[name] = pd.read_csv(path, **kwargs)
        logger.info(f"✓ Loaded {name}: {tables[name].shape[0]} rows × {tables[name].shape[1]} cols")

    return tables


def clean_order_items(order_items: pd.DataFrame) -> pd.DataFrame:
    """
    Xử lý order_items theo đúng FE notebook Phase 1.

    3 bước theo thứ tự NGHIÊM NGẶT:
    1. Drop promo cols TRƯỚC (không ảnh hưởng tính toán)
    2. Tính line_gross_value = quantity × unit_price
       → PHẢI làm TRƯỚC aggregate vì unit_price sẽ mất sau khi sum
    3. Aggregate theo (order_id, product_id) để xử lý 16 duplicate pairs

    Args:
        order_items: DataFrame raw từ order_items.csv

    Returns:
        DataFrame đã aggregate, grain = (order_id, product_id)
    """
    oi = order_items.copy()  # Không modify input gốc

    # Bước 1: Drop cột promo — có thể không tồn tại nên dùng errors="ignore"
    oi.drop(columns=["promo_id", "promo_id_2"], errors="ignore", inplace=True)
    logger.info(f"  Dropped promo cols. Còn lại: {oi.shape[1]} cols")

    # Bước 2: Tính line_gross_value TRƯỚC KHI aggregate
    oi["line_gross_value"] = oi["quantity"] * oi["unit_price"]

    # Bước 3: Aggregate — xử lý 16 duplicate (order_id, product_id) pairs
    oi_agg = oi.groupby(["order_id", "product_id"], as_index=False).agg(
        quantity=       ("quantity",       "sum"),
        discount_amount=("discount_amount","sum"),
        line_gross_value=("line_gross_value","sum"),
    )

    n_duplicates = len(order_items) - len(oi_agg)
    logger.info(f"  Aggregate xong: {len(order_items)} rows → {len(oi_agg)} rows "
                f"({n_duplicates} duplicate rows đã được merge)")
    return oi_agg


def aggregate_to_order_level(oi_agg: pd.DataFrame) -> pd.DataFrame:
    """
    Tổng hợp order_items (grain: order×product) lên grain: order.

    Tách thành hàm riêng để dễ test độc lập.

    Returns:
        DataFrame, grain = order_id, gồm 4 cột aggregate
    """
    order_level = oi_agg.groupby("order_id", as_index=False).agg(
        total_quantity=      ("quantity",        "sum"),
        unique_product_count=("product_id",      "nunique"),
        total_discount_amount=("discount_amount","sum"),
        total_gross_value=   ("line_gross_value","sum"),
    )
    return order_level


def build_product_multihot(
    oi_agg: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """
    Tạo multi-hot encoding cho product descriptors ở grain order_id.

    Multi-hot encoding = nếu đơn hàng có ÍT NHẤT 1 sản phẩm thuộc category X → cột = 1.
    Khác với one-hot: một đơn có thể có cả Casual lẫn GenZ nếu mua 2 loại.

    Chỉ encode: category (4 values), segment (6 values), size (4 values).
    color_* bị drop ở feature selection → KHÔNG tạo ở đây.

    Returns:
        DataFrame, grain = order_id, gồm 14 cột multi-hot
    """
    # Join để biết mỗi product trong đơn thuộc category/segment/size nào
    merged = oi_agg[["order_id", "product_id"]].merge(
        products[["product_id", "category", "segment", "size"]],
        on="product_id",
        how="left",  # Giữ tất cả order_items dù không match products
    )

    # Tạo binary flag cho từng value
    for val in ["Casual", "GenZ", "Outdoor", "Streetwear"]:
        merged[f"category_{val}"] = (merged["category"] == val).astype(int)

    for val in ["Activewear", "Balanced", "Everyday", "Performance", "Premium", "Standard"]:
        merged[f"segment_{val}"] = (merged["segment"] == val).astype(int)

    for val in ["L", "M", "S", "XL"]:
        merged[f"size_{val}"] = (merged["size"] == val).astype(int)

    # Dùng .max() để aggregate về order_id
    # Nếu BẤT KỲ product nào trong đơn có category_Casual = 1 → max = 1
    multihot_cols = [c for c in merged.columns
                     if c.startswith(("category_", "segment_", "size_"))]
    return merged.groupby("order_id")[multihot_cols].max().reset_index()


def validate_output(df: pd.DataFrame) -> None:
    """
    Kiểm tra cleaned_df đáp ứng schema trước khi return.

    Fail-fast: báo lỗi ngay tại đây thay vì để lỗi xuất hiện ở giữa pipeline.

    Raises:
        ValueError: nếu thiếu cột hoặc grain bị duplicate
    """
    # Kiểm tra đủ cột
    missing_cols = [c for c in REQUIRED_OUTPUT_COLS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Schema violation — cleaned_df thiếu {len(missing_cols)} cột:\n"
            f"  {missing_cols}\n"
            f"Kiểm tra lại logic merge hoặc tên cột nguồn."
        )

    # Kiểm tra grain
    n_rows = len(df)
    n_unique = df["order_id"].nunique()
    if n_rows != n_unique:
        raise ValueError(
            f"Grain violation — cleaned_df có {n_rows} rows nhưng chỉ có "
            f"{n_unique} unique order_id. Có {n_rows - n_unique} duplicate rows.\n"
            f"Kiểm tra lại logic merge (có thể bị many-to-many join)."
        )

    logger.info(f"✓ Schema validation passed: {n_rows} rows, {len(df.columns)} cols")


# ─────────────────────────────────────────────────────────
#  HÀM ENTRY POINT — đây là hàm các script khác sẽ import
# ─────────────────────────────────────────────────────────

def clean_data(data_dir: str) -> tuple[pd.DataFrame, dict]:
    """
    Entry point của clean_data.py.

    Usage từ script khác:
        from scripts.clean_data import clean_data
        cleaned_df, summary = clean_data("data/")

    Args:
        data_dir: đường dẫn thư mục chứa 5 file CSV

    Returns:
        tuple:
          - cleaned_df: DataFrame, grain=order_id, chỉ gồm REQUIRED_OUTPUT_COLS
          - summary: dict thống kê nhanh để debug/log

    Raises:
        FileNotFoundError: nếu thiếu file CSV nào
        ValueError: nếu schema hoặc grain không hợp lệ
    """
    logger.info("=== clean_data bắt đầu ===")

    # ── Phase 0: Load ──────────────────────────────────────────
    tables = load_tables(data_dir)

    # ── Phase 1: Parse datetime ────────────────────────────────
    # Phải parse trước tất cả phép tính liên quan đến ngày
    orders = tables["orders"].copy()
    customers = tables["customers"].copy()

    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"], errors="coerce")
    # errors="coerce": nếu parse lỗi → NaT (Not a Time) thay vì crash

    # ── Phase 2: Xử lý order_items ────────────────────────────
    oi_agg = clean_order_items(tables["order_items"])
    order_level = aggregate_to_order_level(oi_agg)
    product_multihot = build_product_multihot(oi_agg, tables["products"])

    # ── Phase 3: Tính derived cols trên orders + customers ─────
    # Tính ngày đặt hàng đầu tiên của mỗi khách hàng
    first_orders = orders.groupby("customer_id")["order_date"].min().reset_index(name="first_order_date")
    orders = orders.merge(first_orders, on="customer_id", how="left")

    # Join customers vào orders để lấy thêm thông tin
    orders = orders.merge(
        customers[["customer_id", "signup_date", "age_group", "gender"]],
        on="customer_id",
        how="left",  # Giữ tất cả orders dù có order không tìm được customer
    )

    # Điều chỉnh signup_date: Nếu khách mua hàng trước khi tạo tài khoản, 
    # ta lấy ngày mua hàng đầu tiên làm mốc bắt đầu (actual_signup_date)
    orders["actual_signup_date"] = orders[["signup_date", "first_order_date"]].min(axis=1)

    # Số ngày từ ngày bắt đầu đến ngày đặt hàng hiện tại (đảm bảo >= 0)
    orders["customer_tenure_days"] = (
        orders["order_date"] - orders["actual_signup_date"]
    ).dt.days

    # Dọn dẹp các cột tạm
    orders.drop(columns=["first_order_date", "actual_signup_date"], inplace=True)

    # COD flag: 1 nếu thanh toán khi nhận hàng
    orders["is_cod"] = (orders["payment_method"] == "COD").astype(int)

    # ── Phase 4: Merge tất cả về grain order_id ───────────────
    payments = tables["payments"][["order_id", "payment_value"]]

    cleaned = (
        orders
        .merge(order_level,    on="order_id", how="left")
        .merge(product_multihot, on="order_id", how="left")
        .merge(payments,       on="order_id", how="left")
    )

    # ── Phase 5: Tính thêm discount features ──────────────────
    # discount_ratio: tỷ lệ giảm giá so với tổng giá trị đơn hàng
    cleaned["discount_ratio"] = np.where(
        cleaned["total_gross_value"] > 0,
        cleaned["total_discount_amount"] / cleaned["total_gross_value"],
        0.0,  # Nếu gross_value = 0, tránh chia 0
    )
    cleaned["is_discounted"] = (cleaned["discount_ratio"] > 0).astype(int)

    # ── Phase 6: Validate schema ───────────────────────────────
    validate_output(cleaned)

    # ── Phase 7: Chỉ giữ đúng các cột cần thiết ───────────────
    cleaned = cleaned[REQUIRED_OUTPUT_COLS]

    # CHỖ CẦN SỬA: Ép kiểu các cột datetime thành string để tránh lỗi JSON serializable khi gọi API
    cleaned["order_date"] = cleaned["order_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    cleaned["signup_date"] = cleaned["signup_date"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # Tổng hợp thông tin để log
    summary = {
        "n_orders":   len(cleaned),
        "n_cols":     len(cleaned.columns),
        "null_counts": cleaned.isnull().sum()[cleaned.isnull().sum() > 0].to_dict(),
        "grain_ok":   True,
    }

    logger.info(f"=== clean_data hoàn thành: {summary['n_orders']} orders ===")
    return cleaned, summary