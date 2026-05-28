# Kế hoạch EDA sơ khởi bằng các file Python

## 0. Mục tiêu

Kế hoạch này dùng để viết các file `.py` kiểm tra và khám phá sơ khởi bộ dữ liệu trước khi làm EDA sâu. Không dùng notebook. Mỗi script sẽ đọc dữ liệu bằng code, tạo bảng thông tin, biểu đồ và lưu vào một thư mục đầu ra để cả nhóm xem lại.

Mục tiêu chính:

- Biết bộ dữ liệu có những file/bảng nào.
- Hiểu mỗi bảng đại diện cho đối tượng gì.
- Ghi lại kích thước, cột, kiểu dữ liệu, missing, duplicate ở mức tổng quan.
- Hiểu phạm vi thời gian của từng bảng.
- Hiểu khóa join giữa các bảng.
- Tạo các bảng summary và biểu đồ khám phá ban đầu.
- Tạo một báo cáo tóm tắt dạng Markdown/CSV để chuẩn bị cho EDA sâu.

Nguyên tắc:

- Không để AI tự đọc dữ liệu và tự kết luận.
- Mọi thông tin phải được lấy bằng code trong file `.py`.
- Output phải được lưu ra file để người làm đọc.
- Giai đoạn này chỉ khám phá dữ liệu, chưa sửa/xóa dữ liệu gốc.
- Nếu cần parse ngày hoặc ép kiểu để thống kê đúng hơn, chỉ làm trong bản copy dataframe.

## 1. Cấu trúc thư mục đề xuất

Tạo cấu trúc như sau:

```text
VinuniDatathon/
├── data/
│   ├── products.csv
│   ├── customers.csv
│   └── ...
├── eda_scripts/
│   ├── config.py
│   ├── 01_data_catalog.py
│   ├── 02_schema_overview.py
│   ├── 03_time_coverage.py
│   ├── 04_missing_duplicates.py
│   ├── 05_key_join_overview.py
│   ├── 06_master_data_overview.py
│   ├── 07_transaction_overview.py
│   ├── 08_sales_operational_overview.py
│   ├── 09_build_eda_summary.py
│   └── 10_draw_erd.py
├── outputs/
│   └── eda_initial/
│       ├── tables/
│       ├── figures/
│       └── reports/
└── kế hoạch.md
```

Thư mục output:

- `outputs/eda_initial/tables/`: lưu CSV summary.
- `outputs/eda_initial/figures/`: lưu biểu đồ PNG.
- `outputs/eda_initial/reports/`: lưu file Markdown/TXT tổng hợp.

## 2. File `config.py`

Mục tiêu: gom đường dẫn, cấu hình chung, danh sách cột ngày và helper lưu file.

Nội dung cần có:

```python
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "outputs" / "eda_initial"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
REPORT_DIR = OUTPUT_DIR / "reports"

for path in [OUTPUT_DIR, TABLE_DIR, FIGURE_DIR, REPORT_DIR]:
    path.mkdir(parents=True, exist_ok=True)

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

def load_tables(parse_dates=False):
    tables = {}
    for path in sorted(DATA_DIR.glob("*.csv")):
        name = path.stem
        df = pd.read_csv(path)
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

def save_figure(fig, filename):
    output_path = FIGURE_DIR / filename
    fig.tight_layout()
    fig.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return output_path
```

Output của file này:

- Không tạo bảng chính.
- Chỉ tạo thư mục output và helper dùng chung.

## 3. File `01_data_catalog.py`

Mục tiêu: lập catalog tổng quan để biết đang có những bảng nào.

Input:

- Tất cả CSV trong `data/`.

Output:

- `outputs/eda_initial/tables/01_data_catalog.csv`
- `outputs/eda_initial/reports/01_file_list.txt`

Nội dung script cần làm:

1. Load toàn bộ file CSV.
2. Ghi tên bảng, số dòng, số cột, dung lượng bộ nhớ.
3. Ghi danh sách cột của từng bảng.
4. Lưu catalog ra CSV.

Code logic gợi ý:

```python
from config import DATA_DIR, REPORT_DIR, load_tables, save_table
```

Bảng output cần có cột:

- `table`
- `rows`
- `columns`
- `memory_mb`
- `column_names`
- `file_path`

