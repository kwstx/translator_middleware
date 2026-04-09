# Quickstart

This guide walks you through installing Engram, registering your first tool, and testing intelligent routing. By the end, you'll know the key features and how to explore further.

---

## 1. Install Engram

Run the one-line installer:

```bash
# Linux / macOS / WSL2
curl -fsSL https://kwstx.github.io/engram_translator/setup.sh | bash
```

> **Windows Users**
> Install WSL2 first, then run the command above inside your WSL2 terminal. Native Windows is supported via the `engram.bat` wrapper for local development, but production deployments should use WSL2, Docker, or a Linux server.

After it finishes, reload your shell:

```bash
source ~/.bashrc   # or source ~/.zshrc
```

---

## 2. Start the Gateway

Engram runs a lightweight backend API that powers the CLI, SDK, and all tool integrations. Start it with a single command:

```bash
engram run
```

You'll see the animated ENGRAM banner, the gateway URL, and an interactive REPL prompt. The backend starts automatically in the background — no separate server process to manage.

```
  ███████╗███╗   ██╗ ██████╗ ██████╗  █████╗ ███╗   ███╗
  ██╔════╝████╗  ██║██╔════╝ ██╔══██╗██╔══██╗████╗ ████║
  █████╗  ██╔██╗ ██║██║  ███╗██████╔╝███████║██╔████╔██║
  ██╔══╝  ██║╚██╗██║██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║
  ███████╗██║ ╚████║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝

  Connect any AI agent to any tool
  from your terminal.

  Gateway: http://127.0.0.1:8000
  API docs: http://127.0.0.1:8000/docs

$ engram
```

The banner animates on launch — a white-to-blue sweep followed by blue-to-white — and settles into the REPL. From here, every Engram subcommand is available without re-typing `engram` as a prefix. Type `help` to see all available commands, or `exit` to shut the gateway down.

> **Tip:** If you prefer a visual debugging dashboard instead of the REPL, start with `engram run --debug` to launch the Textual-based TUI with live trace panels, event monitors, task tracking, and routing visualizations. This is particularly useful for watching multi-agent orchestration in real time.

---

## 3. Register Your First Tool

Engram connects agents to any API, CLI tool, or service. The quickest way to register a tool is by pointing at an OpenAPI spec:

```bash
engram register openapi https://petstore.swagger.io/v2/swagger.json
```

The system:
1. Fetches and validates the OpenAPI specification
2. Extracts endpoints, parameters, and response schemas
3. Auto-generates dual MCP and CLI representations
4. Aligns fields through the semantic ontology (`protocols.owl`)
5. Stores the tool in the registry for immediate agent discoverability

You'll see schema mismatch resolution happening in real time, followed by a registration summary:

```
ℹ Info: 3 schema mismatches resolved via ontology alignment

╭──── [*] Registration Summary ─────────────────────────────╮
│ Successfully registered: Petstore API                      │
│ ID: 7a3f2b1c-...                                          │
│ Test Command: engram run --tool Petstore API --inspect     │
╰────────────────────────────────────────────────────────────╯
```

You're not limited to OpenAPI specs. Engram's universal onboarding accepts multiple source formats:

| Source Type | Command | What it does |
|---|---|---|
| OpenAPI / Swagger URL | `engram register openapi <url>` | Fetches spec, generates dual MCP+CLI schemas |
| Local OpenAPI file | `engram register openapi ./spec.yaml` | Same as above, from a local file |
| Partial documentation | `engram register openapi "<text>" --partial` | Extracts tool structure from freeform docs |
| Shell command | `engram register command docker` | Parses `--help` text, synthesizes semantic wrapper |
| Interactive wizard | `engram register tool` | Step-by-step manual registration with prompts |

The interactive wizard (`engram register tool`) walks you through each field: name, description, base URL, path, HTTP method, and parameters. It's the best option when you don't have a spec and want full control over the tool definition.

---

## 4. Verify Your Tools

List everything that's been registered:

