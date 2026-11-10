# Health Reserve model optimization

This is a reproducible benchmark for two simulated outcomes: whether a selected contribution plan was maintained for three follow-ups and the fraction of that selected contribution reported during follow-up. Use it for internal evaluation or a synthetic demo. Real contribution recommendations and emergency readiness require independently observed outcomes and validation on new users.

## How the optimizers work

- **Linear:** searches logistic regularization for classification and compares Ridge with a median quantile regressor for regression.
- **Random Forest:** searches tree depth, minimum leaf size and feature sampling.
- **CatBoost:** searches iterations, tree depth, learning rate and regularization; regression compares median quantile and squared-error loss.
- **LightGBM:** searches tree count, leaf count, minimum leaf size, learning rate and regularization; regression compares quantile, absolute and squared-error loss.
- **Isolation Forest:** searches sample and feature settings for agreement between random seeds. Its score measures unusual inputs, and there are no labeled anomalies to calculate accuracy.

The supervised search compares the full 95-column input with a 16-column cash flow subset, which uses the financial profile, selected amount and burden ratios, liquid savings, household size and employment categories. Feature transformations fit inside each of three user-group training folds. Classifiers optimize ROC AUC in the training folds and set the decision threshold by balanced accuracy on development users. Regressors optimize absolute error in the training folds and select a blend with the training median on development users. A weight of zero uses the median alone.

Method references: [scikit-learn randomized search](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.RandomizedSearchCV) and [CatBoost regression objectives](https://catboost.ai/docs/en/concepts/loss-functions-regression).

The 2,236 training users, 748 development users and 740 test users are the same as the earlier benchmark. The comparison uses the same test users for both runs; the test cohort is not new external evidence. `metrics.json` contains every trial, the chosen models and settings, corrected metrics for the previous classifiers, and paired bootstrap intervals for regression MAE differences versus the median. Negative MAE differences favor the optimized candidate.

The previous run labeled class 1 precision, recall and average precision as “adjusted down.” Class 1 actually means sustainable. This report recalculates the previous and optimized values for class 0 (adjusted down); the archived metrics are kept as recorded.

## Results: `hr_optimized_20261110T131723Z`

[Full metrics and search trials](weights/health_reserve_affordability/hr_optimized_20261110T131723Z/metrics.json)

| Family | Old → optimized balanced accuracy | Optimized ROC AUC | Adjusted-down recall | Optimized ratio MAE |
|---|---:|---:|---:|---:|
| Linear | 60.6% → 63.6% | 0.682 | 65.6% | 0.0917 |
| Random Forest | 61.4% → 62.7% | 0.669 | 71.8% | 0.0948 |
| CatBoost | 62.1% → 63.6% | 0.673 | 69.0% | 0.0911 |
| LightGBM | 61.9% → 62.0% | 0.671 | 69.0% | 0.0907 |

The constant classification baseline is 50.0% balanced accuracy. The constant training median gives 0.0960 MAE on the ratio target. All four regression candidates beat that baseline when applying the blend chosen on development; the raw Random Forest did not. LightGBM had the lowest test MAE, an improvement of 0.53 percentage points over the baseline (paired 95% bootstrap interval: 0.24 to 0.82 percentage points). This interval is for the reused synthetic cohort and does not account for choosing the lowest result among multiple families.

Development data selected LightGBM for classification and Linear for regression. Keep those choices when testing on a fresh cohort; the best test scores above are descriptive. Isolation Forest's two seed runs agreed on 80.7% of the union of their flagged development users and flagged 11.5% of test users at the saved cutoff. These flags have no measured relationship to affordability.

The training run reloaded the nine fitted model files and the median baseline and checked that they reproduce the saved predictions. The manifest covers 12 files. These results support an internal synthetic demo; the model has not been validated for recommending what a person can afford to save.

## Reproduce the run

From the repo's `ml` folder with `requirements-ml.txt` installed:

```powershell
$previous = '.\weights\health_reserve_affordability\hr_tuned_clean_20261110T130502Z'
$run = 'hr_optimized_' + [DateTime]::UtcNow.ToString("yyyyMMdd'T'HHmmss'Z'")
python .\feature_engineering\optimize_health_reserve_models.py `
  --source-run $previous --output-dir (Join-Path '.\outputs' $run)
```

The script checks the source run hashes and evaluation cohort before fitting. The optimized package contains nine model files, the median baseline, test predictions, metrics and an artifact manifest. It reuses the earlier engineered dataset, so keep the previous run for reproduction.

For research inference, use the feature names in `metrics.json` to assemble a row from the same point in time feature builder. Use class 1 probability (sustainable) with that family's recorded threshold; class 0 means adjusted down. For a reported ratio, use `median + blend_model_weight * (raw_model_prediction - median)` or the median itself if selected. Regression weights alone return the raw prediction. Isolation flags use the recorded cutoff on the negative `score_samples` value. Load these Joblib files only from a trusted source.