Người làm đọc output và ghi nhận:

- Có bao nhiêu bảng?
- Bảng nào lớn nhất?
- Bảng nào là master/transaction/analytical/operational?
- Có file nào thiếu hoặc dư so với đề không?

## 4. File `02_schema_overview.py`

Mục tiêu: xem mỗi bảng có cột gì, dtype gì, số unique, số non-null.

Output:

- `outputs/eda_initial/tables/02_dtype_summary.csv`
- `outputs/eda_initial/tables/02_column_summary_by_table.csv`

Script cần làm:

1. Load tables.
2. Với từng cột, tính:
   - dtype
   - non-null count
   - missing count
   - unique count
   - ví dụ 3 giá trị đầu tiên không null
3. Lưu ra CSV.

Bảng output cần có cột:

- `table`
- `column`
- `dtype`
- `non_null`
- `missing`
- `missing_pct`
- `unique_values`
- `sample_values`

Người làm đọc output và ghi nhận:

- Cột nào có thể là ID?
- Cột nào là metric?
- Cột nào là categorical dimension?
- Cột ngày nào đang cần parse?
- Cột nào có missing đáng chú ý?

## 5. File `03_time_coverage.py`

Mục tiêu: kiểm tra bảng nào có thời gian và thời gian bao phủ từ đâu đến đâu.

Output:

- `outputs/eda_initial/tables/03_date_ranges.csv`
- `outputs/eda_initial/figures/03_sales_revenue_timeline.png`
- `outputs/eda_initial/figures/03_web_sessions_timeline.png`

Script cần làm:

1. Load tables với `parse_dates=True`.
2. Với mỗi cột ngày trong config, tính:
   - min date
   - max date
   - missing date
   - số ngày khác nhau
3. Vẽ line chart doanh thu theo ngày từ `sales.csv`.
4. Nếu có `web_traffic.csv`, aggregate theo ngày rồi vẽ sessions theo ngày.

Người làm đọc output và ghi nhận:

- Dữ liệu chính nằm trong giai đoạn nào?
- `sales.csv` có range train ra sao?
- `sample_submission.csv` có range test ra sao?
- Bảng nào có thể dùng cho phân tích mùa vụ?
- Có bảng nào có ngày vượt ngoài kỳ vọng không?

## 6. File `04_missing_duplicates.py`

Mục tiêu: xem missing và duplicate ở mức tổng quan.

Output:

- `outputs/eda_initial/tables/04_missing_summary.csv`
- `outputs/eda_initial/tables/04_duplicate_summary.csv`
- `outputs/eda_initial/figures/04_top_missing_columns.png`

Script cần làm:

1. Với từng cột, tính missing count và missing pct.
2. Với từng bảng, tính duplicate full rows.
3. Vẽ bar chart top 30 cột missing cao nhất.

Người làm đọc output và ghi nhận:

- Missing nào có vẻ hợp lý, ví dụ `promo_id` null nghĩa là không dùng khuyến mãi.
- Missing nào cần kiểm tra sâu trước khi dùng phân tích.
- Bảng nào có duplicate full rows.

## 7. File `05_key_join_overview.py`

Mục tiêu: hiểu khóa chính, khóa phụ và khả năng join.

Output:

- `outputs/eda_initial/tables/05_key_summary.csv`
- `outputs/eda_initial/tables/05_relationship_notes.csv`
- `outputs/eda_initial/reports/05_join_map.md`

Script cần làm:

1. Tính số unique/non-null cho các key candidates:
   - `products.product_id`
   - `customers.customer_id`
   - `geography.zip`
   - `promotions.promo_id`
   - `orders.order_id`
   - `order_items.order_id`
   - `order_items.product_id`
   - `payments.order_id`
   - `shipments.order_id`
   - `returns.order_id`
   - `reviews.order_id`
   - `inventory.product_id`
2. Tạo file Markdown mô tả join map.
3. Ghi chú bảng nào là 1 dòng/entity, bảng nào là nhiều dòng/entity.

Nội dung `05_join_map.md` nên có:

