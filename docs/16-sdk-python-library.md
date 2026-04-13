# SDK & Python Library

The Engram SDK provides programmatic access to all Engram capabilities — authentication, tool registration, translation, task execution, and agent management. Use it to integrate Engram into your Python applications or build custom agent workflows.

---

## Installation

```bash
pip install engram-sdk
```

Or import directly from the `engram_sdk/` package if you're developing within the monorepo:

```python
from engram_sdk.client import EngramSDK
```

---

---

## Quick Start (Recommended)

The recommended way to use Engram in production is via **Governed Sequencing**. This pattern uses the `ControlPlane` to enforce a strict state machine on the agent, ensuring it follows the correct sequence of steps and uses a centralized `GlobalData` store for state.

```python
from engram_sdk import ControlPlane, Step, GlobalData, adapter

# 1. Initialize the GlobalData store (Single Source of Truth)
data = GlobalData()

# 2. Define the workflow state machine
cp = ControlPlane(
    steps=[
        Step(name="search", tools=["web_search"], next_step="analyze"),
        Step(name="analyze", tools=["extract_sentiment"], next_step="finalize"),
        Step(name="finalize", tools=["submit_report"])
    ]
)

# 3. Execute with strict step enforcement
with cp.step("search"):
    # The agent is ONLY allowed to call 'web_search'.
    # All results are automatically logged and persisted to GlobalData.
    adapter.execute_tool("web_search", query="Engram SDK")
```

---

## Governed Sequencing

Governed sequencing removes autonomy from the model regarding *the order of operations*, while allowing it to make *small, local decisions* within each step.

### `ControlPlane` & `Step`

The `ControlPlane` acts as the orchestrator. You define a list of `Step` objects that dictate:
- **Allowed Tools**: Exactly which tools are visible to the model in this turn.
- **Strict Transitions**: Where the agent can go next.
- **State Validation**: Ensuring required data exists in `GlobalData` before proceeding.

### `GlobalData` Store

`GlobalData` is a state store that exists entirely outside the model's memory (the "stateless agent" pattern). 
- **Tool Writes**: Tools should be designed to write their results directly to `GlobalData`.
- **Tool Reads**: Subsequent tools pull their inputs from `GlobalData`, not from the model's previous messages.
- **Consistency**: This ensures that even if a model hallucinates a value in its thought process, the system only uses the validated value in the store.

```python
# Reading from the store
user_id = data.read("user_id")

# Writing to the store (managed by tools or manually)
data.write("session_token", "abc-123")
```

---

## Validated Scopes (Granular Pattern)

If you don't need a full state machine but want to restrict tools for a single turn, use **Validated Scopes**.

```python
with sdk.scope("one_off_task", tools=["calculator", "date_fetcher"]) as scope:
    # Validation and activation happen automatically.
    pass
```

> [!IMPORTANT]
> **Ambient Mode (Prototyping Only)**
> Calling tools without a `ControlPlane` or `Scope` is suitable only for quick development. Ambient mode allows the agent to see all registered tools, increasing the risk of hallucinations and unauthorized tool usage.

---

## Authentication

The `AuthClient` (via `engram_sdk/auth.py`) handles the full authentication lifecycle:

### Login

```python
sdk.login()  # Uses email/password from initialization
```

### Signup

```python
sdk.signup()  # Creates a new account, then logs in
```

### EAT Generation

```python
eat = sdk.generate_eat()
```

### Token Refresh

```python
sdk.refresh_eat()  # Automatically refreshes if expired
```

### Auto-Retry on Expiration

The `EngramTransport` layer automatically detects 401 responses, refreshes the EAT token, and retries the request. No manual token management needed in most cases.

---

## Tool Registration

### Single Tool

```python
from engram_sdk.client import ToolDefinition, ToolAction

tool = ToolDefinition(
    name="My API",
    description="My custom API integration",
    actions=[
        ToolAction(
            name="create_item",
            description="Create a new item",
            parameters={
                "name": {"type": "string", "required": True},
                "category": {"type": "string", "required": False}
            },
            endpoint="/items",
            method="POST"
        )
    ]
)

result = sdk.register_tool(tool)
```

### Batch Registration

```python
tools = [tool1, tool2, tool3]
results = sdk.register_tools(tools)
```

### ToolDefinition Dataclass

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Human-readable tool name |
| `description` | `str` | What the tool does |
| `actions` | `List[ToolAction]` | Available actions/endpoints |
| `tags` | `List[str]` | Semantic tags for discovery |
| `base_url` | `str` | Optional base URL override |

### ToolAction Dataclass

| Field | Type | Description |
|---|---|---|
| `name` | `str` | Action name |
| `description` | `str` | What this action does |
| `parameters` | `Dict` | Parameter definitions with types |
| `endpoint` | `str` | API endpoint path |
| `method` | `str` | HTTP method (GET, POST, etc.) |

