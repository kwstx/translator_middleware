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
