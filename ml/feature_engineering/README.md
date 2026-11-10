# Health Reserve affordability model feature engineering

## Scope and intended output

This pipeline builds one row per selected synthetic contribution plan. It predicts (1) whether all three later simulated follow-ups remain sustainable and (2) the mean realized contribution divided by the selected monthly contribution. It is an engineering benchmark only: the labels and financial inputs are simulated, so it cannot establish a real household's affordable contribution or emergency readiness.

## Point-in-time rule

Every predictor must have been knowable at `choice_timestamp`. Transaction/activity event dates **and** their `recorded_at` timestamps must be no later than the choice. Effective-dated profiles and dependents must be active and recorded by the choice. Goals and exposure estimates must be created by the choice. Scenarios are excluded because their records are dated after all plan choices and describe counterfactuals. Follow-up fields are labels only.

## Feature catalog

| Feature group | Engineered fields | Source and rule |
|---|---|---|
| Household cash flow | monthly income, essential expenses, debt repayments, other obligations, net cash flow, obligations/income, net-cash-flow/income | The plan's linked financial profile; profile must be recorded by choice. Ratios are null when the denominator is zero. |
| Existing reserve assessment | Latest prior coverage status, reserve status, estimated exposure, emergency resources, obligations, dependents, current preparedness amount/target/gap/ratio, previous assessments count, first-to-latest exposure and ratio changes | The existing `health_reserve_assessments.csv` row with the latest `assessed_at` no later than plan choice; no future assessment is used. These values are synthetic. |
| Liquidity | liquid savings, liquid-savings months of obligations | Profile balances and monthly obligations; no target or future transaction fields. |
| Contribution burden | selected contribution/income, selected contribution/net positive cash flow, selected contribution/estimated surplus | User-selected amount at choice; user-facing system suggestion and rule capacity are deliberately excluded. |
| Income history | prior 30/90-day income totals, mean, standard deviation, count, recurring-income share | Transactions whose event and record dates precede choice; only income transactions. |
| Spending and volatility | prior 30/90-day expense totals, essential-category amount, amount mean/std, transaction count, monthly net-flow mean/std | Transactions strictly before choice; amount category/type mapping is documented in code and missing classes map to zero. |
| Household dependents | active count, high/partial dependency counts and shares, age-band and relationship counts | Effective-dated, recorded dependents active at choice. No dependents recorded later are included. |
| Reserve goal context | active goal count, selected target sum, months to target, target relative to income/savings | Goals recorded by choice and active then. Uses target state available at the choice only. |
| Prior reserve activity | prior 30/90-day allocation totals, count, mean, last-event age | Activities with both activity and recorded timestamps no later than choice. Current/future events are excluded. |
| Prior healthcare exposure | historical exposure total/count/category counts, exposure relative to income/savings | Exposure items created by choice, grouped by user and assessment history. These are synthetic cost estimates. |
| Basic categories | income type, employment status, currency, country/region | Profile/plan values known at choice. Identifiers are retained only for split/audit, never model inputs. |

## Target definition

- Classification: `sustainable` iff all three follow-ups are sustainable; `adjusted_down` if any observed follow-up is adjusted down. Plans containing `unknown` or `not_observed` follow-ups are excluded from supervised fitting.
- Regression: average of the three reported contributions divided by the user-selected contribution. Invalid/missing or zero selected contributions are excluded.
- Isolation Forest is an unlabeled anomaly comparator only. It has no anomaly accuracy and its flags must not be called unaffordability.

The training input package includes the existing assessment table and eight applicable extension tables: financial profile, transaction, dependent, goal, reserve activity, healthcare exposure, contribution plan and affordability follow-up. The scenario table is deliberately excluded: all its rows were created after the plan choices and are counterfactual. Healthcare cost references are also excluded because they are simulated market assumptions; the per-user healthcare exposure estimate already enters through the recorded assessment and exposure rows.

## Validation design

The split is deterministic and user-disjoint (60/20/20 train/development/test). Hyperparameters are selected on development only. The test set is evaluated once. Metrics include accuracy, balanced accuracy, macro-F1, adjusted-down precision/recall, ROC-AUC, average precision, Brier score, log loss, regression MAE/RMSE/R² and persistence/median baselines. Artifacts contain source hashes, feature names, split counts and a manifest with hashes.

## Known limits

All extension tables and labels are synthetic. There is one plan per synthetic user, three generated follow-ups, and no independently observed affordability label. Strong metrics would only reflect this generator. Do not present scores as personal financial advice, safe savings amounts, or clinical/emergency readiness.
