# Engram SDK Toolkit Example

This example shows the full loop:

1. Start a simple health endpoint (`/health`)
2. Register a tool and agent with Engram
3. Enqueue a task to that agent
4. Run a worker that polls and responds

---

## Prerequisites

* Engram backend running on `http://localhost:8000`
* Python 3.9+

---

## Install the SDK

From the repo root:

```bash
pip install -e .
```

---

## 1. Generate a dev token (task queue requires it)

```bash
python scripts/generate_token.py --secret <AUTH_JWT_SECRET> --scope translate:a2a
```

Set it for the SDK:

```bash
set ENGRAM_EAT=<token>
```

---

## 2. Start the agent health endpoint

```bash
python examples/engram_toolkit/agent_server.py
```

---

## 3. Register the tool + agent

```bash
python examples/engram_toolkit/register_tool.py
```

This stores the generated agent ID in `examples/engram_toolkit/agent_id.txt` so the other scripts can reuse it.

---

## 4. Run the worker loop

```bash
python examples/engram_toolkit/run_worker.py
```

---

## 5. Enqueue a task

```bash
python examples/engram_toolkit/submit_task.py
```

The worker should print the translated MCP payload and respond.

---

## Environment Overrides

You can override defaults via env vars:

* `ENGRAM_BASE_URL` (default `http://localhost:8000/api/v1`)
* `ENGRAM_ENDPOINT_URL` (default `http://localhost:8080`)
* `ENGRAM_AGENT_ID` (optional override for the stored ID)
* `ENGRAM_EAT` (required for queue calls)
