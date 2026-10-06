# Saved model packages

Each versioned subfolder contains model parameters or fitted estimators and an integrity manifest. These files are based on synthetic data and are for engineering validation, not clinical use.

| Package | Contents |
| --- | --- |
| `20260926T143802_134359Z/` | Statistical coefficients, baseline rule, training reference, and fidelity surrogate. |
| `ml_20260926T170633_659162Z/` | Initial five-family benchmark: 13 estimators in `weights/`, metrics, and manifest. |
| `ml_tuned_20260926T173724_230556Z/` | Bounded development-tuned benchmark: 13 estimators in `weights/`, metrics, and manifest. |
| `hr_ml_20261006T135923_863977Z/` | Health Reserve next-assessment benchmark: 9 estimators in `weights/`, metrics, and manifest. |

Both MindGuard ML packages are retained. Their comparison is in [the MindGuard benchmark](../README_ML.md); neither is approved for automatic alerts. The separate Health Reserve package is explained in [its ML benchmark](../README_HEALTH_RESERVE_ML.md). From `ml/`, verify MindGuard with `python src/modeling/verify_ml_run.py` and Health Reserve with `python src/health_reserve/verify_ml_run.py`.

`.joblib` files are Python pickle artifacts. Load only from a trusted source after verifying the package hash manifest. The package does not contain user-level predictions or raw run logs.

The existing manifests record the source-file hashes at the time each package was created. Moving the model scripts into `src/modeling/` changed their file bytes, so those historical source hashes are provenance records; the package file hashes still verify the preserved weights and metrics.
