<p align="center">
  <img src="assets/logo.png" alt="Engram Logo" width="400">
</p>

<h1 align="center">Engram</h1>

<p align="center">
  <strong>CONNECT ANY AGENT. ANY TOOL. ANY API.</strong><br>
  One identity layer. One routing engine. One semantic bridge.
</p>

<p align="center">
  <a href="https://github.com/kwstx/engram_translator/actions"><img src="https://img.shields.io/github/actions/workflow/status/kwstx/engram_translator/ci.yml?branch=main&style=for-the-badge" alt="CI status"></a>
  <a href="https://github.com/kwstx/engram_translator/releases"><img src="https://img.shields.io/github/v/release/kwstx/engram_translator?include_prereleases&style=for-the-badge" alt="GitHub release"></a>
  <a href="https://discord.gg/engram"><img src="https://img.shields.io/discord/1456350064065904867?label=Discord&logo=discord&logoColor=white&color=5865F2&style=for-the-badge" alt="Discord"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Works_with-MCP-blue?style=for-the-badge" alt="Works with MCP">
  <img src="https://img.shields.io/badge/Works_with-A2A-green?style=for-the-badge" alt="Works with A2A">
  <img src="https://img.shields.io/badge/Works_with-ACP-orange?style=for-the-badge" alt="Works with ACP">
</p>

**Engram** is the lightweight interoperability layer that sits between any AI agents, tools, and third-party APIs. It translates protocols (A2A, MCP, ACP), auto-fixes schema mismatches with OWL ontologies + self-healing ML, routes tasks through a weighted directed graph, and gives every participant a single EAT token. No more custom glue code.

If you are tired of rewriting adapters every time a new agent or standard drops, this is it.

<p align="center">
  <a href="https://useengram.com">Website</a> &#183;
  <a href="https://docs.useengram.com">Docs</a> &#183;
  <a href="https://docs.useengram.com/showcase">Showcase</a> &#183;
  <a href="https://discord.gg/engram">Discord</a> &#183;
  <a href="https://docs.useengram.com/integrations/openclaw">OpenClaw Companion Guide</a>
</p>

**Preferred setup:** `docker compose up` (or `uvicorn` for local dev).

---

## Install (recommended)

```bash
git clone https://github.com/kwstx/engram_translator.git && cd engram_translator
docker compose up --build -d
```

Open `http://localhost:8000/docs` for the Swagger UI. The full stack (PostgreSQL, Redis, Prometheus, Grafana) starts automatically.

Upgrading? `git pull && docker compose up --build -d`.

---

## Quick Start

```bash
# 1. Start Engram
docker compose up --build

# 2. Register an agent
curl -X POST http://localhost:8000/api/v1/register \
  -H "Authorization: Bearer <your-eat-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "supported_protocols": ["MCP"],
    "capabilities": ["shell", "web", "email"],
    "semantic_tags": ["automation", "research"],
    "endpoint_url": "http://openclaw:9000"
  }'

# 3. Translate a message between protocols
curl -X POST http://localhost:8000/api/v1/beta/translate \
  -H "Authorization: Bearer <your-eat-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "source_protocol": "A2A",
    "target_protocol": "MCP",
    "payload": {
      "payload": { "intent": "dispatch", "delivery_window": { "start": "2026-03-12T09:00:00Z" } }
    }
  }'

# 4. Delegate a natural-language task (intent is resolved automatically)
curl -X POST http://localhost:8000/api/v1/delegate \
  -H "Authorization: Bearer <your-eat-token>" \
  -H "Content-Type: application/json" \
  -d '{"command": "Summarize the latest OpenClaw release and send it to Slack"}'
```

---

## Highlights

- **Protocol translation** -- Full bidirectional A2A, MCP, ACP conversion. Multi-hop routing when no direct edge exists (e.g., A2A -> MCP -> ACP). Version delta upgrades normalize source messages before translation.
- **Semantic self-healing mapper** -- OWL ontology + PyDatalog rules + TF-IDF/LogisticRegression fallback. On failure: logs the unmapped field, predicts a correction, auto-applies if confidence >= 0.85, and retrains itself every N corrections.
- **Weighted directed graph routing** -- NetworkX DiGraph with Dijkstra shortest-path. Edge weights are computed from agent latency (`avg_latency * 0.1`) and success rate (`(1.0 - success_rate) * 50.0`). Dead agents are dropped by the heartbeat service.
- **Unified identity layer** -- One Engram Access Token (EAT) per participant. JWT-based, HS256/RS256, scoped to specific protocols and tools. Issued automatically on `/signup`.
- **Natural-language orchestration** -- Free-text commands are decomposed into atomic tasks via the IntentResolver, mapped to agent capability tags, and delegated through the Orchestrator without the caller specifying a protocol or endpoint.
- **Cryptographic execution proofs** -- Every translation hop produces a `v1:sha256:<hash>` proof. Multi-hop translations return an aggregate `v1:agg:<hash>` proving the full chain.
- **Production observability** -- Prometheus counters, histograms, and rolling-window gauges. Pre-provisioned Grafana dashboards for throughput, error rate, and latency. Real-time TUI debug console with structured event streaming.
- **Discovery + heartbeat** -- Agents register once. `DiscoveryService` pings `/health` every 60s. Compatibility scoring ranks candidates by `(shared_protocols + mappable_protocols) / total_candidate_protocols`.

---

## Everything We Built So Far

### Core Platform

| Component | Description |
| :--- | :--- |
| **FastAPI service** | Async Python backend (`app/main.py`). All routes under `/api/v1`. |
| **Task queue** | PostgreSQL-backed with lease-based polling, retry up to `TASK_MAX_ATTEMPTS`, dead-letter on exhaustion. |
| **Real-time TUI** | Textual-based terminal interface. WelcomeScreen, ProviderSelectionScreen, DebugScreen with live task/log/trace tabs. |
| **Prometheus + Grafana** | `GET /metrics` endpoint. Pre-configured dashboards in `monitoring/grafana/`. |

### Protocol Layer

| Component | Description |
| :--- | :--- |
| **TranslatorEngine** | Structural transformation between protocol pairs. Each `(source, target)` maps to a dedicated method. |
| **Version deltas** | `ProtocolVersionDelta` table stores `rename`, `drop`, `set` rules. BFS finds the upgrade path between versions. |
| **Multi-hop conversion** | `ProtocolGraph` + `Orchestrator` chains hops via Dijkstra when no direct translator exists. |

### Semantic Bridge

| Component | Description |
| :--- | :--- |
| **OWL ontology engine** | `owlready2`-based. Bundled `protocols.owl` defines A2A/MCP/ACP namespace equivalences. |
| **PyDatalog rules** | Explicit field renames asserted as Datalog facts. Queried before ontology fallback. |
| **ML fallback pipeline** | `TfidfVectorizer(char, ngram 3-5)` + `LogisticRegression(max_iter=1000)`. Model persisted to `mapping_model.joblib`. |
| **Self-healing loop** | Failure logged -> ML predicts -> auto-applies if conf >= 0.85 -> retrains every `ML_AUTO_RETRAIN_THRESHOLD` corrections. |

### Routing Engine

| Component | Description |
| :--- | :--- |
| **ProtocolGraph** | NetworkX `DiGraph`. Nodes = protocols + agent endpoints. Edges = translation capabilities with computed weights. |
| **Dynamic weighting** | `weight = 1.0 + (avg_latency * 0.1) + ((1.0 - success_rate) * 50.0)` per agent. |
| **Compatibility scoring** | `score = (shared_protocols + mappable_protocols) / total_candidate_protocols`. |

### Identity and Security

| Component | Description |
| :--- | :--- |
| **EAT system** | JWT with `sub`, `iss`, `aud`, `exp`, `allowed_tools`, `scopes`. Issued on `/signup` or via `scripts/generate_token.py`. |
| **Scope enforcement** | Route-level guards: `translate:a2a`, `translate:beta`. Tool-level: `scopes.translator = ["*"]` or `["MCP", "ACP"]`. |

---

## How It Works (one glance)

```mermaid
flowchart TB
    subgraph Sources
        AG1["Agent A (A2A)"]
        AG2["Agent B (MCP)"]
        NL["Human (Natural Language)"]
    end
    subgraph Engram Core
        AUTH["EAT Auth Layer"]
        IR["Intent Resolver"]
        PG["Protocol Graph + Dijkstra"]
        SM["Semantic Mapper (OWL + ML)"]
        TQ["Task Queue"]
    end
    subgraph Targets
        AG3["Agent C (ACP)"]
        TOOL["External Tools / APIs"]
    end
    AG1 --> AUTH
    AG2 --> AUTH
    NL --> AUTH
    AUTH --> IR
    IR --> PG
    PG --> SM
    SM --> TQ
    TQ --> AG3
    TQ --> TOOL
```

---

## Already Works With

