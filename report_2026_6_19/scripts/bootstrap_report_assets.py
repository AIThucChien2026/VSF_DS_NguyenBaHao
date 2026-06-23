"""Bootstrap the report workspace by copying source data and artifacts.

The script mirrors the intended report structure:
  report_2026_6_19/
    data/
    artifacts/
    outputs/

What it does:
  - copies the 5 required CSV files from the workspace root `data/`
  - skips `returns.csv` by design
  - copies `preprocessor_v1_outer_train.joblib` from FE outputs first, then from root `artifacts/`
  - copies the model bundle from `report_2026_06_14/modeling_outputs/models`
  - optionally generates `outputs/cleaned_sample.csv` and `features_sample.csv`
  - optionally tries to generate `predictions_sample.csv` if the pipeline can be built

The script is intentionally defensive:
  if a source artifact is missing, it prints a warning and continues.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REQUIRED_DATA_FILES = [
    "orders.csv",
    "order_items.csv",
    "customers.csv",
    "products.csv",
    "payments.csv",
]

EXPECTED_ARTIFACTS = [
    "final_model.joblib",
    "logistic_tuned.joblib",
    "random_forest_tuned.joblib",
    "preprocessor_v1_outer_train.joblib",
]


def copy_file(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def safe_print(message: str) -> None:
    print(message.encode("ascii", "backslashreplace").decode("ascii"))


def write_text_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def first_existing_path(*candidates: Path) -> Path | None:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def generate_samples(report_root: Path) -> None:
    sys.path.insert(0, str(report_root))
    try:
        from scripts.clean_data import clean_data
        from scripts.inference_pipeline import FeatureBuilder, InferencePipeline
    except Exception as exc:  # pragma: no cover - defensive bootstrap
        safe_print(f"[warn] Skip sample generation: cannot import pipeline modules ({exc})")
        return

    data_dir = report_root / "data"
    outputs_dir = report_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    try:
        cleaned_df, summary = clean_data(str(data_dir))
        cleaned_sample = cleaned_df.head(5).copy()
        cleaned_sample.to_csv(outputs_dir / "cleaned_sample.csv", index=False)
        print(f"[ok] wrote outputs/cleaned_sample.csv ({summary['n_orders']} rows source)")
    except Exception as exc:
        safe_print(f"[warn] Skip cleaned sample: {exc}")
        return

    try:
        fb = FeatureBuilder()
        features_df = fb.transform(cleaned_df)
        features_df.head(5).to_csv(outputs_dir / "features_sample.csv", index=False)
        print("[ok] wrote outputs/features_sample.csv")
    except Exception as exc:
        safe_print(f"[warn] Skip features sample: {exc}")

    try:
        pipeline = InferencePipeline(
            preprocessor_path=str(report_root / "artifacts" / "preprocessor_v1_outer_train.joblib"),
            fallback_model_path=str(report_root / "artifacts" / "final_model.joblib"),
        )
        predictions_df = pipeline.predict(cleaned_df)
        predictions_df.head(5).to_csv(outputs_dir / "predictions_sample.csv", index=False)
        print("[ok] wrote outputs/predictions_sample.csv")
    except Exception as exc:
        safe_print(f"[warn] Skip predictions sample: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap report_2026_6_19 assets")
    parser.add_argument(
        "--source-root",
        default=None,
        help="Workspace root that contains source data/ and artifacts/ (default: parent of report folder)",
    )
    parser.add_argument(
        "--generate-samples",
        action="store_true",
        help="Generate cleaned/features sample outputs after copying data",
    )
    args = parser.parse_args()

    report_root = Path(__file__).resolve().parent.parent
    source_root = Path(args.source_root).resolve() if args.source_root else report_root.parent
    source_data_root = source_root / "data"
    source_model_root = source_root / "report_2026_06_14" / "modeling_outputs" / "models"
    source_preprocessor_candidates = [
        source_root / "report_2026_06_12" / "fe_outputs" / "tables" / "preprocessor_v1_outer_train.joblib",
        source_root / "artifacts" / "preprocessor_v1_outer_train.joblib",
    ]

    dest_data_root = report_root / "data"
    dest_artifacts_root = report_root / "artifacts"
    dest_outputs_root = report_root / "outputs"

    dest_data_root.mkdir(parents=True, exist_ok=True)
    dest_artifacts_root.mkdir(parents=True, exist_ok=True)
    dest_outputs_root.mkdir(parents=True, exist_ok=True)

    print(f"[info] source root      : {source_root}")
    print(f"[info] report root      : {report_root}")

    copied = []
    for filename in REQUIRED_DATA_FILES:
        src = source_data_root / filename
        dst = dest_data_root / filename
        if copy_file(src, dst):
            copied.append(filename)
            print(f"[ok] data  : {filename}")
        else:
            print(f"[warn] missing data source: {src}")

    for artifact_name in EXPECTED_ARTIFACTS:
        if artifact_name == "preprocessor_v1_outer_train.joblib":
            src = first_existing_path(*source_preprocessor_candidates)
        else:
            src = source_model_root / artifact_name
        dst = dest_artifacts_root / artifact_name
        if src and copy_file(src, dst):
            print(f"[ok] model : {artifact_name}")
        else:
            missing_src = src if src is not None else source_preprocessor_candidates[0]
            print(f"[warn] missing artifact source: {missing_src}")

    write_text_if_missing(
        report_root / "data" / "README.md",
        "# data/\n\nThis folder is populated by `scripts/bootstrap_report_assets.py`.\n"
        "It intentionally keeps only the five inference inputs:\n"
        "`orders.csv`, `order_items.csv`, `customers.csv`, `products.csv`, `payments.csv`.\n",
    )
    write_text_if_missing(
        report_root / "artifacts" / "README.md",
        "# artifacts/\n\nExpected inference artifacts:\n"
        "- `final_model.joblib`\n"
        "- `logistic_tuned.joblib`\n"
        "- `random_forest_tuned.joblib`\n"
        "- `preprocessor_v1_outer_train.joblib`\n\n"
        "The bootstrap script copies them from the source report/model folders if they exist.\n",
    )
    write_text_if_missing(
        report_root / "outputs" / "README.md",
        "# outputs/\n\nGenerated inference samples live here.\n"
        "Typical files: `cleaned_sample.csv`, `features_sample.csv`, `predictions_<run_id>.csv`.\n",
    )

    if args.generate_samples:
        generate_samples(report_root)

    print(f"[done] copied {len(copied)} data files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
