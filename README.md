![Engram](https://raw.githubusercontent.com/kwstx/engram_translator/main/assets/engram-header.png)

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
curl -fsSL https://kwstx.github.io/engram_translator/setup.sh | bash
```

Works on Linux, macOS, and WSL2. The installer sets up Python dependencies, the `engram` CLI, and core services.

After installation:

```bash
source ~/.bashrc    # or source ~/.zshrc
engram              # start the CLI
```

## Getting Started

```bash
engram                  # Interactive CLI mode
engram scope create     # Define a tool boundary (Recommended)
engram scope validate   # Check for drift & pre-calculate routing
engram register         # Onboard any API or CLI tool
engram tools list       # View all registered tools
engram route test "ask" # Test intelligent routing
```

## Core Features

1. **Universal onboarding** that accepts any OpenAPI, GraphQL, URL+auth, partial docs, or CLI manifest.
2. **Validated Scopes (Primary Pattern)**: Define narrow, explicit toolsets for each agent turn to prevent hallucinations and ensure zero-drift execution.
3. **Core self-healing engine** using OWL ontologies + ML that detects and fixes schema drift in real time.
4. **Unified EAT token** with semantic permissions that works across MCP and CLI.
5. **Hybrid MCP + CLI execution** with performance-weighted routing (MCP for structure, CLI for speed).
6. **Self-evolving tools**: ML continuously improves descriptions and recovery strategies from real executions.
7. **Cross-protocol federation** with seamless translation between MCP, CLI, A2A, and ACP.

---

## SDK Usage (Recommended)

Use the **Validated Scope** pattern for robust production agents:

```python
with sdk.scope("research_phase", tools=["web_search", "get_company_info"]) as scope:
    # Agent ONLY sees these tools. Validation & activation are automatic.
    pass
```

> **Note:** "Ambient mode" (calling tools without a scope) is suitable only for quick prototyping.

---

## Documentation

- **Quickstart** -- Install to first validated scope in under 5 minutes  
  The shortest path from zero to a reliable agent: install, register, and active your first scope.
  
  ```bash
  curl -fsSL https://kwstx.github.io/engram_translator/setup.sh | bash
  source ~/.bashrc   # or ~/.zshrc
  engram register
  engram tools list
  ```

- CLI Reference -- All commands and flags  
  A full inventory of `engram` commands with usage, flags, exit codes, and JSON output shape. Use this when scripting or wiring agents to the CLI.
  
  ```bash
  engram <command> --help
  engram tools list --json
  engram route test "send an email" --help
  ```

- Universal Onboarding -- How to connect any API or CLI tool  
  Shows how to onboard OpenAPI, GraphQL, or raw CLI tools using the same flow. You will see what to provide (endpoint, auth, or CLI manifest) and how the system generates both MCP and CLI representations.
  
  ```bash
  engram register
  # Follow the prompts to paste an OpenAPI URL, a GraphQL endpoint, or a CLI command.
  ```

- Self-Healing Engine -- OWL ontologies + ML explained  
  Explains how schema drift is detected, how mismatched fields get mapped through the ontology layer, and when ML-based reconciliation kicks in. Also covers how healing decisions are traced for review.
  
  ```bash
  engram route test "send an email"
  engram trace list
  ```

- MCP + CLI Hybrid Routing -- When each backend is chosen  
  Details the routing heuristics (structure vs. speed), how performance weights are applied, and how to force a backend when needed for debugging.
  
  ```bash
  engram route test "send an email"
  engram route test "send an email" --force-mcp
  engram route test "send an email" --force-cli
  ```

- Protocol Federation -- A2A and ACP handoff  
  Covers how requests hop across protocols, how identity and permissions follow the request, and how payloads are normalized through the ontology in transit.
  
  ```text
  Agent -> MCP tool -> ontology bridge -> ACP peer -> response back to agent
  ```

- Configuration -- EAT tokens, routing weights, ontology  
  Shows where configuration lives, how to set EAT tokens, and how to tune routing defaults. The CLI config file lives at `~/.engram/config.yaml`, and secrets are stored in the system keyring when available.
  
  ```bash
  engram info
  engram auth login
  engram auth status
  engram config show
  engram config set backend_preference mcp
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
