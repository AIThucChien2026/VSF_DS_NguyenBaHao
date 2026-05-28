"""
Mục tiêu:
    Chạy toàn bộ pipeline EDA sơ khởi theo đúng thứ tự.

Input:
    - Thư mục data/ chứa các file CSV.
    - Các script trong eda_scripts/.

Quy trình:
    - Lần lượt chạy 01_data_catalog.py đến 09_build_eda_summary.py bằng Python hiện tại.
    - Dừng lại nếu bất kỳ script nào lỗi.

Output:
    - outputs/eda_initial/tables/: các bảng CSV summary.
    - outputs/eda_initial/figures/: các biểu đồ PNG.
    - outputs/eda_initial/reports/: các report TXT/MD.

Cách chạy:
    python run_initial_eda.py
"""

import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent

SCRIPTS = [
    "01_data_catalog.py",
    "02_schema_overview.py",
    "03_time_coverage.py",
    "04_missing_duplicates.py",
    "05_key_join_overview.py",
    "05_data_quality_validation.py",
    "06_master_data_overview.py",
    "07_transaction_overview.py",
    "08_sales_operational_overview.py",
    "9_ERD.py",
]


def main():
    for script in SCRIPTS:
        script_path = ROOT_DIR / "eda_scripts" / script
        print(f"Running {script}")
        subprocess.run([sys.executable, str(script_path)], check=True)

    print("Initial EDA completed.")
    print("Outputs saved to outputs/eda_initial")


if __name__ == "__main__":
    main()