```bash
engram tools list
```

The output is a Rich table showing each tool's name, backend (MCP, CLI, or Dual), semantic type, success rate, and description:

```
                   Engram Tool Catalog
┏━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ S ┃ Tool / Extension   ┃ Backend  ┃ Semantic Type┃ Success ┃ Description                  ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ * │ Petstore API       │ MCP      │ Universal    │  100.0% │ Swagger's sample pet store…  │
│ * │ docker             │ CLI      │ Container    │   98.5% │ Docker container management… │
│ > │ Slack              │ Dual     │ Messaging    │   99.0% │ Pre-optimized Slack integ…   │
└───┴────────────────────┴──────────┴──────────────┴─────────┴──────────────────────────────┘

Showing 3 active tools. Use --popular to see pre-optimized integrations.
```

The `*` marker indicates your custom-registered tools (hero tools). The `>` marker indicates pre-optimized tools from the built-in catalog. Add `--popular` to include pre-optimized wrappers for common apps like Slack, GitHub, and Stripe. Use `--filter <query>` for fuzzy search by name, description, or tag.

---

## 5. Test Intelligent Routing

Ask Engram to route a natural-language task to the best tool and backend:

```bash
engram route test "send an email to the team"
```

The router evaluates all registered tools, scores them on five dimensions, then selects the optimal backend:

```
╭──── ▶ Optimal Routing Decision ──────────────────╮
│ Chosen Tool: Slack                                │
│ Backend: MCP                                      │
│ Confidence: 87.3%                                 │
│ Predicted Latency: 245ms                          │
│ Estimated Cost: 12.5 tokens                       │
│                                                   │
│ Reasoning: Highest composite score for messaging  │
│ tasks. MCP backend selected for structured        │
│ reliability over CLI speed.                       │
╰──────────────────────────────────────────────────╯

  Alternative Backends Comparison
┏━━━━━━━━━━━┳━━━━━━━┳━━━━━━┳━━━━━━━━━┳━━━━━━━━━┓
┃ Backend   ┃ Score ┃ Sim. ┃ Latency ┃ Success ┃
┡━━━━━━━━━━━╇━━━━━━━╇━━━━━━╇━━━━━━━━━╇━━━━━━━━━┩
│ * MCP     │  0.87 │ 0.82 │   245ms │   99.0% │
│   CLI     │  0.71 │ 0.78 │   120ms │   95.2% │
└───────────┴───────┴──────┴─────────┴─────────┘
```

The scoring algorithm weights five factors:

- **Semantic Similarity** (55%) — sentence-embedding match between your task description and tool descriptions
- **Success Rate** (20%) — historical success rate for this tool/backend combination
- **Latency** (15%) — average execution time from past runs
- **Token Cost** (7%) — efficiency of the backend in token consumption
- **Context Overhead** (3%) — how much prompt engineering the backend requires

> **Tip:** Force a specific backend for debugging with `--force-mcp` or `--force-cli`. This is useful when testing how the same task performs across different execution paths.

---

## 6. Try Key Features

Now that you have tools registered and routing working, explore these capabilities:

### Check self-healing status

```bash
engram heal status
```

The reconciliation engine continuously monitors for schema drifts and field mismatches between your registered tools and the actual APIs they connect to. This command shows any detected drifts, their confidence scores, and whether they've been auto-repaired or need manual review.

```
   Semantic Drift Analysis
╭──────────────────┬──────────────┬──────────────┬───────┬─────────────╮
│ Source Protocol   │ Field Drift  │ Ontology Match│ Conf. │ Status     │
├──────────────────┼──────────────┼──────────────┼───────┼─────────────┤
│ N/A              │ No active    │ -            │ -     │ HEALTHY    │
│                  │ drifts       │              │       │            │
╰──────────────────┴──────────────┴──────────────┴───────┴─────────────╯
```

When drifts are detected, the engine evaluates each one and either auto-repairs (confidence ≥ 70%) or flags it for manual review. Use `heal status --verbose` for full telemetry excerpts, or `heal now` to trigger an immediate repair loop.

