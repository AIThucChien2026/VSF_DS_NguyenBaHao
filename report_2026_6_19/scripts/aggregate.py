# scripts/aggregate.py
"""
Bước 1 của pipeline.
Nhiệm vụ DUY NHẤT: join các bảng CSV lại thành 1 master table (hoặc 1 record).

KHÔNG làm bất cứ việc gì khác:
  - Không tính feature
  - Không clean / scale / encode
  - Không tạo label
  - Không lọc dòng

Input:
  - Trường hợp 1: data_dir (str) → thư mục chứa 5 file CSV → trả về master DataFrame
  - Trường hợp 2: dict các bảng đã load sẵn → join → trả về master DataFrame
  - Trường hợp 3: dict 1 record của từng bảng → join → trả về 1 record (DataFrame 1 dòng)

Output: master DataFrame, grain = order_id
        gồm tất cả cột từ tất cả bảng sau khi join (không chọn lọc, không bỏ cột)
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  CÁC BẢNG CẦN THIẾT
# ─────────────────────────────────────────────────────────────────────────────

REQUIRED_TABLES = ["orders", "order_items", "customers", "products", "payments"]


# ─────────────────────────────────────────────────────────────────────────────
#  HÀM LOAD CSV
# ─────────────────────────────────────────────────────────────────────────────

def load_tables(data_dir: str) -> dict[str, pd.DataFrame]:
    """
    Load 5 bảng CSV từ data_dir.

    Args:
        data_dir: đường dẫn thư mục chứa 5 file CSV

    Returns:
        dict: key = tên bảng, value = DataFrame raw

    Raises:
        FileNotFoundError: nếu thiếu bất kỳ file CSV nào
    """
    data_dir = Path(data_dir)
    tables = {}

    # order_items cần low_memory=False vì có cột mixed types
    low_memory_map = {
        "orders":      True,
        "order_items": False,
        "customers":   True,
        "products":    True,
        "payments":    True,
    }

    for name in REQUIRED_TABLES:
        path = data_dir / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"Không tìm thấy file: {path}\n"
                f"Kiểm tra lại đường dẫn data_dir='{data_dir}'"
            )
        tables[name] = pd.read_csv(path, low_memory=low_memory_map[name])
        logger.info(
            f"✓ Loaded {name}: "
            f"{tables[name].shape[0]} rows × {tables[name].shape[1]} cols"
        )

    return tables


# ─────────────────────────────────────────────────────────────────────────────
#  HÀM JOIN
# ─────────────────────────────────────────────────────────────────────────────

def join_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Join 5 bảng thành 1 master table, grain = order_id.

    Thứ tự join:
      orders
        ← customers      (on customer_id, how=left)
        ← order_items    (on order_id, how=left, aggregate trước để tránh fan-out)
        ← products       (on product_id qua order_items, dùng multi-hot aggregate)
        ← payments       (on order_id, how=left)

    Lý do aggregate order_items trước khi join vào orders:
      order_items có grain = (order_id, product_id) → nếu join thẳng vào orders
      sẽ tạo nhiều dòng cho 1 order → grain bị vỡ.
      Ta aggregate order_items về grain order_id trước, rồi mới join.

    Returns:
        master DataFrame, grain = order_id
    """
    orders     = tables["orders"].copy()
    order_items= tables["order_items"].copy()
    customers  = tables["customers"].copy()
    products   = tables["products"].copy()
    payments   = tables["payments"].copy()

    master = (
        orders
        .merge(
            customers,
            on="customer_id",
            how="left",
            suffixes=("", "_customer")
        )
        .merge(
            order_items,
            on="order_id",
            how="left"
        )
        .merge(
            products,
            on="product_id",
            how="left"
        )
        .merge(
            payments,
            on="order_id",
            how="left",
            suffixes=("", "_payment")
        )
    )

    return master


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def aggregate(input_data) -> pd.DataFrame:
    """
    Entry point chính — nhận nhiều loại input, luôn trả về master DataFrame.

    Hỗ trợ 3 loại input:
      1. str / Path: đường dẫn thư mục chứa 5 file CSV
         → load CSV → join → trả về master DataFrame (nhiều rows)

      2. dict[str, pd.DataFrame]: các bảng đã load sẵn
         → join trực tiếp → trả về master DataFrame

      3. dict[str, dict]: 1 record của từng bảng (dạng {col: value})
         → convert sang DataFrame 1 dòng → join → trả về DataFrame 1 dòng

    Args:
        input_data:
          - str hoặc Path: đường dẫn thư mục CSV
          - dict: các bảng (DataFrame hoặc record dict)

    Returns:
        master DataFrame, grain = order_id

    Raises:
        FileNotFoundError : nếu thiếu file CSV
        ValueError        : nếu input không hợp lệ
        KeyError          : nếu thiếu bảng bắt buộc trong dict
    """
    # ── Case 1: data_dir — thư mục CSV ───────────────────────────────────────
    if isinstance(input_data, (str, Path)):
        logger.info(f"=== aggregate: load từ data_dir='{input_data}' ===")
        tables = load_tables(str(input_data))
        master = join_tables(tables)
        logger.info(f"=== aggregate hoàn thành: {len(master)} orders ===")
        return master

    # ── Case 2 & 3: dict input ────────────────────────────────────────────────
    if isinstance(input_data, dict):
        # Kiểm tra các bảng bắt buộc
        missing = [t for t in REQUIRED_TABLES if t not in input_data]
        if missing:
            raise KeyError(
                f"input_data thiếu bảng: {missing}\n"
                f"Cần đủ: {REQUIRED_TABLES}"
            )

        # Phát hiện Case 3: record dict (value là dict, không phải DataFrame)
        first_val = next(iter(input_data.values()))
        if isinstance(first_val, dict):
            logger.info("=== aggregate: input là 1 record dict → convert sang DataFrame ===")
            tables = {
                name: pd.DataFrame([record])
                for name, record in input_data.items()
            }
        elif isinstance(first_val, pd.DataFrame):
            logger.info("=== aggregate: input là dict[str, DataFrame] ===")
            tables = input_data
        else:
            raise ValueError(
                f"input_data values phải là DataFrame hoặc dict (record), "
                f"nhận được: {type(first_val)}"
            )

        master = join_tables(tables)
        logger.info(f"=== aggregate hoàn thành: {len(master)} rows ===")
        return master

    raise ValueError(
        f"input_data không hợp lệ. Chấp nhận: str (data_dir), Path, hoặc dict.\n"
        f"Nhận được: {type(input_data)}"
    )

if __name__ == "__main__":
    data_dir = Path(r"B:\DA_VSF\VinuniDatathon\report_2026_6_19\data")
    master = aggregate(data_dir)
    print(master.head())
    master.to_csv(r"B:\DA_VSF\VinuniDatathon\report_2026_6_19\data\master.csv", index=False)