| Integration | Type | Notes |
| :--- | :--- | :--- |
| **OpenClaw** | Official companion layer | See [companion guide](https://docs.useengram.com/integrations/openclaw) |
| **Claude Code / Cursor agents** | MCP-compatible | Register with `supported_protocols: ["MCP"]` |
| **LangGraph / CrewAI / AutoGPT** | A2A-compatible | Register with `supported_protocols: ["A2A"]` |
| **MiroFish Swarm** | Native connector | Seed injection + God's Eye live context via `/mirofish/pipe` and `/mirofish/gods-eye` |
| **Anthropic / Perplexity / Slack** | Tool connectors | Configured via `ANTHROPIC_API_KEY`, `PERPLEXITY_API_KEY`, `SLACK_API_TOKEN` in `.env` |
| **Binance / Coinbase / FRED / Reuters** | Trading semantic templates | Standard adapters with pre-defined schemas |
| **Any custom A2A, MCP, or ACP agent** | Self-registration | `POST /api/v1/register` with protocols, capabilities, and endpoint URL |

---

## Latest Changes (March 2026)

- AI Provider Selection Hub added to TUI (OpenAI, Anthropic, Google, Grok, Perplexity, DeepSeek, Mistral, LLaMA)
- Automated EAT generation on `/signup`
- Alembic database migrations replacing manual schema management
- Self-healing semantic mapping loop (failure -> ML predict -> auto-apply -> retrain)
- Cryptographic execution proofs on every translation hop
- Performance-aware Dijkstra routing with dynamic agent weights
- Transformer-ready NL intent resolver with automated delegation via `POST /api/v1/delegate`
- Structured observability: Prometheus metrics, Grafana dashboards, TUI debug console

---

## Docs and Links

| Resource | Link |
| :--- | :--- |
| Full documentation | [docs.useengram.com](https://docs.useengram.com) |
| API reference (Swagger) | `http://localhost:8000/docs` (local) |
| Self-hosting guide | [docs.useengram.com/self-hosting](https://docs.useengram.com/self-hosting) |
| OpenClaw integration | [docs.useengram.com/integrations/openclaw](https://docs.useengram.com/integrations/openclaw) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Discord | [discord.gg/engram](https://discord.gg/engram) |

---

## What's New

### 1. AI Provider Selection Hub (TUI)

The TUI includes a categorized **Model Directory** that lists major AI providers and their available model families. Selecting a provider opens a provider-specific API connection screen with pre-filled key format hints.

**Supported providers and their connection screens:**

| Provider | Models | Key Format | Connection Screen Class |
| :--- | :--- | :--- | :--- |
| **OpenAI** | GPT-4o, o1, o3-mini | `sk-proj-...` | `OpenAIConnectScreen` |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus | `sk-ant-api03-...` | `AnthropicConnectScreen` |
| **Google DeepMind** | Gemini 1.5 Pro, 2.0 Flash | `AIzaSy...` | `GoogleConnectScreen` |
| **Meta / LLaMA** | LLaMA 3.1, 3.2 (self-hosted/API) | `llama-...` | `LlamaConnectScreen` |
| **Mistral AI** | Mistral Large, Mixtral 8x22B | Mistral API Key | `MistralConnectScreen` |
| **xAI (Grok)** | Grok-2, Grok-1.5 | `xoxb-...` | `GrokConnectScreen` |
| **Perplexity** | Research / Web Search | `pplx-...` | `PerplexityConnectScreen` |
| **DeepSeek** | DeepSeek-Coder | `sk-...` | `DeepseekConnectScreen` |

The directory is rendered via `ProviderSelectionScreen` in `tui/app.py`. Providers are grouped into categories (**AI Models** and **Software Tools**), with disabled header rows acting as section labels. Selecting a list item dismisses the screen and pushes the matching connection screen onto the stack.

```mermaid
flowchart TD
    A["WelcomeScreen"] -->|"Setup API Keys"| B["ProviderSelectionScreen"]
    B -->|"sel-openai"| C["OpenAIConnectScreen"]
    B -->|"sel-anthropic"| D["AnthropicConnectScreen"]
    B -->|"sel-google"| E["GoogleConnectScreen"]
    B -->|"sel-llama"| F["LlamaConnectScreen"]
    B -->|"sel-mistral"| G["MistralConnectScreen"]
    B -->|"sel-grok"| H["GrokConnectScreen"]
    B -->|"sel-perplexity"| I["PerplexityConnectScreen"]
    B -->|"sel-deepseek"| J["DeepseekConnectScreen"]
    C -->|"POST /credentials"| K["Backend Vault"]
    D -->|"POST /credentials"| K
    E -->|"POST /credentials"| K
    F -->|"POST /credentials"| K
    G -->|"POST /credentials"| K
    H -->|"POST /credentials"| K
    I -->|"POST /credentials"| K
    J -->|"POST /credentials"| K
```

Each connection screen inherits from `BaseServiceConnectScreen`, which handles the `POST /credentials` call to the backend and stores the credential locally via `VaultService`. The connection is provider-specific: it sends the `provider_name`, `credential_type` (either `api_key` or `oauth`), and the raw token as encrypted metadata.

---

### 2. Automated Engram Access Token (EAT) Generation

The `/signup` endpoint (`app/api/v1/auth.py`) automatically generates and returns a long-lived JWT called an **Engram Access Token (EAT)** upon successful registration. This eliminates the need to run `scripts/generate_token.py` manually after signing up.

**What happens on `POST /api/v1/auth/signup`:**

```mermaid
sequenceDiagram
    participant Client
    participant API as POST /auth/signup
    participant DB as PostgreSQL
    participant JWT as Token Engine

    Client->>API: { email, password }
    API->>DB: INSERT User + PermissionProfile
    DB-->>API: user_id
    API->>JWT: create_access_token(sub=user_id, scope="translate:a2a", sid=session_id)
    JWT-->>API: access_token (short-lived, 7 days)
    API->>JWT: create_engram_access_token(user_id, permissions, 30 days)
    JWT-->>API: EAT (long-lived, 30 days)
    API-->>Client: { user, access_token, eat }
```

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "dev@example.com", "password": "s3cur3!", "user_metadata": {}}'
```

**Response (HTTP 201):**

```json
{
  "user": {
    "id": "a1b2c3d4-...",
    "email": "dev@example.com",
    "user_metadata": {},
    "is_active": true
  },
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "eat": "eyJhbGci..."
}
```

**EAT structure (decoded):**

| Claim | Value | Description |
| :--- | :--- | :--- |
| `sub` | `"a1b2c3d4-..."` | User UUID |
| `type` | `"EAT"` | Token type identifier — distinguishes EATs from standard session tokens |
| `allowed_tools` | `["core_translator", "discovery"]` | Tool IDs this token grants access to |
| `scopes` | `{"core_translator": ["read", "execute"], "discovery": ["read"]}` | Per-tool permission map |
| `scope` | `"execute read"` | Flattened space-separated scope string for OAuth2 compatibility |
| `exp` | `1750000000` | Expiration (30 days from issue by default) |
| `iss` | `AUTH_ISSUER` | Issuer claim, validated on every request |
| `aud` | `AUTH_AUDIENCE` | Audience claim, validated on every request |
| `jti` | `"uuid-..."` | Unique token ID for revocation tracking via Redis |

The `access_token` is a short-lived session token (default 7 days, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`). The `eat` is the long-lived token (30 days) intended for agent-to-agent authentication. Both tokens can be revoked via `POST /api/v1/auth/tokens/revoke-eat` or `POST /api/v1/auth/logout`.

---

### 3. CLI Debugging & Monitoring Suite

A `debug` subcommand was added to the CLI (`app/cli.py`). Running `engram debug` (or `python app/cli.py debug`) starts the backend and launches the TUI directly into a `DebugScreen` instead of the standard `WelcomeScreen`.

**Launch commands:**

```bash
# Via the CLI entry point
python app/cli.py debug

# Via the batch script (Windows)
.\engram.bat debug

# With custom host/port
python app/cli.py debug --host 0.0.0.0 --port 9000
```

**DebugScreen capabilities:**

| Panel | Widget | What it shows |
| :--- | :--- | :--- |
| **Task List** | `DataTable` | All queued/running/completed tasks with IDs, status, and timestamps |
| **Protocol Trace** | `TabbedContent` with source/target panes | Side-by-side view of the original message and its translated output (e.g., A2A input → MCP output) |
| **Event Log** | `RichLog` | Live stream of backend events — translation attempts, version delta upgrades, mapping failures, and task state transitions |

The event log is powered by `tui_bridge.py`, which defines a `structlog` processor called `tui_logger_processor`. This processor intercepts translation-related log events and pushes plain-English messages to an async queue (`tui_event_queue`) that the TUI polls. The following backend events are captured and displayed:

```
Event: "Translating message"    → "🔄 Translating message from MCP to A2A..."
Event: "Applied version delta"  → "✨ MCP message upgraded: 1.0 ➡️ 2.0"
Event: "Translation failed"     → "❌ Translation failed: <error>"
Event: "No translation rule"    → "⚠️ Missing map: No path found for X to Y"
Event: "Version mismatch"       → "⚖️ Version mismatch in MCP: Found 1.0, expected 2.0"
```

The debug CSS layout (`#debug-container`, `#debug-list-panel`, `#debug-detail-panel`, `#debug-tabs`) occupies 95% of the terminal width and height with a green heavy border to visually distinguish it from the standard shell.

---

### 4. Integrated SDK Translation Layer

The `engram_sdk` Python package includes a built-in `TranslationClient` (`engram_sdk/translation.py`) that wraps the middleware's translation API. When you call `sdk.translate()`, the SDK automatically handles protocol detection, request formatting, and response parsing. You do not need to manually construct protocol-specific payloads or define custom mappings.

**How the SDK auto-resolves protocols:**

```mermaid
flowchart LR
    A["sdk.translate(payload)"] --> B{"source_protocol\nprovided?"}
    B -->|Yes| D["Use explicit protocols"]
    B -->|No| C{"agent_id\nset on SDK?"}
    C -->|Yes| E["Use agent_id as source_agent"]
    C -->|No| F["Use first entry in\nsupported_protocols list"]
    D & E & F --> G["POST /api/v1/translate"]
    G --> H["TranslationResponse"]
```

**Example — explicit protocol pair:**

```python
from engram_sdk import EngramSDK

sdk = EngramSDK(
    base_url="http://localhost:8000/api/v1",
    eat="<YOUR_EAT>",
)

result = sdk.translate(
    {"intent": "schedule_meeting", "participants": ["alice", "bob"]},
    source_protocol="a2a",
    target_protocol="mcp",
)

print(result.status)   # "success"
print(result.payload)  # Translated MCP-format payload
print(result.mapping_suggestions)  # ML-suggested field mappings (if any)
```

**Example — agent-to-agent (protocol auto-resolved from registry):**

```python
result = sdk.translate(
    {"intent": "schedule_meeting", "participants": ["alice", "bob"]},
    source_agent="agent-a",
    target_agent="agent-b",
)
```

When `source_agent` and `target_agent` are provided, the backend looks up each agent's `supported_protocols` from the `AgentRegistry` table and determines the translation path automatically via the `ProtocolGraph` (Dijkstra shortest path).

**Response structure (`TranslationResponse`):**

```python
@dataclass
class TranslationResponse:
    status: str                                  # "success" or "error"
    message: str                                 # Human-readable result
    payload: Dict[str, Any]                      # The translated payload
    mapping_suggestions: List[MappingSuggestion]  # ML fallback suggestions
```

Each `MappingSuggestion` contains a `source_field`, `suggestion` (predicted target field name), `confidence` (float 0–1), and `applied` (bool indicating if it was auto-applied because confidence ≥ 0.85).

---

### 5. Production-Grade Database Migrations (Alembic)

The backend uses **Alembic** for version-controlled database schema migrations, replacing the previous `SQLModel.metadata.create_all` approach.

**Directory structure:**

```
alembic/
├── env.py           # Async migration runner (uses async_engine_from_config)
├── script.py.mako   # Migration template
└── versions/        # Generated migration scripts (one per schema change)
alembic.ini          # Alembic configuration (reads DATABASE_URL from settings)
```

**How it works:**

1. `alembic/env.py` imports all SQLModel models from `app/db/models.py` to register them with `SQLModel.metadata`.
2. The `target_metadata` is set to `SQLModel.metadata`, so Alembic can auto-detect schema changes.
3. Migrations run in **async mode** using `async_engine_from_config` with the `asyncpg` driver — the same connection pool used by the application.
4. The `DATABASE_URL` is injected from `app.core.config.settings`, ensuring migrations always target the same database as the running application.

**Common commands:**

```bash
# Generate a new migration after modifying models
alembic revision --autogenerate -m "add_new_column"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Show current migration state
alembic current

# Show migration history
alembic history
```

**Models tracked by Alembic** (defined in `app/db/models.py`):

| Model | Table | Purpose |
| :--- | :--- | :--- |
| `ProtocolMapping` | `protocolmapping` | Source→target protocol translation rules |
| `ProtocolVersionDelta` | `protocolversiondelta` | Version upgrade operations (rename, drop, set) |
| `AgentRegistry` | `agentregistry` | Registered agents with protocols, tags, health status |
| `SemanticOntology` | `semanticontology` | OWL ontology entries for semantic resolution |
| `Task` | `task` | Queued translation tasks (JSONB payload, status, lease) |
| `AgentMessage` | `agentmessage` | Translated messages pending agent pickup |
| `MappingFailureLog` | `mappingfailurelog` | Failed field mappings for ML retraining |
| `User` | `user` | User accounts with hashed passwords |
| `PermissionProfile` | `permissionprofile` | Per-user tool permission maps |
| `ProviderCredential` | `providercredential` | Encrypted API keys for connected providers |
| `Workflow` | `workflow` | Multi-step workflow definitions |
| `WorkflowSchedule` | `workflowschedule` | Cron/interval schedules for workflows |

---

### 6. Containerized Infrastructure (Docker Compose)

The `docker-compose.yml` orchestrates the full production stack with a single command:

```bash
docker compose up --build
```

**Services defined in `docker-compose.yml`:**

| Service | Image / Build | Port | Role |
| :--- | :--- | :--- | :--- |
| `app` | `Dockerfile` (FastAPI + uvicorn) | `8000` | Runs the FastAPI backend, TranslatorEngine, TaskWorker, and DiscoveryService |
| `frontend` | `playground/Dockerfile` | `3000` | Vite dev server for the interactive translation playground |
| `db` | `postgres:16-alpine` | `5432` | PostgreSQL persistent storage for all models |
| `redis` | `redis:7.2-alpine` | `6379` | Semantic mapping cache (key pattern `semantic:equivalent:<protocol>:<concept>`) with configurable TTL (default 600s) |
| `prometheus` | `prom/prometheus:v2.52.0` | `9090` | Scrapes `/metrics` from the FastAPI app for translation counters and latency histograms |
| `grafana` | `grafana/grafana:10.4.2` | `3001` | Pre-provisioned dashboards from `monitoring/grafana/` for translation throughput and error rate visualization |

```mermaid
flowchart TB
    subgraph Docker Compose Stack
        APP["app :8000<br/>FastAPI + TaskWorker<br/>+ DiscoveryService"]
        FE["frontend :3000<br/>Playground (Vite)"]
        DB["db :5432<br/>PostgreSQL 16"]
        REDIS["redis :6379<br/>Redis 7.2"]
        PROM["prometheus :9090<br/>Metrics Scraper"]
        GRAF["grafana :3001<br/>Dashboards"]
    end

    APP --> DB
    APP --> REDIS
    PROM -->|"scrape /metrics"| APP
    GRAF --> PROM
    FE --> APP

    style APP fill:#132019,stroke:#2bdc8d
    style DB fill:#1a1a2e,stroke:#4285F4
    style REDIS fill:#2d1a1a,stroke:#FF4E00
    style PROM fill:#1a1a1a,stroke:#e6e1d7
    style GRAF fill:#1a1a1a,stroke:#e0b15b
    style FE fill:#1a1a1a,stroke:#FF9966
```

All services are connected via the `agent_network` bridge network. PostgreSQL data persists across restarts via the `postgres_data` named volume.

**Staging environment** (adds WireMock for mocking external agent endpoints):

```bash
docker compose -f docker-compose.staging.yml up --build -d
```

**Environment variables** consumed from `.env`:

| Variable | Default | Used By |
| :--- | :--- | :--- |
| `POSTGRES_USER` | `admin` | `db` service + `app` connection string |
| `POSTGRES_PASSWORD` | `password` | `db` service + `app` connection string |
| `POSTGRES_DB` | `translator_db` | `db` service + `app` connection string |
| `GRAFANA_ADMIN_USER` | `admin` | Grafana login |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana login |
| `GRAFANA_SMTP_*` | — | Email alerting from Grafana |

---

### 7. Visual Branding & Startup Screen

The TUI displays a clean, standard-font **ENGRAM** typographic logo on startup via the `WelcomeScreen` class. The logo uses an ASCII block font rendered in the `#FF9966` (orange) color.

```
  _____   _   _    ____   ____       _      __  __ 
 | ____| | \ | |  / ___| |  _ \     / \    |  \/  |
 |  _|   |  \| | | |  _  | |_) |   / _ \   | |\/| |
 | |___  | |\  | | |_| | |  _ <   / ___ \  | |  | |
 |_____| |_| \_|  \____| |_| \_\ /_/   \_\ |_|  |_|
```

The `WelcomeScreen` provides two entry paths:

- **"Start Bridging"** — Pops the welcome screen and drops the user into the main shell.
- **"Setup API Keys"** — Pushes `ProviderSelectionScreen` onto the stack to configure AI provider credentials before entering the shell.

The main shell header reuses the same logo with the tagline `Universal Protocol Bridge` rendered in dim text below it.

---

### 8. Agent Heartbeat (Periodic Discovery Service)

The `DiscoveryService` (`app/services/discovery.py`) runs a background loop that pings every registered agent's `/health` endpoint on a configurable interval (default: **60 seconds**).

**How the heartbeat loop works:**

```mermaid
sequenceDiagram
    loop Every 60 seconds
        DiscoveryService->>DB: SELECT * FROM agentregistry
        DB-->>DiscoveryService: List of all agents
        par For each agent
            DiscoveryService->>Agent: GET {endpoint_url}/health
            alt HTTP 200
                Agent-->>DiscoveryService: OK
                DiscoveryService->>DB: SET is_active=true, last_seen=now()
            else Timeout / Error / Non-200
                DiscoveryService->>DB: SET is_active=false, last_seen=now()
            end
        end
        DiscoveryService->>DB: COMMIT
    end
```

**Implementation details:**

| Parameter | Value | Description |
| :--- | :--- | :--- |
| `ping_interval` | `60` seconds (constructor arg) | Time between full discovery cycles |
| `ping_timeout` | `5` seconds (constructor arg) | Per-agent HTTP timeout via `aiohttp.ClientTimeout` |
| `DEFAULT_HEALTH_PATH` | `/health` | Appended to the agent's `endpoint_url` |
| Concurrency | `asyncio.gather(*tasks)` | All agents are pinged concurrently within each cycle |

When an agent's status changes (online → offline or vice versa), the service logs the transition:

```
DiscoveryService: Agent status changed | agent_id=agent-a | status=OFFLINE
```

The service is started automatically on application boot via `start_periodic_discovery()` and stopped gracefully with `stop_periodic_discovery()` on shutdown (cancels the background `asyncio.Task`).

**Why this matters:** Inactive agents are excluded from the collaborator search results. The `TaskWorker` will not route tasks to agents marked `is_active=false`, preventing message delivery to dead endpoints.

---

### 9. Agent Compatibility Scoring & Matchmaking

The `GET /api/v1/discovery/collaborators` endpoint returns a ranked list of agents sorted by a **compatibility score**. This score quantifies how well a candidate agent can interoperate with the requesting agent.

**The compatibility formula:**

$$Score = \frac{\text{Shared Protocols} + \text{Mappable Protocols}}{\text{Total Candidate Protocols}}$$

| Term | Definition |
| :--- | :--- |
| **Shared Protocols** | Protocols that both the requesting agent and the candidate agent support natively (e.g., both speak `MCP`) |
| **Mappable Protocols** | Protocols the candidate supports that the requesting agent does not, but which the `TranslatorEngine` can translate to from one of the requester's protocols (determined by `ProtocolMapping` rows in the database) |
| **Total Candidate Protocols** | The total number of protocols the candidate agent supports |

**Example:**

Your agent speaks `A2A`. A candidate agent speaks `A2A`, `MCP`, and `ACP`. The database has a `ProtocolMapping` row for `A2A → MCP`, but not `A2A → ACP`.

```
shared     = {A2A}         → count = 1
mappable   = {MCP}         → count = 1  (A2A→MCP exists)
total      = {A2A,MCP,ACP} → count = 3

score = (1 + 1) / 3 = 0.6667
```

**API usage:**

```bash
# Find agents compatible with an A2A-speaking agent, minimum score 0.5
curl "http://localhost:8000/api/v1/discovery/collaborators?protocols=A2A&min_score=0.5" \
  -H "Authorization: Bearer <TOKEN>"
```

**Response:**

```json
[
  {
    "agent_id": "agent-scheduler",
    "endpoint_url": "http://agent-scheduler:8080",
    "supported_protocols": ["a2a", "mcp"],
    "is_active": true,
    "compatibility_score": 1.0,
    "shared_protocols": ["A2A"],
    "mappable_protocols": ["MCP"]
  },
  {
    "agent_id": "agent-weather",
    "endpoint_url": "http://agent-weather:8081",
    "supported_protocols": ["mcp", "acp"],
    "is_active": true,
    "compatibility_score": 0.5,
    "shared_protocols": [],
    "mappable_protocols": ["MCP"]
  }
]
```

**Implementation:** `DiscoveryService.find_collaborators()` in `app/services/discovery.py`. Only agents with `is_active=true` are considered. Results are sorted by `compatibility_score` descending. The `min_score` query parameter (default `0.7`, range `0.0–1.0`) filters out low-compatibility candidates.

---

### 10. Semantic Tag Filtering

Agents can register with **semantic tags** — a list of capability keywords (e.g., `["weather", "scheduling", "search"]`). The discovery endpoints use these tags to filter agents by functional capability, not just protocol compatibility.

**Registering an agent with semantic tags:**

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-weather",
    "endpoint_url": "http://agent-weather:8081",
    "supported_protocols": ["mcp"],
    "semantic_tags": ["weather", "forecast", "geo"],
    "is_active": true
  }'
```

**Discovering agents filtered by tags:**

```bash
curl -X POST http://localhost:8000/api/v1/discovery/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{
    "protocols": ["a2a"],
    "semantic_tags": ["weather"]
  }'
