# Health Reserve: preliminary score and feature engineering

Health Reserve is described by the repository's SQL schema and API contract as **financial preparedness for healthcare**. The existing synthetic dataset has 24,376 assessments for 4,000 users (4–7 snapshots per user, dated 16 September 2025 to 14 September 2026). This first pass provides a transparent **1–10 obligation-buffer rank**. It does not estimate the costs of medicines, supplements, procedures, surgery, or care; it does not measure health status, clinical risk, insurance adequacy, or ability to pay for a specific treatment.

## Why the old labels cannot train this score

The dataset's `preparedness_target`, `preparedness_gap`, `preparedness_ratio`, and `reserve_status` already encode a synthetic target. `estimated_healthcare_exposure` is an unverified synthetic cost estimate. Predicting any of these fields would merely reproduce the generator's assumptions, so the **statistical baseline** does not fit an ML model or report classification accuracy against those labels. A separate [next-assessment ML benchmark](README_HEALTH_RESERVE_ML.md) predicts a future synthetic score, not the cost-derived status. There are no defensible real-world healthcare outcome labels yet.

The existing gap and ratio formulas passed the repository's consistency check on all 24,376 rows. That check confirms arithmetic, not validity of the underlying target or prices. All source columns are present in the synthetic file; production data must still handle missing and stale values.

## Feature contract

| Source field | Engineered feature / use | Reason |
| --- | --- | --- |
| `current_preparedness_amount` | Numerator of obligation-buffer months | Current reported reserve amount; assumed usable, pending product definition. |
| `monthly_financial_obligations` | Denominator of obligation-buffer months | Makes the rank scale-free across currency amounts. It is **not** confirmed to equal total essential living expenses. Must be positive. |
| `emergency_health_resources` | Companion `health_resource_obligation_months`; **not added to the score** | Its overlap with `current_preparedness_amount` is undocumented. Adding both may double-count money. |
| `healthcare_coverage_status` | Display only | `insured`, `partial`, or `uninsured` does not describe covered services, exclusions, deductible, or benefit cap. |
| `number_of_dependants` | Display/context only | No validated adjustment; obligations may already reflect household size. |
| `user_id`, `assessed_at`, `reserve_assessment_id` | Identity, chronology, latest snapshot | Comparisons must use the same user's earlier assessments, never a later row. The assessment ID breaks timestamp ties. |
| `estimated_healthcare_exposure`, `preparedness_target`, `preparedness_gap`, `preparedness_ratio`, `reserve_status` | **Excluded** | Cost or target-derived synthetic values would leak the old score and imply unsupported healthcare-price knowledge. |
| Profile age, sex, location; MindGuard scores; wellbeing reports | **Excluded** | No validated link to this financial-buffer rank. Avoid demographic penalties and cross-product mixing. |

`obligation_buffer_months = current_preparedness_amount / monthly_financial_obligations`. The amount and obligations must be finite and nonnegative, with obligations strictly positive. Invalid inputs have **no score**; they are never converted to zero or imputed. The amount and obligations must use the same currency and time basis. The code retains full numeric precision for thresholding.

## Fixed 1–10 rank

These cutoffs are a **product-design proposal**, not a medical or actuarial standard. They are fixed before comparison to the synthetic dataset and are not learned from `reserve_status`. Higher scores mean a larger buffer relative to recorded monthly obligations; score 10 does **not** mean healthcare costs are fully covered.

| Score | Obligation-buffer months |
| ---: | --- |
| 1 | 0 to <0.25 |
| 2 | 0.25 to <0.5 |
| 3 | 0.5 to <1 |
| 4 | 1 to <2 |
| 5 | 2 to <3 |
| 6 | 3 to <4 |
| 7 | 4 to <6 |
| 8 | 6 to <9 |
| 9 | 9 to <12 |
| 10 | 12 or more |

For a compact display, group scores as **1–3**, **4–6**, **7–8**, and **9–10**. These are rank bands only; do not label them as disease risk, treatment access, or financial safety. Example: an amount of 300,000 against monthly obligations of 100,000 yields 3 obligation-buffer months, score **6**, band **4–6**.

## Dataset audit and score distribution

The synthetic file has no missing fields, duplicate assessment IDs, duplicate user/timestamp pairs, negative monetary values, or zero monthly obligations. Its current amount and monthly obligations change across snapshots, so the score can support a within-user trend. Coverage status changes for 3,959 of 4,000 users; this appears synthetic and is another reason not to infer actual insurance protection.

The latest-snapshot score counts are:

| Score | Users |
| ---: | ---: |
| 1 | 373 |
| 2 | 224 |
| 3 | 435 |
| 4 | 796 |
| 5 | 543 |
| 6 | 403 |
| 7 | 469 |
| 8 | 311 |
| 9 | 164 |
| 10 | 282 |

All 24,376 rows produced a valid score, with 4,000 latest-user scores. This demonstrates deterministic coverage on the synthetic data, **not** real-world validity. The latest score bands contain 1,032 users at 1–3, 1,742 at 4–6, 780 at 7–8, and 446 at 9–10. Those counts were inspected after fixing the thresholds and were not used to tune them.

## Statistical baseline model and saved run

The MVP model has two parts. The **fixed 1–10 rank** uses the current assessment only. A **personal statistical baseline** takes the median obligation-buffer months from the same user's three to five strictly earlier assessments in the preceding 365 days. It reports the current minus prior median in months. If fewer than three eligible earlier snapshots exist, `baseline_available=false` and the median/delta are null. Assessments with the same timestamp never become one another's history. This is descriptive change, not a forecast, medical alert, or probability.

The versioned run `hr_20261006T134917_017529Z` scored 24,376 assessments for 4,000 synthetic users. A prior median was available for **12,376 assessments (50.77%)**. Every user's latest synthetic assessment had enough prior history, a consequence of this dataset's structured 4–7 assessments per user; it must not be assumed in production. The run records per-assessment scores and history comparisons in ignored `outputs/health_reserve_runs/`, plus aggregate summary, fixed model parameters, source/input hashes, and completion status. No ML weights are fitted or necessary for this deterministic statistical baseline.

From `ml/`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s .\tests -p test_health_reserve.py -v
python .\src\health_reserve\statistical_baseline.py
python .\src\health_reserve\verify_run.py
```

The first script writes a new run ID without overwriting older runs; the independent verifier rereads the original CSV and recounts every score, prior median, delta, and artifact hash. The original `score.py` can still print aggregate score counts without saving a run. The earlier MindGuard statistical and five-family ML models remain separate.

## Before user-facing use

Confirm whether `current_preparedness_amount` is liquid, whether `emergency_health_resources` is included in it, whether monthly obligations include essential spending, and what currency is used. Obtain actual insurance benefit details and user consent before giving any coverage interpretation. Validate the fixed cutoffs on governed real-world data and test comprehension, subgroup effects, missingness, and trends. If treatment-cost data arrive later, build a separately versioned cost-adequacy model; do not silently change this rank's meaning.

The [WHO financial-protection overview](https://www.who.int/health-topics/financial-protection) explains why out-of-pocket healthcare spending can create hardship. The [FDIC emergency-savings guide](https://www.fdic.gov/consumer-resource-center/2025-01/saving-unexpected-and-your-future) discusses savings relative to living expenses. Neither source validates these specific score cutoffs or turns recorded obligations into total living expenses.

The five-family future-score benchmark, its held-out metrics, and saved weights are documented in [Health Reserve ML](README_HEALTH_RESERVE_ML.md).
