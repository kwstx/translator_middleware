# MiroFish Swarm Bridge for Engram

We’re building a native MiroFish Swarm Bridge for Engram — a lightweight, one-line router that lets AI agents (like those from OpenClaw or Clawdbot ecosystems) instantly pipe inter-agent messages, live external data (news headlines, real-time prices, sentiment scores), and trading signals directly into a running MiroFish swarm simulation. By connecting to a user’s own local or self-hosted MiroFish instance (running on their machine with their personal LLM API key), the bridge injects clean, semantically preserved context into the swarm’s seed text and God’s-eye variables, keeps thousands to millions of digital agents perfectly synchronized without drift, and pipes the resulting high-fidelity swarm predictions back to the originating agent for immediate execution — turns simple prediction-market bots into powerful, real-time predict + execute hybrid systems in seconds.

## Getting Started

To initialize the bridge during development, follow these steps:

1.  **Ensure Node.js 18+** is installed on your system.
2.  **Install dependencies**: Run `npm install` in the root directory.
3.  **Launch the Services**:
    - **Docker (Recommended)**: Run `docker compose up -d --build`. This starts all components, including the backend bridge and the playground frontend.
    - **Individual Components**: Alternatively, run `npm run dev` in the root directory.
4.  **Verification**:
    - The **Backend REST service** (MiroFish Bridge) will be accessible at `http://localhost:5001`.
    - The **Frontend Playground** will run on port `3000`.

This setup is optimized for external piping discovery operations during your development testing only.

## Step 9 — Router Integration

The MiroFish bridge is now fully wired into the core Engram message routing system.  When the **target platform** equals `mirofish`, the Orchestrator automatically normalises the payload through the existing translation layer and forwards it to the user's MiroFish swarm instance.

### Prerequisites

> **Users must first launch their own MiroFish instance** with a valid `LLM_API_KEY` configured in its `.env` file.  Without a running MiroFish backend the router will return a connection error.

### One-Line Configuration (TypeScript — OpenClaw / Clawdbot)

```ts
import { engram } from './mirofish-bridge';

// Immediately send a message
const report = await engram.routeTo('mirofish', {
  swarmId: 'prediction-market-1',
  mirofishBaseUrl: 'http://localhost:5001',
}, 'Analyse upcoming ETH merge impact');

// Or get a re-usable sender
const sendToSwarm = await engram.routeTo('mirofish', {
  swarmId: 'prediction-market-1',
  mirofishBaseUrl: 'http://localhost:5001',
});
const report2 = await sendToSwarm('Another inter-agent message');
```

### Python Backend — Orchestrator Routing

On the server side, passing `target_protocol="mirofish"` to the Orchestrator triggers the same bridge:

```python
from app.messaging.orchestrator import Orchestrator

orchestrator = Orchestrator()

# Sync path (e.g. from TaskWorker):
result = orchestrator.handoff(
    source_message={
        "intent": "predict",
        "content": "BTC 7-day forecast",
        "metadata": {
            "swarmId": "crypto-swarm",
            "mirofishBaseUrl": "http://localhost:5001",
            "numAgents": 500,
            "externalData": {"prices": [{"symbol": "BTC/USD", "price": "64200"}]}
        }
    },
    source_protocol="A2A",
    target_protocol="mirofish",
)

# Async path (e.g. from a FastAPI route):
result = await orchestrator.handoff_async(
    source_message=payload,
    source_protocol="MCP",
    target_protocol="mirofish",
)
```

### Environment Configuration

Add these to your `.env` (all optional — sensible defaults are applied):

| Variable | Default | Description |
|---|---|---|
| `MIROFISH_BASE_URL` | `http://localhost:5001` | MiroFish service base URL |
| `MIROFISH_DEFAULT_NUM_AGENTS` | `1000` | Default swarm size |
| `MIROFISH_DEFAULT_SWARM_ID` | `default` | Default swarm identifier |

### Semantic Fidelity

All payloads are run through the existing `TranslatorEngine` translation layer before injection.  This means any A2A, MCP, or ACP message is normalised to MCP format first, preserving semantic fidelity regardless of the originating protocol.

### How It Works

1. The caller passes `target_protocol="mirofish"` (case-insensitive) to the Orchestrator.
2. The Orchestrator detects the `MIROFISH` target and short-circuits the normal protocol graph.
3. `pipe_to_mirofish_swarm()` (in `app/services/mirofish_router.py`) normalises the payload via `TranslatorEngine`.
4. The normalised payload is POSTed to the user's MiroFish `/api/simulation/start` endpoint.
5. The compiled simulation report is returned as the `HandoffResult.translated_message`.

### File Map

