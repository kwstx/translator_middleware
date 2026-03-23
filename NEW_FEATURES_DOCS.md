# New Features Documentation: MiroFish Bridge & Trading Templates

This document provides in-depth information on the two latest additions to the Engram Agent Translator Middleware: the **MiroFish Swarm Bridge** and the **Multi-Platform Trading Semantic Templates**. These features transform Engram from a simple protocol translator into a powerful orchestration hub for predict-and-execute AI agent workflows.

---

## 🚀 MiroFish Swarm Bridge

### Overview
The **MiroFish Swarm Bridge** is a native integration layer that connects Engram's protocol translation pipeline directly to a running [MiroFish](https://github.com/666ghj/MiroFish) swarm-intelligence simulation. 

MiroFish is a next-generation AI prediction engine that spawns thousands of autonomous agents inside a high-fidelity digital world. The bridge allows any AI agent (OpenClaw, Clawdbot, or any agent using A2A/MCP/ACP) to:
1. Pipe inter-agent messages and live data (news, prices, sentiment) into a swarm.
2. Receive a compiled, high-fidelity prediction report back in a single call.
3. Turn a simple bot into a **real-time predict + execute hybrid system**.

### How It Works
When a message is routed with `target_protocol="mirofish"`, the following occurs:
1. **Normalization**: The source payload (A2A, ACP, etc.) is normalized to the MCP format via Engram's `TranslatorEngine`, preserving semantic fidelity.
2. **Context Enrichment**: The bridge automatically fetches live market data (via CCXT), sentiment scores (X/Reuters), and recent headlines.
3. **Injection**: The enriched data is injected as "God's-eye variables" and seed text into the MiroFish simulation.
4. **Execution**: The payload is `POST`ed to the user's local MiroFish `/api/simulation/start` endpoint.
5. **Reporting**: The resulting simulation report (predictions, consensus, recommendations) is returned to the agent.

### Prerequisites
> [!IMPORTANT]
> **Self-Hosted Infrastructure:** Users must run their own MiroFish instance. Engram connects to *your* local or self-hosted installation to ensure data privacy and use of your own LLM keys.

1.  **Set up MiroFish**:
    ```bash
    cd MiroFish
    cp .env.example .env
    ```
2.  **Configure LLM Keys**: Add your personal API keys (e.g., OpenAI, DashScope, ZEP) to the MiroFish `.env`.
3.  **Start MiroFish**: Run `npm run dev` or `docker compose up -d`. Verify it is running at `http://localhost:5001`.

### Configuration
Customize the bridge by adding these variables to your Engram `.env`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MIROFISH_BASE_URL` | `http://localhost:5001` | Base URL of your MiroFish service. |
| `MIROFISH_DEFAULT_NUM_AGENTS` | `1000` | Default agents to spawn per simulation. |
| `MIROFISH_DEFAULT_SWARM_ID` | `default` | Default identifier for parallel simulations. |

### Usage Examples

#### TypeScript SDK (One-Liner)
```ts
import { engram } from './mirofish-bridge';

const report = await engram.routeTo('mirofish', 'Analyse upcoming ETH merge impact', {
  swarmId: 'prediction-market-1',
  numAgents: 1000,
});
console.log(report); // Full simulation report
```

#### Python Backend
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

## 💸 Multi-Platform Trading Semantic Templates

### Overview
The **Trading Semantic Templates** module (`@engram/trading-templates`) provides drop-in, one-click adapters for major crypto exchanges, prediction markets, payment rails, and live data feeds. 

It allows agents to route a **single unified payload** across multiple platforms simultaneously without writing custom schema transformations or endpoint-specific code.

### Supported Platforms

| Category | Platforms | Key Integration |
| :--- | :--- | :--- |
| **Crypto** | Binance, Coinbase, Robinhood Crypto | CCXT / Direct REST |
| **Prediction** | Kalshi | Direct REST (trade-api/v2) |
| **Payments** | Stripe, PayPal | Payment Intents / Orders API |
| **Data Feeds** | X (Twitter), FRED, Reuters, Bloomberg | Search & Series APIs |

### How It Works
1.  **Unified Schema**: Agents construct a standard `tradeOrder`, `balanceQuery`, `paymentIntent`, or `feedRequest` object.
2.  **Semantic Normalization**: Engram maps these fields to the platform's native API (e.g., mapping `quantity` to `amount` or `size` as required).
3.  **Authentication**: Adapters use keys provided in your environment configuration, stored securely and never shared.
4.  **Response Unification**: Heterogeneous responses from different APIs are normalized back into a consistent structure for your agent to parse easily.

### Setup & Configuration
1.  **Install**:
    ```bash
    cd trading-templates && npm install
    ```
2.  **Configure `.env`**: Add your API keys for the platforms you intend to use (e.g., `BINANCE_API_KEY`, `KALSHI_TOKEN`, `STRIPE_SECRET_KEY`).
3.  **Enable in SDK**:
    ```ts
    engram.enableTradingTemplate('binance', {
      BINANCE_API_KEY: process.env.BINANCE_API_KEY,
      BINANCE_SECRET: process.env.BINANCE_SECRET,
    });
    ```

### Usage: The Predict-Execute Loop
The most powerful way to use these features is by combining them. Use a **Feed Request** to gather data, a **MiroFish Swarm** to predict, and a **Trading Template** to execute.

#### Example: Enriching a Trade with Live Data
```ts
const result = await engram.routeTo('binance', {
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
// result contains both the trade confirmation and the recent sentiment data
```

#### Example: Sequential Multi-Platform Execution
```ts
const order = {
  tradeOrder: { symbol: 'BTC/USDT', action: 'limit', quantity: 0.01, price: 60000 }
};

await engram.routeTo('binance', order);
await engram.routeTo('coinbase', order);
// The same 'order' object works for both platforms instantly
```

### Unified Schema Reference

| Payload Type | Key Fields |
| :--- | :--- |
| **Trade Order** | `symbol`, `action` (buy/sell/limit/market/balance), `quantity`, `price` |
| **Payment Intent** | `amount`, `currency`, `customerId` |
| **Feed Request** | `source` (x/fred/reuters/bloomberg), `query` |

---

## 🛡️ Testing & Validation
Both features come with comprehensive test suites to ensure reliability:
*   **MiroFish Bridge**: Includes an E2E test (`tests/integration/test_mirofish_e2e.py`) that uses a built-in mock server. It verifies signal construction, routing, and response timing (< 60s).
*   **Trading Templates**: Validated via `tests/integration/test_feeds_enrichment.js` and `test_trading_scenarios_e2e.js`, ensuring precise execution across diverse API structures.
