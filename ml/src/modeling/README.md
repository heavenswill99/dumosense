# Model tooling

This folder contains the active model scripts. Run commands from `ml/` with Python 3.11.

| Script | Purpose |
| --- | --- |
| `save_model_artifacts.py` | Export the verified statistical coefficients and fidelity surrogate. |
| `predict_statistical_models.py` | Make a population prediction from a verified statistical bundle. |
| `train_ml_models.py` | Fit the initial five-family synthetic benchmark. |
| `tune_ml_models.py` | Search a bounded set of settings using development users. |
| `package_ml_models.py` | Copy 13 fitted estimators and aggregate metrics to `weights/`. |
| `verify_ml_run.py` | Check run/package hashes and independently recalculate test metrics. |

`engine_v3.py` and `mvp_pipeline.py` remain in `src/` because they are the active statistical worker. Generated run details stay in ignored `outputs/`; only versioned model packages belong in `weights/`. See [ML benchmark](../../README_ML.md) for data splits, evaluation and limitations.