| File | Purpose |
|---|---|
| `app/services/mirofish_router.py` | Python-side router — normalises + HTTP POST to MiroFish |
| `app/messaging/orchestrator.py` | Orchestrator conditional: `if tgt == "MIROFISH"` |
| `app/core/config.py` | `MIROFISH_BASE_URL`, `MIROFISH_DEFAULT_NUM_AGENTS`, `MIROFISH_DEFAULT_SWARM_ID` |
| `playground/src/mirofish-bridge.ts` | TypeScript `engram.routeTo('mirofish', ...)` one-liner |
| `playground/src/engram-sdk.ts` | Engram SDK config loader + adapter registry |
| `tests/integration/test_mirofish_e2e.py` | Step 10 E2E test — full predict + execute hybrid loop |

## Step 10 — End-to-End Testing

Thorough E2E validation of the completed bridge.  The test spins up a **mock MiroFish backend**, creates a sample OpenClaw agent, sends a real-shaped trading signal with live context data through the Orchestrator, and verifies every layer of the pipeline.

### What Gets Verified

| # | Check | Detail |
|---|---|---|
| 1 | Mock MiroFish Instance | A standalone FastAPI server emulates `POST /api/simulation/start` on a random free port |
| 2 | OpenClaw Agent Creation | A `ClawBot-Alpha` agent is instantiated with the builder pattern |
| 3 | Trading Signal Message | Builds an A2A-envelope message with prices (BTC, ETH, SOL), sentiment (X + Reuters), and headlines |
| 4 | Orchestrator Routing | `handoff_async(target_protocol="mirofish")` routes through `pipe_to_mirofish_swarm` |
| 5 | Semantic Fidelity | Asserts every price, sentiment score, and headline arrives at MiroFish without drift |
| 6 | Prediction Return | Validates the compiled simulation report flows back into the `HandoffResult` |
| 7 | Trade Execution | Simulates placing a Polymarket trade from the `execution_recommendation` output |
| 8 | Cycle Timing | Asserts the full loop completes in **< 60 seconds** |

### Prerequisites

> **The test does NOT require a live MiroFish instance or LLM key.**  It uses a built-in mock server so any developer can run it locally without extra setup.

### Running the Test

**Standalone** (no pytest needed):

```bash
$env:PYTHONPATH="."
python tests/integration/test_mirofish_e2e.py
```

**Via pytest** (picked up by `pytest -m integration`):

```bash
pytest tests/integration/test_mirofish_e2e.py -v
```

### Against a Real MiroFish Instance

To validate against your own MiroFish instance instead of the mock:

1. Launch your MiroFish instance with your `LLM_API_KEY` in its `.env`.
2. Set `MIROFISH_BASE_URL` in `translator_middleware/.env` to point to your instance.
3. Modify the test to skip mock server startup and use your real URL.

### Sample Output

```
======================================================================
  1/8  Launching mock MiroFish instance
======================================================================
  ✓ Mock MiroFish running at http://127.0.0.1:54321
  ✓ Health probe OK
  ...
======================================================================
  8/8  Cycle timing
======================================================================
  Total cycle time: 1.24s
  ✓ Under 60-second target ✓
  ...
🎉  MiroFish Bridge E2E test PASSED
```

## Step 11 - Native Plugin Packaging (Drop-In Engram Adapter)

The final step is packaging the MiroFish bridge as a **drop-in plugin** inside the Engram distribution. We do that by updating the main configuration loader to auto-register `pipeToMiroFishSwarm` under a new `mirofish` adapter key, and exposing it as a one-line toggle in the SDK or dashboard.

### SDK Config Loader (One-Line Toggle)

```ts
import { loadEngramConfig } from './engram-sdk';

const engram = loadEngramConfig({
  enableMiroFishBridge: true,
  mirofishBaseUrl: 'http://localhost:5001',
  swarmId: 'prediction-market-1',
  defaultAgentCount: 1000,
});

// Later, anywhere in your agent flow:
const report = await engram.routeTo(
  'mirofish',
  'Analyse upcoming ETH merge impact',
);
```

### Required Setting

- `mirofishBaseUrl` is **required** when `enableMiroFishBridge: true`. The loader will throw an error if it is missing.

### Optional Settings

- `swarmId` (default: `default`)
- `defaultAgentCount` (default: `1000`)

### Onboarding Requirement (No Shared Keys)

Every user must run **their own** MiroFish instance locally and supply **their personal LLM key** in that instance's `.env`:

1. Start MiroFish locally:
   - `npm run dev`
   - or `docker compose up -d`
2. Add your personal LLM key to the MiroFish `.env` as `LLM_API_KEY=...`

This ensures any builder following the original Polymarket guide can activate **full swarm synchronization instantly**, without writing additional code or sharing keys with you.