```

This `POST /api/v1/discovery/` endpoint applies **two filters**:

1. **Protocol eligibility** — Returns agents whose `supported_protocols` overlap with the requested protocols or protocols reachable via `ProtocolMapping` translations.
2. **Semantic tag overlap** — Filters the eligible agents to only those whose `semantic_tags` array has at least one element in common with the requested tags. This uses PostgreSQL's `ARRAY && ARRAY` (overlap) operator via SQLAlchemy's `.overlap()`.

**How the two-stage filter works:**

```mermaid
flowchart TD
    A["Request:<br/>protocols=[A2A]<br/>semantic_tags=[weather]"] --> B["Query ProtocolMapping<br/>for A2A → ???"]
    B --> C["Eligible protocols:<br/>{A2A, MCP}"]
    C --> D["SELECT FROM agentregistry<br/>WHERE supported_protocols<br/>OVERLAP {A2A, MCP}"]
    D --> E["Apply tag filter:<br/>WHERE semantic_tags<br/>OVERLAP {weather}"]
    E --> F["Return matching agents"]
```

**SDK usage:**

```python
from engram_sdk import EngramSDK

sdk = EngramSDK(
    base_url="http://localhost:8000/api/v1",
    eat="<YOUR_EAT>",
    agent_id="my-agent",
    endpoint_url="http://localhost:9000",
    supported_protocols=["a2a"],
    semantic_tags=["scheduling", "calendar"],
)

