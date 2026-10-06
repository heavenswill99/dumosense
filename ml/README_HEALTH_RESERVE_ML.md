# Health Reserve: next-assessment ML benchmark

This benchmark follows the [cost-free statistical baseline](README_HEALTH_RESERVE.md). It is an **engineering experiment on synthetic data**, not an approved user-facing healthcare prediction or treatment-affordability estimate.

## Prediction task and features

Each supervised model takes only information available at a completed Health Reserve assessment and predicts the **next recorded assessment's** fixed buffer score (1–10) and score band (1–3, 4–6, 7–8, 9–10). In the synthetic dataset, consecutive assessments are 42–58 days apart; the task has **no guaranteed calendar horizon** for real users. Predicting the current score from its own amount and obligations would just reproduce the scoring formula, so the target is explicitly later.

Inputs are the current score and obligation-buffer months; current preparedness amount and monthly obligations; emergency-resource obligation months; coverage status; number of dependants; count and age of strictly prior assessments; prior median buffer months; and change from that median. Preprocessing and imputation are fitted on training users only and saved inside each model pipeline. User IDs, assessment IDs, the future score/date, and the synthetic healthcare exposure, target, gap, ratio, and status are **never model features**.

The four supervised families are linear (Logistic Regression for bands, Ridge for score), Random Forest, CatBoost, and LightGBM. Each has one four-class classifier and one score regressor. Isolation Forest is a fifth, **unsupervised current-assessment anomaly comparator**; it has no next-score or disease accuracy. All **nine fitted estimators** are saved as `joblib` pipelines.

## Split and selection

Users are separated deterministically into training, development, and test groups. The cutoff is 11 April 2026 at 14:00 UTC, calculated from training users. Training outcomes occur before the cutoff. Development and test inputs are from different users and occur after it. For each supervised family and task, two candidate settings were compared on development users. Classification selected the highest development balanced accuracy (macro F1 breaks ties); regression selected the lowest development MAE. The selected settings were then scored on test users.

| Cohort | Examples | Users |
| --- | ---: | ---: |
| Training | 4,918 | 2,362 |
| Development | 1,576 | 767 |
| Test | 1,753 | 852 |

The first ML iteration already evaluated these same synthetic test users. A later iteration corrected anomaly threshold calibration and saved classifier probabilities for independent recounting. Accordingly, the final test figures are **exploratory repeated-test evidence**, not a fresh external holdout. No settings were selected by optimizing the supervised test scores.

## Held-out results

Four-band accuracy is the percentage assigned the exact next score band. Balanced accuracy is the mean recall across the four bands; macro F1 weights bands equally. Score MAE and RMSE are in **score points** on the 1–10 scale; lower is better. The persistence comparator predicts that the next score equals the current score.

| Model | Band accuracy | Balanced accuracy | Macro F1 | Score MAE | Score RMSE | Rounded score within 1 point |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Persistence | 54.7% | 47.9% | 47.9% | 1.464 | 2.042 | 60.2% |
| Linear | 63.5% | 51.2% | 50.5% | 1.203 | 1.552 | 72.2% |
| Random Forest | **64.0%** | 51.0% | 48.7% | 1.163 | 1.462 | 69.8% |
| CatBoost | 63.5% | 50.8% | 48.6% | **1.133** | **1.452** | **72.7%** |
| LightGBM | 63.0% | **51.6%** | 50.5% | 1.145 | 1.467 | 70.9% |

The exact-score accuracy after rounding each regressor's prediction is only 25.4%–29.3%; the table's band accuracy is a different, easier four-class task. The common 4–6 band accounts for 761 of 1,753 test examples, so ordinary accuracy alone can conceal weaker performance on other bands. Full confusion matrices, class precision/recall, log loss, R², selected settings, and development trials are in the saved `metrics.json`.

An exploratory paired user bootstrap (1,000 resamples, seed 42) gave a 95% interval of **0.281–0.384 score points** for CatBoost's MAE improvement over persistence, and **7.2–11.5 percentage points** for Random Forest's band-accuracy gain. These intervals describe sampling variation among these synthetic test users; they do not repair the repeated-test or real-world validation limits.

Isolation Forest originally flagged **86.0%** of test assessments when using the training-score 90th percentile. The training cohort had a median of one prior assessment, versus four for the later development/test cohorts, creating a large feature shift. Calibrating the cutoff to the **development-score** 90th percentile gave an **8.7%** test flag rate. Both rates are retained in the metrics. With no independently labelled anomalies, neither rate is sensitivity, specificity, or accuracy.

## Files and reproducibility

The final run is `outputs/health_reserve_ml_runs/hr_ml_20261006T135923_863977Z/`. Its per-assessment predictions stay in ignored `outputs/`. The portable package is `weights/hr_ml_20261006T135923_863977Z/`: nine fitted pipelines, aggregate metrics, and SHA256 manifest, without user-level predictions. The internal inference adapter checks package hashes and the complete point-in-time feature contract before loading trusted `joblib` files.

From `ml/` with Python 3.11 and `requirements-ml.txt` installed:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s .\tests -p 'test_*.py' -q
python .\src\health_reserve\train_ml_models.py
python .\src\health_reserve\verify_ml_run.py
```

For internal inference, provide a JSON file with current amount, obligations, emergency resources (or explicit null), coverage status, dependants, and the current statistical baseline's prior count, prior median, delta, and latest-prior age. Then run:

```powershell
python .\src\health_reserve\predict_ml_models.py --family catboost --assessment-json .\assessment.json
```

The resulting probabilities and next-score estimate are experimental. The four classifiers and regressors can disagree, and no automated alert, care recommendation, insurance advice, or treatment-cost claim should use them. A governed real-world dataset, a defined product outcome and horizon, calibration, subgroup checks, and prospective validation are needed before considering that use.
