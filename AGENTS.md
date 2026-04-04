# AGENTS.md: Principles for AI Agents

This document provides guidance to AI agents (including WARP, Antigravity, and others) when working with code in this repository. 

---

## 🚀 Commands

### Run locally
```bash
uvicorn app.main:app --reload
```
Swagger UI is available at `http://localhost:8000/docs`.

### Run with Docker (Recommended)
Starts the app, PostgreSQL, Redis, Prometheus, and Grafana.
```bash
docker compose up --build
```

### Run staging environment
Adds WireMock for external agent mocking.
```bash
docker compose -f docker-compose.staging.yml up --build -d
```

### Install dependencies
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Run tests
```bash
pytest -q
```
Run a single test file: `pytest tests/test_api_endpoints.py -q`

Run with coverage: `pytest --cov=app tests/`

Run the full E2E integration flow (starts a local server internally):
```bash
$env:PYTHONPATH="."
python tests/integration/run_integration_e2e.py
```

### Generate a JWT for local testing
```bash
python scripts/generate_token.py --secret <AUTH_JWT_SECRET> --scope translate:a2a
```
This mints an HS256 token matching the `AUTH_ISSUER`, `AUTH_AUDIENCE`, and `AUTH_JWT_SECRET` in `.env`.

---

## 🏛️ Architecture Overview

### Translation Pipeline
A translation request flows through three layers:

1.  **`TranslatorEngine`** (`app/core/translator.py`): Handles structural transformation. Before translation, it applies version deltas from the `ProtocolVersionDelta` table.
2.  **`Orchestrator` + `ProtocolGraph`** (`app/messaging/orchestrator.py`): Wraps the engine with multi-hop routing using Dijkstra shortest path (Dijkstra by weight).
3.  **`SemanticMapper`** (`app/semantic/mapper.py`): Resolves content/meaning using OWL ontologies (`owlready2`), PyDatalog rules, and Redis caching.

### ML Fallback Mapping
If a semantic gap is detected, `app/services/mapping_failures.py` logs the failure. `MappingPredictor` uses a TF-IDF + Logistic Regression pipeline trained on `ProtocolMapping.semantic_equivalents`. Predictions above `0.85` are auto-applied.

### Task Queue
Requests are persisted as `Task` rows to PostgreSQL. The `TaskWorker` background loop polls with a lease and executes the handoff. Dead-letter status is used for exhausted retries.

### Agent Registry & Discovery
`DiscoveryService` (`app/services/discovery.py`) pings registered agents' `/health` every 60s. Collaboration compatibility is scored based on shared and mappable protocols.

---

## 🔒 Authentication
All `/api/v1` routes require a **Bearer JWT** (app/core/security.py). Tokens carry `iss`, `aud`, and `exp` claims. Scopes `translate:a2a` and `translate:beta` gate respective endpoints.

---

## 🧭 Observability
- **Structured Logging**: `structlog` configured in `app/core/logging.py`.
- **Metrics**: Exposed at `GET /metrics` via `prometheus-fastapi-instrumentator`.
- **Grafana Dashboard**: Automatically provisioned from `monitoring/grafana/`.

---

**Source of Truth for Developer Agents** | *Version 0.1.0*