```markdown
# Join map

products.product_id -> order_items.product_id, returns.product_id, reviews.product_id, inventory.product_id
customers.customer_id -> orders.customer_id, reviews.customer_id
geography.zip -> customers.zip, orders.zip
orders.order_id -> order_items.order_id, payments.order_id, shipments.order_id, returns.order_id, reviews.order_id
promotions.promo_id -> order_items.promo_id, order_items.promo_id_2

## Lưu ý
- Không join tất cả bảng ngay từ đầu.
- Join orders với order_items sẽ đổi granularity từ order-level sang item-level.
- Cần aggregate bảng nhiều dòng trước khi phân tích ở order-level.
```

Người làm đọc output và ghi nhận:

- Bảng trung tâm cho phân tích đơn hàng.
- Bảng trung tâm cho phân tích sản phẩm.
- Bảng trung tâm cho forecasting.
- Join nào có nguy cơ nhân dòng.

## 8. File `06_master_data_overview.py`

Mục tiêu: khám phá nhóm master data.

Nhóm bảng:

- `products`
- `customers`
- `promotions`
- `geography`

Output:

- `outputs/eda_initial/tables/06_products_category_counts.csv`
- `outputs/eda_initial/tables/06_products_segment_counts.csv`
- `outputs/eda_initial/tables/06_customers_profile_counts.csv`
- `outputs/eda_initial/tables/06_promotions_counts.csv`
- `outputs/eda_initial/tables/06_geography_counts.csv`
- `outputs/eda_initial/figures/06_products_by_category.png`
- `outputs/eda_initial/figures/06_customers_by_age_group.png`
- `outputs/eda_initial/figures/06_geography_by_region.png`

Script cần làm:

1. Với `products`, đếm category, segment, size, color; tính mô tả `price`, `cogs`.
2. Với `customers`, đếm gender, age_group, acquisition_channel, city.
3. Với `promotions`, đếm promo_type, applicable_category, promo_channel.
4. Với `geography`, đếm region, city, district.
5. Vẽ các bar chart chính.

Người làm đọc output và ghi nhận:

- Có bao nhiêu category/segment sản phẩm?
- Có nhóm khách hàng nào nổi bật?
- Có các loại khuyến mãi nào?
- Dữ liệu có chiều vùng miền đủ để phân tích không?

## 9. File `07_transaction_overview.py`

Mục tiêu: khám phá nhóm giao dịch.

Nhóm bảng:

- `orders`
- `order_items`
- `payments`
- `shipments`
- `returns`
- `reviews`

Output:

- `outputs/eda_initial/tables/07_orders_status_counts.csv`
- `outputs/eda_initial/tables/07_orders_channel_counts.csv`
- `outputs/eda_initial/tables/07_order_items_numeric_summary.csv`
- `outputs/eda_initial/tables/07_payments_summary.csv`
- `outputs/eda_initial/tables/07_returns_reason_counts.csv`
- `outputs/eda_initial/tables/07_reviews_rating_counts.csv`
- `outputs/eda_initial/figures/07_orders_by_status.png`
- `outputs/eda_initial/figures/07_payment_methods.png`
- `outputs/eda_initial/figures/07_return_reasons.png`
- `outputs/eda_initial/figures/07_review_ratings.png`

Script cần làm:

1. Đếm `order_status`, `payment_method`, `device_type`, `order_source`.
2. Tính summary cho `quantity`, `unit_price`, `discount_amount`.
3. Tính summary cho `payment_value`, `installments`.
4. Đếm lý do trả hàng.
5. Đếm rating.
6. Vẽ biểu đồ phân bố chính.

Người làm đọc output và ghi nhận:

- Trạng thái đơn hàng nào phổ biến?
- Kênh/thiết bị nào đáng phân tích?
- Discount có xuất hiện nhiều không?
- Phương thức thanh toán nào phổ biến?
- Return/review có đủ dữ liệu để phân tích sâu không?

## 10. File `08_sales_operational_overview.py`

Mục tiêu: khám phá nhóm analytical và operational.

Nhóm bảng:

- `sales`
- `sample_submission`
- `inventory`
- `web_traffic`

Output:

