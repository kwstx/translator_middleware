# MiroFish Swarm Bridge

The **MiroFish Swarm Bridge** is a native integration layer that connects Semantic Bridge's protocol translation pipeline directly to a running [MiroFish](https://github.com/666ghj/MiroFish) swarm-intelligence simulation.

---

## 🚀 Overview
MiroFish is a next-generation AI prediction engine that spawns thousands of autonomous agents inside a high-fidelity digital world. The bridge allows any AI agent (A2A, MCP, ACP) to:
1.  Pipe inter-agent messages and live data (news, prices, sentiment) into a swarm.
2.  Receive a compiled, high-fidelity prediction report back in a single call.
3.  Turn a simple bot into a **real-time predict + execute hybrid system**.

---

## 🛠️ How It Works
When a message is routed with `target_protocol="mirofish"`, the following occurs:

1.  **Normalization**: The source payload is normalized to the MCP format via `TranslatorEngine`, preserving semantic fidelity.
2.  **Context Enrichment**: The bridge automatically fetches live market data (via CCXT), sentiment scores (X/Reuters), and recent headlines.
3.  **Injection**: The enriched data is injected as "God's-eye variables" and seed text into the MiroFish simulation.
4.  **Execution**: The payload is `POST`ed to the user's local MiroFish `/api/simulation/start` endpoint.
5.  **Reporting**: The resulting simulation report (predictions, consensus, recommendations) is returned to the agent.

---

## 🏗️ Setup & Configuration

> [!IMPORTANT]
> **Self-Hosted Infrastructure:** Users must run their own MiroFish instance. Engram connects to *your* local or self-hosted installation to ensure data privacy and use of your own LLM keys.

1.  **Set up MiroFish**:
    ```bash
    cd MiroFish
    cp .env.example .env
    ```
2.  **Configure LLM Keys**: Add your personal API keys (e.g., OpenAI, DashScope, ZEP) to the MiroFish `.env`.
3.  **Start MiroFish**: Run `npm run dev` or `docker compose up -d`. Verify it is running at `http://localhost:5001`.

### Configuration (Semantic Bridge `.env`)

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MIROFISH_BASE_URL` | `http://localhost:5001` | Base URL of your MiroFish service. |
| `MIROFISH_DEFAULT_NUM_AGENTS` | `1000` | Default agents to spawn per simulation. |
| `MIROFISH_DEFAULT_SWARM_ID` | `default` | Default identifier for parallel simulations. |

---

## 🚀 Usage Examples

### TypeScript SDK (One-Liner)
```ts
import { engram } from './mirofish-bridge';

const report = await engram.routeTo('mirofish', 'Analyse upcoming ETH merge impact', {
  swarmId: 'prediction-market-1',
  numAgents: 1000,
});
console.log(report); // Full simulation report
```

### Python Backend
```python
from app.messaging.orchestrator import Orchestrator

orchestrator = Orchestrator()
result = await orchestrator.handoff_async(
    source_message={"content": "BTC 7-day forecast"},
    source_protocol="A2A",
    target_protocol="mirofish"
)
print(result.translated_message)
```

---

## 🥊 Testing & Validation
The bridge includes an E2E test (`tests/integration/test_mirofish_e2e.py`) that uses a built-in mock server. It verifies signal construction, routing, and response timing (< 60s).

---

**Version 0.1.0** | *Swarm Prediction Bridge*
