# Dumosense intelligence development

This repository contains engineering prototypes for three distinct parts of Dumosense: the **MindGuard** cognitive baseline and machine-learning research, the **Health Reserve** preparedness score and machine-learning research, and a **Dumosense AI** agent that reads approved product states and explains them. The agent never calculates the underlying product scores. Current datasets are synthetic; the present results and generated answers are for internal validation, not clinical decisions or automated alerts.

The near-term target is a laptop demonstration with a local MedGemma model. The eventual product target is an offline-first phone app. The laptop's Python/Django/Ollama stack is a development reference, not a mobile binary.

## Repository map

| Path | Responsibility |
| --- | --- |
| [`ml/README.md`](ml/README.md) | MindGuard statistical worker, historical baselines, run verification, and saved parameters. |
| [`ml/README_ML.md`](ml/README_ML.md) | MindGuard five-family ML benchmark and held-out metrics. |
| [`ml/README_HEALTH_RESERVE.md`](ml/README_HEALTH_RESERVE.md) | Health Reserve feature contract and cost-free statistical rank. |
| [`ml/README_HEALTH_RESERVE_ML.md`](ml/README_HEALTH_RESERVE_ML.md) | Health Reserve ML benchmark, metrics, and package. |
| [`ml/README_DUMOSENSE_AI.md`](ml/README_DUMOSENSE_AI.md) | Controlled agent, context, response policy, and laptop model adapter. |
| [`ml/src/dumosense_ai/`](ml/src/dumosense_ai/) | Product routing, context assembly, local Ollama adapter, and synthetic smoke test. |
| [`ml/weights/README.md`](ml/weights/README.md) | Versioned statistical and ML artifacts with integrity manifests. |
| [`backend/README_DUMOSENSE_AI.md`](backend/README_DUMOSENSE_AI.md) | Default-off Django API, authenticated data gateway, consent checks, and database validation gap. |
| `data/synthetic/`, `validation/` | Synthetic inputs and evaluation fixtures. |
| `sql/` | Reference SQL schema; verify it against the actual environment before enabling the API. |

`ml/weights/` holds small, versioned **statistical and tabular ML** artifacts. It does **not** contain MedGemma. Ollama stores the language-model weights separately on the development computer. Do not add raw user data, generated run outputs, virtual environments, Ollama weights, or `old_logs/` to Git.

## What works today

- The MindGuard worker and Health Reserve baseline/ML packages have independent documentation, metrics, and saved artifacts under `ml/weights/`. The ML benchmarks use synthetic labels and are not approved for patient-facing predictions.
- The agent routes MindGuard, Health Reserve, and combined questions to fixed product tools. It checks trusted identity, enrollment, consent, source run, and response format. When no language model is enabled, it returns a deterministic product observation.
- An optional adapter calls Ollama **only at `http://127.0.0.1:11434`**, requesting a bounded JSON explanation. A rejected model response does not become a successful generated answer.
- The backend query endpoint and local-model integration both default to **off**. Backend contract tests and an in-memory database smoke test have passed; a real MySQL integration has **not** been validated.
- No MedGemma weights have been downloaded by this project. The selected laptop tag is `medgemma1.5:4b-it-q4_K_M`.

The current backend in this checkout uses **Django ORM and MySQL**, not Djongo/MongoDB. Resolve the intended database branch and validate its real schema and authentication before deployment. The checked-in Django settings are development settings and must not be exposed as a public service. Supply a unique `DJANGO_SECRET_KEY` through the local environment; the repository contains only a development fallback.

## Laptop setup: local explanation model

Use Python 3.11 and Ollama on Windows. The laptop smoke test uses synthetic data only and does not require MySQL. The model owner should review the [Google MedGemma model card and terms](https://huggingface.co/google/medgemma-1.5-4b-it) and download the [Ollama 4-bit MedGemma 1.5 tag](https://ollama.com/library/medgemma1.5/tags) themselves:

```powershell
ollama pull medgemma1.5:4b-it-q4_K_M
ollama list
Set-Location 'C:\Users\HP\Downloads\dumosense\ml'
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m dumosense_ai.local_smoke
```

The smoke script checks that Ollama is reachable and that the exact model tag is installed. It sends one synthetic MindGuard state through the model and policy gate. Success prints `"status": "generated"`; failure exits nonzero with a message. A single success shows integration only. Review answer grounding, latency, peak RAM, and failure cases on the target laptop before enabling the model with stored records. If the model is absent, the script prints the pull command and **does not** download it.

Ollama must be running locally. The adapter does not use a remote inference endpoint and does not accept an endpoint URL from an API caller. Avoid putting real user records into ad hoc prompts or test files.

## Automated checks

From the repository root, run the ML suite and backend contract tests:

```powershell
Set-Location 'C:\Users\HP\Downloads\dumosense\ml'
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m unittest discover -s .\tests -p 'test_*.py' -q

Set-Location '..\backend'
$env:DB_NAME = 'dumosense_test_dummy'
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py test intelligence
```

If `backend/venv` does not exist, create a Python 3.11 virtual environment and install `backend/requirements.txt` first. The dummy database name allows the current `SimpleTestCase` tests to initialize; it does not test a live MySQL instance. Other worker-specific commands and package verification are in the linked ML READMEs. Do not treat a passing unit suite as clinical or live-database validation.

## Optional internal Django integration

The API is **not required** for the synthetic laptop smoke test. For a separate internal integration environment, configure a disposable MySQL copy of the expected schema, install the pinned backend dependencies, and put local credentials in `backend/.env` using `backend/.env.example` as a template. Keep that file out of Git. Only after confirming database connectivity, authentication, active enrollment, consent, ownership, and withdrawal behavior should the two internal switches be set:

```text
DUMOSENSE_ENABLE_INTELLIGENCE_QUERY=1
DUMOSENSE_ENABLE_LOCAL_MODEL=1
```

`POST /api/v1/intelligence/query/` accepts a question from an authenticated user. The backend obtains that user's records through fixed ORM queries, passes a minimal product state to the agent, and records the resulting run and insight. It does not accept user IDs or consent flags from the request body. See the backend README for details. Until the live database and model evaluations are complete, leave both switches off in any user-facing environment.

## Release boundary and next work

Current output is marked `internal_validation_only`. The synthetic MindGuard change detector has missed many labelled changes and produced too many false positives for automatic alerts. Health Reserve has no real treatment-cost inputs, so its rank is a preparedness proxy, not a guarantee of affordability. The language model must not turn either result into a diagnosis, causal claim, treatment recommendation, or financial promise.

Before a user-facing MVP, validate the actual backend/database branch, evaluate MedGemma on an independently reviewed set of product questions and failure cases, verify consent and data retention end to end, benchmark offline performance, and harden the Django deployment configuration. A later phone implementation will require mobile-compatible scoring/inference and on-device model packaging; the laptop Ollama adapter is a reference for that work.

## Publishing source

Commit reviewed source, documentation, and the versioned small statistical/ML packages. The root `.gitignore` excludes `old_logs/`, generated root outputs, local environments, secrets, and common LLM weight formats. Before pushing, inspect `git status` and `git diff --cached --stat`; do not use a blanket `git add .` for this working tree. The Git remote is `https://github.com/heavenswill99/dumosense.git`, and the working branch is `artificial_intelligence_models`.
