# Health Reserve ML build: point-in-time affordability outcome benchmark

See the [optimizer report](README_HEALTH_RESERVE_OPTIMIZED.md) for the newer benchmark and its comparison with this run.

## What was built

The pipeline uses the existing Health Reserve assessment table plus eight usable extension tables to build one row per selected synthetic contribution plan. Four supervised model families each have a classification and regression model; a fifth family, Isolation Forest, is an unlabeled anomaly comparator. The package contains the feature engineering code, source CSVs, the engineered training table, held-out predictions, metrics, a manifest and all nine serialized model artifacts.

This predicts generated follow-up behavior for a synthetic plan. It does **not** estimate what a real person can afford to save, recommend a contribution amount, or determine whether someone is ready for a health emergency. The data and labels are synthetic.

## Feature engineering

The full catalog and point-in-time rules are in [`feature_engineering/README.md`](feature_engineering/README.md). The main groups are:

- **Existing assessment:** latest assessment at or before plan choice: coverage, reserve status, estimated exposure, emergency resources, obligations, dependents, current reserve, target, gap and preparedness ratio. All 4,000 plans have at least one earlier assessment; none have two or more earlier assessments, so two assessment-trend columns were removed before fitting.
- **Financial profile:** income, essential expenses, debt, other obligations, liquid savings and income stability, using only the profile snapshot linked to the plan and recorded/effective by choice.
- **Cash-flow and contribution burden:** net cash flow, obligations-to-income, liquidity months, selected contribution-to-income, selected contribution-to-positive-cash-flow, and surplus after the selected amount. Rule capacity and system-suggested contribution are excluded.
- **Transactions:** 30- and 90-day income, expense and net-flow amounts, counts, variability, recurring income share and healthcare expense categories. A transaction is included only if both its event date and recorded timestamp precede the plan choice.
- **Household and reserve history:** active dependents by dependency and age band; active goal targets; prior allocations/withdrawals; and healthcare exposure estimates created by choice.

The scenario table was excluded because every scenario was created after all plan choices and is counterfactual. The synthetic healthcare cost reference table was also excluded; per-user estimates are already represented in prior assessments and exposure records. ML feature/target export tables were absent by design, so features and labels are derived from the operational inputs here.

## Targets and evaluation

- **Classification:** sustainable only when all three later monthly follow-ups are marked sustainable; adjusted down when at least one follow-up is adjusted down. Unknown plans and plans that were not selected are excluded.
- **Regression:** mean reported contribution across the three later follow-ups divided by the contribution selected at plan choice.
- **Split:** deterministic user-disjoint 60/20/20 train/development/test. Hyperparameters are selected on development data; the final metrics use the 740-user test partition.
- **Classification metrics:** accuracy, balanced accuracy, macro-F1, precision/recall for adjusted down, ROC-AUC, average precision, Brier score, log loss and confusion matrix.
- **Regression metrics:** MAE, RMSE, R² and fraction within 0.10 of the realized ratio, compared with persistence and training-median baselines.
- **Isolation Forest:** 90th-percentile development threshold; no labeled accuracy is available, and its flags do not mean unaffordability.

### Fine-tuned run: `hr_tuned_clean_20261110T130502Z`

There were 4,000 plans and 12,000 follow-up rows. After excluding 276 unknown or non-selected plans, 3,724 plans remained: 2,106 sustainable and 1,618 adjusted down. The held-out test set contains 740 users.

| Model family | Class accuracy | Balanced accuracy | ROC-AUC | Regression MAE | Regression R² |
|---|---:|---:|---:|---:|---:|
| Linear | 60.0% | 60.6% | 0.644 | 0.0983 | 0.038 |
| Random Forest | 61.6% | 61.6% | 0.662 | 0.0982 | 0.060 |
| CatBoost | **62.6%** | **62.1%** | **0.665** | **0.0978** | 0.066 |
| LightGBM | 60.8% | 61.9% | 0.659 | 0.0979 | 0.065 |

The classifier threshold was selected on the development set only (CatBoost threshold 0.56); test-set accuracy was 62.6%, with 58.0% recall and 57.4% precision for adjusted-down plans. The majority-class baseline accuracy was 55.9%. Fine-tuning raised CatBoost balanced accuracy from 59.9% to 62.1% on the same held-out test set. CatBoost regression MAE was 0.0978 ratio points, while the training-median baseline MAE was lower at 0.0960 and had better within-10-percentage-point coverage. The regression model still did not beat the simple baseline.

These modest scores are only a check against the synthetic outcome generator. They do not validate an affordability or financial-wellbeing claim.

## Reproduce in PowerShell

From the repository's `ml` directory, with the project's ML dependencies installed:

```powershell
$run = 'hr_point_in_time_' + (Get-Date -Format 'yyyyMMddTHHmmssZ')
python .\feature_engineering\train_health_reserve_models.py `
  --data-dir .\data\health_reserve_point_in_time `
  --output-dir (Join-Path '.\outputs\health_reserve_affordability_runs' $run)
```

The script uses `ml\.deps` when available. A new run folder must not already exist. It writes engineered features, metrics, held-out predictions, manifest and weights without replacing the frozen run. Candidate hyperparameters and classification thresholds are selected using development data only; the test set remains reserved for final scoring.

## Provenance and limits

The extension inputs came from branch `data-engineering-foundations`, commit `5d33e493a5d612497483a6ceed42643a8c46d53e`; the existing assessment CSV came from this repository's synthetic data. Plans and outcomes are marked simulation-only/synthetic. The source branch's validation report does not cover the later contribution-plan and affordability-outcome files; this training pipeline checks ID uniqueness, profile joins and three follow-ups per plan, but no external/real outcome validation exists. Keep this package research-only until real, consented longitudinal labels, fairness review, prospective validation and suitable financial governance are available.