- `outputs/eda_initial/tables/08_sales_summary.csv`
- `outputs/eda_initial/tables/08_sales_by_year_month.csv`
- `outputs/eda_initial/tables/08_sample_submission_summary.csv`
- `outputs/eda_initial/tables/08_inventory_summary.csv`
- `outputs/eda_initial/tables/08_web_traffic_summary.csv`
- `outputs/eda_initial/figures/08_sales_monthly_revenue.png`
- `outputs/eda_initial/figures/08_sales_monthly_cogs.png`
- `outputs/eda_initial/figures/08_web_traffic_by_source.png`
- `outputs/eda_initial/figures/08_inventory_flags.png`

Script cần làm:

1. Với `sales`, tính summary Revenue/COGS.
2. Aggregate sales theo năm-tháng.
3. Vẽ monthly revenue và monthly COGS.
4. Với `sample_submission`, ghi shape và date range.
5. Với `inventory`, tính tổng stock, units sold, stockout days; đếm các flag.
6. Với `web_traffic`, tính sessions/page_views theo source và theo ngày.

Người làm đọc output và ghi nhận:

- Sales có xu hướng/mùa vụ sơ bộ không?
- COGS đi cùng Revenue không?
- Forecasting cần dự báo giai đoạn nào?
- Inventory là monthly snapshot, không cùng granularity với sales daily.
- Web traffic có thể dùng để giải thích demand hoặc marketing không?

## 11. File `09_build_eda_summary.py`

Mục tiêu: gom các output quan trọng thành một báo cáo đọc nhanh.

Output:

- `outputs/eda_initial/reports/09_eda_initial_summary.md`

Script cần làm:

1. Đọc các CSV summary đã tạo.
2. Ghi Markdown report gồm:
   - Danh sách bảng.
   - Shape từng bảng.
   - Date range từng bảng.
   - Top missing columns.
   - Key/join notes.
   - Các biểu đồ đã tạo.
   - Hướng EDA sâu đề xuất.
3. Không tự kết luận quá sâu; để phần "Người làm ghi nhận" trong report.

Cấu trúc report:

```markdown
# EDA Initial Summary

## 1. Dataset catalog

## 2. Time coverage

## 3. Missing and duplicate overview

## 4. Join map

## 5. Master data observations

## 6. Transaction data observations

## 7. Sales and operational observations

## 8. Open questions

## 9. Candidate deep EDA directions
```

## 12. File `10_draw_erd.py`

Mục tiêu: vẽ ERD/relationship map để nhìn nhanh các bảng nối với nhau như thế nào.

Output:

- `outputs/eda_initial/figures/10_erd_relationships.png`
- `outputs/eda_initial/figures/10_erd_relationships.svg`
- `outputs/eda_initial/tables/10_erd_relationships.csv`
- `outputs/eda_initial/reports/10_erd_notes.md`

Script cần làm:

1. Khai báo danh sách bảng, nhóm bảng và các khóa/cột chính.
2. Khai báo relationship giữa các bảng theo đề bài.
3. Vẽ từng bảng thành box, tô màu theo nhóm master/transaction/analytical/operational.
4. Vẽ mũi tên thể hiện quan hệ join.
5. Lưu hình ERD và bảng relationship ra output.

Người làm đọc output và ghi nhận:

- Bảng nào là trung tâm cho phân tích order-level.
- Bảng nào là trung tâm cho phân tích item/product-level.
- Join nào có nguy cơ làm nhân dòng.
- Bảng nào không nên join trực tiếp vì khác granularity.

## 13. File chạy tổng hợp `run_initial_eda.py`

Mục tiêu: chạy toàn bộ script theo đúng thứ tự.

Đặt ở thư mục gốc:

```text
run_initial_eda.py
```

Script cần chạy:

```python
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

scripts = [
    "01_data_catalog.py",
    "02_schema_overview.py",
    "03_time_coverage.py",
    "04_missing_duplicates.py",
    "05_key_join_overview.py",
    "06_master_data_overview.py",
    "07_transaction_overview.py",
    "08_sales_operational_overview.py",
    "10_draw_erd.py",
    "09_build_eda_summary.py",
]

for script in scripts:
    script_path = ROOT_DIR / "eda_scripts" / script
    print(f"Running {script_path}")
    subprocess.run([sys.executable, str(script_path)], check=True)

print("Initial EDA completed.")
print("Outputs saved to outputs/eda_initial/")
```

Cách chạy:

```bash
python run_initial_eda.py
```

## 14. Quy ước đặt tên output

