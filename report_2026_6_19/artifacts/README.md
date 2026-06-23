# artifacts/

Expected inference artifacts:

- `final_model.joblib`
- `logistic_tuned.joblib`
- `random_forest_tuned.joblib`
- `preprocessor_v1_outer_train.joblib`

The bootstrap script copies the model files from
`report_2026_06_14/modeling_outputs/models`.
It copies `preprocessor_v1_outer_train.joblib` from
`report_2026_06_12/fe_outputs/tables` first, then falls back to the root
`artifacts/` folder if needed.
