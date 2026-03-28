# Engram Developer Toolkit

This guide ships the release-ready documentation and examples for the Engram SDK. It focuses on four developer goals:

1. Install the SDK
2. Register a tool
3. Connect an agent to Engram
4. Run tasks end-to-end

If you are new to the system, start with the quickstart below and then explore the example project in `examples/engram_toolkit/`.

---

## Quickstart (Local)

### 1. Start the Engram backend

From the repository root:

```bash
docker compose up --build
```

Or run locally:

```bash
uvicorn app.main:app --reload
```

Swagger UI will be available at `http://localhost:8000/docs`.

---

### 2. Install the SDK (from this repo)

The SDK lives in `engram_sdk/` and can be imported directly from the repo.

```bash
pip install httpx
```

Then either:

```bash
set PYTHONPATH=%CD%
```

Or, if you prefer `pip` editable installs:

```bash
pip install -e .
```

---

### 3. Generate a dev token (required for task queue)

The task queue (`/api/v1/queue/enqueue`) expects a bearer token with the `translate:a2a` scope. For local development you can generate one using the helper script:

```bash
python scripts/generate_token.py --secret <AUTH_JWT_SECRET> --scope translate:a2a
```

Export it so the SDK can use it:

```bash
set ENGRAM_EAT=<token>
```

---

### 4. Run the example toolkit

The example project lives in:

`examples/engram_toolkit/`

It includes a minimal health server, tool registration, a worker loop, and a submit script.

Start the health endpoint:

```bash
python examples/engram_toolkit/agent_server.py
```

Register the tool + agent:

```bash
python examples/engram_toolkit/register_tool.py
```

Run the task worker (polls Engram for messages):

```bash
python examples/engram_toolkit/run_worker.py
```

In a separate terminal, enqueue a task:

```bash
python examples/engram_toolkit/submit_task.py
```

You should see the worker receive the translated payload and respond.

---

## What This Demonstrates

1. **SDK installation**
2. **Tool metadata registration**
3. **Agent registry connection**
4. **Queue-based task execution**

At runtime, the flow is:

1. `submit_task.py` enqueues an A2A payload for an MCP-capable agent.
2. Engram translates A2A -> MCP.
3. The worker polls `/agents/{agent_id}/messages/poll`.
4. The worker returns a structured response via `/agents/messages/{message_id}/respond`.

---

## SDK Surface Map (Minimal)

Core entrypoints from `engram_sdk/`:

* `EngramSDK` in `engram_sdk/client.py`
* `ToolDefinition`, `ToolAction` in `engram_sdk/types.py`
* `TaskExecutor` in `engram_sdk/execution.py`

Key calls you'll use most often:

* `sdk.register_tool(...)`
* `sdk.register_agent(...)`
* `sdk.tasks.enqueue_task(...)`
* `sdk.task_executor().run(...)`

---

## Notes

* Registering an agent requires an `endpoint_url` and `agent_id`.
* Discovery pings `/health` on your `endpoint_url`.
* Task queue calls require a bearer token with `translate:a2a`.
* A2A -> MCP is currently the supported translation path for queue tasks in this repo.
