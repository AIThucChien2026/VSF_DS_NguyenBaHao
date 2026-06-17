from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FEATURE_COLS_PATH = PROJECT_ROOT / "report_14_6_2026" / "modeling_outputs" / "tables" / "feature_cols_v1.csv"
PRODUCTS_PATH = PROJECT_ROOT / "Data" / "products.csv"

DEFAULT_FEATURE_COLS = [
    "payment_method",
    "device_type",
    "order_source",
    "customer_tenure_days",
    "tenure_group",
    "age_group",
    "gender",
    "total_quantity",
    "unique_product_count",
    "discount_ratio",
    "is_discounted",
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
    "payment_value",
    "is_cod",
    "log_payment_value",
]

CATEGORY_LEVELS = ["Casual", "GenZ", "Outdoor", "Streetwear"]
SEGMENT_LEVELS = ["Activewear", "Balanced", "Everyday", "Performance", "Premium", "Standard"]
SIZE_LEVELS = ["L", "M", "S", "XL"]


def load_feature_cols() -> list[str]:
    if FEATURE_COLS_PATH.exists():
        cols = pd.read_csv(FEATURE_COLS_PATH)["feature"].dropna().astype(str).tolist()
        if cols:
            return cols
    return DEFAULT_FEATURE_COLS.copy()


FEATURE_COLS = load_feature_cols()


def _load_product_lookup() -> dict[str, dict[str, Any]]:
    if not PRODUCTS_PATH.exists():
        return {}
    products = pd.read_csv(PRODUCTS_PATH)
    lookup: dict[str, dict[str, Any]] = {}
    for row in products.to_dict(orient="records"):
        product_id = row.get("product_id")
        if pd.isna(product_id):
            continue
        lookup[str(int(product_id)) if float(product_id).is_integer() else str(product_id)] = row
    return lookup


PRODUCT_LOOKUP = _load_product_lookup()


def _as_records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        raise ValueError("Payload must be an object or a list of objects.")
    for key in ("orders", "records", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return [payload]


def _nested_get(record: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return default


def _clean_str(value: Any, default: str = "unknown") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _normalize_product_id(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
        if number.is_integer():
            return str(int(number))
    except (TypeError, ValueError):
        pass
    return str(value).strip()


def _tenure_group(days: int) -> str:
    if days < 30:
        return "new_lt_30d"
    if days < 180:
        return "30_179d"
    if days < 365:
        return "180_364d"
    return "loyal_365d_plus"


def _items_from_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    items = record.get("items")
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    item = record.get("item")
    if isinstance(item, dict):
        return [item]
    return []


def _enrich_item(item: dict[str, Any]) -> dict[str, Any]:
    product_id = _normalize_product_id(item.get("product_id"))
    product_row = PRODUCT_LOOKUP.get(product_id or "", {})
    return {
        **item,
        "category": item.get("category") or product_row.get("category"),
        "segment": item.get("segment") or product_row.get("segment"),
        "size": item.get("size") or product_row.get("size"),
        "unit_price": item.get("unit_price") if item.get("unit_price") is not None else product_row.get("price"),
    }


def transform_order(record: dict[str, Any]) -> dict[str, Any]:
    customer = record.get("customer") if isinstance(record.get("customer"), dict) else {}
    payment = record.get("payment") if isinstance(record.get("payment"), dict) else {}

    payment_method = _clean_str(_nested_get(record, "payment_method", default=payment.get("payment_method"))).lower()
    device_type = _clean_str(record.get("device_type")).lower()
    order_source = _clean_str(record.get("order_source")).lower()
    age_group = _clean_str(_nested_get(record, "age_group", default=customer.get("age_group")))
    gender = _clean_str(_nested_get(record, "gender", default=customer.get("gender")))

    order_date = _to_date(record.get("order_date")) or date.today()
    first_order_date = _to_date(record.get("first_order_date")) or _to_date(customer.get("first_order_date"))
    signup_date = _to_date(record.get("signup_date")) or _to_date(customer.get("signup_date"))
    tenure_start = first_order_date or signup_date or order_date
    customer_tenure_days = max((order_date - tenure_start).days, 0)

    items = [_enrich_item(item) for item in _items_from_record(record)]
    total_quantity = 0.0
    total_discount_amount = 0.0
    total_gross_value = 0.0
    product_ids: set[str] = set()
    categories: set[str] = set()
    segments: set[str] = set()
    sizes: set[str] = set()

    for index, item in enumerate(items):
        quantity = max(_to_float(item.get("quantity"), 1.0), 0.0)
        unit_price = max(_to_float(item.get("unit_price"), 0.0), 0.0)
        discount_amount = max(_to_float(item.get("discount_amount"), 0.0), 0.0)
        product_id = _normalize_product_id(item.get("product_id")) or f"item_{index}"

        total_quantity += quantity
        total_discount_amount += discount_amount
        total_gross_value += quantity * unit_price
        product_ids.add(product_id)

        category = _clean_str(item.get("category"), default="")
        segment = _clean_str(item.get("segment"), default="")
        size = _clean_str(item.get("size"), default="")
        if category:
            categories.add(category)
        if segment:
            segments.add(segment)
        if size:
            sizes.add(size.upper())

    payment_value = _nested_get(record, "payment_value", default=payment.get("payment_value"))
    payment_value_float = _to_float(payment_value, default=np.nan)
    if math.isnan(payment_value_float):
        payment_value_float = max(total_gross_value - total_discount_amount, 0.0)

    discount_ratio = 0.0
    if total_gross_value > 0:
        discount_ratio = min(max(total_discount_amount / total_gross_value, 0.0), 1.0)

    feature_record: dict[str, Any] = {
        "payment_method": payment_method,
        "device_type": device_type,
        "order_source": order_source,
        "customer_tenure_days": int(customer_tenure_days),
        "tenure_group": _tenure_group(customer_tenure_days),
        "age_group": age_group,
        "gender": gender,
        "total_quantity": int(total_quantity),
        "unique_product_count": int(len(product_ids)),
        "discount_ratio": float(discount_ratio),
        "is_discounted": int(total_discount_amount > 0),
        "payment_value": float(payment_value_float),
        "is_cod": int(payment_method == "cod"),
        "log_payment_value": float(np.log1p(max(payment_value_float, 0.0))),
    }

    for level in CATEGORY_LEVELS:
        feature_record[f"category_{level}"] = int(level in categories)
    for level in SEGMENT_LEVELS:
        feature_record[f"segment_{level}"] = int(level in segments)
    for level in SIZE_LEVELS:
        feature_record[f"size_{level}"] = int(level in sizes)

    return {col: feature_record.get(col, 0) for col in FEATURE_COLS}


def transform_orders(payload: Any) -> pd.DataFrame:
    records = _as_records(payload)
    if not records:
        raise ValueError("Payload must contain at least one order record.")
    transformed = [transform_order(record) for record in records]
    return pd.DataFrame(transformed, columns=FEATURE_COLS)


def transform_payload(payload: Any) -> dict[str, Any]:
    records = _as_records(payload)
    features = transform_orders(records)
    order_ids = [record.get("order_id") for record in records]
    return {
        "feature_count": len(FEATURE_COLS),
        "feature_columns": FEATURE_COLS,
        "records": [
            {"order_id": order_id, "features": row}
            for order_id, row in zip(order_ids, features.to_dict(orient="records"))
        ],
    }
