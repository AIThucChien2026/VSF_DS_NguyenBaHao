"""Track existing modeling results and register the champion model in MLflow.

This script reuses the trained artifacts under report_14_6_2026. It does not
retrain the models.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

try:
    import mlflow
    import mlflow.sklearn
    from mlflow.models import infer_signature
    from mlflow.tracking import MlflowClient
except ImportError as exc:
    raise SystemExit(
        "MLflow is not installed. Run: "
        "python -m pip install -r requirements-mlflow.txt"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_16_DIR = PROJECT_ROOT / "report_16_6_2026"
MODEL_OUTPUT_DIR = PROJECT_ROOT / "report_14_6_2026" / "modeling_outputs"
MODEL_DIR = MODEL_OUTPUT_DIR / "models"
TABLE_DIR = MODEL_OUTPUT_DIR / "tables"
FIGURE_DIR = MODEL_OUTPUT_DIR / "figures"
REPORT_DIR = MODEL_OUTPUT_DIR / "reports"
FE_TABLE_DIR = PROJECT_ROOT / "report_12_6_2026" / "fe_outputs" / "tables"

MODEL_FILES = {
    "Logistic Regression Tuned": MODEL_DIR / "logistic_tuned.joblib",
    "Random Forest Tuned": MODEL_DIR / "random_forest_tuned.joblib",
    "LightGBM Tuned": MODEL_DIR / "final_model.joblib",
}

PARAM_FILES = {
    "Logistic Regression Tuned": TABLE_DIR / "phase7_logistic_best_params.json",
    "Random Forest Tuned": TABLE_DIR / "phase7_rf_best_params.json",
    "LightGBM Tuned": TABLE_DIR / "phase7_lgbm_best_params.json",
}

COMMON_ARTIFACTS = (
    TABLE_DIR / "model_comparison.csv",
    TABLE_DIR / "modeling_contract.csv",
    TABLE_DIR / "champion_model.json",
    TABLE_DIR / "final_test_metrics.csv",
    TABLE_DIR / "final_model_reload_audit.csv",
    FE_TABLE_DIR / "feature_cols_v1.csv",
    FE_TABLE_DIR / "phase5_model_schema.csv",
    REPORT_DIR / "Modeling_final_report.md",
)

CODE_ARTIFACTS = (
    PROJECT_ROOT / "report_14_6_2026" / "4_Modeling.ipynb",
    PROJECT_ROOT / "scripts" / "mlflow_track_and_register.py",
    PROJECT_ROOT / "scripts" / "README_mlflow.md",
    PROJECT_ROOT / "requirements-mlflow.txt",
)


class ThresholdedClassifier:
    """Serve class predictions with the validation-locked threshold."""

    def __init__(self, model: Any, threshold: float) -> None:
        self.model = model
        self.threshold = threshold

    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        return self.model.predict_proba(features)

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        positive_probability = self.predict_proba(features)[:, 1]
        return (positive_probability >= self.threshold).astype(int)


def parse_args() -> argparse.Namespace:
    default_db = (REPORT_16_DIR / "mlflow" / "mlflow.db").as_posix()
    parser = argparse.ArgumentParser(
        description="Track existing experiments and register the champion model."
    )
    parser.add_argument(
        "--tracking-uri",
        default=f"sqlite:///{default_db}",
        help="MLflow tracking URI. Defaults to a local SQLite database.",
    )
    parser.add_argument(
        "--experiment-name",
        default="customer-return-prediction",
        help="MLflow experiment name.",
    )
    parser.add_argument(
        "--registered-model-name",
        default="customer-return-champion",
        help="Model Registry name for the champion.",
    )
    parser.add_argument(
        "--alias",
        default="champion",
        help="Alias assigned to the newly registered champion version.",
    )
    parser.add_argument(
        "--run-name",
        default="model-comparison-and-registration",
        help="Name of the parent MLflow run.",
    )
    parser.add_argument(
        "--skip-registration",
        action="store_true",
        help="Track runs and models without adding the champion to Model Registry.",
    )
    return parser.parse_args()


def require_files(paths: list[Path] | tuple[Path, ...]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        formatted = "\n".join(f"- {path}" for path in missing)
        raise FileNotFoundError(f"Required project artifacts are missing:\n{formatted}")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def scalar(value: Any) -> bool:
    return isinstance(value, (str, bool, int, float)) and not (
        isinstance(value, float) and not math.isfinite(value)
    )


def clean_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.\-/ ]", "_", value).strip()


def row_metrics(row: pd.Series, prefix: str = "validation") -> dict[str, float]:
    metric_columns = (
        "pr_auc",
        "roc_auc",
        "precision",
        "recall",
        "f1",
        "balanced_accuracy",
        "fit_seconds",
        "mean_fold_pr_auc",
        "std_fold_pr_auc",
    )
    return {
        f"{prefix}_{column}": float(row[column])
        for column in metric_columns
        if column in row.index and pd.notna(row[column])
    }


def row_params(row: pd.Series) -> dict[str, Any]:
    param_columns = ("model", "threshold", "threshold_policy", "n_features")
    return {
        clean_key(column): row[column]
        for column in param_columns
        if column in row.index and pd.notna(row[column]) and scalar(row[column])
    }


def load_pipeline(model_name: str) -> Any:
    artifact = joblib.load(MODEL_FILES[model_name])
    if isinstance(artifact, dict):
        return artifact["model"]
    return artifact


def load_input_example(feature_columns: list[str]) -> pd.DataFrame:
    raw_test_path = FE_TABLE_DIR / "test_features_raw.csv"
    require_files([raw_test_path])
    input_example = pd.read_csv(
        raw_test_path,
        usecols=feature_columns,
        nrows=5,
    )
    integer_columns = input_example.select_dtypes(include="integer").columns
    input_example[integer_columns] = input_example[integer_columns].astype(float)
    return input_example


def ensure_experiment(
    client: MlflowClient, experiment_name: str, artifact_root: Path
) -> str:
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is not None:
        return experiment.experiment_id

    artifact_root.mkdir(parents=True, exist_ok=True)
    return mlflow.create_experiment(
        experiment_name,
        artifact_location=artifact_root.resolve().as_uri(),
        tags={
            "project": "customer_churn_PL",
            "problem_type": "binary_classification",
            "target": "returned_label",
        },
    )


def log_project_artifacts() -> None:
    for artifact in COMMON_ARTIFACTS:
        mlflow.log_artifact(str(artifact), artifact_path="project_metadata")

    for artifact in CODE_ARTIFACTS:
        if artifact.exists():
            mlflow.log_artifact(str(artifact), artifact_path="code")

    if FIGURE_DIR.exists():
        for figure in FIGURE_DIR.glob("*.png"):
            mlflow.log_artifact(str(figure), artifact_path="figures")


def get_registered_version(
    client: MlflowClient, model_name: str, run_id: str
) -> str:
    versions = client.search_model_versions(f"name='{model_name}'")
    matching = [version for version in versions if version.run_id == run_id]
    if not matching:
        raise RuntimeError(
            f"Could not find a registered version of {model_name!r} "
            f"for run {run_id}."
        )
    return str(max(matching, key=lambda version: int(version.version)).version)


def log_candidate(
    row: pd.Series,
    experiment_id: str,
    feature_columns: list[str],
    input_example: pd.DataFrame,
    champion_name: str,
    registered_model_name: str,
    skip_registration: bool,
) -> tuple[str, str | None]:
    model_name = str(row["model"])
    pipeline = load_pipeline(model_name)
    thresholded_model = ThresholdedClassifier(
        model=pipeline,
        threshold=float(row["threshold"]),
    )
    predictions = thresholded_model.predict(input_example)
    signature = infer_signature(input_example, predictions)
    best_params = read_json(PARAM_FILES[model_name])
    is_champion = model_name == champion_name

    with mlflow.start_run(
        experiment_id=experiment_id,
        run_name=model_name,
        nested=True,
    ) as child_run:
        mlflow.set_tags(
            {
                "model_name": model_name,
                "candidate_type": "tuned",
                "is_champion": str(is_champion).lower(),
                "evaluation_split": "validation",
            }
        )
        mlflow.log_params(row_params(row))
        mlflow.log_params(
            {
                f"best_{clean_key(key)}": value
                for key, value in best_params.items()
                if scalar(value)
            }
        )
        mlflow.log_metrics(row_metrics(row))
        mlflow.log_artifact(str(PARAM_FILES[model_name]), artifact_path="tuning")

        if is_champion:
            test_row = pd.read_csv(TABLE_DIR / "final_test_metrics.csv").iloc[0]
            mlflow.log_metrics(row_metrics(test_row, prefix="test"))
            mlflow.set_tag("threshold_locked_from", "validation_max_f1")
            log_project_artifacts()

        model_info = mlflow.sklearn.log_model(
            sk_model=thresholded_model,
            name="model",
            signature=signature,
            input_example=input_example,
            registered_model_name=(
                registered_model_name
                if is_champion and not skip_registration
                else None
            ),
            metadata={
                "feature_count": len(feature_columns),
                "decision_threshold": float(row["threshold"]),
                "target": "returned_label",
                "positive_class": "returned = 1",
            },
        )

        mlflow.set_tag("logged_model_uri", model_info.model_uri)
        return child_run.info.run_id, (
            registered_model_name
            if is_champion and not skip_registration
            else None
        )


def main() -> None:
    args = parse_args()
    required = [
        TABLE_DIR / "model_comparison.csv",
        TABLE_DIR / "champion_model.json",
        TABLE_DIR / "final_test_metrics.csv",
        FE_TABLE_DIR / "feature_cols_v1.csv",
        *MODEL_FILES.values(),
        *PARAM_FILES.values(),
        *COMMON_ARTIFACTS,
    ]
    require_files(required)

    tracking_dir = REPORT_16_DIR / "mlflow"
    tracking_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(args.tracking_uri)
    client = MlflowClient()
    experiment_id = ensure_experiment(
        client,
        args.experiment_name,
        tracking_dir / "artifacts",
    )

    comparison = pd.read_csv(TABLE_DIR / "model_comparison.csv")
    champion = read_json(TABLE_DIR / "champion_model.json")
    champion_name = str(champion["model"])
    feature_columns = pd.read_csv(FE_TABLE_DIR / "feature_cols_v1.csv")[
        "feature"
    ].tolist()
    input_example = load_input_example(feature_columns)

    champion_run_id: str | None = None
    with mlflow.start_run(
        experiment_id=experiment_id,
        run_name=args.run_name,
        tags={
            "run_type": "model_comparison",
            "project": "customer_churn_PL",
            "primary_metric": "pr_auc",
        },
    ) as parent_run:
        mlflow.log_param("candidate_count", len(comparison))
        mlflow.log_param("champion_model", champion_name)
        mlflow.log_param("feature_count", len(feature_columns))
        mlflow.log_metric(
            "best_validation_pr_auc", float(comparison["pr_auc"].max())
        )

        for _, candidate_row in comparison.iterrows():
            run_id, registered_name = log_candidate(
                row=candidate_row,
                experiment_id=experiment_id,
                feature_columns=feature_columns,
                input_example=input_example,
                champion_name=champion_name,
                registered_model_name=args.registered_model_name,
                skip_registration=args.skip_registration,
            )
            if registered_name is not None:
                champion_run_id = run_id

        parent_run_id = parent_run.info.run_id

    registered_version: str | None = None
    if champion_run_id is not None:
        registered_version = get_registered_version(
            client, args.registered_model_name, champion_run_id
        )
        client.set_registered_model_alias(
            args.registered_model_name, args.alias, registered_version
        )
        client.set_model_version_tag(
            args.registered_model_name,
            registered_version,
            "validation_status",
            "champion",
        )
        client.set_model_version_tag(
            args.registered_model_name,
            registered_version,
            "decision_threshold",
            str(champion["selected_threshold"]),
        )
        client.update_model_version(
            name=args.registered_model_name,
            version=registered_version,
            description=(
                "LightGBM pipeline selected by validation PR-AUC and temporal "
                "stability. The decision threshold was locked on validation."
            ),
        )

    print(f"Tracking URI: {mlflow.get_tracking_uri()}")
    print(f"Experiment: {args.experiment_name} (ID: {experiment_id})")
    print(f"Parent run ID: {parent_run_id}")
    if registered_version is not None:
        print(
            f"Registered model: {args.registered_model_name} "
            f"version {registered_version} (alias: {args.alias})"
        )
        print(
            f"Model URI: models:/{args.registered_model_name}@{args.alias}"
        )
    else:
        print("Model registration was skipped.")


if __name__ == "__main__":
    main()
