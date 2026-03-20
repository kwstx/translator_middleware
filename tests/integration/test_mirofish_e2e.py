"""
Step 10 — MiroFish Bridge End-to-End Test
==========================================
Validates the full predict-plus-execute hybrid loop:

1. Spins up a **mock MiroFish backend** on a free port that mimics
   ``POST /api/simulation/start`` (the endpoint a real user's self-hosted
   MiroFish would expose).
2. Registers a sample *OpenClaw*-style agent connected to Engram.
3. Sends a test inter-agent message containing a **trading signal** with
   live price / sentiment / headline data.
4. Routes the message through the Orchestrator (``target_protocol="mirofish"``)
   -> ``pipe_to_mirofish_swarm`` -> mock MiroFish.
5. Asserts **zero semantic drift**: the mock MiroFish received every field
   injected by the caller, verifying that the swarm sees the exact piped data.
6. Confirms the **simulation report flows back** correctly to the originating
   agent (the HandoffResult carries ``compiled_report`` with actionable output).
7. Simulates an **execution action** (placing a Polymarket trade) based on
   the returned prediction.
8. Times the entire cycle and asserts it completes in **under 60 seconds**.

Run::

    $env:PYTHONPATH="."
    python tests/integration/test_mirofish_e2e.py
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────────
# 1.  MOCK MIROFISH BACKEND
# ──────────────────────────────────────────────────────────────────
# Captures every request body so we can assert semantic fidelity later.

_captured_requests: List[Dict[str, Any]] = []

mock_mirofish_app = FastAPI(title="Mock MiroFish Instance")


class SimulationStartRequest(BaseModel):
    seedText: str
    numAgents: int = 1000
    swarmId: str = "default"
    godsEyeVariables: Optional[Dict[str, Any]] = None


@mock_mirofish_app.post("/api/simulation/start")
async def mock_simulation_start(req: SimulationStartRequest):
    """Simulates a MiroFish ``simulation/start`` response.

    Returns a compiled report containing a synthetic prediction that the
    caller can immediately act on (e.g. place a Polymarket trade).
    """
    body = req.model_dump()
    _captured_requests.append(body)

    # Deterministic synthetic prediction for verification.
    compiled_report = {
        "status": "completed",
        "swarm_id": req.swarmId,
        "agents_used": req.numAgents,
        "consensus_prediction": {
            "direction": "bullish",
            "confidence": 0.87,
            "target_price": 68500.00,
            "timeframe": "7d",
            "reasoning": (
                "Swarm consensus from {} agents indicates bullish momentum "
                "driven by ETF inflows and positive sentiment."
            ).format(req.numAgents),
        },
        "execution_recommendation": {
            "action": "BUY",
            "market": "polymarket",
            "asset": "BTC-7D-UP",
            "size_pct": 15,
            "confidence_threshold_met": True,
        },
        "seed_echo": req.seedText,  # echo back for drift check
        "gods_eye_echo": req.godsEyeVariables,  # echo back for drift check
    }

    return compiled_report


async def _start_mock_mirofish(host: str = "127.0.0.1", port: int = 0):
    """Start the mock server on a random free port and return it."""
    config = uvicorn.Config(
        mock_mirofish_app,
        host=host,
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)

    # Let uvicorn bind to a free port, then report it back.
    # We create sockets manually to discover the port.
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, 0))
    actual_port = sock.getsockname()[1]
    sock.close()

    config.port = actual_port

    task = asyncio.create_task(server.serve())
    # Give the server a moment to bind.
    await asyncio.sleep(0.5)
    return server, task, actual_port


# ──────────────────────────────────────────────────────────────────
# 2.  SIMULATED OPENCLAW AGENT
# ──────────────────────────────────────────────────────────────────

class OpenClawAgent:
    """Minimal stand-in for an OpenClaw / Clawdbot agent."""

    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.received_reports: List[Dict[str, Any]] = []
        self.executed_trades: List[Dict[str, Any]] = []

    def build_trading_signal_message(
        self,
        signal_text: str,
        prices: List[Dict[str, Any]],
        sentiments: List[Dict[str, Any]],
        headlines: List[str],
        swarm_id: str,
        mirofish_base_url: str,
        num_agents: int = 500,
    ) -> Dict[str, Any]:
        """Build an A2A-style message containing a trading signal + live data."""
        return {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "protocol": "A2A",
            "intent": "predict",
            "content": signal_text,
            "payload": {
                "signal": signal_text,
                "asset": "BTC/USD",
            },
            "data": {
                "task": "prediction_market_forecast",
            },
            "metadata": {
                "swarmId": swarm_id,
                "mirofishBaseUrl": mirofish_base_url,
                "numAgents": num_agents,
                "externalData": {
                    "currentPrices": prices,
                    "sentimentScores": sentiments,
                    "latestNewsHeadlines": headlines,
                },
            },
        }

    def receive_report(self, report: Dict[str, Any]) -> None:
        self.received_reports.append(report)

    def execute_trade(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate placing a Polymarket trade based on the swarm output."""
        trade = {
            "trade_id": f"trade-{uuid.uuid4().hex[:8]}",
            "market": recommendation.get("market", "polymarket"),
            "asset": recommendation.get("asset", "UNKNOWN"),
            "action": recommendation.get("action", "HOLD"),
            "size_pct": recommendation.get("size_pct", 0),
            "status": "EXECUTED",
            "timestamp": time.time(),
        }
        self.executed_trades.append(trade)
        return trade