---

## Agent Registration

```python
sdk.register_agent(
    agent_id="my-agent-001",
    endpoint_url="http://my-agent:5000/webhook",
    supported_protocols=["mcp", "a2a"],
    capabilities=["messaging", "data_processing"],
    tags=["production", "v2"]
)
```

---

## Translation

```python
# Protocol-to-protocol translation
result = sdk.translate(
    payload={"name": "send_message", "arguments": {"text": "Hello"}},
    source_protocol="mcp",
    target_protocol="a2a"
)

print(result.translated_payload)
print(result.canonical_bridge)
print(result.field_mappings)
```

### TranslationResponse

| Field | Type | Description |
|---|---|---|
| `translated_payload` | `Dict` | The payload in the target protocol format |
| `canonical_bridge` | `Dict` | The intermediate ontology representation |
| `field_mappings` | `Dict` | Source → target field translations |
| `ontology_version` | `str` | Ontology version used |

---

## Task Execution

The SDK supports submitting tasks within a validated scope:

### Submit a Task with Scope

```python
# Create a scope for the task
scope = sdk.scope("deployment_step", tools=["kubectl", "docker"])

# Submit task with restricted toolset
result = sdk.submit_task(
    "Deploy 'webapp' to production",
    scope=scope
)
```

---

## Transport Layer

The `EngramTransport` class (`engram_sdk/transport.py`) manages HTTP communication:

| Feature | Detail |
|---|---|
| **Auto-retry** | Retries on transient errors (500, 502, 503, 504) |
| **Token refresh** | Automatically refreshes EAT on 401 |
| **Health check** | `sdk.ping()` to verify connectivity |
| **Timeout** | Configurable request timeout (default: 30s) |

```python
# Health check
if sdk.ping():
    print("Connected to Engram gateway")
```

---

## Type Reference

All SDK types are defined as Python dataclasses:

| Type | Purpose |
|---|---|
| `ToolDefinition` | Complete tool definition for registration |
| `ToolAction` | Individual action within a tool |
| `TaskLease` | Leased task for execution |
| `TaskExecution` | Task execution context |
| `TaskResponse` | Response to submit after execution |
| `TranslationResponse` | Result of a protocol translation |
| `MappingSuggestion` | ML-suggested field mapping |
| `TaskSubmissionResult` | Result of submitting a new task |

---

## Error Handling

The SDK raises typed exceptions:

| Exception | When |
|---|---|
| `EngramSDKError` | Base class for all SDK errors |
| `EngramAuthError` | Authentication failure (invalid credentials, expired token) |
| `EngramRequestError` | Network or HTTP error (connection refused, timeout) |
| `EngramResponseError` | Unexpected response from the gateway (400, 500) |

```python
from engram_sdk.client import EngramSDK, EngramAuthError, EngramRequestError

try:
    sdk.login()
except EngramAuthError as e:
    print(f"Auth failed: {e}")
except EngramRequestError as e:
    print(f"Network error: {e}")
```

---

## Example: Full Agent Loop

```python
from engram_sdk.client import EngramSDK, ToolDefinition, ToolAction

# 1. Initialize and authenticate
sdk = EngramSDK(
    base_url="http://127.0.0.1:8000",
    email="agent@company.com",
    password="agent-password"
)
sdk.connect()
sdk.login()
sdk.generate_eat()

# 2. Register this agent
sdk.register_agent(
    agent_id="weather-agent",
    endpoint_url="http://localhost:5001",
    supported_protocols=["mcp"],
    capabilities=["weather_queries"]
)

# 3. Register tools
sdk.register_tool(ToolDefinition(
    name="Weather Service",
    description="Real-time weather data",
    actions=[
        ToolAction(
            name="current",
            description="Get current weather",
            parameters={"city": {"type": "string", "required": True}},
            endpoint="/weather/current",
            method="GET"
        )
    ]
))

# 4. Task execution loop
print("Agent ready. Polling for tasks...")
while True:
    task = sdk.receive_task()
    if task:
        print(f"Received task: {task.command}")
        try:
            # Execute the task (your custom logic here)
            result = {"temperature": 72, "city": "San Francisco", "unit": "F"}
            sdk.send_response(task_id=task.task_id, result=result, status="completed")
            print(f"Task {task.task_id} completed")
        except Exception as e:
            sdk.send_response(task_id=task.task_id, result=None, status="failed", error=str(e))
```

---

## What's Next

- **[Architecture](./17-architecture.md)** — Understand the system internals
- **[EAT Identity & Security](./12-eat-identity-security.md)** — Configure authentication
- **[CLI Reference](./06-cli-reference.md)** — CLI counterparts of SDK operations