# Register this agent with its tags
sdk.register_agent()
```

Tags are stored as a PostgreSQL `ARRAY` column on the `AgentRegistry` model. There is no predefined tag vocabulary -- agents define their own tags during registration, and discovery consumers query against them freely.

---

### 11. Near Real-Time Machine Learning Retraining

The ML mapping model (`MappingPredictor` in `app/semantic/ml_mapper.py`) can be retrained on demand or automatically based on accumulated corrections. The retraining function lives in `app/services/ml_retraining.py`.

**How retraining works:**

1. `retrain_mapping_model(session)` queries all `ProtocolMapping` rows from the database.
2. It calls `MappingPredictor.train_from_mappings(mappings)`, which:
   - Extracts `(source_protocol, target_protocol, source_field, target_field)` tuples from the `semantic_equivalents` JSONB column on each mapping.
   - Requires at least `ML_MIN_TRAIN_SAMPLES` (default: 20) training rows and at least 2 distinct target labels.
   - Builds a scikit-learn `Pipeline` consisting of a `TfidfVectorizer` (char-level, ngram range 3-5) and a `LogisticRegression` classifier (max 1000 iterations).
3. The trained model is serialized via `joblib.dump()` to `ML_MODEL_PATH` (default: `app/semantic/models/mapping_model.joblib`).

**Automatic retraining trigger:**

When a mapping failure is manually corrected via `correct_mapping_failure()`, the function counts total applied corrections. Every `ML_AUTO_RETRAIN_THRESHOLD` (default: 5) applied corrections, it calls `retrain_mapping_model()` inline. This keeps the model current without requiring a manual trigger.

```mermaid
flowchart TD
    A["Developer corrects mapping<br/>POST /beta/mapping-failures/{id}/correct"] --> B["correct_mapping_failure()"]
    B --> C["Update ProtocolMapping<br/>semantic_equivalents"]
    C --> D{"applied_count<br/>% ML_AUTO_RETRAIN_THRESHOLD<br/>== 0?"}
    D -->|Yes| E["retrain_mapping_model()"]
    D -->|No| F["Return updated entry"]
    E --> G["MappingPredictor.train_from_mappings()"]
    G --> H["Pipeline: TfidfVectorizer + LogisticRegression"]
    H --> I["joblib.dump() to ML_MODEL_PATH"]
    I --> F
```

**Manual retraining endpoint:**

```bash
curl -X POST http://localhost:8000/api/v1/beta/ml/retrain \
  -H "Authorization: Bearer <TOKEN>"
```

Returns `{"status": "success", "message": "ML model retraining initiated."}` on success.

**Configuration:**

| Setting | Default | Description |
| :--- | :--- | :--- |
| `ML_ENABLED` | `true` | Master toggle for ML features |
| `ML_MODEL_PATH` | `app/semantic/models/mapping_model.joblib` | Filesystem path for the serialized model |
| `ML_MIN_TRAIN_SAMPLES` | `20` | Minimum `(field, target)` tuples required to train |
| `ML_AUTO_APPLY_THRESHOLD` | `0.85` | Confidence above which predictions are auto-applied |
| `ML_AUTO_RETRAIN_THRESHOLD` | `5` | Number of corrections between automatic retrains |

---

### 12. Integration Mapping Failure Correction

When a translation fails (a semantic field cannot be mapped), the system logs the failure to the `MappingFailureLog` table and attempts an ML-assisted correction. This is the self-correcting feedback loop that feeds into the retraining pipeline above.

**Failure logging flow (triggered by `POST /api/v1/beta/translate`):**

```mermaid
sequenceDiagram
    participant Client
    participant API as beta/translate
    participant MF as mapping_failures.py
    participant ML as MappingPredictor
    participant DB as PostgreSQL

    Client->>API: POST { source_protocol, target_protocol, payload }
    API->>API: Translation attempt (raises exception)
    API->>MF: extract_fields(payload) returns field list
    loop For each unmapped field
        MF->>DB: INSERT into MappingFailureLog
        MF->>ML: predictor.predict(source_protocol, target_protocol, field)
        ML-->>MF: MappingPrediction { suggestion, confidence }
        alt confidence >= 0.85
            MF->>DB: UPDATE ProtocolMapping.semantic_equivalents[field] = suggestion
            MF->>DB: SET MappingFailureLog.applied = true
        else confidence < 0.85
            MF->>DB: SET model_suggestion, model_confidence (not applied)
        end
    end
    API-->>Client: HTTP 422 + mapping_suggestions[]
```

**Key functions in `app/services/mapping_failures.py`:**

| Function | Purpose |
| :--- | :--- |
| `extract_fields(payload, max_fields)` | Recursively walks a nested dict/list and returns up to `max_fields` dotted-path keys (e.g., `user.address.city`) |
| `extract_payload_excerpt(payload, max_keys)` | Takes the first `max_keys` top-level keys from the payload for logging context |
| `log_mapping_failure(session, ...)` | Creates a `MappingFailureLog` row with `source_protocol`, `target_protocol`, `source_field`, `payload_excerpt`, and `error_type` |
| `apply_ml_suggestion(session, entry)` | Loads the ML model, calls `predict()`, and auto-applies if confidence >= `ML_AUTO_APPLY_THRESHOLD` |
| `correct_mapping_failure(session, id, correct_suggestion)` | Manual correction endpoint -- updates `ProtocolMapping.semantic_equivalents` and optionally triggers retraining |

**Viewing logged failures:**

```bash
# List all unapplied mapping failures
curl "http://localhost:8000/api/v1/beta/mapping-failures?applied=false" \
  -H "Authorization: Bearer <TOKEN>"
```

**Manually correcting a failure:**

```bash
curl -X POST http://localhost:8000/api/v1/beta/mapping-failures/<failure-uuid>/correct \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"correct_suggestion": "profile.full_name"}'
```

This updates the `ProtocolMapping` row, marks the failure as applied, and may trigger an automatic retrain if the correction count is a multiple of `ML_AUTO_RETRAIN_THRESHOLD`.

---

### 13. Self-Healing Semantic Loop

The three components above (failure logging, ML suggestion, and retraining) form a closed feedback loop. When wired together end-to-end, the system self-corrects semantic mapping gaps without manual intervention for high-confidence predictions.

```mermaid
flowchart LR
    A["Translation Attempt"] -->|Fails| B["MappingFailureLog"]
    B --> C["MappingPredictor.predict()"]
    C -->|"conf >= 0.85"| D["Auto-apply to<br/>ProtocolMapping"]
    C -->|"conf < 0.85"| E["Surface as<br/>mapping_suggestion"]
    E -->|"Developer corrects"| F["correct_mapping_failure()"]
    F --> D
    D -->|"Every N corrections"| G["retrain_mapping_model()"]
    G -->|"Updated model"| C
```

**The cycle in detail:**

1. A `beta/translate` request fails because field `user_info.name` has no mapping rule for `A2A -> MCP`.
2. `log_mapping_failure()` persists the failure. `apply_ml_suggestion()` loads the model and predicts `profile.fullname` with confidence `0.91`.
3. Because `0.91 >= ML_AUTO_APPLY_THRESHOLD (0.85)`, the prediction is written into `ProtocolMapping.semantic_equivalents["user_info.name"] = "profile.fullname"` and `applied = true`.
4. The next identical translation request succeeds because the mapping now exists.
5. After 5 total auto-applied or manually corrected failures, `retrain_mapping_model()` fires, incorporating all current mappings into a fresh model. The model improves and can handle new unseen fields with higher accuracy.

No human is required in the loop for predictions above the confidence threshold. Below-threshold predictions are surfaced in the API response as `mapping_suggestions` for manual review and correction.

---

### 14. Verifiable Cryptographic Execution Proofs

Every multi-hop translation produces a chain of SHA-256 hashes that prove the translation was executed and the payloads were not tampered with after the fact. The proof is returned in the `execution_proof` field of `TranslateResponse` and `BetaTranslateResponse`.

**How proofs are generated (`Orchestrator._generate_execution_proof()`):**

For each hop in a multi-hop translation:

```python
payload_hash = hashlib.sha256(json.dumps({
    "in": input_payload,
    "out": output_payload,
    "src": source_protocol,
    "tgt": target_protocol,
    "ts": datetime.now(timezone.utc).isoformat()
}, sort_keys=True).encode()).hexdigest()

hop_proof = f"v1:sha256:{payload_hash}"
```

After all hops complete, the per-hop proofs are concatenated and hashed again to produce the aggregate proof:

```python
aggregate = hashlib.sha256(
    "".join([hop.proof for hop in hops]).encode()
).hexdigest()

result.proof = f"v1:agg:{aggregate}"
```

**Data structures:**

```python
@dataclass
class HopResult:
    source_protocol: str
    target_protocol: str
    message_snapshot: Dict[str, Any]  # Payload after this hop's translation
    weight: float                     # Edge cost used for this hop
    proof: str                        # "v1:sha256:<hex>"

@dataclass
class HandoffResult:
    translated_message: Dict[str, Any]
    route: List[str]                  # e.g., ["A2A", "MCP", "ACP"]
    total_weight: float
    proof: str                        # "v1:agg:<hex>"
    hops: List[HopResult]
```

**Example API response with proof:**

```json
{
  "status": "completed",
  "message": "Translated message from agent-a to agent-b",
  "payload": { "data_bundle": { "action": "thermal_check" } },
  "execution_proof": "v1:agg:a3f2c98e17b4d..."
}
```

The proof format is `v1:agg:<sha256>` for multi-hop translations and `v1:sha256:<sha256>` for single-hop translations. The `v1` prefix is a version tag for future algorithm upgrades.

---

### 15. Hierarchical Multi-Hop Pathfinding

The `ProtocolGraph` (`app/messaging/orchestrator.py`) models all protocol translation capabilities as a weighted directed graph using NetworkX. When no direct translation edge exists between a source and target protocol, the Orchestrator finds the shortest multi-hop path using Dijkstra's algorithm.

**How the graph is built:**

1. On startup, `Orchestrator.__init__()` calls `ProtocolGraph.build_from_translator(translator)` which adds an edge for every `(source, target)` pair registered in `TranslatorEngine._mappers`.
2. Each connector registered via `connector_registry.list_connectors()` is added as a protocol node.
3. At runtime, `ProtocolGraph.build_from_registry(session)` can populate the graph dynamically from `ProtocolMapping` and `AgentRegistry` database tables.

**Graph layout (default static edges):**

```
Nodes: [A2A, MCP, NL, MIROFISH, ANTHROPIC, PERPLEXITY, SLACK, ...]
Edges:
  A2A  ---(w=1.0)---> MCP
  NL   ---(w=1.0)---> MCP
  (connector nodes added per registered tool)
