# Dumosense ML worker

## Run and test
From this ml directory, run: 

    python src/engine_v3.py

Or run run_mvp.cmd on Windows. Tests execute before every full run. For tests only:

    python src/test_engine_v3.py

The worker accepts --data-dir, --validation-dir, and --output-dir. It never changes raw inputs or writes to the application database. A run creates a unique outputs/runs directory. outputs/latest_successful_run.json points only to a completed and verified run. A completed analysis is **not** authorization to deploy patient-facing alerts. Inspect the release assessment in the generated report.

## Supported behavior
- After-result evaluation: current result calculated_at is the index time. Only measurements with strictly earlier calculated_at enter personal history. Tied results cannot see one another.
- Exact median/MAD baselines for accuracy and RT. Per-domain, raw cross-domain, hybrid, and training-reference-adjusted strategies are evaluated separately.
- Three finite prior observations required; degenerate scales are unavailable rather than replaced by arbitrary noise.
- Point deviations in both directions are compared with user-level synthetic change labels. Persistence is user-aware. Gradual-change and recovery classification are not claimed.
- Development chooses a research strategy/threshold. Internal held-out users after the training cutoff are scored once without tuning to their results. Existing synthetic data have already informed development; this is not external validation.
- Real model fitting, warnings, subgroup counts, uncertainty, and surrogate explanations are recorded. Failed secondary analyses remain visible.

## Application boundary
The existing docs/api-data-contracts.md says backend endpoints have not been implemented. This repository supplies an offline worker and src/insight_adapter.py, not a deployed authenticated service. The backend must authenticate requests, enforce current consent, scope each user's history, validate source ownership, persist immutable run provenance, and deliver results.

The adapter checks the supplied authenticated user ID against the record and requires explicit consent verification. It returns a descriptive same-domain session summary with run provenance; it does not issue change alerts or medical claims. Its session_summary insight type is a proposed nonclinical extension to the contract's varchar insight_type field. Backend/UI integration must handle it before enabling this adapter in an application. Do not pass a caller-provided consent flag directly from an HTTP request.

## Production release boundary
Synthetic observations can validate software behavior but cannot establish medical utility or real-user alert quality. No live deployment, external notifications, database migration, or clinical release is performed by this worker. Production infrastructure, authentication, consent lifecycle, retention, monitoring, and deployment integration tests remain backend work. The report separates computational checks from this release decision.

## Evidence and failures
Each run has a status manifest, source/input hashes, dependency versions, a continuous log, executed tests, computed metrics, session JSONL, plots, and a report generated from the same summary. Interruptions/failures must never advance the latest-successful pointer. Old V1/V2 reports are historical and should not be consumed by the MVP.

No claimed linear-time complexity: exact median/MAD history work is quadratic per short trajectory; group extraction avoids repeated dataframe construction. Long real-world histories require a separately specified window or optimized order-statistic implementation before scaling.