Để dễ tìm lại, mọi file output nên bắt đầu bằng số thứ tự script:

```text
01_data_catalog.csv
02_dtype_summary.csv
03_date_ranges.csv
04_missing_summary.csv
05_key_summary.csv
06_products_by_category.png
07_orders_by_status.png
08_sales_monthly_revenue.png
10_erd_relationships.png
09_eda_initial_summary.md
```

Quy ước:

- CSV cho bảng.
- PNG cho biểu đồ.
- MD/TXT cho báo cáo.
- Không ghi đè dữ liệu gốc trong `data/`.
- Nếu chạy lại, cho phép ghi đè output cũ trong `outputs/eda_initial/`.

## 15. Các biểu đồ tối thiểu cần có

Nên tạo ít nhất các biểu đồ:

- `03_sales_revenue_timeline.png`: Revenue daily theo thời gian.
- `03_web_sessions_timeline.png`: Web sessions theo thời gian.
- `04_top_missing_columns.png`: top cột missing.
- `06_products_by_category.png`: số sản phẩm theo category.
- `06_customers_by_age_group.png`: số khách theo age group.
- `06_geography_by_region.png`: số zip/city theo region.
- `07_orders_by_status.png`: số đơn theo status.
- `07_payment_methods.png`: số thanh toán theo method.
- `07_return_reasons.png`: lý do trả hàng.
- `07_review_ratings.png`: phân bố rating.
- `08_sales_monthly_revenue.png`: monthly revenue.
- `08_inventory_flags.png`: tỷ lệ stockout/overstock/reorder.
- `10_erd_relationships.png`: ERD/relationship map giữa các bảng.

## 16. Data dictionary cần tạo sau khi chạy script

Sau khi xem output, người làm nên điền thủ công vào report hoặc một file riêng:

```markdown
| Table | Granularity | Key | Time column | Main metrics | Main dimensions | Join with | EDA potential |
|---|---|---|---|---|---|---|---|
| products | 1 row/product | product_id | none | price, cogs | category, segment, size, color | order_items, inventory | margin, product mix |
| customers | 1 row/customer | customer_id | signup_date | none | city, gender, age_group, acquisition_channel | orders | customer behavior |
```

Mục tiêu của data dictionary:

- Cả nhóm thống nhất mỗi bảng là gì.
- Tránh join sai granularity.
- Biết bảng nào dùng cho phân tích nào.

## 17. Hướng EDA sâu sau bước này

Sau khi chạy xong các script EDA sơ khởi, chọn 3-5 hướng để làm EDA chính:

1. Doanh thu và mùa vụ: dùng `sales`, có thể so với `web_traffic`.
2. Sản phẩm và lợi nhuận: dùng `products`, `order_items`, `orders`.
3. Khách hàng và kênh mua: dùng `customers`, `orders`, `payments`.
4. Khuyến mãi: dùng `promotions`, `order_items`, `orders`, `products`.
5. Trả hàng và review: dùng `returns`, `reviews`, `products`, `orders`.
6. Vận hành tồn kho: dùng `inventory`, `products`, có thể so với sales/order_items.

Mỗi hướng EDA sâu cần trả lời:

- Câu hỏi kinh doanh là gì?
- Bảng nào cần dùng?
- Join path là gì?
- Metric chính là gì?
- Dimension chính là gì?
- Biểu đồ nào phù hợp?
- Insight có thể dẫn đến đề xuất gì?

## 18. Checklist hoàn thành EDA sơ khởi

Hoàn thành bước này khi có đủ:

- `outputs/eda_initial/tables/01_data_catalog.csv`
- `outputs/eda_initial/tables/02_dtype_summary.csv`
- `outputs/eda_initial/tables/03_date_ranges.csv`
- `outputs/eda_initial/tables/04_missing_summary.csv`
- `outputs/eda_initial/tables/05_key_summary.csv`
- Các bảng summary cho master, transaction, sales, operational.
- Các biểu đồ tối thiểu trong `figures/`.
- `outputs/eda_initial/reports/09_eda_initial_summary.md`
- Một danh sách 3-5 hướng EDA sâu sẽ triển khai.

Nếu các output trên đã có, nhóm đã đủ bức tranh "mình đang có dữ liệu gì" để bắt đầu code phân tích sâu một cách có định hướng.

