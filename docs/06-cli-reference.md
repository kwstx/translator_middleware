# CLI Reference

Engram's CLI is a full terminal interface — not a web UI. It features an interactive REPL with all subcommands available inline, Rich-powered output with tables, panels, trees, and progress spinners, an animated banner, `--json` machine-readable output mode, and a visual TUI debugging dashboard. Built for people who live in the terminal.

---

## Running the CLI

```bash
# Start the gateway + interactive REPL (default)
engram run

# Start with the visual TUI debugging dashboard
engram run --debug

# Bind to a custom host/port
engram run --host 0.0.0.0 --port 9000
```

When you run `engram run`, the CLI:

1. Suppresses all startup noise (import logs, uvicorn output)
2. Starts the FastAPI backend in a background daemon thread
3. Waits for the server to be ready (up to 60 seconds)
4. Clears the screen and plays the animated ENGRAM banner
5. Prints the gateway URL and API docs link
6. Drops into the interactive REPL

The REPL prompt is:

```
$ engram
```

From here, type any Engram subcommand without the `engram` prefix:

```
$ engram tools list
$ engram route test "send a message"
$ engram heal status
$ engram auth whoami
```

### REPL Built-in Commands

| Command | Description |
|---|---|
| `help` | Display all available commands in a formatted table |
| `clear` | Clear the screen and reprint the ENGRAM banner |
| `exit` / `quit` / `q` | Shut down the gateway and exit |
| Any other input | Delegated to the Typer CLI via subprocess |

> **Tip:** The REPL uses Rich's `Console.input()` for styled prompts. On terminals that support it, you get full color and Unicode rendering.

### Debug TUI Mode

```bash
engram run --debug
```

This launches the full Textual-based TUI dashboard (`tui/app.py`) instead of the REPL. The TUI provides:

| Panel | Location | What it shows |
|---|---|---|
| **Connections** | Top-left | Live connection events to external services |
| **Agent Execution** | Top-right | Agent step events during orchestration |
| **Tool Usage** | Middle-left | Tool invocation events with payloads |
| **Responses** | Middle-right | Response events from tools and agents |
| **Translation** | Center | Three-panel view: Engram Task → Tool Request → Tool Response |
| **System Status** | Right sidebar | FastAPI engine, discovery service, task worker status |
| **Task Tracker** | Right sidebar | Current task, progress with per-step agent tracking |
| **Connected Services** | Right sidebar | Status of each provider (Claude, Slack, etc.) |
| **Log View** | Bottom | Timestamped log stream of all events |
| **Command Input** | Bottom bar | Input field for tasks and `/commands` |

The TUI requires authentication — it shows an inline login form on first launch. Credentials are encrypted with Fernet and stored in `~/.engram/config.enc`.

---

## Global Options

These flags apply to every `engram` command:

| Flag | Type | Default | Description |
|---|---|---|---|
| `--json` | `bool` | `false` | Output in machine-readable JSON format |
| `--config` | `Path` | `~/.engram/config.yaml` | Path to a custom config file |
| `--help` | — | — | Show help text for any command |

### JSON Output Mode

When you pass `--json`, all Rich-formatted output (tables, panels, trees) is replaced with structured JSON. This makes every command scriptable and pipeable:

```bash
# Human-readable (default)
engram tools list

# Machine-readable
engram --json tools list | jq '.[] | select(.backend == "MCP")'

# Use in scripts
TOOL_COUNT=$(engram --json tools list | jq 'length')
```

Exit codes follow standard conventions:
- `0` — Success
- `1` — Error (authentication failure, API error, invalid input)

---

## Core Commands

### `engram init`

Initialize the Engram configuration and directory structure.

```bash
engram init
```

Creates `~/.engram/` and writes the default `config.yaml`. Safe to run multiple times — it overwrites with defaults.

**Output:**
```
╭──── Initialization Success ──────────────────────╮
│ Initialized Engram directory at ~/.engram         │
│ Config saved to ~/.engram/config.yaml             │
╰──────────────────────────────────────────────────╯
```

### `engram info`

Display current CLI configuration and system status.

```bash
engram info
```

Shows the config file path, API URL, backend preference, authentication status, and a masked EAT token preview.

