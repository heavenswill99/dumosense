# Five model ML benchmark

The first MindGuard machine learning benchmark and a bounded development-set tuning run are complete. They compare the five model families named in the technical handoff: Logistic/linear, Random Forest, CatBoost, LightGBM, and Isolation Forest. The four supervised families each have one binary classifier and two regressors. Isolation Forest is an unsupervised anomaly comparator. Each run saves **13 fitted estimators and their preprocessing pipelines**.

This is an engineering benchmark on synthetic data. It does not predict diagnosis or support automatic user alerts. The initial run is `ml_20260926T170633_659162Z`; the latest tuned run is `ml_tuned_20260926T173724_230556Z`. Both have trained weights and aggregate results under `weights/`, and full run records under the ignored `outputs/ml_runs/` folder.

## Bounded tuning results (latest run)

`src/modeling/tune_ml_models.py` searched four settings per supervised family and target, selected settings on development users, and evaluated the frozen selections on the same held-out users as the initial benchmark. The classifier decision threshold was also selected on development users to maximize balanced accuracy. Isolation Forest was fitted without labels; its settings and score cutoff were selected with development labels. Search details are in `outputs/ml_runs/ml_tuned_20260926T173724_230556Z/development_search.json`.

The table reports ordinary accuracy as requested, but balanced accuracy is the selection metric because 525 of 654 labelled test sessions (80.3%) are stable. Predicting stable every time would achieve 80.3% ordinary accuracy while detecting no changes. These metrics are for synthetic change labels, not medical conditions.

