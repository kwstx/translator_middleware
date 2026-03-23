# Website Documentation Update: New Features Guide

This document outlines the in-depth information that should be added to the official website documentation to cover the two new major features: **MiroFish Swarm Bridge** and **Trading Semantic Templates**. 

> [!TIP]
> Use these updates to emphasize Engram's evolution from a *protocol translator* to a complete *predict-and-execute orchestration platform*.

---

## 1. New Feature: MiroFish Swarm Bridge
**Location Suggestions**: Feature Pages, "Predictive AI" Section, or a dedicated "Integrations" page.

### Copy for Features Page
**Title**: Native MiroFish Swarm Syncing  
**Subtitle**: Turn any agent into a high-fidelity predictive powerhouse.  
**Description**:  
Connect your AI agents (OpenClaw, Clawdbot, etc.) directly to a running MiroFish swarm simulation. Automatically pipe inter-agent messages, live market prices, sentiment scores, and news headlines into a simulation of thousands of digital agents. Receive a compiled consensus report back in seconds to guide your agent's next move.

### Technical Guide (The "In-Depth" Part)
**How It Works (Under the Hood)**:
1. **Normalization**: The bridge intercepts outgoing messages and normalizes them into a standard MCP-compliant format, ensuring MiroFish can parse the intent regardless of the source protocol.
2. **Context Injection**: The `mirofish_router` fetches real-time data (CCXT prices, X sentiment) and injects them as "God's-eye variables" to ground the simulation in current reality.
3. **Execution**: The payload is securely POSTed to your self-hosted MiroFish instance (`POST /api/simulation/start`).
4. **Unified Output**: The final simulation report is returned to the originating agent as a structured `HandoffResult`.

**Prerequisites for Users**:
*   Self-host a [MiroFish instance](https://github.com/666ghj/MiroFish).
*   Add your personal LLM API keys to the MiroFish `.env`.
*   Connect Engram via your `MIROFISH_BASE_URL`.

**Example Code (TypeScript SDK)**:
```ts
import { engram } from './engram-sdk';

const report = await engram.routeTo('mirofish', 'Analyze BTC impact of Fed rate hike', {
  swarmId: 'macro-prediction',
  numAgents: 1500
});
```

---

## 2. New Feature: Trading Semantic Templates
**Location Suggestions**: "Solutions" Page, "Fintech/DeFi" Section, or Developer API Reference.

### Copy for Solutions Page
**Title**: Multi-Platform Trading Templates  
**Subtitle**: One-click adapters for exchanges, predictions, and payments.  
**Description**:  
Stop writing custom API wrappers for every exchange. Engram’s Trading Semantic Templates provide a unified schema for trades, balance queries, and payment intents. Route the exact same payload to Binance, Coinbase, Robinhood, Kalshi, Stripe, or PayPal instantly. We handle the semantic mapping, authentication, and response unification.

### Technical Guide (The "In-Depth" Part)
**The Unified Schema**:
We've collapsed different API structures into four simple objects:
*   **Trade Order**: Covers limit/market/stop orders plus balance checks.
*   **Payment Intent**: Standardizes Stripe and PayPal flows.
*   **Feed Request**: Fetches live data from X, FRED, Reuters, and Bloomberg.
*   **Rich Response**: Normalizes heterogeneous platform data into one consistent JSON structure.

**Setup & Security**:
*   **Zero Shared Keys**: API keys are stored in your local `.env` and never touch Engram's central servers (if self-hosted).
*   **Drop-in Adapters**: Use `npm install @engram/trading-templates` to add support to your agent.

**Example Code (Unified Multi-Platform Order)**:
```ts
// The same object works for both Binance and Coinbase
const order = {
  tradeOrder: { symbol: 'BTC/USDT', action: 'limit', quantity: 0.05, price: 63000 }
};

await engram.routeTo('binance', order);
await engram.routeTo('coinbase', order);
```

---

## 3. Updates for Existing Pages

### `ABOUT_PAGE.md` Additions
*   **Add under "The Solution"**: 
    - "Native MiroFish swarm syncing for massive-scale prediction simulations."
    - "One-click multi-platform trading and payment adapters via semantic templates."
*   **Add under "The Vision"**:
    - "We are moving beyond simple chat. We are building the nervous system for agents that *predict* using swarm intelligence and *execute* across global financial rails."

### `FAQ_PAGE.md` Additions
**Q: Does Engram see my trading API keys?**  
**A**: No. If you are self-hosting Engram (via Docker or local install), your keys stay in your local environment. Engram only provides the translation logic to use them.

**Q: Do I need a live MiroFish instance to use the bridge?**  
**A**: Yes. The bridge is a connector. You must run your own MiroFish instance (locally or on a server) and provide its URL to Engram.

**Q: Can I fetch market data without placing a trade?**  
**A**: Yes. Use the `feeds` adapter within the Trading Templates to fetch sentiment, news, and economic indicators (FRED, X, etc.) independently.

### `MISSION.md` Additions
*   **New Key Goal**: 
    - **Execute Everywhere**: Enable agents to move value across crypto, prediction markets, and fiat rails using a single semantic standard.
    - **Predict at Scale**: Standardize the path from agent intent to high-fidelity swarm simulations.

---

## 4. Documentation Mapping (Quick Reference)

| Topic | File/Page to Update | Depth |
| :--- | :--- | :--- |
| **Setup & Env** | `GETTING_STARTED.md` / `.env` Docs | Moderate (Add `MIROFISH_` vars) |
| **Logic/Workflow** | `ARCHITECTURE.md` | In-depth (Add `mirofish_router.py` flow) |
| **Developer API** | `API_REFERENCE.md` | High (Add `tradeOrder` and `feedRequest` schemas) |
| **Case Studies** | `USE_CASES.md` | High (Predict-Execute loop example) |