**Output:**
```
        System Information
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Key         ┃ Value                         ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Config Path │ ~/.engram/config.yaml         │
│ API URL     │ http://127.0.0.1:8000         │
│ Backend     │ mcp                           │
│ Auth Status │ Authenticated                 │
│ EAT Token   │ ****abc1                      │
└─────────────┴───────────────────────────────┘
```

### `engram run`

Start the Engram Protocol Bridge — interactive CLI mode.

```bash
engram run [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--host` | `str` | `127.0.0.1` | Host to bind the backend |
| `--port` | `int` | `8000` | Port to run the backend |
| `--debug` | `bool` | `false` | Start TUI dashboard instead of REPL |

---

## Auth Subgroup

Manage authentication and EAT (Engram Authorization Tokens).

### `engram auth login`

Authenticate with the Engram backend to retrieve an EAT.

```bash
engram auth login [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--token`, `-t` | `str` | — | Directly input an EAT token (skips browser flow) |
| `--browser / --no-browser` | `bool` | `true` | Open login page in browser |

**Behavior:**
1. If `--token` is provided, saves it directly to the keyring
2. Otherwise, opens the login URL in your browser
3. Prompts you to paste your EAT token (hidden input)
4. Saves the token and displays your identity via `auth whoami`

```bash
# Interactive login (opens browser)
engram auth login

# Direct token input
engram auth login --token eyJhbGciOiJIUzI1NiJ9...

# No browser (manual URL copy)
engram auth login --no-browser
```

### `engram auth whoami`

Display current identity and a semantic permission summary.

```bash
engram auth whoami
```

Decodes the EAT JWT (without verifying the signature, since the CLI is a trusted client) and renders a Rich tree showing:

```
╭──── Current Session Identity ────────────────────╮
│ 👤 Identity: user@company.com                     │
│ ├── 🔐 Permissions (EAT Structured)              │
│ │   ├── slack                                     │
│ │   │   ├── send_message                          │
│ │   │   └── list_channels                         │
│ │   └── docker                                    │
│ │       ├── run                                   │
│ │       └── ps                                    │
│ ├── 🔬 Semantic Scopes (Ontology-based)           │
│ │   ├── execute:tool-invocation                   │
│ │   │   └── Can invoke cross-protocol translations│
│ │   └── read:ontology-metadata                    │
│ │       └── Can query tool catalogs               │
╰──────────────────────────────────────────────────╯
```

### `engram auth scope`

Explore and visualize the semantic scopes assigned to your EAT.

```bash
engram auth scope
```

Renders a table mapping each semantic scope to its ontology context and capability:

```
          Semantic Access Scopes
╔═══════════════════════════╦══════════════╦═══════════════════════╗
║ Scope Identifier          ║ Ontology Ctx ║ Capability            ║
╠═══════════════════════════╬══════════════╬═══════════════════════╣
║ execute:tool-invocation   ║ Global       ║ Translation Execution ║
║ read:ontology-metadata    ║ Global       ║ Metadata Query        ║
╚═══════════════════════════╩══════════════╩═══════════════════════╝
```

### `engram auth status`

Check current authentication status with expiration details.

```bash
engram auth status
```

### `engram auth token-set`

Manually set the Engram Authorization Token.

```bash
engram auth token-set <token>
```

---

## Config Subgroup

View and modify CLI configuration.

### `engram config show`

Display the current configuration as a key-value table.

```bash
engram config show
```

### `engram config set`

Set a configuration value.

```bash
engram config set <key> <value>
```

Supported keys match the `EngramConfig` model fields:

| Key | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | `http://127.0.0.1:8000` | Base URL for the Engram API |
| `backend_preference` | `enum` | `mcp` | Default backend: `mcp` or `cli` |
| `model_provider` | `str` | `openai` | AI model provider name |
| `verbose` | `bool` | `false` | Enable verbose logging |

```bash
# Examples
engram config set api_url http://my-server:8000
engram config set backend_preference cli
engram config set model_provider anthropic
engram config set verbose true
```

The config is saved to `~/.engram/config.yaml` in YAML format. Values are type-coerced automatically (booleans from `"true"`/`"false"`, integers from numeric strings).

---

## Tools Subgroup

Discover and manage tools (MCP & CLI).

### `engram tools list`

List all registered tools with backend type, semantic tags, and performance stats.

```bash
engram tools list [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--popular` | `bool` | `false` | Include pre-optimized wrappers for popular apps |
| `--filter`, `-f` | `str` | — | Quick fuzzy filter for tool names or descriptions |

