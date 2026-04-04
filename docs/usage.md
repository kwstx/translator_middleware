# Getting Started & Usage Guide

Semantic Bridge provides a universal bridge for AI agents, tools, and third-party APIs. This guide provides the technical implementation details for operating seamless cross-protocol agent handoffs.

---

## 🛠️ Installation

### Using Docker (Recommended)
The easiest way to run the middleware with its dependencies (Neon, Redis, Prometheus) is using Docker Compose:

```bash
docker compose up --build
```

### Local Development
To install directly for local development (no background services required):

```bash
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
```

---

## 🚀 Quickstart Example

Initialize the core engine to translate a message and route it via the **Orchestrator**.

```python
import asyncio
from app.core.translator import TranslatorEngine
from app.core.orchestrator import Orchestrator

async def main():
    # 1. Initialize the components
    translator = TranslatorEngine()
    orchestrator = Orchestrator()

    # 2. Translate a payload between protocols
    try:
        translated = translator.translate(
            source_message={"payload": {"intent": "schedule_meeting"}},
            source_protocol="mcp",
            target_protocol="a2a"
        )
        print("✅ Translation successful:", translated)
        
        # 3. Handoff via Orchestrator
        # Triggers: Translation -> Semantic Resolution -> Task Enqueue
        success = await orchestrator.handoff_async(
            source_message=translated,
            source_protocol="a2a",
            target_protocol="acp" # Multi-hop is handled internally!
        )
        
        if success:
            print("🚀 Action Permitted: Message routed to target agent.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📚 Core API Reference

### `TranslatorEngine`
The primary protocol mapping engine for structural "envelope" conversion.
-   **`translate(source_message: dict, source_protocol: str, target_protocol: str)`**:
    -   Applies `ProtocolVersionDelta` upgrades first.
    -   Handles multi-hop translation via the `ProtocolGraph`.
    -   *Raises*: `ProtocolMismatchError` if translation is impossible.

### `SemanticMapper`
The engine for resolving data schema disparities (Data Silos).
-   **`DataSiloResolver(source_data: dict, target_schema: dict)`**:
    -   Applies PyDatalog rule renames.
    -   Falls back to OWL ontology resolution.
    -   Triggers ML prediction if confidence is low.

### `DiscoveryService`
Manages the `AgentRegistry` and finds compatible collaborators.
-   **`get_collaborators(required_capability: str)`**:
    -   Calculates compatibility scores based on protocols.
    -   *Returns*: List of agent IDs with scores above `0.7`.

### `Orchestrator`
Handles the transaction lifecycle, state persistence, and task queue.
-   **`handoff_async(source_message: dict, ...)`**:
    -   Persists a `Task` to PostgreSQL.
    -   Returns a `HandoffResult` with a cryptographic `execution_proof`.

---

## 🔒 Security: The EAT System

The **Engram Access Token (EAT)** is the project’s security backbone.

-   **Stateless but Revocable**: JTI-based revocation in Redis (optional).
-   **Scoped Permissions**:
    - `translate:a2a`: Access to the protocol translator.
    - `discovery:read`: Access to search for collaborators.
    - `tools:*`: Recursive access to all tool connectors.

### Generate a JWT locally
```bash
python scripts/generate_token.py --secret $env:AUTH_JWT_SECRET --scope translate:a2a
```

---

## 📈 Monitoring & Observability

You can view translation traffic and metrics via Prometheus/Grafana:
- **Metrics**: `GET /metrics`
- **Dashboard**: `http://localhost:3000` (Grafana)
- **FastAPI Docs**: `http://localhost:8000/docs`

---

**Version 0.1.0** | *Universal Onboarding Guide*