```

**Path resolution:**

```python
path, total_weight = self.protocol_graph.find_shortest_path("A2A", "ACP")
# path = ["A2A", "MCP", "ACP"]  (if MCP->ACP edge exists)
# total_weight = 2.0
```

If no path exists, `HandoffRoutingError` is raised with the message `"No translation route from 'X' to 'Y'."`.

**Multi-hop execution:**

```mermaid
flowchart LR
    A["A2A Input"] -->|"Hop 1: w=1.0"| B["MCP"]
    B -->|"Hop 2: w=1.5"| C["ACP Output"]

    subgraph "Per-Hop Processing"
        D["TranslatorEngine.translate()"] --> E["Generate hop proof"]
        E --> F["Record HopResult"]
    end
```

Each hop in the path calls `TranslatorEngine.translate()` sequentially. The current message output becomes the next hop's input. Each hop generates a cryptographic proof (see item 14) and records the weight used.

---

### 16. Dynamic Protocol Graph Weighting

Protocol translation edges carry a **weight** value that influences pathfinding. Lower weight means the path is preferred. The `ProtocolGraph.build_from_registry()` method computes weights dynamically from live agent performance data.

**Static weights:**

`build_from_translator()` assigns `default_weight = 1.0` to all edges from `TranslatorEngine._mappers`.

**Dynamic weights (from `build_from_registry()`):**

When the graph is rebuilt from the database (via `handoff_async()` with a `db` parameter), each `ProtocolMapping` row contributes its stored `fidelity_weight` from the database column. For agent-specific edges, the weight is computed as:

```
total_weight = 1.0 + latency_penalty + reliability_penalty
```

Where:

| Component | Formula | Interpretation |
| :--- | :--- | :--- |
| **Base** | `1.0` | Minimum cost for any edge |
| **Latency penalty** | `agent.avg_latency * 0.1` | 0.1 points per second of avg response time |
| **Reliability penalty** | `(1.0 - agent.success_rate) * 50.0` | 5.0 points per 10% drop below 100% success |

**Example:**

An agent with `avg_latency = 2.0s` and `success_rate = 0.90`:

```
latency_penalty   = 2.0 * 0.1 = 0.2
reliability_penalty = (1.0 - 0.9) * 50.0 = 5.0
total_weight       = 1.0 + 0.2 + 5.0 = 6.2
```

An agent with `avg_latency = 0.5s` and `success_rate = 0.99`:

```
latency_penalty   = 0.5 * 0.1 = 0.05
reliability_penalty = (1.0 - 0.99) * 50.0 = 0.5
total_weight       = 1.0 + 0.05 + 0.5 = 1.55
```

Dijkstra will prefer the second agent's path because `1.55 < 6.2`.

---

### 17. Performance-Aware Agent Routing

Dynamic weights (item 16) feed into pathfinding (item 15). Combined, the system routes tasks through agents that are fast and reliable, avoiding slow or failing endpoints.

The `AgentRegistry` model stores per-agent performance columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| `avg_latency` | `Float` | Rolling average response time in seconds |
| `success_rate` | `Float` | Success ratio (0.0 to 1.0) |
| `is_active` | `Boolean` | Set by DiscoveryService heartbeat (item 8) |

`build_from_registry()` creates edges from each protocol node to each agent endpoint node. Dijkstra then selects the lowest-cost path across protocols and agents.

```mermaid
flowchart LR
    subgraph "Protocol Nodes"
        A2A
        MCP
    end

    subgraph "Agent Endpoints"
        AG1["Agent-1<br/>w=1.55"]
        AG2["Agent-2<br/>w=6.2"]
    end

    MCP -->|"w=1.55"| AG1
    MCP -->|"w=6.2"| AG2
    A2A -->|"w=1.0"| MCP
```

In this graph, `A2A -> MCP -> Agent-1` has total cost `2.55`, while `A2A -> MCP -> Agent-2` has total cost `7.2`. The Orchestrator routes to Agent-1.

Inactive agents (`is_active = false`) are excluded from the graph entirely during `build_from_registry()`, so they never appear as candidates.

---

### 18. Transformer-Based Natural Language Intent Resolution

The `IntentResolver` (`app/messaging/intent_resolver.py`) decomposes complex, free-form user prompts into normalized `AtomicTask` objects. It is invoked automatically when `source_protocol = "NL"` in the Orchestrator.

**Architecture:**

The resolver is designed with a transformer-ready interface. The current implementation uses a rule-based classifier as the inference layer, structured to be replaced by a fine-tuned transformer (BERT/T5/LLM) without changing the API surface. The `_model_ready` flag is set on initialization.

**Processing pipeline:**

```mermaid
flowchart TD
    A["User prompt:<br/>'Please predict the BTC market<br/>and also find agents for weather'"] --> B["_decompose_prompt()"]
    B -->|"Split by: and, then, also, commas, periods"| C["Segment 1: 'predict the BTC market'<br/>Segment 2: 'find agents for weather'"]
    C --> D["_parse_segment() per segment"]
    D --> E["Strip ambient language:<br/>'please', 'can you', 'I want to'"]
    E --> F["Classify intent via keyword matching"]
    F --> G["_extract_parameters()"]
    G --> H["AtomicTask 1: {intent: 'predict', market: 'market', confidence: 0.92}<br/>AtomicTask 2: {intent: 'discover', content: '...', confidence: 0.90}"]
```

**Intent classification rules:**

| Keywords | Detected Intent | Confidence |
| :--- | :--- | :--- |
| `translate`, `convert`, `transform` | `translate` | 0.95 |
| `predict`, `market`, `price`, `forecast` | `predict` | 0.92 |
| `status`, `where is`, `progress` | `check_status` | 0.88 |
| `find`, `discover`, `search`, `who can` | `discover` | 0.90 |
| (none matched) | `general_query` | 0.50 |

**Capability tag mapping:**

After intent detection, the resolver maps the intent to a registry capability tag, either by querying the `AgentRegistry` for matching `capabilities` or `semantic_tags`, or falling back to a static map:

```python
{
    "translate":    "universal_translation",
    "predict":      "market_forecasting",
    "check_status": "task_monitoring",
    "discover":     "agent_discovery",
}
```

**Data structures:**

```python
class AtomicTask(BaseModel):
    id: str           # UUID
    intent: str       # e.g., "translate", "predict", "discover"
    parameters: dict  # Extracted key-value params stripped of ambient language
    confidence: float # 0.0 to 1.0
    capability_tag: str  # Matched registry capability

class IntentResolutionResult(BaseModel):
    original_prompt: str
    tasks: List[AtomicTask]
    metadata: dict    # {"segments_processed": N}
```

---

### 19. Automated Request Delegation

The `DelegationEngine` (`delegation/engine.py`) accepts a natural language command through `POST /api/v1/delegate` and routes it through the full orchestration pipeline without requiring the caller to specify protocols or targets.

**What happens on `POST /api/v1/delegate`:**

```mermaid
sequenceDiagram
    participant Client
    participant API as POST /delegate
    participant DE as DelegationEngine
    participant IR as IntentResolver
    participant Orch as Orchestrator
    participant MF as MiroFish Connector

    Client->>API: { command: "predict BTC", source_agent: "Research Agent" }
    API->>API: Verify EAT authorization
    API->>DE: delegate_subtask(command, source_agent, eat)
    DE->>DE: Generate correlation_id (UUID)
    DE->>DE: Store delegation record in SwarmMemory
    DE->>Orch: handoff_async(source_protocol="NL", target_protocol="MIROFISH")
    Orch->>IR: resolve(command)
    IR-->>Orch: AtomicTask { intent: "predict", capability_tag: "market_forecasting" }
    Orch->>MF: Execute via connector
    MF-->>Orch: Simulation result
    Orch-->>DE: HandoffResult
    DE->>DE: Push result to TUI event queue
    DE->>DE: Write completion record to SwarmMemory
    DE-->>API: { status, correlation_id, result }
    API-->>Client: JSON response
```

**Request:**

```bash
curl -X POST http://localhost:8000/api/v1/delegate \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"command": "predict the BTC market for next week", "source_agent": "Research Agent"}'
```

**Response:**

```json
{
  "status": "success",
  "correlation_id": "c3d4e5f6-...",
  "result": {
    "summary": "Swarm initialized with 1000 agents.",
    "confidence": 87
  }
}
```

The `DelegationEngine` uses the source protocol `"NL"` and determines the target protocol based on the resolved intent. If the intent is `"predict"`, the target defaults to `"MIROFISH"`. For other intents, it defaults to `"MCP"`. The correlation ID is persisted in the bridge memory backend for traceability.

---

### 20. PyDatalog Rule Synthesis and OWL Ontology Management

The semantic mapping layer operates at two levels: **PyDatalog rules** for explicit field renames, and **OWL ontologies** for concept equivalence resolution. Both are managed through `SemanticMapper` (`app/semantic/mapper.py`).

**PyDatalog Rule Synthesis:**

When `DataSiloResolver()` is called, it loads field mapping rules from either custom rules passed as arguments or (in future) from the database, and asserts them as PyDatalog facts:

```python
# For each rule { "user_info.name": "profile.fullname" }
+ map_field("user_info.name", "profile.fullname")
```

During field resolution, the mapper queries PyDatalog first:

```python
res = map_field("user_info.name", Y)
# Returns: [("profile.fullname",)]
```

If no PyDatalog rule matches, it falls back to the OWL ontology.

**OWL Ontology Management:**

The bundled ontology (`app/semantic/protocols.owl`) defines concept equivalences in RDF/OWL format:

```xml
<!-- A2A:task_handoff is equivalent to MCP:coord_transfer -->
<owl:Class rdf:about="http://agent.middleware.org/A2A#task_handoff">
    <owl:equivalentClass rdf:resource="http://agent.middleware.org/MCP#coord_transfer"/>
</owl:Class>
```

The `SemanticMapper` loads this via `owlready2` and resolves equivalents by:

1. Searching for the concept IRI in the source protocol's namespace.
2. Walking `equivalent_to` relationships.
3. Returning the first equivalent found in a different protocol's namespace.

Results are cached in Redis with key pattern `semantic:equivalent:<protocol>:<concept>` and TTL of `SEMANTIC_CACHE_TTL_SECONDS` (default: 600s).

**Runtime ontology upload via API:**

```bash
curl -X POST http://localhost:8000/api/v1/ontology/upload \
  -H "Content-Type: application/json" \
  -d '{"name": "custom_mappings", "rdf_xml": "<rdf:RDF ...>...</rdf:RDF>"}'