The fuzzy filter uses `difflib.SequenceMatcher` and scores matches across tool name, description, and tags. Results are sorted by match score descending.

```bash
# List custom tools only
engram tools list

# Include popular pre-optimized apps
engram tools list --popular

# Fuzzy search
engram tools list --filter "weather"
engram tools list -f docker
```

### `engram tools search`

Search for tools using fuzzy matching. Shortcut for `tools list --filter`.

```bash
engram tools search <query> [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--popular / --no-popular` | `bool` | `true` | Include popular app catalog in search |

```bash
engram tools search slack
engram tools search "file management" --no-popular
```

---

## Register Subgroup

Onboard and register new APIs, CLI manifests, or direct shell commands.

### `engram register openapi`

Universal onboarding for APIs via OpenAPI specs or partial documentation.

```bash
engram register openapi <source> [OPTIONS]
```

| Argument/Option | Type | Description |
|---|---|---|
| `source` | `str` | URL, local file path, or documentation text |
| `--agent-id` | `str` | Agent UUID to link the tool to (auto-detected if omitted) |
| `--partial` | `bool` | Treat source as partial documentation text |

```bash
# From URL
engram register openapi https://api.example.com/openapi.json

# From local file
engram register openapi ./specs/weather-api.yaml

# From partial documentation
engram register openapi "The weather API has a GET /current endpoint that takes a city parameter" --partial
```

The registration pipeline:

1. **Source validation** — URL fetch, local file read, or partial text detection
2. **Schema parsing** — OpenAPI spec validation and endpoint extraction
3. **Dual schema generation** — Creates both MCP tool definition and CLI wrapper
4. **Ontology alignment** — Maps fields through `protocols.owl`, resolves 3+ schema mismatches
5. **Registry storage** — Tool is immediately discoverable by agents

### `engram register command`

Onboard a local CLI tool by parsing its help text and generating a semantic wrapper.

```bash
engram register command <command> [OPTIONS]
```

| Argument/Option | Type | Description |
|---|---|---|
| `command` | `str` | The shell command to register (e.g., `docker`, `kubectl`, `git`) |
| `--agent-id` | `str` | Agent UUID to link the tool to |

```bash
engram register command docker
engram register command kubectl
engram register command ffmpeg
```

The system probes the shell for the command, parses its `--help` output, discovers subcommands, infers argument types, and synthesizes a semantic wrapper with both MCP and CLI schemas.

### `engram register tool`

Start an interactive session to manually register a new tool.

```bash
engram register tool
```

The wizard prompts for:

1. **Tool Name** — Human-readable name
2. **Description** — What the tool does
3. **Base URL** — The API's base URL (e.g., `https://api.weather.com`)
4. **Path** — The endpoint path (e.g., `/v1/current`)
5. **HTTP Method** — GET, POST, PUT, or DELETE
6. **Parameters** — Name, type, description, and required flag for each parameter (repeat until done)

After confirming, the tool is registered via `POST /api/v1/registry/manual` with a synthetic OpenAPI schema.

---

---

## Scope Subgroup (Recommended Pattern)

Manage narrow tool scopes for agent turns and bounded workflows. This is the primary recommended pattern for production agents to prevent hallucinations and ensure zero-drift execution.

### `engram scope create`

Register a named tool scope in the registry.

```bash
engram scope create --name <name> --tools <tools>
```

| Option | Type | Description |
|---|---|---|
| `--name`, `-n` | `str` | Unique name for the scope (e.g., `research_phase`) |
| `--tools`, `-t` | `str` | Comma-separated list of tool names to include |

```bash
engram scope create --name research --tools "web_search,get_company_info"
```

### `engram scope list`

List all pre-registered scope templates.

```bash
engram scope list
```

### `engram scope validate`

Perform deep validation of a scope: check for schema drift, self-heal, and pre-calculate routing decisions.

```bash
engram scope validate [OPTIONS]
```

| Option | Type | Description |
|---|---|---|
| `--name`, `-n` | `str` | Name of the scope to validate |
| `--tools`, `-t` | `str` | Comma-separated list of tools to validate (ad-hoc) |

```bash
# Validate a registered scope
engram scope validate --name research

# Validate an ad-hoc set of tools
engram scope validate --tools "web_search,docker"
```

### `engram scope show`

Show tool definitions and details for a specific named scope.

```bash
engram scope show <name>
```

