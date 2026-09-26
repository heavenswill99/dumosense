# Dumosense MindGuard ML

This folder contains the reproducible **statistical development baseline** for MindGuard. It turns synthetic cognitive session data into personal history summaries, fits descriptive statistical models, and measures change detection against synthetic interval labels. It is intended for engineering and model research. The present change detector does not support automatic user alerts.

The current reference run is `20260926T143802_134359Z`, produced by `STAT_ENGINE_MVP_1.0` on 26 September 2026. Its run manifest, metrics, detailed session output, logs, and plots are under `outputs/runs/20260926T143802_134359Z/` on the development machine. `outputs/latest_successful_run.json` points to the most recent completed run. These generated files are intentionally excluded from Git.

## What is here

| Path | Purpose |
| --- | --- |
| `src/engine_v3.py` | Validated data joins, exact historical median/MAD baselines, evaluation helpers, and mixed model fitting. |
| `src/mvp_pipeline.py` | End to end run orchestration, split and label alignment, four statistical fits, metrics, SHAP fidelity study, reports, and failure tracking. |
| `src/insight_adapter.py` | Example nonclinical session summary adapter with user identity and consent checks at its boundary. |
| `src/verify_run.py` | Independent read only verification of a completed run's hashes, baselines, and confusion counts. |
| `src/save_model_artifacts.py` | Packages model parameters from a verified run and recreates the fidelity surrogate. |
| `src/predict_statistical_models.py` | Loads a saved statistical parameter bundle and calculates a population prediction. |
| `model_artifacts/<run_id>/` | Small, versioned model files and their hash manifest. |
| `tests/test_mvp*.py` | Unit and failure lifecycle tests for the active worker. |
| `README_MVP.md` | Short operational and release boundary note. |

Older `engine_v1.py`, `engine_v2.py`, and exploratory scripts remain locally for reference. The supported entry point is `engine_v3.py`.

## Data and timing contract

The default input files are in the repository's sibling `data/synthetic/` and `validation/` folders. The worker joins cognitive results to **completed** sessions and assessment types. A session's `calculated_at` is the moment its result becomes available. Each personal baseline uses only valid observations with **strictly earlier** result timestamps; tied results do not see one another. Context and wellbeing records are joined backward in time and used descriptively.

The synthetic ground truth is a user and date interval label aligned to the session start. It does not establish clinical onset, direction of change, recovery, or diagnosis. The historical baseline needs at least three prior observations and a nonzero median absolute deviation. Otherwise the result is marked `insufficient_data` with a reason. The selected hybrid rule tries a same domain accuracy baseline first and uses a cross domain accuracy baseline when the former is unavailable. A separate adjusted strategy uses training only domain and difficulty reference values.

The run divides users deterministically into train, development, and test groups (60/20/20 by SHA256). Reference statistics use train users before a fixed time cutoff. Development data choose a rule and threshold; held out users after the cutoff are evaluated once. All four statistical regression fits are **descriptive in sample fits over the full synthetic dataset**. Their in sample fit measures must not be described as held out regression performance.

## Saved model parameters

The original run recorded coefficients, uncertainty, variance terms, diagnostics, and evaluation JSON, but had no dedicated model package. `model_artifacts/20260926T143802_134359Z/` now contains:

| File | Meaning | Prediction output |
| --- | --- | --- |
| `accuracy.json` | Random intercept mixed model for accuracy, fitted with REML. | Population fixed effect accuracy on the 0 to 1 scale. |
| `rt.json` | Random intercept mixed model for log median reaction time, fitted with REML. | Exponentiated population prediction in milliseconds. |
| `rt_clustered_ols.json` | Log reaction time OLS with user clustered standard errors. | Exponentiated population prediction in milliseconds. |
| `accuracy_binomial_clustered.json` | Binomial successes and failures model with user clustered standard errors. | Probability of a correct trial. |
| `baseline_rule.json` and `training_reference.csv` | Historical rule configuration, selected research threshold, and training domain/difficulty references. | A rule requiring a user's prior sessions; no global learned weights. |
| `fidelity_surrogate.joblib` | Random forest trained to mimic the engine's state output. | Engine fidelity only; **not** prediction of real change. |
| `bundle_manifest.json` | Source run and SHA256 hashes for the files above. | Provenance and integrity checks. |

The four statistical JSON files contain the complete reported global coefficients and uncertainty/variance estimates. Mixed model **user specific random intercepts are not exported**; `predict_statistical_models.py` therefore gives population predictions. The package does not contain a serialized statsmodels object. `joblib` is a Python pickle format: load the surrogate only from a trusted source after checking the bundle hash. The surrogate was recreated from the verified session export with the original random seed and split, then reloaded and checked against the original test confusion matrix and metrics.