```

This persists the ontology to the `SemanticOntology` table and loads it into the in-memory `rdflib.Graph` managed by `OntologyManager` (`app/semantic/ontology_manager.py`). The `OntologyManager` supports:

| Method | Purpose |
| :--- | :--- |
| `load_ontology(source, format)` | Parse RDF from file path or string |
| `add_mapping(source_term, target_term)` | Add an `owl:sameAs` triple programmatically |
| `resolve_mapping(source_term)` | Return all terms linked via `owl:sameAs` |
| `get_rdf_xml()` | Serialize the current graph back to RDF/XML |

**Resolution order:**

```mermaid
flowchart TD
    A["Source field: user_info.name"] --> B{"PyDatalog rule<br/>exists?"}
    B -->|Yes| C["Return rule target"]
    B -->|No| D{"OWL ontology<br/>equivalent?"}
    D -->|Yes| E["Return ontology target"]
    D -->|No| F{"ML model<br/>prediction?"}
    F -->|"conf >= 0.85"| G["Auto-apply prediction"]
    F -->|"conf < 0.85"| H["Pass through unchanged<br/>+ log to MappingFailureLog"]
```

---

### 21. Automated Schema Inference

The `DataSiloResolver` method on `SemanticMapper` validates source data against JSON Schema before translation, flattens nested structures, and infers mapping targets through the resolution chain described above. This constitutes the automated schema inference pipeline.

**Processing steps:**

1. **JSON Schema Validation** -- `jsonschema.validate(instance=source_data, schema=source_schema)` validates the incoming payload against the declared source schema. If validation fails, a `ValueError` is raised with the specific schema violation.

2. **Deep Flattening** -- `_flatten_dict()` recursively converts nested dicts into dotted-path keys:

```python
# Input
{"user": {"address": {"city": "NYC"}}}

# Output
{"user.address.city": "NYC"}
```

3. **Rule-Based Mapping** -- Each flattened key is passed through the PyDatalog rules, then the OWL ontology, in order.

4. **Schema-Aware Reconstruction** -- The mapped keys are assembled into a new dict structure compatible with the target schema.

**Example:**

```python
mapper = SemanticMapper("app/semantic/protocols.owl")

result = mapper.DataSiloResolver(
    source_data={"user_info": {"name": "Alice", "email": "a@b.com"}},
    source_schema={
        "type": "object",
        "properties": {
            "user_info": {"type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"}
                }
            }
        }
    },
    target_schema={
        "type": "object",
        "properties": {
            "profile": {"type": "object",
                "properties": {
                    "fullname": {"type": "string"},
                    "email": {"type": "string"}
                }
            }
        }
    },
    source_protocol="A2A",
    target_protocol="MCP",
    custom_rules={"user_info.name": "profile.fullname"},
)

# result: {"profile.fullname": "Alice", "email": "a@b.com"}
```

---

### 22. Structured Observability Dashboards

The system exposes Prometheus metrics at `GET /metrics` via `prometheus-fastapi-instrumentator`. These metrics are scraped by the Prometheus container and visualized in pre-provisioned Grafana dashboards.

**Prometheus metrics defined in `app/core/metrics.py`:**

| Metric | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `translations_total` | Counter | `channel`, `source_protocol`, `target_protocol` | Total completed translations |
| `translation_errors_total` | Counter | `channel`, `source_protocol`, `target_protocol` | Total translation errors |
| `translations_per_second` | Gauge | `channel` | Rolling translations/sec over 60s window |
| `translation_error_rate` | Gauge | `channel` | Rolling error rate (0-1) over 60s window |
| `tasks_started_total` | Counter | `task_type`, `user_id` | Total tasks started |
| `tasks_completed_total` | Counter | `task_type`, `user_id`, `status` | Total tasks completed (by status) |
| `task_latency_seconds` | Histogram | `task_type`, `user_id` | Task execution latency (buckets: 0.1s to 60s) |
| `connector_calls_total` | Counter | `connector`, `user_id`, `status` | Total connector invocations |
| `connector_latency_seconds` | Histogram | `connector`, `user_id` | Connector call latency (buckets: 0.1s to 20s) |

**Rolling rate calculation:**

`translations_per_second` and `translation_error_rate` use a 60-second sliding window implemented with a `deque`. On each translation event, expired entries (older than 60s) are evicted, and the gauge is recalculated:

```python
translations_per_second = len(success_events) / 60
error_rate = len(error_events) / (len(success_events) + len(error_events))
```

**Live task monitoring via execution events:**

The `emit_execution_event()` function (`app/core/execution_events.py`) pushes structured events to both the TUI event queue and the `TaskEvent` database table. Each event contains:

```python
{
    "type": "translation.engram",    # Event category
    "message": "Hop 1: Translating A2A to MCP",
    "data": {"payload": {...}},       # Full payload snapshot
    "task_id": "uuid-...",
    "level": "info",
    "ts": 1711828800.0                # Unix timestamp
}
```

These events are consumed by:
- The TUI `RichLog` panels via `tui_event_queue` (in-process, real-time).
- Remote CLI clients via `GET /api/v1/tasks/{task_id}/events` (database-backed, polled).

**Grafana dashboard provisioning:**

The `monitoring/grafana/` directory contains pre-configured dashboard JSON and a datasource provisioning file. When the Docker Compose stack starts, Grafana auto-loads these dashboards, providing out-of-the-box panels for:

- Translation throughput (translations/sec by channel)
- Error rate over time
- Task latency distribution (p50, p95, p99)
- Connector call success/failure ratio

Access Grafana at `http://localhost:3001` with the credentials configured in `.env` (`GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD`, defaults: `admin`/`admin`).

---

## Core Features

*   **Protocol Translation:** Converts messages and payloads between A2A, MCP, and ACP formats.
*   **Semantic Mapping:** Uses OWL ontologies, JSON Schema, and PyDatalog to map data fields between different agent schemas (e.g., mapping `user_info.name` to `profile.fullname`).
*   **MiroFish Swarm Bridge:** Pipe inter-agent messages and live data directly into a MiroFish swarm simulation and receive compiled prediction reports back.
*   **Trading Semantic Templates:** Standard adapters for Binance, Coinbase, Robinhood, Kalshi, Stripe, PayPal, and live data feeds (X, FRED, Reuters, Bloomberg).
*   **Agent Registry & Discovery:** Registration and lookup of agent protocols and semantic capabilities based on computed compatibility scores.
*   **Async Orchestration:** Task queues and worker processes for multi-turn agent handoffs, message leases, and retries.
*   **Fallback Mapping:** Machine learning model for field mapping suggestions when default semantic rules are insufficient.

---

## Developer Toolkit (SDK + Examples)

If you want to integrate your own tools quickly, start here:

* `docs/DEVELOPER_TOOLKIT.md`
* `examples/engram_toolkit/README.md`

These cover SDK installation, tool registration, agent connection, and task execution.

---

## MiroFish Swarm Bridge

The **MiroFish Swarm Bridge** connects Engram's protocol translation pipeline to a [MiroFish](https://github.com/666ghj/MiroFish) simulation. Agents can pipe messages and external context into a swarm simulation and receive predictions or reports back.

This integration enables predictive trading flows where live data context is used to run a swarm simulation before trade execution.

### How It Works (Under the Hood)

```mermaid
sequenceDiagram
    participant Agent as AI Agent<br/>(OpenClaw / Clawdbot)
    participant Engram as Engram Orchestrator
    participant Translator as TranslatorEngine
    participant Router as MiroFish Router
    participant MF as MiroFish Instance<br/>(User's Local)

    Agent->>Engram: routeTo('mirofish', payload)
    Engram->>Translator: Normalise to MCP format
    Translator-->>Engram: Normalised payload
    Engram->>Router: pipe_to_mirofish_swarm()
    Note over Router: Builds enriched seedText<br/>+ God's-eye variables
    Router->>MF: POST /api/simulation/start
    MF-->>Router: Simulation report
    Router-->>Engram: HandoffResult
    Engram-->>Agent: Prediction report
```

1. The caller specifies `target_protocol="mirofish"` (case-insensitive).
2. The Orchestrator detects the MiroFish target and short-circuits the normal protocol graph.
3. The payload is normalised through Engram's `TranslatorEngine` (A2A/ACP → MCP), preserving **semantic fidelity** regardless of the originating protocol.
4. The router automatically fetches live context — real-time prices (via CCXT), sentiment scores (X / Reuters), and recent news headlines — and injects them as "God's-eye variables" alongside the seed text.
5. The enriched payload is `POST`ed to the user's MiroFish `/api/simulation/start` endpoint.
6. The compiled simulation report (predictions, agent consensus, recommendations) is returned as the `HandoffResult.translated_message`.

### Prerequisites

> **Every user must run their own MiroFish instance.** The bridge connects to *your* local (or self-hosted) MiroFish installation. No shared API keys or cloud dependencies.

1. **Clone and set up MiroFish** (already included as a submodule in this repository under `MiroFish/`):
   ```bash
   cd MiroFish
   cp .env.example .env
   ```
2. **Add your personal LLM API key** to the MiroFish `.env`:
   ```env
   LLM_API_KEY=your_api_key_here
   LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
   LLM_MODEL_NAME=qwen-plus
   ZEP_API_KEY=your_zep_api_key_here
   ```
3. **Start MiroFish**:
   ```bash
   npm run dev          # Source code
   # OR
   docker compose up -d # Docker
   ```
4. Verify MiroFish is running at `http://localhost:5001`.

### Configuration

Add these optional environment variables to your Engram `.env` file to customise bridge defaults:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MIROFISH_BASE_URL` | `http://localhost:5001` | Base URL of your MiroFish service. |
| `MIROFISH_DEFAULT_NUM_AGENTS` | `1000` | Default number of agents to spawn per swarm simulation. |
| `MIROFISH_DEFAULT_SWARM_ID` | `default` | Default swarm identifier for parallel simulations. |

### Usage Examples

#### TypeScript — One-Line SDK (OpenClaw / Clawdbot)

The fastest way to use the bridge. One import, one call, full swarm simulation:

```ts
import { engram } from './mirofish-bridge';

// Send a message and receive the simulation report
const report = await engram.routeTo('mirofish', 'Analyse upcoming ETH merge impact', {
  swarmId: 'prediction-market-1',
  mirofishBaseUrl: 'http://localhost:5001',
  numAgents: 1000,
});

console.log(report); // Full simulation report with predictions
```

You can also use the SDK config loader for a persistent, reusable connection:

```ts
import { loadEngramConfig } from './engram-sdk';

const engram = loadEngramConfig({
  enableMiroFishBridge: true,
  mirofishBaseUrl: 'http://localhost:5001',
  swarmId: 'crypto-swarm',
  defaultAgentCount: 500,
});

// Now use it anywhere in your agent flow
const report = await engram.routeTo('mirofish', 'BTC 7-day price forecast');
```

#### TypeScript — Low-Level Bridge API