---

## Route Subgroup

Test and visualize performance-weighted routing decisions.

### `engram route test`

Simulate routing for a task description and display choice reasoning.

```bash
engram route test <description> [OPTIONS]
```

| Argument/Option | Type | Description |
|---|---|---|
| `description` | `str` | Natural language description of the task |
| `--force-mcp` | `bool` | Force routing to MCP backend |
| `--force-cli` | `bool` | Force routing to CLI backend |

```bash
# Natural routing
engram route test "deploy the application to staging"

# Force a specific backend
engram route test "list all docker containers" --force-cli
engram route test "send a notification" --force-mcp
```

**Output includes:**

1. **Optimal Routing Decision** panel — Chosen tool, backend, confidence, predicted latency, estimated cost, and reasoning
2. **Alternative Backends Comparison** table — All candidates with composite score, similarity, latency, and success rate

### `engram route list`

Display a sorted table of tools with historical performance statistics.

```bash
engram route list
```

Shows tool name, backend, average latency, success rate, average token cost, and sample count for all tools with routing history.

---

## Heal Subgroup

Inspect and trigger semantic self-healing for tool drifts.

### `engram heal status`

Query the reconciliation engine for detected semantic drifts and pending repairs.

```bash
engram heal status [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--verbose`, `-v` | `bool` | `false` | Show full logs and detailed drift analysis |
| `--fix` | `bool` | `false` | Trigger immediate repair loops if drifts are found |

**Output includes two tables:**

1. **Semantic Drift Analysis** — Source protocol, field drift, ontology match, confidence, and status (AUTO-REPAIR or PENDING-REVIEW)
2. **Persistent Semantic Mappings** — Active mappings between protocols with version numbers

```bash
# Basic status
engram heal status

# Detailed with payload excerpts
engram heal status --verbose

# Check and fix in one command
engram heal status --fix
```

When `--verbose` is used, each pending drift includes a full JSON panel showing the payload excerpt and failure type.

### `engram heal now`

Trigger immediate semantic repair loops for all detected drifts.

```bash
engram heal now
```

Calls `POST /api/v1/reconciliation/heal` and displays progress with Rich spinners. The engine queries the drift database, re-aligns with the semantic ontology, and synchronizes mapping tables.

---

## Trace Subgroup

Observability and semantic execution tracing.

### `engram trace list`

Renders a filterable Rich table of recent semantic execution traces.

```bash
engram trace list [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--limit` | `int` | `20` | Number of traces to show |
| `--tool` | `str` | — | Filter by tool name |
| `--export` | `bool` | `false` | Export as JSON for piping |

```bash
# Recent traces
engram trace list

# Filter by tool
engram trace list --tool slack

# Export for analysis
engram trace list --export | jq '.[] | select(.success == false)'
```

### `engram trace detail`

Detailed inspection including semantic path, routing reasoning, and healing steps.

```bash
engram trace detail <trace_id>
```

| Argument | Type | Description |
|---|---|---|
| `trace_id` | `str` | Trace ID to inspect. Use `.` for the latest trace. |

```bash
# Inspect a specific trace
engram trace detail 7a3f2b1c

# Shortcut: inspect the latest trace
engram trace detail .

# Export full trace as JSON
engram trace detail . --export
```

**Output includes:**

1. **AI-generated Summary** — Natural-language reasoning about the routing and healing decisions (generated by the backend LLM via `POST /api/v1/traces/query`)
2. **Semantic Trace Tree** — Rich tree visualization:
   - **Execution Path** — Tool selection, routing choice, backend, latency, success/failure
   - **Performance Weights** — Semantic similarity, composite score, token efficiency
   - **Self-Healing Steps** — Any reconciliation steps taken during execution
   - **Ontological Alignment** — Context interpretation and synthesized field mappings

---

## Evolve Subgroup

Manage self-evolving tools and ML-driven improvements.

### `engram evolve status`

Display ML improvement progress in a dashboard-like Rich layout.

```bash
engram evolve status
```

Shows:
- Pipeline status (active/idle)
- Pending proposal count
- Total historical evolutions
- Last ML update timestamp
- Table of pending refinements with tool name, version change, refinement type, proposed changes, confidence score, and proposal ID

Refinement types include:
- **Description Path Refinement** — Improved tool descriptions based on execution history
- **Parameter Schema Optimization** — Tightened action schemas based on failure analysis
- **New Recovery Strategy** — Pattern-based automated fallback mapping

