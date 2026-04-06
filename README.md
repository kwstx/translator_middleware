# Engram

The adaptive semantic interoperability layer for AI agents. Connect **anything** — any API, any system, any protocol — with one lightweight layer that auto-generates tools, self-heals schema drift, intelligently routes between MCP and CLI, and scales seamlessly from single agents to multi-agent swarms.

It creates reliable, self-improving tool integrations: register once (or point at any endpoint), and your agents get tools that adapt over time, fix mismatches on the fly, choose the best execution backend (MCP for structure or CLI for speed), and collaborate across protocols without glue code or maintenance hell.

**Universal onboarding** • **Self-healing schemas with OWL + ML** • **Hybrid MCP + CLI execution** • **Performance-weighted routing** • **Unified EAT identity** • **Bidirectional sync** • **Cross-protocol federation (A2A/ACP)** • **Self-evolving tools**

Works with any agent framework. No lock-in. Runs lightweight on your laptop, VPS, or in production.

## What It Does

Semantic Bridge solves brittle agent tool integrations that break in production. It sits between agents and tools, translating and routing across protocols while keeping integrations healthy over time:

- Translates between MCP, CLI, A2A, and ACP with multi-hop handoffs when needed.
- Auto-generates tool schemas and keeps them aligned as APIs drift.
- Chooses the best execution backend (structured MCP or faster CLI) per task.
- Maintains a unified EAT identity and permissions model across protocols.
- Syncs and normalizes events for reliable cross-system collaboration.

## Quick Install

```bash
curl -fsSL https://get.engram.dev/install | bash
```

Works on Linux, macOS, and WSL2. The installer sets up Python dependencies, the `sb` CLI, and core services.

After installation:

```bash
source ~/.bashrc    # or source ~/.zshrc
sb                  # start the CLI
```

## Getting Started

```bash
sb                  # Interactive CLI mode
sb register         # Onboard any API or CLI tool
sb tools list       # View all registered tools
sb route test "send an email"   # Test intelligent routing
sb doctor           # Check system health
sb update           # Update to latest version
```

## Core Features

1. Universal onboarding that accepts any OpenAPI, GraphQL, URL+auth, partial docs, or CLI manifest and auto-generates dual MCP + CLI representations.
2. Core self-healing engine using OWL ontologies + ML that detects and fixes schema drift, custom fields, and output mismatches in real time.
3. Unified EAT token with semantic permissions that works across MCP and CLI.
4. Basic performance-weighted routing that chooses the best backend (CLI for token efficiency or MCP for structured calls) based on task and history.
5. Bidirectional sync and event layer for any connected system with semantic normalization.
6. Context-aware pruning and rich semantic traces for observability.
7. Efficient support for popular apps while keeping custom and internal tools as the hero.
8. Self-evolving tools: ML continuously improves descriptions, defaults, and recovery strategies from real executions.
9. Full cross-protocol federation with seamless translation and handoff between MCP, CLI, A2A, and ACP.
10. Predictive optimizer and adaptive wrappers for legacy/non-API systems.

## CLI Command Reference

The `sb` CLI is your primary interface — clean, scriptable, and agent-friendly with Rich formatting and JSON output mode.

Add `--json` for machine-readable output perfect for agents. Run `sb <command> --help` for detailed flags.

## Why It’s Different

Most tool platforms give you connectors that break on custom fields or API changes. Semantic Bridge gives agents tools that heal themselves, intelligently pick between MCP and CLI, evolve over time, and work across protocols — so your agents stay reliable in production without constant maintenance.

## Documentation

- Quickstart -- Install to first connected tool in under 5 minutes  
  The shortest path from zero to a working tool is: install the CLI, register a tool, verify it shows up. This section walks through the minimal happy path.
  
  ```bash
  curl -fsSL https://get.engram.dev/install | bash
  source ~/.bashrc   # or ~/.zshrc
  sb register
  sb tools list
  ```

- CLI Reference -- All commands and flags  
  A full inventory of `sb` commands with usage, flags, exit codes, and JSON output shape. Use this when scripting or wiring agents to the CLI.
  
  ```bash
  sb <command> --help
  sb tools list --json
  sb route test "send an email" --help
  ```

- Universal Onboarding -- How to connect any API or CLI tool  
  Shows how to onboard OpenAPI, GraphQL, or raw CLI tools using the same flow. You will see what to provide (endpoint, auth, or CLI manifest) and how the system generates both MCP and CLI representations.
  
  ```bash
  sb register
  # Follow the prompts to paste an OpenAPI URL, a GraphQL endpoint, or a CLI command.
  ```

- Self-Healing Engine -- OWL ontologies + ML explained  
  Explains how schema drift is detected, how mismatched fields get mapped through the ontology layer, and when ML-based reconciliation kicks in. Also covers how healing decisions are traced for review.
  
  ```bash
  sb route test "send an email"
  sb trace list
  ```

- MCP + CLI Hybrid Routing -- When each backend is chosen  
  Details the routing heuristics (structure vs. speed), how performance weights are applied, and how to force a backend when needed for debugging.
  
  ```bash
  sb route test "send an email"
  sb route test "send an email" --force-mcp
  sb route test "send an email" --force-cli
  ```

- Protocol Federation -- A2A and ACP handoff  
  Covers how requests hop across protocols, how identity and permissions follow the request, and how payloads are normalized through the ontology in transit.
  
  ```text
  Agent -> MCP tool -> ontology bridge -> ACP peer -> response back to agent
  ```

- Configuration -- EAT tokens, routing weights, ontology  
  Shows where configuration lives, how to set EAT tokens, and how to tune routing defaults. The CLI config file lives at `~/.engram/config.yaml`, and secrets are stored in the system keyring when available.
  
  ```bash
  sb info
  sb auth login
  sb auth status
  sb config show
  sb config set backend_preference mcp
  ```
  
  ```yaml
  api_url: http://127.0.0.1:8000
  backend_preference: mcp
  model_provider: openai
  verbose: false
  ```

- Architecture -- Phases, components, and design decisions  
  A system-level walkthrough: ingestion and registration, ontology mapping, routing, execution, tracing, and evolution. Includes why key tradeoffs were made (MCP vs CLI, ontology-first mapping, and weighted routing).

- Contributing -- Development setup and guidelines  
  The steps to run locally, the repo layout, and how to add or update features without breaking routing or reconciliation.
  
  ```bash
  pip install -r requirements.txt
  python -m pytest -q
  ```

Built for developers who want agents that actually work on real-world systems — not just popular SaaS.

Star the repo if you’re building reliable agent tooling.