These files are small and based on synthetic data. They are suitable for versioning together with this code. The generated run JSONL, session level predictions, and historical logs stay outside Git. For a new run, export to a **new** run ID folder; do not overwrite the package for this run.

## What the current numbers say

The latest completed run processed 45,775 cognitive sessions from 7,999 users. Across 27,981 user and domain combinations, the median is one session, and 3,967 combinations have at least three sessions. This limits personal baseline coverage.

| Measure | Current result | Interpretation |
| --- | ---: | --- |
| Accuracy mixed model ICC | 0.0245 | Small user random intercept variance in this synthetic data. |
| Accuracy mixed model marginal / conditional R² | 0.0535 / 0.0767 | Descriptive in sample fit. |
| RT mixed model ICC | 0.0061 | RT `lbfgs` failed; `bfgs` converged and warnings remain recorded. |
| RT mixed model marginal / conditional R² | 0.2723 / 0.2768 | Descriptive in sample fit on log RT. |
| RT clustered OLS R² | 0.2724 | Descriptive in sample comparison. |
| Held out change detector balanced accuracy | **47.6%** | Below the 50% always negative balanced accuracy reference. |
| Held out sensitivity / false positive rate | **27.1% / 32.0%** | Too many misses and false alarms for automated alerts. |
| Held out evaluable coverage | **81.2%** | 123 of 654 held out labelled sessions abstained. |
| Surrogate fidelity accuracy | 99.53% | Reproduces the rule engine output; does not validate change detection. |

Held out change evaluation used 654 labelled sessions from 280 users: TP 35, TN 357, FP 168, FN 94. Its user bootstrap 95% balanced accuracy interval was 43.5% to 52.2%. The engine's `insufficient_data` state is counted as no alert in the full view; conditional metrics exclude abstentions. Historical model selection has already seen this synthetic dataset, so the held out split is internal evidence, not external validation.

## Install and run

Use Python 3.11. Install the pinned dependencies from this folder:

```powershell
Set-Location 'C:\Users\HP\Downloads\dumosense\ml'
python -m pip install -r .\requirements-mvp.txt
python .\src\test_engine_v3.py
.\run_mvp.cmd
```

`run_mvp.cmd` executes tests before a full run, then writes a unique `outputs/runs/<run_id>/` directory. It updates `outputs/latest_successful_run.json` only after completion. A full run took about five minutes on the reference machine. Use `python .\src\engine_v3.py --help` for custom data and output directories. Inputs are read only; the worker does not write to the application database.

Check the finished run independently:

```powershell
python .\src\verify_run.py .\outputs\runs\20260926T143802_134359Z
```

Package the latest verified run's models (the default destination must not already exist):

```powershell
python .\src\save_model_artifacts.py
```

For this existing bundle, a population prediction can be calculated as follows:

```powershell
python .\src\predict_statistical_models.py --model accuracy_binomial_clustered --started-at '2026-05-01T12:00:00+00:00' --difficulty 2 --domain attention
```

That prediction is a descriptive expected trial accuracy from synthetic training data. It is not a personal change score. Historical personal baselines also require the user's earlier sessions and should be generated by the worker. The `insight_adapter.py` gives only a descriptive same domain summary; application authentication and current consent must be enforced by the backend.

## Reproducibility and integrity

Each run contains a manifest with input and source hashes, dependency versions, test output, failure state, artifact hashes, warnings, summary metrics, session records, and plots. `verify_run.py` independently checks the 45,775 exported session baselines, 12 confusion views, and artifact hashes. The reference run passed that verification and 34 unit tests. The new model bundle records its source manifest SHA256 and hashes every exported file. Rerunning the surrogate reconstruction reproduces its original metrics and confusion matrix exactly.

The `outputs/` directory is ignored by Git because it contains large generated files and session level data. `old_logs/` is a sibling of `ml/` and should also remain out of commits. Stage reviewed ML source and small model artifacts explicitly; do not stage the whole repository blindly.

## Release boundary and next work

The current worker is a tested development foundation. It does not include the live authenticated API, consent lifecycle, deployment monitoring, or an externally validated detector. The latest run's release status is `internal_validation_only`; patient facing automatic alerts remain blocked. See the repository's `docs/api-data-contracts.md` for the proposed application interface.

The planned **five machine learning models** are a separate next phase. They have not been trained or saved by this package. Before building them, define each target and outcome, reuse the user/time split without leakage, set regression and classification baselines, and report both held out metrics and calibration where appropriate. Keep model weights, preprocessing, feature schema, and evaluation provenance together for each model. A high score on the fidelity surrogate must never be presented as performance against change labels.