### `engram evolve apply`

Trigger updates with confirmation prompts and show before/after diffs.

```bash
engram evolve apply <evolution_id> [OPTIONS]
```

| Argument/Option | Type | Description |
|---|---|---|
| `evolution_id` | `str` | ID (or prefix) of the evolution proposal to apply |
| `--force`, `-f` | `bool` | Apply without confirmation prompt |

```bash
# Interactive apply with diff preview
engram evolve apply 7a3f2b1c

# Skip confirmation
engram evolve apply 7a3f2b1c --force
```

The command shows a preview of changes (before/after diffs) and asks for confirmation before applying. Once applied, the tool registry is hot-redeployed with the new version.

---

## Protocol Subgroup

Federated protocol management and translation.

### `engram protocol translate`

Perform real-time translation between protocols using the system ontology as a bridge.

```bash
engram protocol translate [OPTIONS]
```

| Option | Type | Description |
|---|---|---|
| `--from` | `str` | Source protocol: `mcp`, `cli`, `a2a`, `acp` |
| `--to` | `str` | Target protocol: `mcp`, `cli`, `a2a`, `acp` |
| `--payload`, `-p` | `str` | JSON payload or path to JSON file (optional — uses demo payload if omitted) |

```bash
# Translate MCP to CLI (demo payload)
engram protocol translate --from mcp --to cli

# Translate with custom payload
engram protocol translate --from a2a --to mcp --payload '{"task": "search", "query": "AI news"}'

# Translate from file
engram protocol translate --from cli --to a2a --payload ./request.json
```

**Output:** Three side-by-side panels showing Source → Canonical Bridge (Ontology) → Target.

### `engram protocol handoff simulate`

Simulate a seamless multi-agent task handoff, demonstrating semantic state transfer.

```bash
engram protocol handoff simulate [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--source-agent` | `str` | `CLI-Local` | Name of the source agent |
| `--target-agent` | `str` | `Remote-MCP` | Name of the target agent |

**Output:** A Rich tree showing session ID, semantic readiness, bridged protocols, and transferred state (Redis-backed) with full JSON payloads for each state category.

---

## Sync Subgroup

Manage bidirectional synchronization and event monitoring.

### `engram sync list`

List active event listeners, pollers, and CLI watchers.

```bash
engram sync list
```

### `engram sync add`

Add a new bidirectional sync or event listener to a tool.

```bash
engram sync add <tool_id> [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--direction` | `str` | `both` | Sync direction: `both`, `to_mcp`, `from_mcp` |
| `--type` | `str` | `polling` | Source type: `polling` or `cli_watch` |
| `--url` | `str` | — | URL for polling (required for `polling` type) |
| `--command` | `str` | — | Command for CLI watch (required for `cli_watch` type) |
| `--interval` | `int` | `60` | Polling interval in seconds |

```bash
# Add polling sync
engram sync add <tool-uuid> --type polling --url https://api.example.com/changes --interval 30

# Add CLI watch sync
engram sync add <tool-uuid> --type cli_watch --command "docker ps --format json"
```

### `engram sync status`

Show live monitoring of recent events and semantic conflict resolutions.

```bash
engram sync status
```

Uses Rich's `Live` display with auto-refresh (2 frames/second) to show a real-time event stream. Press `Ctrl+C` to stop monitoring.

---

## Interactive REPL Reference

When running inside `engram run`, all subcommands are available without the `engram` prefix. The REPL delegates to the Typer CLI via subprocess, so every feature works identically.