For more granular control (seed injection, mid-simulation God's-eye injection):

```ts
import { MiroFishBridge } from './mirofish-bridge';

const bridge = MiroFishBridge('http://localhost:5001');

// 1. Pipe a seed text into the swarm
await bridge.pipe('agent-1', 'A2A', {
  seed_text: 'Analyse impact of new SEC regulations on DeFi',
  num_agents: 2000,
}, 'regulation-swarm');

// 2. Inject live events mid-simulation (God's-eye injection)
await bridge.godsEye('regulation-swarm', [
  { type: 'price_update', symbol: 'ETH/USD', price: '3800.50' },
  { type: 'news_flash', headline: 'SEC announces new DeFi framework' },
]);
```

#### Python — Orchestrator Routing (Backend)

On the server side, use the Orchestrator directly. This is the path used by the TaskWorker for async queue processing:

```python
from app.messaging.orchestrator import Orchestrator

orchestrator = Orchestrator()

# Async path (from a FastAPI route or async handler):
result = await orchestrator.handoff_async(
    source_message={
        "intent": "predict",
        "content": "BTC 7-day forecast",
        "metadata": {
            "swarmId": "crypto-swarm",
            "mirofishBaseUrl": "http://localhost:5001",
            "numAgents": 500,
            "externalData": {
                "prices": [{"symbol": "BTC/USD", "price": "64200"}],
                "sentiment": {"source": "X", "score": 0.72, "label": "Bullish"}
            }
        }
    },
    source_protocol="A2A",
    target_protocol="mirofish",
)

print(result.translated_message)  # Simulation report
```

#### cURL — REST API

```bash
curl -X POST http://localhost:8000/api/v1/translate \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"source_protocol\":\"a2a\",\"target_protocol\":\"mirofish\",\"payload\":{\"intent\":\"predict\",\"content\":\"Analyse ETH merge impact\",\"metadata\":{\"swarmId\":\"eth-swarm\",\"numAgents\":1000}}}"
```

### Testing the Bridge

The integration test suite includes a full end-to-end test that **does not require a live MiroFish instance or LLM key** — it uses a built-in mock server:

```bash
# Standalone (no pytest needed)
$env:PYTHONPATH="."
python tests/integration/test_mirofish_e2e.py

# Via pytest
pytest tests/integration/test_mirofish_e2e.py -v
```

The test validates: mock MiroFish server startup → agent creation → enriched trading signal construction → Orchestrator routing → semantic fidelity (prices, sentiment, headlines arrive without drift) → simulation report return → trade execution simulation → cycle timing (< 60 seconds).

### File Map

| File | Purpose |
| :--- | :--- |
| `app/services/mirofish_router.py` | Python-side router — normalises payloads + HTTP POST to MiroFish |
| `app/messaging/orchestrator.py` | Orchestrator conditional: `if target == "MIROFISH"` |
| `app/core/config.py` | `MIROFISH_BASE_URL`, `MIROFISH_DEFAULT_NUM_AGENTS`, `MIROFISH_DEFAULT_SWARM_ID` |
| `playground/src/mirofish-bridge.ts` | TypeScript `engram.routeTo('mirofish', ...)` one-liner + low-level bridge |
| `playground/src/engram-sdk.ts` | SDK config loader + adapter registry |
| `tests/integration/test_mirofish_e2e.py` | Full E2E test — predict + execute hybrid loop |

---

## Multi-Platform Trading Semantic Templates

### What Is It?

**Trading Semantic Templates** provide standardized adapters for exchanges, prediction markets, payment systems, and data feeds. This module allows agents to use a single schema across platforms without custom transformation code.

Engram translates the unified payload into the specific API format for the target platform (e.g., Binance, Kalshi, Stripe).

### Supported Platforms

| Category | Platform | Adapter | API Method |
| :--- | :--- | :--- | :--- |
| **Crypto Exchanges** | Binance | `binance-adapter.js` | CCXT (HMAC signing, rate limiting) |
| | Coinbase | `coinbase-adapter.js` | CCXT (Advanced Trade v3) |
| | Robinhood Crypto | `robinhood-adapter.js` | Direct REST (v2 fee-tier endpoint) |
| **Prediction Markets** | Kalshi | `kalshi-adapter.js` | Direct REST (trade-api/v2) |
| **Payment Rails** | Stripe | `stripe-adapter.js` | Direct REST (Payment Intents API) |
| | PayPal | `paypal-adapter.js` | OAuth2 → Orders API |
| **Live Data Feeds** | X (Twitter) | `feeds-adapter.js` | Tweets Search (recent) |
| | FRED | `feeds-adapter.js` | Series Observations API |
| | Reuters | `feeds-adapter.js` | Placeholder (enterprise license) |
| | Bloomberg | `feeds-adapter.js` | Placeholder (Terminal/B-PIPE) |

### How It Works

```mermaid
flowchart TD
    A[AI Agent] -->|Unified tradeOrder| B(Engram Router)
    B --> C{Platform?}
    C -->|binance| D[Binance Adapter<br/>CCXT + HMAC]
    C -->|coinbase| E[Coinbase Adapter<br/>CCXT + Advanced Trade v3]
    C -->|robinhood| F[Robinhood Adapter<br/>axios + Signature Headers]
    C -->|kalshi| G[Kalshi Adapter<br/>axios + Bearer Token]
    C -->|stripe| H[Stripe Adapter<br/>axios + Secret Key]
    C -->|paypal| I[PayPal Adapter<br/>OAuth2 → Orders API]
    C -->|feeds| J[Feeds Multi-Adapter<br/>X / FRED / Reuters / Bloomberg]
    
    D --> K[Normalised Response]
    E --> K
    F --> K
    G --> K
    H --> K
    I --> K
    J --> K
    K --> A
```

1. **Unified Schema** — Your agent builds a single structured payload (`tradeOrder`, `balanceQuery`, `paymentIntent`, or `feedRequest`) using the unified schema. This schema covers trade orders (limit, market, stop), balance queries, payment intents, and feed requests.
2. **Semantic Normalisation** — Engram maps the unified schema fields to each platform's native API format automatically.
3. **API Authentication** — Each adapter uses the API keys you provide in your configuration (per-platform, stored securely per instance).
4. **Response Unification** — Heterogeneous platform responses are normalised back into a consistent structure.

### Setup

1. **Install the trading templates module** (if not already bundled):
   ```bash
   cd trading-templates
   npm install
   ```

2. **Configure your platform API keys** in your `.env`:
   ```env
   # Crypto Exchanges
   BINANCE_API_KEY=your_binance_api_key
   BINANCE_SECRET=your_binance_secret
   COINBASE_API_KEY=your_coinbase_api_key
   COINBASE_SECRET=your_coinbase_secret
   ROBINHOOD_API_KEY=your_robinhood_api_key
   ROBINHOOD_ACCESS_TOKEN=your_robinhood_access_token

   # Prediction Markets
   KALSHI_TOKEN=your_kalshi_token

   # Payment Rails
   STRIPE_SECRET_KEY=your_stripe_secret_key
   PAYPAL_CLIENT_ID=your_paypal_client_id
   PAYPAL_CLIENT_SECRET=your_paypal_client_secret

   # Live Data Feeds
   X_BEARER_TOKEN=your_x_bearer_token
   FRED_API_KEY=your_fred_api_key
   REUTERS_APP_KEY=your_reuters_partner_key      # Enterprise only
   BLOOMBERG_SERVICE_ID=your_bloomberg_id         # Terminal/B-PIPE only
   ```

3. **Enable platforms** via the SDK (only configure the platforms you need):
   ```ts
   import { engram } from './mirofish-bridge';

   engram.enableTradingTemplate('binance', {
     BINANCE_API_KEY: process.env.BINANCE_API_KEY,
     BINANCE_SECRET: process.env.BINANCE_SECRET,
   });

   engram.enableTradingTemplate('stripe', {
     STRIPE_SECRET_KEY: process.env.STRIPE_SECRET_KEY,
   });
   ```

### Usage Examples

#### Example 1: Place a Trade on Binance

```ts
const result = await engram.routeTo('binance', {
  tradeOrder: {
    symbol: 'BTC/USDT',
    action: 'limit',
    quantity: 0.01,
    price: 64000,
  }
});

console.log(result);
// {
//   status: 'success',
//   platform: 'binance',
//   result: { orderId: '...', status: 'NEW', ... },
//   timestamp: '2026-03-21T...'
// }
```

#### Example 2: Check Balance on Coinbase

```ts
const balance = await engram.routeTo('coinbase', {
  tradeOrder: {
    action: 'balance',
  }
}, {
  COINBASE_API_KEY: process.env.COINBASE_API_KEY,
  COINBASE_SECRET: process.env.COINBASE_SECRET,
});
```

#### Example 3: Place a Prediction Market Bet on Kalshi

```ts
const prediction = await engram.routeTo('kalshi', {
  tradeOrder: {
    symbol: 'PRES-2028-DEM',
    action: 'buy',
    quantity: 50,
  }
});
```

#### Example 4: Create a Stripe Payment Intent

```ts
const payment = await engram.routeTo('stripe', {
  tradeOrder: {
    amount: 49.99,
    currency: 'usd',
    customerId: 'cus_abc123',
  }
});
```

#### Example 5: Process a PayPal Order

```ts
const order = await engram.routeTo('paypal', {
  tradeOrder: {
    amount: 29.99,
    currency: 'USD',
    customerId: 'buyer_ref_001',
  }
});
```

#### Example 6: Fetch Live Data Feeds

Pull real-time sentiment, economic indicators, or news to enrich your trading decisions:

```ts
// Fetch recent tweets about Bitcoin from X
const xFeed = await engram.routeTo('feeds', {
  source: 'x',
  query: 'Bitcoin price prediction',
});

// Fetch GDP data from FRED
const fredFeed = await engram.routeTo('feeds', {
  source: 'fred',
  query: 'GDP',
});
```

#### Example 7: Combined Trade + Feed Enrichment (Predict-Execute Loop)

The most powerful pattern — automatically enrich a trade order with live data before execution:

```ts
const enrichedTrade = await engram.routeTo('binance', {
  tradeOrder: {
    symbol: 'ETH/USDT',
    action: 'market',
    quantity: 0.5,
  },
  feedRequest: {
    source: 'x',
    query: 'Ethereum sentiment',
  }
});

console.log(enrichedTrade);
// {
//   status: 'success',
//   platform: 'binance',
//   result: { ... },
//   enrichedContext: {
//     source: 'x',
//     data: [{ id: '...', text: '...' }, ...],
//     metadata: { newest_id: '...', result_count: 10 }
//   },
//   timestamp: '2026-03-21T...'
// }
```

#### Example 8: Multi-Platform Routing (Same Payload, Multiple Exchanges)

Route the identical unified payload to multiple platforms sequentially:

```ts
const order = {
  tradeOrder: {
    symbol: 'BTC/USDT',
    action: 'limit',
    quantity: 0.005,
    price: 63500,
  }
};

const binanceResult = await engram.routeTo('binance', order);
const coinbaseResult = await engram.routeTo('coinbase', order);
// Same structured payload, no changes needed between platforms
```

### Unified Schema Reference

The unified schema covers four payload types. Your agent constructs one of these objects and the adapters handle the rest:

| Payload Type | Key Fields | Used By |
| :--- | :--- | :--- |
| **Trade Order** | `symbol`, `action` (limit/market/stop/buy/sell/balance), `quantity`, `price` | Binance, Coinbase, Robinhood, Kalshi |
| **Payment Intent** | `amount`, `currency`, `customerId` | Stripe, PayPal |
| **Feed Request** | `source` (x/fred/reuters/bloomberg), `query` | Feeds adapter |
| **Balance Query** | `action: 'balance'` | Binance, Coinbase |

### File Map

| File | Purpose |
| :--- | :--- |
| `trading-templates/index.js` | Module entry point — exports all adapters |
| `trading-templates/adapters/binance-adapter.js` | Binance exchange adapter (CCXT) |
| `trading-templates/adapters/coinbase-adapter.js` | Coinbase Advanced Trade adapter (CCXT) |
| `trading-templates/adapters/robinhood-adapter.js` | Robinhood Crypto adapter (direct REST) |
| `trading-templates/adapters/kalshi-adapter.js` | Kalshi prediction market adapter (REST) |
| `trading-templates/adapters/stripe-adapter.js` | Stripe Payment Intents adapter (REST) |
| `trading-templates/adapters/paypal-adapter.js` | PayPal Orders adapter (OAuth2 + REST) |
| `trading-templates/adapters/feeds-adapter.js` | Multi-source feeds adapter (X, FRED, Reuters, Bloomberg) |
| `trading-templates/package.json` | npm package metadata (`@engram/trading-templates`) |

---

## One-Command Quick Start

Engram provides a "Single Command Runtime Experience" — a unified entry point that launches the FastAPI bridge, background orchestration services (Discovery + Task Worker), and the real-time TUI dashboard simultaneously.

### Installation & Run

#### **Windows**
```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch Engram (Starts backend + TUI immediately)
.\engram.bat
```

#### **Linux / macOS**
```bash
# 1. Run the auto-installer
chmod +x setup.sh && ./setup.sh

# 2. Launch Engram
python app/cli.py
```


Once running, the Swagger UI API documentation is available at:  
`http://localhost:8000/docs`

---

## Terminal Dashboard (TUI)

The Engram TUI provides a terminal interface to monitor protocol bridge operations and background services.

### TUI Command Reference
Type these commands directly into the prompt at the bottom of the dashboard:

| Command | Action |
| :--- | :--- |
| `/status` | Check the health of the bridge, memory silos, and worker loops. |
| `/agents` | List all connected agents and their compatibility scores. |
| `/clear` | Clear the translation event logs from the view. |
| `/help` | Show the available command list. |
| **`[Natural Language]`** | Any text not starting with `/` is automatically routed to the **Delegation Engine** for intent detection and swarm orchestration. |

### Key Bindings
- **`Q`**: Quit the daemon and stop background services.
- **`C`**: Clear the log view.
- **`R`**: Force refresh system metrics.

---

## Live Playground

Deploy the static playground in `playground/` (GitHub Pages or Vercel), then share pre-loaded scenarios
with a URL hash. Replace the domain below with your deployed playground URL.

[Open in Playground](https://kwstx.github.io/engram_translator/#state=JTdCJTIyc291cmNlUHJvdG9jb2wlMjIlM0ElMjJBMkElMjIlMkMlMjJ0YXJnZXRQcm90b2NvbCUyMiUzQSUyMk1DUCUyMiUyQyUyMmlucHV0VGV4dCUyMiUzQSUyMiU3QiU1Q24lMjAlMjAlNUMlNUMlNUMlMjJpbnRlbnQlNUMlNUMlNUMlMjIlM0ElMjAlNUMlNUMlNUMlMjJzY2hlZHVsZV9tZWV0aW5nJTVDJTVDJTVDJTIyJTJDJTVDbiUyMCUyMCU1QyU1QyU1QyUyMnBhcnRpY2lwYW50cyU1QyU1QyU1QyUyMiUzQSUyMCU1QiU1QyU1QyU1QyUyMmFsaWNlJTQwZXhhbXBsZS5jb20lNUMlNUMlNUMlMjIlMkMlMjAlNUMlNUMlNUMlMjJib2IlNDBleGFtcGxlLmNvbSU1QyU1QyU1QyUyMiU1RCUyQyU1Q24lMjAlMjAlNUMlNUMlNUMlMjJ3aW5kb3clNUMlNUMlNUMlMjIlM0ElMjAlN0IlNUNuJTIwJTIwJTIwJTIwJTVDJTVDJTVDJTIyc3RhcnQlNUMlNUMlNUMlMjIlM0ElMjAlNUMlNUMlNUMlMjIyMDI2LTAzLTEyVDA5JTNBMDAlM0EwMFolNUMlNUMlNUMlMjIlMkMlNUNuJTIwJTIwJTIwJTIwJTVDJTVDJTVDJTIyZW5kJTVDJTVDJTVDJTIyJTNBJTIwJTVDJTVDJTVDJTIyMjAyNi0wMy0xMlQxMSUzQTAwJTNBMDBaJTVDJTVDJTVDJTIyJTVDbiUyMCUyMCU3RCUyQyU1Q24lMjAlMjAlNUMlNUMlNUMlMjJ0aW1lem9uZSU1QyU1QyU1QyUyMiUzQSUyMCU1QyU1QyU1QyUyMlVUQyU1QyU1QyU1QyUyMiUyQyU1Q24lMjAlMjAlNUMlNUMlNUMlMjJ1c2VyX2lkJTVDJTVDJTVDJTIyJTNBJTIwJTVDJTVDJTVDJTIydXNlcl80MiU1QyU1QyU1QyUyMiU1Q24lN0QlMjIlN0Q=)

### Embed in README

```html
<iframe
  src="https://kwstx.github.io/engram_translator/"
  width="100%"
  height="720"
  style="border: 1px solid #e5e4e7; border-radius: 12px;"
  title="Agent Translator Playground"
></iframe>
```

---

## Authentication Prerequisites

Some endpoints (such as message translation) require a JSON Web Token (JWT) for authorization. Ensure you have your token configured and that its issuer and audience match the `AUTH_ISSUER` and `AUTH_AUDIENCE` environment variables. For local testing, you can use the built-in development utilities to mock or mint a token.

---

## Usage Examples

Here is a typical workflow to connect two isolated agents using the middleware API.

### 1. Register the Scheduling Agent
Add an agent to the registry, defining its supported protocols and capabilities.

```bash
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"agent-a\",\"endpoint_url\":\"http://agent-a:8080\",\"supported_protocols\":[\"a2a\"],\"semantic_tags\":[\"scheduling\"],\"is_active\":true}"
```

**Example Response:**
```json
{
  "message": "Agent agent-a registered successfully",
  "status": "active"
}
```

### 2. Discover a Compatible Collaborator
Search the registry for available agents that match specific protocols or semantic requirements (e.g., finding an agent that can handle scheduling).

```bash
curl -X GET "http://localhost:8000/api/v1/discovery/collaborators"
```

**Example Response:**
```json
{
  "collaborators": [
    {
      "agent_id": "agent-a",
      "supported_protocols": ["a2a"],
      "compatibility_score": 0.95
    }
  ]
}
```

### 3. Send a Meeting Request Across Protocols
Send a message from a source agent to a target agent. The middleware receives the request, translates the protocol and payload, and forwards it to the target.

*(Note: Requires a Bearer token in the Authorization header as described in the Prerequisites)*

```bash
curl -X POST http://localhost:8000/api/v1/translate \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d "{\"source_agent\":\"agent-b\",\"target_agent\":\"agent-a\",\"payload\":{\"intent\":\"schedule_meeting\"}}"
```

**Example Response:**
```json
{
  "status": "success",
  "source_protocol": "mcp",
  "target_protocol": "a2a",
  "translated_payload": {
    "action": "book_calendar",
    "details": "meeting"
  },
  "delivery_status": "forwarded"
}
```

---

## Performance

Built for high-throughput, low-latency agent handoffs. Based on our [JMeter load tests](PERF_TESTING.md):

*   **Low Latency:** p50 ≤ 120 ms, p95 ≤ 300 ms, p99 ≤ 600 ms (tested on local Docker stack).
*   **High Throughput:** Handles ≥ 150 requests/sec sustained for 5 minutes.
*   **Stable:** Low error rate and optimized CPU utilization under peak load.

---

## Configuration

Configuration is managed via environment variables. Create a `.env` file in the root directory for local overrides. 

| Variable | Description |
| :--- | :--- |
| `ENVIRONMENT` | Operating environment (`development`, `production`). |
| `DATABASE_URL` | Neon connection string. |
| `REDIS_ENABLED` | Set to `true` to use Redis for semantic cache. |
| `AUTH_ISSUER` | Expected JWT issuer for validation. |
| `AUTH_AUDIENCE` | Expected JWT audience for validation. |
| `AUTH_JWT_SECRET` | Secret key required for JWT verification. |

---

## Manual Development Setup

If you prefer to run components individually for debugging:

```bash
# 1. Backend + Orchestration + TUI (Unified)
python app/main.py

# 2. Web Playground (Frontend)
cd playground && npm run dev
```

Run test suite:
```bash
pytest -q
```

---

## Testing & CI

We run unit tests on every pull request and push to `main` via GitHub Actions, and store JUnit + coverage artifacts for quick triage. For API-focused test examples (curl/PowerShell) and UAT guidance, see `TESTING_GUIDE.md`.

---

## Troubleshooting

*   **HTTP 401/403 on Translation**: Ensure an `Authorization: Bearer <TOKEN>` header is provided. The token's issuer and audience must match your `AUTH_ISSUER` and `AUTH_AUDIENCE` settings.
*   **Translation/Mapping Errors**: Check the application logs. If the semantic engine fails to map fields, check the ML fallback suggestions in the logs or upload an updated ontology file.
*   **Database Connection Failed**: Ensure the Neon database is reachable and the `DATABASE_URL` is set correctly.

---

## Documentation & Links

*   **Website:** [useengram.com](https://useengram.com)
*   [Architecture (ARCHITECTURE.md)](ARCHITECTURE.md): System components, data silos resolution, and overall architecture.
*   [Deployment (DEPLOYMENT.md)](DEPLOYMENT.md): Instructions for deploying to Render and Cloud Run.

---

## What's Next?

*   **Try the Live Playground:** Host a tiny live playground on GitHub Pages or Replit that lets people paste two agent JSONs and see the translation instantly. You already have the API — just wrap it!
*   **Explore the API:** Once running, visit `http://localhost:8000/docs` to interact with the full Swagger UI.
*   **Customize Semantics:** Define your own custom semantic mapping rules (OWL/PyDatalog) to handle specific data structures required by your proprietary agents.
*   **Contribute:** Check the [Architecture](ARCHITECTURE.md) to understand the internals and start contributing to the core orchestration engine.
