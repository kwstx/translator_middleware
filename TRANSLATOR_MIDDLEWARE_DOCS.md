# Agent Translator Middleware Documentation
VERSION 0.1.0 (ALPHA) | LAST UPDATED: 2026-03-10

## Getting Started
Welcome to the Agent Translator Middleware. This guide provides the accurate technical implementation details for operating seamless cross-protocol agent handoffs (A2A, MCP, ACP) securely using the current codebase.

## Installation
Currently, the easiest way to run the middleware with its dependencies (Neon, Redis) is using Docker Compose:

```bash
docker compose up --build
```

To install directly for local development:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Minimal Example
Initialize the core engine to translate a message and route it via the Orchestrator. This demonstrates the core translation and routing capabilities using the actual SDK-like methods.

```python
import asyncio
from app.core.translator import TranslatorEngine
from app.core.orchestrator import Orchestrator

async def main():
    # 1. Initialize the components
    translator = TranslatorEngine()
    orchestrator = Orchestrator(db_url="postgresql://neon_connection_string")

    # 2. Translate a payload between protocols
    try:
        translated = translator.translate(
            source_message={"payload": {"intent": "schedule_meeting"}},
            source_protocol="mcp",
            target_protocol="a2a"
        )
        print("Translation successful:", translated)
        
        # 3. Handoff via Orchestrator
        # Triggers: Translation -> Semantic Resolution -> Neon Publish
        success = await orchestrator.publish(
            target_queue="agent-a-queue",
            message=translated
        )
        
        if success:
            print("Action Permitted: Message routed to target agent.")
        else:
            print("Action Denied/Failed in routing.")
            
    except Exception as e:
        print(f"Translation Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Core API Reference

### TranslatorEngine
The primary protocol mapping engine.

`translate(source_message, source_protocol, target_protocol) -> dict`
Applies specific mapping rules for protocol transformations.
- `source_message`: The original payload dict.
- `source_protocol`: Origin protocol (e.g., 'mcp').
- `target_protocol`: Destination protocol (e.g., 'a2a').
- *Returns*: Translated dictionary (e.g., converting keys from 'payload' to 'data_bundle'). Raises `ProtocolMismatchError` if translation is impossible.

### SemanticMapper
The engine for resolving meaning and data schema disparities.

`DataSiloResolver(source_data, target_schema) -> dict`
Uses JSON Schema validation to detect differences and resolves them.
- `source_data`: Input data dict.
- `target_schema`: Expected output schema.
- *Returns*: Transformed data, flattening nested objects and dynamically mapping fields using PyDatalog and OWL ontologies.

### DiscoveryService
Finds compatible agents based on capabilities.

`ping_agents() -> None`
Periodically pings registered agents via `aiohttp` to check availability.

`get_collaborators(required_capability) -> list`
Calculates compatibility using `(shared_protocols + mappable_protocols) / total_protocols`.
- *Returns*: List of agent IDs with scores above 0.7.

### Orchestrator
Handles asynchronous delivery and task chaining.

`publish(target_queue, message) -> bool`
Publishes translated messages to agent-specific Neon database queues (e.g., 'agent-uuid-queue').

## Architecture Overview
The system follows a strict orchestrational hierarchy for agent communication:

`Source Agent (A2A/MCP/ACP) -> API Gateway -> Protocol Mapper -> Semantic Resolver -> Orchestration Engine -> Target Agent`

**Current Modules implemented:**
- **Protocol Mapper**: Deterministic envelope translation (A2A ↔ MCP ↔ ACP).
- **Semantic Resolver**: Overcomes data silos via JSON schema flattening.
- **Discovery Service**: Registry state and compatibility scoring.
- **Orchestration Engine**: Asynchronous task handoffs via Neon Postgres.

## Error Handling
The middleware raises specialized exceptions:
- `ProtocolMismatchError`: Raised when a requested protocol pairing lacks a translation strategy.
- `AuthError`: HTTP 401/403 when JWT validation fails against expected `AUTH_ISSUER` and `AUTH_AUDIENCE`.
- `SemanticMappingError`: Failed to map payload structurally.

## Enforcement & Semantic Resolution
Integrating the Middleware requires understanding how the engine moves from identifying protocol differences to physically morphing data structures. This section covers two primary methods for data-level integration.

### The Data Silo Resolver
The strongest way to unify disparate agents is by passing payloads through the `DataSiloResolver`.

#### How it Works
1. **Intercept**: The resolver intercepts data mid-flight before hitting the `Orchestrator` queues.
2. **Evaluate Schema**: Uses JSON schema to detect disparities (e.g., checking if the nested `user_info.name` maps to a flat `profile.fullname`).
3. **Resolve**: Applies PyDatalog rule engine dynamically. If successful, data flows to the target. If failed, it logs and attempts an ML fallback.

## Strategic Implementation Tips
- **Set realistic compatibility thresholds**: The Discovery engine considers a score `> 0.7` as compatible. Monitor how often mismatched agents fail tasks and adjust your queries.
- **Handle routing paths**: Ensure you handle multi-hop routing paths properly across multiple translations.
- **Token management**: Standardize JWT deployment so external agents aren't blocked at the external Gateway.

## Development vs Production
- **Local Mode**: Run using `uvicorn app.main:app --reload` with a local SQLite/Memory state. Useful for direct HTTP testing.
- **Remote Mode**: Run via `docker compose up --build` which boots Redis (Semantic Cache) and connects to Neon configurations required for high-availability production routing.

## Monitoring & Observability
Adding real-time monitoring transforms the Middleware into an operations-ready platform.

### Operational Command Center
You can view the translation traffic via standard monitoring tools integrated via Docker Compose.

**Key Performance Metrics (Glossary)**
1. **Translation Latency (Histogram)**: Time taken to map and semantically translate a payload.
2. **Protocol Distribution (Counter)**: Metrics differentiating A2A, MCP, and ACP traffic loads.
3. **Compatibility Match Rate (Gauge)**: Shows the average compatibility scores across the `DiscoveryService`.

## Incident Response & Human-in-the-Loop
When to Intervene:
- **Translation Failures Plateau**: If `ProtocolMismatchError` rates spike, an ontology patch is needed. Investigate the "Top Incompatible Agents".
- **Latency Spikes**: Increased semantic mapping latency usually indicates complex nested JSON objects stalling the PyDatalog engine.
- **Orchestration Queues**: If Neon database queues stall, check if Target Agents are reachable despite `DiscoveryService` pings.

## Updated Architecture Flow
The system operates in a closed observation loop for multi-hop collaborations:

`Agent Action -> Middleware (Translating) -> Orchestrator Payload -> Semantic Adjustment Log -> Metrics Emitted -> Human Schema Adjustment`

## Integrating with MCP & NetworkX
To ensure multi-hop collaborations are efficient, the Orchestrator supports complex routing calculations.

### NetworkX Handoff Chaining
The Orchestrator utilizes NetworkX to model protocol compatibilities. For complex tasks spanning multiple agents (e.g., A2A -> MCP -> ACP), the engine calculates the shortest path for optimal mapping sequences to minimize data loss.

### AI Client Configuration for MCP
If using this middleware in front of a standard MCP Guard Server or Claude Desktop, point your MCP client to the middleware.

```json
{
  "mcpServers": {
    "translator-middleware": {
      "command": "python",
      "args": ["-m", "uvicorn", "app.main:app", "--port", "8000"]
    }
  }
}
```

**Strategic Tips for Documentation**
- **Highlight Semantic Importance**: Emphasize that protocol mapping envelope translation is incomplete without semantic ontology mapping.
- **Explain Compatibility Scores**: Detail how the Discovery service score effectively filters appropriate agents using `(shared_protocols + mappable_protocols) / total_protocols`.
- **Environment Isolation**: Mention that Redis is essential to cache ontology trees to prevent latency bottlenecks in `DataSiloResolver`.