### Full Command Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     Available Commands                          │
├───────────────────────────────┬─────────────────────────────────┤
│ Command                      │ Description                     │
├───────────────────────────────┼─────────────────────────────────┤
│ tools list                   │ List all registered tools        │
│ tools search <query>         │ Search tools by name or tag      │
│ register openapi <url>       │ Register from OpenAPI spec       │
│ register command <cmd>       │ Register a shell command         │
│ register tool                │ Interactive manual registration  │
│ route test <tool>            │ Test routing decision            │
│ route list                   │ Show tools with routing stats    │
│ trace list                   │ List recent execution traces     │
│ trace detail <id>            │ Inspect a specific trace         │
│ heal status                  │ Self-healing status              │
│ heal now                     │ Trigger immediate repair loop    │
│ evolve status                │ ML improvement dashboard         │
│ evolve apply <id>            │ Apply a proposed refinement      │
│ protocol translate           │ Translate between protocols      │
│ protocol handoff simulate    │ Simulate multi-agent handoff     │
│ sync list                    │ List sync connections            │
│ auth whoami                  │ Show identity & scopes           │
│ clear                        │ Clear the screen                 │
│ exit                         │ Shut down the gateway            │
└───────────────────────────────┴─────────────────────────────────┘
```

---

## TUI Dashboard Reference

The TUI dashboard (`engram run --debug`) is a full Textual application with multiple screens, interactive forms, and real-time event routing.

### Screens

| Screen | Trigger | Purpose |
|---|---|---|
| **Welcome** | On startup (if authenticated) | Animated logo and system status |
| **Auth** | On startup (if not authenticated) | Login/Signup form with base URL, email, password |
| **Debug** | `--debug` flag | Live trace panels and event monitors |
| **Provider Selection** | Service setup (`S` key) | Choose an AI provider to connect |
| **Service Connect** | Provider button click | Enter API key for a specific provider |

### Provider Connection Screens

Each provider has a dedicated connection screen with branding and instructions:

| Provider | Screen Class | Auth Type |
|---|---|---|
| OpenAI | `OpenAIConnectScreen` | API Key |
| Claude (Anthropic) | `AnthropicConnectScreen` | API Key |
| Gemini (Google) | `GoogleConnectScreen` | API Key |
| Llama | `LlamaConnectScreen` | API Key |
| Mistral | `MistralConnectScreen` | API Key |
| Grok | `GrokConnectScreen` | API Key |
| Perplexity | `PerplexityConnectScreen` | API Key |
| DeepSeek | `DeepseekConnectScreen` | API Key |
| Other | `GenericServiceConnectScreen` | API Key |

### Event Routing

The TUI routes events from the backend to specific trace panels based on event type prefix:

| Event Type Prefix | Panel | Example |
|---|---|---|
| `connection.*` | Connections | Connection established, connection lost |
| `agent.*` | Agent Execution | Agent step started, agent step completed |
| `tool.*` | Tool Usage | Tool invoked, tool response received |
| `response.*` | Responses | Final response generated |
| `translation.*` | Translation panels | Engram task, tool request, tool response |

### Task Tracking

The TUI automatically parses orchestration events to build a live task tracker:

- **Orchestration Plan** detected → Sets total step count
- **Handing off to [Agent]** → Marks step as RUNNING
- **Step N OK** → Marks step as COMPLETED

The tracker shows current task text, status (IDLE → SUBMITTING → PLANNED → RUNNING → COMPLETED), per-step progress with agent names, and active connector list.

### TUI Bridge

The `app/core/tui_bridge.py` module provides the event pipeline between the FastAPI backend and the TUI:

- `emit_tui_event(event)` — Thread-safe event push to the shared async queue
- `tui_logger_processor` — Structlog processor that translates technical log events into plain-English TUI messages with emojis:
  - `"Translating message"` → `🔄 Translating message from MCP to CLI...`
  - `"Applied version delta"` → `✨ MCP message upgraded: v1.0 ➡️ v1.1`
  - `"Translation failed"` → `❌ Translation failed: <error>`
  - `"No translation rule found"` → `⚠️ Missing map: No path found for MCP to ACP`
  - `"Version mismatch detected"` → `⚖️ Version mismatch in MCP: Found v1.0, expected v1.1`

### Credential Storage (TUI)

The TUI stores credentials differently from the CLI:

| CLI | TUI |
|---|---|
| System keyring (`keyring` library) | Fernet-encrypted file (`~/.engram/config.enc`) |
| `config.yaml` fallback | Encryption key in `~/.engram/key` (chmod 600) |
| Plain text config | Encrypted JSON with base URL, tokens, email |

Both paths are valid. The TUI's encrypted storage is designed for environments where the system keyring isn't available (headless servers, containers).

---

## What's Next

- **[Configuration](./07-configuration.md)** — Customize every setting, routing weight, and ontology path
- **[Universal Onboarding](./08-universal-onboarding.md)** — Deep dive into tool registration
- **[Self-Healing Engine](./09-self-healing-engine.md)** — Understand the reconciliation engine
- **[Observability & Tracing](./14-observability-tracing.md)** — Set up monitoring and alerting