### Inspect execution traces

```bash
engram trace list
```

Every tool execution is traced with semantic detail — routing reasoning, ontology alignment, healing steps, and performance metrics. The trace table shows timestamp, trace ID, tool, backend, success/failure, and token cost.

Use `engram trace detail .` (dot for "latest") to drill into the most recent execution with a full semantic inspection tree:

```bash
engram trace detail .
```

This shows:
- An **AI-generated natural-language summary** of the routing and healing decisions
- The **execution path** with tool selection, routing choice, latency, and backend used
- **Performance weights** with semantic similarity, composite score, and token efficiency
- **Self-healing steps** (if any drift was detected and repaired)
- **Ontological alignment** details with synthesized field mappings

### View your identity

```bash
engram auth whoami
```

Displays your EAT (Engram Authorization Token) identity, structured permissions per tool, and semantic scopes derived from the `security.owl` ontology. The output is a Rich tree showing:

- Your identity (the `sub` claim from the JWT)
- Structured permissions per tool (what you can do with each registered tool)
- Semantic scopes with ontology context (e.g., `execute:tool-invocation` → "Can invoke cross-protocol tool translations")

### Translate between protocols

```bash
engram protocol translate --from mcp --to cli
```

Performs real-time translation between MCP, CLI, A2A, and ACP protocols using the semantic ontology as a canonical bridge. Without a `--payload` flag, it uses a demonstration payload. The output shows three panels side by side:

1. **Source panel** — the original payload in the source protocol format
2. **Canonical Bridge panel** — the intermediate ontology-normalized representation
3. **Target panel** — the translated payload in the target protocol format

This is invaluable for debugging cross-protocol integrations and understanding how Engram normalizes data between agent frameworks.

---

## Quick Reference

| Command | Description |
|---|---|
| `engram run` | Start the gateway and interactive REPL |
| `engram run --debug` | Start with the TUI debugging dashboard |
| `engram register openapi <url>` | Register a tool from an OpenAPI spec |
| `engram register command <cmd>` | Register a shell command as a tool |
| `engram register tool` | Interactive manual tool registration |
| `engram tools list` | List all registered tools |
| `engram tools list --popular` | Include pre-optimized integrations |
| `engram tools search <query>` | Fuzzy search across all tools |
| `engram route test "<desc>"` | Test intelligent routing for a task |
| `engram route list` | Show all tools with routing stats |
| `engram heal status` | Check self-healing reconciliation status |
| `engram heal now` | Trigger immediate repair loop |
| `engram trace list` | List recent semantic execution traces |
| `engram trace detail .` | Inspect the latest trace in detail |
| `engram evolve status` | View ML tool improvement dashboard |
| `engram evolve apply <id>` | Apply a proposed tool refinement |
| `engram protocol translate` | Translate between agent protocols |
| `engram protocol handoff simulate` | Simulate multi-agent handoff |
| `engram sync list` | List active sync connections |
| `engram sync status` | Live event stream monitoring |
| `engram auth login` | Authenticate and retrieve an EAT |
| `engram auth whoami` | Show current identity and scopes |
| `engram config show` | Display current configuration |
| `engram config set <key> <value>` | Update a configuration value |
| `engram info` | Show system information and status |

---

## Next Steps

- **[Installation](./02-installation.md)** — Detailed installation guide with prerequisites, manual setup, and troubleshooting
- **[CLI Reference](./06-cli-reference.md)** — Master every command, subcommand, and flag
- **[Configuration](./07-configuration.md)** — Customize routing weights, ontology paths, and provider settings
- **[Universal Onboarding](./08-universal-onboarding.md)** — Deep dive into connecting any API or CLI tool
- **[Self-Healing Engine](./09-self-healing-engine.md)** — Understand how OWL ontologies and ML keep your tools aligned
- **[SDK & Python Library](./16-sdk-python-library.md)** — Integrate Engram programmatically into your applications
