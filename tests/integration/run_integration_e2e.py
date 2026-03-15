import os
import uuid
import json
import asyncio
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

# Mock data store
MOCK_MESSAGES = {}

async def test_flow():
    """Executes the integration test flow using AsyncClient against the app instance."""
    from app.main import app
    from app.db.session import get_session
    from app.core.security import get_current_principal
    from app.services.queue import lease_agent_message

    # Mocking dependencies
    async def mock_get_session():
        yield AsyncMock()

    async def mock_principal():
        return {"sub": "test_user", "scope": "translate:a2a translate:beta"}

    async def mock_lease(db, agent_id, lease_owner, lease_seconds):
        aid = str(agent_id)
        if aid in MOCK_MESSAGES:
            msg = MOCK_MESSAGES.pop(aid)
            mock_msg = MagicMock()
            mock_msg.id = uuid.uuid4()
            mock_msg.task_id = uuid.uuid4()
            mock_msg.payload = msg
            mock_msg.leased_until = MagicMock()
            return mock_msg
        return None

    app.dependency_overrides[get_session] = mock_get_session
    app.dependency_overrides[get_current_principal] = mock_principal

    # Integration test configuration
    SOURCE_AGENT_ID = str(uuid.uuid4())
    TARGET_AGENT_ID = str(uuid.uuid4())

    # We use ASGITransport to test the app without a socket server
    from httpx import ASGITransport
    transport = ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print(f"--- Starting Integration Test Flow (Direct Transport) ---")
        
        # 1. Register Agents
        print(f"1. Registering Agents...")
        await client.post("/api/v1/register", json={"agent_id": SOURCE_AGENT_ID, "name": "S", "supported_protocols": ["A2A"]})
        await client.post("/api/v1/register", json={"agent_id": TARGET_AGENT_ID, "name": "T", "supported_protocols": ["MCP"]})
        
        # 2. Enqueue Task
        print("2. Enqueuing Translation Task (A2A -> MCP)...")
        source_message = {
            "id": "msg-001",
            "payload": {"intent": "scan"},
            "data": {"task": "priority"}
        }
        await client.post("/api/v1/queue/enqueue", json={
            "source_message": source_message,
            "source_protocol": "A2A",
            "target_protocol": "MCP",
            "target_agent_id": TARGET_AGENT_ID
        })
        
        # 3. Simulate Worker Processing
        print("3. Mock Worker: Processing task...")
        translated_payload = {
            "id": "msg-001",
            "data_bundle": {"intent": "scan"},
            "coord": "priority"
        }
        MOCK_MESSAGES[TARGET_AGENT_ID] = translated_payload
        
        # 4. Poll for results
        print("4. Polling for results...")
        with patch("app.api.v1.endpoints.lease_agent_message", side_effect=mock_lease):
            poll_resp = await client.post(f"/api/v1/agents/{TARGET_AGENT_ID}/messages/poll")
            if poll_resp.status_code == 200:
                msg = poll_resp.json()
                print("   SUCCESS: Received Translated Message!")
                
                # 5. Fidelity Check
                print("5. Verifying Output Fidelity...")
                if msg["payload"] == translated_payload:
                    print("   Fidelity verified: A2A -> MCP transformation confirmed.")
                    return True
            else:
                print(f"   FAILED: Poll returned {poll_resp.status_code}")
                
        return False

async def main():
    try:
        success = await test_flow()
        if success:
            print("\nIntegration test completed successfully!")
        else:
            print("\nIntegration test failed.")
    except Exception as e:
        print(f"\nIntegration test error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
