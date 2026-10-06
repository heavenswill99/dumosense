# Dumosense central agent backend integration

This backend was imported from the locally available `data-engineering-foundations` branch into the `artificial_intelligence_models` working tree. Its configured database is **Django ORM over MySQL**, not Djongo or MongoDB: see `config/settings.py` and `requirements.txt`. The original `intelligence` app was a scaffold. The new central agent integration uses the existing SQL tables; all ORM mappings are `managed = False`, so it does not create or migrate tables.

`POST /api/v1/intelligence/query/` accepts a JSON object containing only `question`. `GET /api/v1/insights/` and `GET /api/v1/insights/latest/` retrieve stored results, optionally filtered by `?product=MINDGUARD` or `?product=HEALTH_RESERVE`; list requests accept `limit=1..20`. Retrieval rechecks current product access and scopes every row to the authenticated user. Django/DRF authentication supplies the user. The endpoint is **off by default**; set `DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=1` only in an internal validation environment after configuring the existing database. The endpoint does not accept user IDs, consent flags, tool names, SQL, or model output from the request body. It returns a deterministic, nonclinical response unless the separately gated local MedGemma adapter is enabled.

Inside one database transaction, `intelligence.gateway` locks and checks the active account, active product enrollment, current `product_data_processing` consent, and the relevant product consent (`cognitive_assessment` or `health_reserve_data`). It reads only that user's latest completed cognitive result or latest reserve assessment and strictly earlier history. It uses the single existing Health Reserve score implementation under `ml/src/health_reserve/score.py`. The bounded agent then routes the question and creates one `intelligence_runs`, `insights`, `recommendations`, and `events` row per requested product. A combined request keeps the two product outputs separate. The event contains tool/evidence IDs and policy status, not the raw question. Unavailable data or denied access do not create completed run records.

The backend imports the sibling `ml/src/dumosense_ai` package; deploy those directories together. Set `DUMOSENSE_ENABLE_LOCAL_MODEL=1` only for internal laptop validation after installing the `medgemma1.5:4b-it-q4_K_M` Ollama model yourself; the adapter sends compact context to the loopback Ollama API and remains subject to the agent's output validation. Both local-model and query flags default to off. Existing MindGuard and Health Reserve ML estimators are **not** used by this endpoint. The current data do not justify medical alerts, reserve targets, or treatment-affordability claims. The database mappings assume the existing MySQL schema in `sql/dumosense_dev.sql`; verify the real deployed schema before enabling the endpoint.

From `backend/` after installing pinned dependencies into a local virtual environment:

```powershell
$env:DB_NAME = 'dumosense_test_dummy'
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test intelligence
.\venv\Scripts\python.exe intelligence/sqlite_smoke.py
```

After installing MedGemma in the local Ollama store, an optional synthetic-data integration check also exercises the actual Ollama adapter through the disposable SQLite ORM path:

```powershell
$env:DUMOSENSE_SMOKE_LOCAL_MODEL = '1'
.\venv\Scripts\python.exe intelligence/sqlite_smoke.py
Remove-Item Env:DUMOSENSE_SMOKE_LOCAL_MODEL
```

The extra check sends only a fabricated MindGuard state and requires a validated generated answer. It does not contact the configured MySQL database or use real user records.

The 15 backend tests mock ORM calls. The checked-in disposable in-memory SQLite smoke script exercised the actual ORM transaction and produced two runs, two insights, two recommendations, and two audit events for a combined query. It also verified that withdrawing Health Reserve consent immediately hides that product’s stored insight. The optional model-on pass produced a third run and a validated synthetic MindGuard explanation. Neither check validates the live MySQL connection. The full ML suite is separate. Before activation, provide backend-owned MySQL credentials in `backend/.env` (do not commit them), run database connectivity and transaction tests against a disposable copy of the schema, and verify authentication, consent withdrawal, ownership, and API responses end to end. This repository has no `backend/.env` at present. Existing backend settings also require production security configuration before any external deployment.
