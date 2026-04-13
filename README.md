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

1. **Governed Sequencing (Primary Pattern)**: Define strict, deterministic multi-step workflows using the `ControlPlane`. Ensure agents follow the "Golden Path" of data collection without hallucinating order or skipping steps.
2. **GlobalData Store**: Maintain state entirely outside the LLM's memory. Tools read from and write to a centralized, validated repository, ensuring the model remains stateless and decisions are based on the ground truth.
3. **Validated Scopes**: Define narrow tool boundaries for each agent turn. Automatic drift detection and pre-calculated routing ensure zero-hallucination execution.
4. **Self-Healing Engine**: Real-time schema drift detection using OWL ontologies + ML reconcile mismatched fields automatically.
5. **Unified EAT Identity**: Cryptographically secure identity with step-aware permissions that follow the request across protocols.
6. **Hybrid MCP + CLI Execution**: Intelligent routing chooses the best backend (MCP for structure, CLI for speed) based on latency and reliability.

---

## SDK Usage (Recommended)

Build production-grade agents using **Governed Sequencing**:

```python
from engram_sdk import ControlPlane, Step, GlobalData

# 1. Define the workflow state machine
cp = ControlPlane(steps=[
    Step("find_user", tools=["search_db"], next_step="check_subscription"),
    Step("check_subscription", tools=["get_stripe_status"], next_step="finalize")
])

# 2. Execute with strict step enforcement
with cp.step("find_user"):
    # Model is ONLY allowed to call 'search_db'
    # Orchestrator handles state transitions and logging
    pass
```

> **Why?** Moving sequencing logic into the `ControlPlane` makes agents 10x more reliable. The model makes small decisions within narrow steps, while the code enforces the process.

---

## Documentation

- **Governed Sequencing** -- The "Golden Path" for multi-step agents  
  Learn how to use `ControlPlane`, `Step`, and `GlobalData` to build deterministic agents that never skip a step.
  ```python
  # See examples/governed_sequencing_agent.py
  ```

- **Universal Onboarding** -- How to connect any API or CLI tool  
  Onboard OpenAPI, GraphQL, or CLI tools. The system generates both MCP and CLI representations.
  
- **Self-Healing Engine** -- OWL ontologies + ML explained  
  How schema drift is detected and fixed in real-time. Coveres ontology mapping and ML reconciliation.

- **MCP + CLI Hybrid Routing** -- When each backend is chosen  
  Details on performance-weighted routing and how to force a backend for debugging.

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
