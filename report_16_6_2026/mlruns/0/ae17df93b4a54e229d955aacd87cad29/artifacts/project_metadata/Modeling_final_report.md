# Modeling Final Report

## Problem
- Binary classification: Returned = 1, Delivered = 0.
- Grain: one row per order.
- Prediction time: order placement.
- Label source: orders.order_status.
- Only features available at or before order_date are used.
- Main feature count: 28.
- Train / validation / test rows: 386,907 / 82,906 / 83,045.

## Leakage Governance
- Centralized FE leakage gate banned 3 features.
- Banned features: high_risk_product_count, max_product_return_rate, mean_product_return_rate.
- Modeling fails before training if a banned feature appears in any feature set or raw split.
- Preprocessing is refit within each temporal CV fold.

## Model Selection
- Compared Logistic Regression, Random Forest and LightGBM.
- Primary metric: PR-AUC.
- Champion: LightGBM Tuned.
- Validation PR-AUC: 0.082374.
- Validation ROC-AUC: 0.552626.
- Locked threshold: 0.063357.

## Final Test
- Test PR-AUC: 0.084922.
- Test ROC-AUC: 0.548519.
- Test precision: 0.115128.
- Test recall: 0.235675.
- Test F1: 0.154690.
- Test balanced accuracy: 0.552761.

## Governance
- Feature Engineering readiness passed: True.
- Threshold was selected on outer validation.
- Test was evaluated once after champion lock.