# ──────────────────────────────────────────────────────────────────
# 3.  E2E TEST FLOW
# ──────────────────────────────────────────────────────────────────

_SEPARATOR = "=" * 70


def _print_section(title: str):
    print(f"\n{_SEPARATOR}")
    print(f"  {title}")
    print(_SEPARATOR)


async def run_e2e():
    """Full predict + execute hybrid loop validation."""
    _captured_requests.clear()
    cycle_start = time.perf_counter()

    # ── 1. Launch mock MiroFish ──────────────────────────────────
    _print_section("1/8  Launching mock MiroFish instance")
    server, server_task, mirofish_port = await _start_mock_mirofish()
    mirofish_url = f"http://127.0.0.1:{mirofish_port}"
    print(f"  [OK] Mock MiroFish running at {mirofish_url}")

    try:
        # Quick health sanity check.
        async with httpx.AsyncClient(timeout=5) as hc:
            probe = await hc.post(
                f"{mirofish_url}/api/simulation/start",
                json={"seedText": "probe", "numAgents": 1, "swarmId": "health"},
            )
            assert probe.status_code == 200, f"Mock MiroFish probe failed: {probe.status_code}"
        print("  [OK] Health probe OK")

        # ── 2. Instantiate OpenClaw agent ────────────────────────
        _print_section("2/8  Creating sample OpenClaw agent")
        agent = OpenClawAgent(agent_id=str(uuid.uuid4()), name="ClawBot-Alpha")
        print(f"  [OK] Agent '{agent.name}' created  (id={agent.agent_id})")

        # ── 3. Build the trading signal message ──────────────────
        _print_section("3/8  Building inter-agent trading signal")
        test_prices = [
            {"symbol": "BTC/USD", "price": "64200.50", "currency": "USD"},
            {"symbol": "ETH/USD", "price": "3410.75", "currency": "USD"},
            {"symbol": "SOL/USD", "price": "142.30", "currency": "USD"},
        ]
        test_sentiments = [
            {"source": "X", "score": 0.72, "label": "Bullish", "confidence": "0.81"},
            {"source": "Reuters", "score": 0.44, "label": "Bullish", "confidence": "0.65"},
        ]
        test_headlines = [
            "Bitcoin hits new local high amid ETF inflows",
            "Ethereum Shanghai upgrade shows positive network growth",
            "Polymarket sees record volume on crypto prediction markets",
        ]

        swarm_id = "prediction-market-btc-7d"
        signal_text = (
            "BTC 7-day forecast: analyse ETF flow impact and on-chain accumulation "
            "patterns. Provide directional confidence for Polymarket execution."
        )

        source_message = agent.build_trading_signal_message(
            signal_text=signal_text,
            prices=test_prices,
            sentiments=test_sentiments,
            headlines=test_headlines,
            swarm_id=swarm_id,
            mirofish_base_url=mirofish_url,
            num_agents=500,
        )
        print(f"  [OK] Message built (id={source_message['id']})")
        print(f"    Signal : {signal_text[:80]}...")
        print(f"    Prices : {len(test_prices)} assets")
        print(f"    Swarm  : {swarm_id}  ({500} agents)")

        # ── 4. Route through the Orchestrator ────────────────────
        _print_section("4/8  Routing through Orchestrator -> MiroFish bridge")
        # Clear probe request from captured list.
        _captured_requests.clear()

        from app.messaging.orchestrator import Orchestrator

        orchestrator = Orchestrator()
        result = await orchestrator.handoff_async(
            source_message=source_message,
            source_protocol="A2A",
            target_protocol="mirofish",
        )
        print(f"  [OK] Handoff complete")
        print(f"    Route       : {' -> '.join(result.route)}")
        print(f"    Total weight: {result.total_weight}")

        # ── 5. Verify semantic fidelity (no drift) ───────────────
        _print_section("5/8  Verifying semantic fidelity (zero drift)")
        assert len(_captured_requests) == 1, (
            f"Expected exactly 1 request to mock MiroFish, got {len(_captured_requests)}"
        )
        captured = _captured_requests[0]

        # 5a. seedText must contain the signal text.
        seed = captured["seedText"]
        # The signal may have been part of a JSON-serialised payload or used as-is.
        # The important thing is the original signal content is present.
        assert signal_text in seed or "BTC 7-day forecast" in seed, (
            f"Signal text not found in seedText! seedText={seed[:200]}..."
        )
        print("  [OK] Signal text preserved in seedText")

        # 5b. godsEyeVariables must contain the external data verbatim.
        gods_eye = captured.get("godsEyeVariables")
        assert gods_eye is not None, "godsEyeVariables was not forwarded!"

        # Verify prices survived the round-trip.
        forwarded_prices = gods_eye.get("currentPrices", [])
        for expected in test_prices:
            match = [p for p in forwarded_prices if p["symbol"] == expected["symbol"]]
            assert len(match) == 1, f"Price for {expected['symbol']} not found in forwarded data"
            assert match[0]["price"] == expected["price"], (
                f"Price drift for {expected['symbol']}: "
                f"expected={expected['price']}, got={match[0]['price']}"
            )
        print(f"  [OK] All {len(test_prices)} prices forwarded without drift")

        # Verify sentiments.
        forwarded_sentiments = gods_eye.get("sentimentScores", [])
        assert len(forwarded_sentiments) == len(test_sentiments), (
            f"Sentiment count mismatch: {len(forwarded_sentiments)} != {len(test_sentiments)}"
        )
        for i, expected in enumerate(test_sentiments):
            actual = forwarded_sentiments[i]
            assert actual["source"] == expected["source"], f"Sentiment source drift at index {i}"
            assert float(actual["score"]) == expected["score"], f"Sentiment score drift at index {i}"
        print(f"  [OK] All {len(test_sentiments)} sentiment scores forwarded without drift")

        # Verify headlines.
        forwarded_headlines = gods_eye.get("latestNewsHeadlines", [])
        assert forwarded_headlines == test_headlines, "Headline drift detected!"
        print(f"  [OK] All {len(test_headlines)} headlines forwarded without drift")

        # 5c. numAgents and swarmId.
        assert captured["numAgents"] == 500, f"numAgents drift: {captured['numAgents']}"
        assert captured["swarmId"] == swarm_id, f"swarmId drift: {captured['swarmId']}"
        print(f"  [OK] numAgents={captured['numAgents']}, swarmId={captured['swarmId']} -- correct")

        # ── 6. Validate prediction output flows back ─────────────
        _print_section("6/8  Validating prediction output returned to agent")
        report = result.translated_message
        agent.receive_report(report)

        assert report["status"] == "completed", f"Unexpected status: {report['status']}"
        prediction = report["consensus_prediction"]
        assert "direction" in prediction, "Missing direction in prediction"
        assert "confidence" in prediction, "Missing confidence in prediction"
        assert "target_price" in prediction, "Missing target_price in prediction"
        assert prediction["confidence"] >= 0.80, (
            f"Confidence below threshold: {prediction['confidence']}"
        )
        print(f"  [OK] Report received by agent '{agent.name}'")
        print(f"    Status     : {report['status']}")
        print(f"    Direction  : {prediction['direction']}")
        print(f"    Confidence : {prediction['confidence']}")
        print(f"    Target     : ${prediction['target_price']:,.2f}")
        print(f"    Timeframe  : {prediction['timeframe']}")

        exec_rec = report.get("execution_recommendation", {})
        assert exec_rec.get("confidence_threshold_met") is True, (
            "Execution recommendation confidence threshold not met"
        )
        print(f"  [OK] Execution recommendation: {exec_rec['action']} "
              f"on {exec_rec['market']} ({exec_rec['asset']})")

        # ── 7. Simulate trade execution ──────────────────────────
        _print_section("7/8  Executing Polymarket trade from prediction")
        trade = agent.execute_trade(exec_rec)
        assert trade["status"] == "EXECUTED", f"Trade failed: {trade}"
        print(f"  [OK] Trade EXECUTED")
        print(f"    Trade ID : {trade['trade_id']}")
        print(f"    Market   : {trade['market']}")
        print(f"    Asset    : {trade['asset']}")
        print(f"    Action   : {trade['action']}")
        print(f"    Size     : {trade['size_pct']}%")

        # ── 8. Timing assertion ──────────────────────────────────
        cycle_end = time.perf_counter()
        elapsed = cycle_end - cycle_start
        _print_section("8/8  Cycle timing")
        print(f"  Total cycle time: {elapsed:.2f}s")
        assert elapsed < 60.0, f"Cycle exceeded 60s limit: {elapsed:.2f}s"
        print(f"  [OK] Under 60-second target")

        # ── Summary ──────────────────────────────────────────────
        _print_section("E2E SUMMARY")
        print("  All checks passed:")
        print("    [OK] Mock MiroFish instance launched & healthy")
        print("    [OK] OpenClaw agent created & message built")
        print("    [OK] Orchestrator routed A2A -> MIROFISH")
        print("    [OK] Semantic fidelity: prices, sentiments, headlines -- zero drift")
        print("    [OK] Prediction report returned to originating agent")
        print("    [OK] Polymarket trade executed from prediction output")
        print(f"    [OK] Full cycle completed in {elapsed:.2f}s (< 60s)")
        print()
        return True

    finally:
        # Shutdown mock server.
        server.should_exit = True
        try:
            await asyncio.wait_for(server_task, timeout=3.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            server_task.cancel()


# ──────────────────────────────────────────────────────────────────
# 4.  ALSO EXPOSE AS A PYTEST TEST
# ──────────────────────────────────────────────────────────────────

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_mirofish_e2e_full_loop():
    """Pytest wrapper so ``pytest -m integration`` discovers this test."""
    success = await run_e2e()
    assert success, "MiroFish E2E loop did not pass"


# ──────────────────────────────────────────────────────────────────
# 5.  STANDALONE RUNNER
# ──────────────────────────────────────────────────────────────────

async def main():
    try:
        success = await run_e2e()
        if success:
            print("\n>>>  MiroFish Bridge E2E test PASSED  <<<\n")
        else:
            print("\n!!!  MiroFish Bridge E2E test FAILED  !!!\n")
    except Exception as exc:
        print(f"\n!!!  MiroFish Bridge E2E test ERROR: {exc}  !!!\n")
        import traceback
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