| Family | Test accuracy | Test balanced accuracy | Sensitivity | False positive rate | ROC AUC | Accuracy RMSE | RT RMSE (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.599 | 0.625 | 0.667 | 0.417 | 0.679 | 0.1157 | 83.64 |
| Random Forest | 0.564 | 0.644 | 0.775 | 0.488 | 0.695 | 0.1171 | 84.26 |
| CatBoost | 0.566 | **0.651** | 0.791 | 0.490 | **0.710** | **0.1149** | 83.71 |
| LightGBM | 0.552 | 0.642 | 0.791 | 0.507 | 0.691 | 0.1162 | 84.21 |
| Isolation Forest | 0.529 | 0.528 | 0.527 | 0.470 | 0.520 | n/a | n/a |

Lower RMSE is better. For reaction time, the linear model has the lowest test RMSE (83.64 ms); for current-session accuracy, CatBoost has the lowest (0.1149 fraction units). Full precision, F1, average precision, Brier, MAE, R², thresholds, and selected settings are in the tuned run's `metrics.json`.

This bounded search does **not** establish the global optimum. Development balanced accuracy improved for all four supervised families, but held-out balanced accuracy fell for Logistic Regression, Random Forest, and CatBoost. LightGBM improved from 0.619 to 0.642; Isolation Forest improved from 0.507 to 0.528. The initial CatBoost model still has the strongest observed balanced accuracy on these test users (0.663), but choosing a model after inspecting these test results would bias an estimate of future performance. Moreover, the same synthetic test users have now been evaluated twice. Treat all comparisons as exploratory until a fresh, independently generated test set is available. Neither run's false positive rate supports automatic user alerts.

## Targets and features

The classification target is **synthetic temporary or gradual change versus stable pattern** for a labelled cognitive session. It excludes `wellbeing_context_detected` and `insufficient_data` labels rather than treating them as cognitive change. Classification may use the current completed session's accuracy and reaction time, plus historical baselines and robust deviations. It never uses the rule engine's predicted state, synthetic label, insight, or recommendation as a feature.

The regression targets are the **current session accuracy fraction** and **current median reaction time in milliseconds**. Their inputs contain only prior personal baseline statistics, task difficulty, cognitive domain, and session time. Current accuracy, current reaction time, and their robust deviations are excluded from regression inputs. Reaction time is fitted on the log scale and converted to milliseconds for reported error. These are concurrent performance estimates from prior history, not forecasts of a later session or clinical outcomes.

The verified statistical run `20260926T143802_134359Z` provides features and synthetic interval labels. Its baseline calculations use strictly earlier result timestamps. The development selected domain and difficulty reference was fitted on train users before the cutoff. The five-model benchmark does not refit that reference from test data.
The time feature's origin is also calculated from the training cohort only.

## Data split and evaluation

Users are assigned by a deterministic SHA256 split. Training uses train users before the frozen time cutoff. Development and test use separate users after it. There is no user overlap among the three groups. In the initial run, the development set selected each classifier's probability threshold from 0.10 to 0.90 using balanced accuracy; Isolation Forest used a fixed 95th percentile training anomaly-score threshold. The later tuning run reused the same test users, as disclosed above.

| Cohort | Train | Development | Test |
| --- | ---: | ---: | ---: |
| Labelled classification sessions | 3,630 | 585 | 654 |
| Regression sessions | 16,278 | 3,740 | 3,735 |

The test classification set contains **129 change sessions** and **525 stable sessions**. The regression test set has 3,735 sessions. Comparisons to the earlier statistical change rule use the same 654 labelled held out sessions. All labels are synthetic scenario labels, not diagnoses.

## Initial run: held out classification results

Thresholds were chosen on development users only. AP is average precision, a summary of the precision recall curve. Brier is probability error; it does not apply to Isolation Forest's uncalibrated anomaly scores.

| Family | Threshold | TP | FP | FN | Balanced accuracy | Sensitivity | False positive rate | ROC AUC | AP | Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.30 | 79 | 171 | 50 | 0.643 | 0.612 | 0.326 | 0.677 | 0.368 | 0.155 |
| Random Forest | 0.30 | 89 | 205 | 40 | 0.650 | 0.690 | 0.390 | 0.694 | 0.363 | 0.155 |
| CatBoost | 0.25 | 83 | 167 | 46 | **0.663** | 0.643 | 0.318 | **0.708** | **0.370** | **0.146** |
| LightGBM | 0.10 | 94 | 258 | 35 | 0.619 | 0.729 | 0.491 | 0.682 | 0.368 | 0.151 |
| Isolation Forest | train score p95 | 39 | 151 | 90 | 0.507 | 0.302 | 0.288 | 0.506 | 0.195 | n/a |

The always no-alert comparator has balanced accuracy 0.500. The earlier hybrid rule had balanced accuracy 0.476, sensitivity 0.271, and false positive rate 0.320 on the same held out labelled cohort. CatBoost is strongest on this internal synthetic test, but a 31.8% false positive rate is too high for automatic alerts. The train-prevalence probability comparator has Brier 0.165; CatBoost's 0.146 is better on this test. These results need independent external validation before any release decision.

## Initial run: held out regression results

Accuracy errors are in fraction units (0.10 equals ten percentage points). Reaction time errors are milliseconds. R² is measured on the held out test users after the cutoff.

| Family | Accuracy MAE | Accuracy RMSE | Accuracy R² | RT MAE ms | RT RMSE ms | RT R² |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train mean comparator | 0.0958 | 0.1193 | 0.000 | 79.1 | 98.6 | -0.002 |
| Linear / Ridge | 0.0935 | 0.1157 | 0.060 | 67.0 | 83.6 | 0.279 |
| Random Forest | 0.0948 | 0.1173 | 0.034 | 67.4 | 84.5 | 0.265 |
| CatBoost | **0.0926** | **0.1149** | **0.074** | 67.0 | 83.7 | 0.278 |
| LightGBM | 0.0934 | 0.1162 | 0.053 | 67.5 | 84.4 | 0.267 |

The gains for accuracy are small. Reaction time is more predictable from prior history and task settings in this synthetic dataset. Neither result establishes real-world predictive utility. The older mixed model metrics in `README.md` were **in sample descriptive fits**; this table is a separate held out test and should not be compared as though the evaluation designs were identical.

## Files and reproducibility

`src/modeling/train_ml_models.py` checks the source run's manifest hashes before reading data, constructs fixed feature sets, checks the user/time split, fits all estimators, evaluates them, reloads every saved weight file, and writes a completion manifest with hashes. `src/modeling/package_ml_models.py` checks that manifest again and creates the portable package. The package includes only 13 estimator files, aggregate `metrics.json`, and `package_manifest.json`; it excludes session and user-level predictions.

Install the ML dependencies with Python 3.11 and run from this folder:

```powershell
python -m pip install -r .\requirements-ml.txt
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s .\tests -p test_ml_models.py -v
python .\src\modeling\train_ml_models.py
python .\src\modeling\package_ml_models.py
python .\src\modeling\verify_ml_run.py
# Optional bounded search; creates a separate run and its own package.
python .\src\modeling\tune_ml_models.py
python .\src\modeling\package_ml_models.py
python .\src\modeling\verify_ml_run.py
```

The runs used `catboost==1.2.10`, `lightgbm==4.7.0`, and the pinned dependencies in `requirements-mvp.txt`. On the development machine, CatBoost was installed under `.deps/` to keep that installation inside `ml/`; the training scripts also work when the packages are installed normally. `.deps/` and `outputs/` are ignored by Git. The independent verifier passed all 17 tuned-run artifact hashes, all 14 portable package hashes, five classification recounts, and eight regression recounts.

For a new run, keep the new run ID and do not overwrite earlier weights. Treat `joblib` files as trusted-code artifacts; loading an untrusted pickle can execute code. The package hashes verify integrity against this local export, not the identity of an external publisher. The fitted pipelines include imputation, category encoding, scaling where used, and model weights. They require the feature columns listed in `metrics.json` and the same dependency versions for reliable loading.

## Interpretation and next gates

This benchmark answers whether simple tabular methods can recover **synthetic scenario states** and estimate concurrent synthetic performance better than basic comparators. It does not identify dementia, establish a causal role for sleep or stress, or validate a medical alert. The current feature set deliberately omits context and wellbeing rather than using an unbounded historical join. The source handoff requires an explicit context window before such features are added.

The next useful checks are an independently generated dataset or governed real-world validation set, a defined acceptable false positive rate, probability calibration if probabilities will be shown, subgroup sample sizes large enough for stable comparisons, and backend authentication and consent integration. The statistical engine and ML benchmark should remain separate versioned components until those checks are met.
