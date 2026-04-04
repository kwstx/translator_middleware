# Testing & Performance

This document outlines the procedures for testing the **Semantic Bridge** in local and staging environments, including benchmarks and profiling-driven optimization.

---

## 🧪 Automated Testing (Pytest)

Run the full suite with coverage:

```bash
pytest --cov=app tests/
```

### Async Testing
All tests use `@pytest.mark.asyncio`. We use `httpx.AsyncClient` for API testing.

### Integration & E2E Testing
We have automated integration flows that simulate end-to-end agent interactions:

```bash
$env:PYTHONPATH="."
python tests/integration/run_integration_e2e.py
```
This script starts a local server and worker, registers mock agents, and performs a full translation flow with fidelity verification and cryptographic proofs.

---

## 📊 Benchmarks (Baseline Targets)

Targets for `POST /api/v1/beta/translate` under local Docker Compose:

| Metric | Target |
| :--- | :--- |
| **Latency (p50)** | ≤ 120 ms |
| **Latency (p95)** | ≤ 300 ms |
| **Throughput** | ≥ 150 requests/sec |
| **Error Rate** | ≤ 1% |
| **Resource Usage** | CPU ≤ 80% avg, memory stable |

---

## ⚡ Performance & Load Testing (JMeter)

### Run Load Test (CLI)
Make sure `jmeter` is on your PATH.

```powershell
.\scripts\perf\run_jmeter.ps1 `
  -TargetHost localhost `
  -Port 8000 `
  -Threads 50 `
  -RampUp 30 `
  -Duration 180 `
  -Jwt "<YOUR_JWT_TOKEN>"
```

### Resource Usage Sampling
Collect CPU/RAM/threads for the FastAPI process while load runs:

```powershell
.\scripts\perf\collect_metrics.ps1 -ProcessName "python" -DurationSec 300 -IntervalSec 1 -OutFile .\perf_results\resource_metrics.csv
```

---

## 🔍 Profiling Tools (Hotspot Detection)

### py-spy (Sampling, Low Overhead)
```bash
py-spy record -o .\perf_results\pyspy.svg --pid <PID>
```

### pyinstrument (Request-Level Profiling)
```bash
pyinstrument -r html -o .\perf_results\pyinstrument.html -m uvicorn app.main:app --reload
```

---

## 🏗️ Staging Instance (Docker)
We use a dedicated Docker Compose file for staging to isolate it from production/dev:

```bash
docker compose -f docker-compose.staging.yml up --build -d
```
**This boots up:**
- Engram (Staging) on port 8001
- PostgreSQL (Staging)
- Redis (Staging)
- **WireMock** (External Agent Mock) on port 8080
- **Sentry Mock** (Error track placeholder)

---

## 🚀 Troubleshooting Bottlenecks

1.  **Semantic mapping (OWL + PyDatalog)**:
    - Cache resolved concepts in Redis (`REDIS_ENABLED=true`).
    - Preload ontologies on startup to avoid per-request parsing.
2.  **Orchestrator / Translator path building**:
    - Keep `Orchestrator` singleton to avoid rebuilding the `ProtocolGraph`.
3.  **DB roundtrips on failure logging**:
    - Batch writes for `MappingFailureLog` or reduce `MAPPING_FAILURE_MAX_FIELDS`.
4.  **JSON Schema validation**:
    - Cache compiled schemas or skip validation for known safe payloads.

---

**Version 0.1.0** | *Performance Guide*
