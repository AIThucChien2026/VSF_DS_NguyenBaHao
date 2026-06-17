from pathlib import Path
import shutil

import cloudpickle
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


ROOT = Path(__file__).resolve().parents[1]
RUN_ARTIFACTS = ROOT / "mlruns" / "0" / "ae17df93b4a54e229d955aacd87cad29" / "artifacts"
MODEL_PATH = ROOT / "mlruns" / "0" / "models" / "m-0546808e0cca46f8a80a239d26e8c111" / "artifacts" / "model.pkl"
FE_TABLES = ROOT / "report_12_6_2026" / "fe_outputs" / "tables"
OUT_ROOT = ROOT / "report_14_6_2026" / "modeling_outputs"
FIG_DIR = OUT_ROOT / "figures"
TABLE_DIR = OUT_ROOT / "tables"
REPORT_DIR = OUT_ROOT / "reports"

TARGET = "returned_label"


def ensure_dirs() -> None:
    for path in [FIG_DIR, TABLE_DIR, REPORT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def copy_existing_artifacts() -> None:
    for src_dir, dst_dir in [
        (RUN_ARTIFACTS / "figures", FIG_DIR),
        (RUN_ARTIFACTS / "project_metadata", TABLE_DIR),
    ]:
        if not src_dir.exists():
            continue
        for src in src_dir.iterdir():
            if src.is_file():
                shutil.copy2(src, dst_dir / src.name)

    report_src = RUN_ARTIFACTS / "project_metadata" / "Modeling_final_report.md"
    if report_src.exists():
        shutil.copy2(report_src, REPORT_DIR / "Modeling_final_report.md")


def load_inputs():
    feature_cols = pd.read_csv(TABLE_DIR / "feature_cols_v1.csv")["feature"].tolist()
    champion = pd.read_json(TABLE_DIR / "champion_model.json", typ="series")
    threshold = float(champion["selected_threshold"])
    test_df = pd.read_csv(FE_TABLES / "test_features_raw.csv")
    with MODEL_PATH.open("rb") as f:
        model = cloudpickle.load(f)
    proba = model.predict_proba(test_df[feature_cols])[:, 1]
    y_true = test_df[TARGET].astype(int).to_numpy()
    return feature_cols, threshold, test_df, y_true, proba


def save_selected_threshold_metrics(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> None:
    y_pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    metrics = pd.DataFrame(
        [
            {
                "split": "test",
                "threshold": threshold,
                "pr_auc": average_precision_score(y_true, proba),
                "roc_auc": roc_auc_score(y_true, proba),
                "precision": precision_score(y_true, y_pred, zero_division=0),
                "recall": recall_score(y_true, y_pred, zero_division=0),
                "f1": f1_score(y_true, y_pred, zero_division=0),
                "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
                "predicted_positive_rate": float(y_pred.mean()),
                "true_negative": int(tn),
                "false_positive": int(fp),
                "false_negative": int(fn),
                "true_positive": int(tp),
            }
        ]
    )
    metrics.to_csv(TABLE_DIR / "phase10_test_selected_threshold_metrics.csv", index=False)


def plot_score_distribution(y_true: np.ndarray, proba: np.ndarray, threshold: float) -> None:
    returned = proba[y_true == 1]
    delivered = proba[y_true == 0]
    bins = np.linspace(proba.min(), proba.max(), 45)

    summary_rows = []
    for label_name, values in [("delivered", delivered), ("returned", returned)]:
        quantiles = np.quantile(values, [0.05, 0.25, 0.5, 0.75, 0.95])
        summary_rows.append(
            {
                "split": "test",
                "label": label_name,
                "n_rows": len(values),
                "score_min": float(values.min()),
                "score_q05": float(quantiles[0]),
                "score_q25": float(quantiles[1]),
                "score_median": float(quantiles[2]),
                "score_q75": float(quantiles[3]),
                "score_q95": float(quantiles[4]),
                "score_max": float(values.max()),
            }
        )
    pd.DataFrame(summary_rows).to_csv(TABLE_DIR / "phase10_test_score_distribution_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.hist(delivered, bins=bins, density=True, alpha=0.58, label="Delivered (0)", color="#4C78A8")
    ax.hist(returned, bins=bins, density=True, alpha=0.58, label="Returned (1)", color="#F58518")
    ax.axvline(threshold, color="#222222", linestyle="--", linewidth=1.6, label=f"Locked threshold {threshold:.4f}")
    ax.set_title("Test Score Distribution by True Label")
    ax.set_xlabel("Predicted return probability")
    ax.set_ylabel("Density")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "phase10_test_score_distribution_by_label.png", dpi=160)
    plt.close(fig)


def plot_decile_lift(y_true: np.ndarray, proba: np.ndarray) -> None:
    df = pd.DataFrame({"returned_label": y_true, "score": proba})
    df["score_decile"] = pd.qcut(df["score"], q=10, labels=False, duplicates="drop") + 1
    base_rate = df["returned_label"].mean()
    deciles = (
        df.groupby("score_decile", observed=True)
        .agg(
            n_rows=("returned_label", "size"),
            returned_count=("returned_label", "sum"),
            return_rate=("returned_label", "mean"),
            score_min=("score", "min"),
            score_max=("score", "max"),
        )
        .reset_index()
    )
    deciles["lift_vs_test_base_rate"] = deciles["return_rate"] / base_rate
    deciles.to_csv(TABLE_DIR / "phase10_test_score_decile_lift.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5.5))
    x = deciles["score_decile"].astype(int)
    bars = ax.bar(x, deciles["return_rate"] * 100, color="#54A24B", alpha=0.88)
    ax.axhline(base_rate * 100, color="#222222", linestyle="--", linewidth=1.4, label=f"Test base rate {base_rate * 100:.2f}%")
    ax.set_title("Observed Return Rate by Test Score Decile")
    ax.set_xlabel("Score decile (1 = lowest risk, 10 = highest risk)")
    ax.set_ylabel("Observed return rate (%)")
    ax.set_xticks(x)
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    for bar, lift in zip(bars, deciles["lift_vs_test_base_rate"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{lift:.2f}x",
            ha="center",
            va="bottom",
            fontsize=8,
        )
    fig.tight_layout()
    fig.savefig(FIG_DIR / "phase10_test_score_decile_lift.png", dpi=160)
    plt.close(fig)


def write_chart_review() -> None:
    review_rows = [
        {
            "chart": "phase2_label_distribution.png",
            "decision": "keep",
            "reason": "Shows class imbalance before interpreting PR-AUC and threshold metrics.",
        },
        {
            "chart": "phase5_model_comparison.png",
            "decision": "keep",
            "reason": "Compares candidate models; useful for champion selection review.",
        },
        {
            "chart": "phase6_pr_roc_curves.png",
            "decision": "keep",
            "reason": "Shows initial model ranking under PR/ROC views.",
        },
        {
            "chart": "phase8_tuned_pr_roc_curves.png",
            "decision": "keep",
            "reason": "Shows tuned model ranking after hyperparameter search.",
        },
        {
            "chart": "phase9_confusion_calibration.png",
            "decision": "keep",
            "reason": "Useful for operating-point and calibration review.",
        },
        {
            "chart": "phase9_top_feature_importance.png",
            "decision": "keep",
            "reason": "Quick sanity check of champion drivers against leakage policy.",
        },
        {
            "chart": "phase9_shap_summary.png",
            "decision": "keep",
            "reason": "More detailed interpretability review on validation sample.",
        },
        {
            "chart": "phase10_test_score_distribution_by_label.png",
            "decision": "added",
            "reason": "Shows whether final model separates returned and delivered orders on untouched test data.",
        },
        {
            "chart": "phase10_test_score_decile_lift.png",
            "decision": "added",
            "reason": "Shows whether score ranking is useful for business review/risk triage.",
        },
        {
            "chart": "validation_threshold_optimization_from_final_model",
            "decision": "not_added",
            "reason": "Final model is refit on train+validation, so recomputing validation threshold curves from model.pkl would be in-sample and misleading.",
        },
    ]
    pd.DataFrame(review_rows).to_csv(TABLE_DIR / "modeling_chart_review.csv", index=False)

    report = """# Modeling Chart Review

## Ket Luan
Can bo sung chart, nhung chi bo sung chart co ich cho review van hanh. Bo chart san co da du de cover label imbalance, model comparison, PR/ROC, confusion/calibration va interpretability. Phan con thieu la nhin tren untouched test data: score co tach duoc returned/delivered khong va ranking theo score co tao lift khong.

## Chart Da Bo Sung
- `phase10_test_score_distribution_by_label.png`: phan phoi score tren test theo true label, co vach threshold da lock. Chart nay giup thay ro muc overlap giua returned va delivered, nen co y nghia hon viec them chart model comparison lap lai.
- `phase10_test_score_decile_lift.png`: return rate thuc te theo decile score tren test. Chart nay tra loi cau hoi model co dung duoc de rank/risk triage khong.

## Chart Khong Bo Sung
- Khong tao validation threshold optimization tu `model.pkl`, vi final model da refit tren train+validation. Ve chart threshold tren validation bang final model se la in-sample va de gay hieu nham.
- Khong them chart trang tri hoac chart trung lap voi PR/ROC/model comparison/SHAP da co.

## Nhan Xet Review
Neu decile cao nhat chi lift nhe so voi base rate thi model nen dung lam risk ranking ho tro, khong nen auto-decision. Neu score distribution cua hai label overlap manh, do la bang chung truc quan cho ket luan metric: model co tin hieu nhung separation con yeu.
"""
    (REPORT_DIR / "modeling_chart_review.md").write_text(report, encoding="utf-8")

    final_report = REPORT_DIR / "Modeling_final_report.md"
    if final_report.exists():
        text = final_report.read_text(encoding="utf-8")
        text = text.replace("phase9_test_score_distribution_by_label.png", "phase10_test_score_distribution_by_label.png")
        text = text.replace("phase9_test_score_decile_lift.png", "phase10_test_score_decile_lift.png")
        marker = "## Chart Review\n"
        if marker not in text:
            text += (
                "\n\n" + marker
                + "- Existing charts are kept because they support label imbalance, model comparison, PR/ROC, calibration/confusion and interpretability review.\n"
                + "- Added `phase10_test_score_distribution_by_label.png` to inspect score overlap by true label on untouched test data.\n"
                + "- Added `phase10_test_score_decile_lift.png` to inspect whether the score is useful for risk ranking/triage.\n"
                + "- Did not add validation threshold optimization from final `model.pkl` because final model was refit on train+validation, making that validation chart in-sample.\n"
            )
            final_report.write_text(text, encoding="utf-8")
        shutil.copy2(final_report, TABLE_DIR / "Modeling_final_report.md")


def main() -> None:
    ensure_dirs()
    copy_existing_artifacts()
    _, threshold, _, y_true, proba = load_inputs()
    save_selected_threshold_metrics(y_true, proba, threshold)
    plot_score_distribution(y_true, proba, threshold)
    plot_decile_lift(y_true, proba)
    write_chart_review()


if __name__ == "__main__":
    main()
