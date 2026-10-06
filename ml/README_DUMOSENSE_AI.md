# Dumosense AI MVP foundation

This implements the Dumosense AI parts of the product's MVP technical blueprint as a bounded, offline component. The blueprint source DOCX is held outside this repository; this README and the root README describe the runnable implementation. MindGuard and Health Reserve remain separate calculation engines. The Dumosense agent routes requests and assembles a small structured context; an optional local MedGemma adapter explains that context during internal laptop validation. It does not own the product calculations.

## What is implemented

- `src/dumosense_ai/service.py` composes product-specific descriptive observations from completed source runs. It checks the authenticated user ID, backend-verified consent and enrollment, product, model version, and source run. Stable IDs fit the current SQL `VARCHAR(20)` columns.
- `src/dumosense_ai/agent.py` is a deterministic single-agent router for MindGuard, Health Reserve, combined, emergency, and out-of-scope questions. Its approved tools are `get_mindguard_state` and `get_health_reserve_state`; it never runs arbitrary code or SQL. Combined answers retain two distinct product states. The `LocalExplanationModel` interface accepts a compact context after a runtime is installed by the team.
- `src/dumosense_ai/context.schema.json` is the machine-readable local explanation-context contract. It carries source run IDs, model versions, observation dates, observations, limitations, evidence IDs, allowed actions, and prohibited claims.
- `src/dumosense_ai/knowledge.py` retrieves short, explicitly approved local JSONL excerpts by lexical overlap. It is an offline retrieval baseline; no external or medical content has been ingested. Source owners must curate, version, license, and approve content before it is added. An embedding index can replace lexical ranking after local evaluation.
- `agent.validate_generation` checks the narrow response schema, action class, source IDs, unverified numbers, and a small list of prohibited phrases. A rejected generation falls back to a refusal. These checks are **not** sufficient evidence of diagnostic, emergency, causal, or financial-advice safety; independent red-team evaluation is required before enabling generated text for users.
- `routing_eval_cases.json` and `evaluate_routing.py` provide a small inspectable routing smoke test. Unit tests cover identity, consent, product separation, provenance, unavailable history, combined routing, emergency bypass, and rejected generated claims.

The deterministic fallback reports only current session accuracy and prior same-domain median for MindGuard, or the fixed obligation-buffer rank and prior median for Health Reserve. Neither path uses the experimental ML scores for automatic alerts or treatment/cost claims. No MedGemma weights are included in this repository, and no fine-tuning was performed. A default-off Django database integration is described below.

## Backend and local model boundary

The backend must supply `authenticated_user_id`, current `consent_verified` and `enrollment_verified` results, a record selected from a **verified local source run**, and source metadata with `status`, `run_id`, `model_version`, and `product_code`. These flags must never be accepted from a user-controlled HTTP body. The in-memory agent is now wired to a default-off Django endpoint and ORM service under `backend/intelligence/`. That backend has passed mocked contract tests, but a real MySQL connection and transactional integration have not been exercised. The source synthetic Health Reserve timestamps lack an offset and are interpreted as UTC, consistent with the current baseline worker; live APIs should require explicit timezone offsets.

The optional laptop adapter in `src/dumosense_ai/ollama_model.py` calls only the loopback Ollama API (`127.0.0.1:11434`). It requests schema-constrained JSON, a short context, and deterministic decoding; the agent still independently validates the result. Generated text must preserve the observation for **every** requested product verbatim. A failed, incomplete, or invalid generation returns a refusal. No model weights are included or downloaded by the project. The backend uses this adapter only when `DUMOSENSE_ENABLE_LOCAL_MODEL=1`; both that flag and the intelligence query endpoint default to off. Generated responses remain `internal_validation_only` until a curated evaluation corpus passes the product policy and groundedness review. The current response validator is an engineering gate, not an approval for medical use.

### Laptop setup with a locally installed model

The selected model tag is `medgemma1.5:4b-it-q4_K_M` from the Ollama library. On your own machine, download it separately with `ollama pull medgemma1.5:4b-it-q4_K_M` after reviewing its Health AI Developer Foundations terms. The weights live in Ollama's model store, outside this Git repository. Confirm Ollama is running with `ollama list`.

From `ml/`, run the synthetic-data end-to-end smoke test:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m dumosense_ai.local_smoke
```

This script does not read the database or real user data. A `generated` status means the loopback model request and agent policy gate both succeeded for one synthetic case; it does not validate medical accuracy. If the model is absent, the script prints the pull command and exits without downloading it.

On the reference laptop after the model owner installed the tag, the MindGuard and Health Reserve synthetic cases returned validated explanations, emergency routing bypassed the model, and a combined response was accepted only when it contained both product observations. One combined attempt omitted Health Reserve and was correctly rejected; a later attempt included both and passed. Individual local generations took tens of seconds (about 34–43 seconds for the sampled Health Reserve and combined cases). This is a small integration check, not a reliability or quality benchmark.

For an internal backend test after configuring a disposable MySQL database, set `DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=1` and `DUMOSENSE_ENABLE_LOCAL_MODEL=1` in `backend/.env`. The endpoint remains subject to the existing authenticated-user and consent checks. Do not expose the current development settings to external users. Benchmark model load time, latency, peak RAM, grounding, and refusal behavior before any release.

The blueprint also calls for richer MindGuard uncertainty and trajectories; Health Reserve cost/exposure inputs, scenarios and target ranges; a local encrypted database; broader approved RAG; and later federated learning. **Those are not present in the current datasets or this component.** The agent does not invent these fields or compute reserve targets without supplied cost assumptions. It exposes the currently verified baseline outputs and marks the whole component `internal_validation_only`.

From `ml/`:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s .\tests -p 'test_*.py' -q
python .\src\dumosense_ai\evaluate_routing.py
```

## Database integration

See `backend/README_DUMOSENSE_AI.md` for the internal query endpoint, authenticated ORM gateway, consent/enrollment checks, transactionally recorded runs/insights/recommendations/events, and the remaining live-MySQL validation gate. The backend available in this repository uses MySQL rather than Djongo.
