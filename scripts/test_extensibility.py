import asyncio
import os
import sys
import uuid
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.getcwd())

# Set mock environment variables for security
os.environ["AUTH_JWT_SECRET"] = "debug-secret-123"
os.environ["AUTH_ISSUER"] = "https://auth.local/"
os.environ["AUTH_AUDIENCE"] = "translator-middleware"

from app.core.security import create_engram_access_token
from app.messaging.orchestrator import Orchestrator
from app.core.exceptions import HandoffAuthorizationError

async def test_extensibility():
    print("--- Testing Extensibility: Adding a New Tool (HYPOTHETICAL) ---")
    
    orchestrator = Orchestrator()
    user_id = str(uuid.uuid4())
    
    # 1. Test Success: User with HYPOTHETICAL permission
    permissions_with = {
        "HYPOTHETICAL": ["execute", "read"],
        "CLAUDE": ["execute"]
    }
    eat_success = create_engram_access_token(user_id, permissions_with)
    
    task_payload = {
        "coord": "analyze_data",
        "payload": {"dataset_id": "DS-99", "depth": "full"}
    }
    
    print("\nScenario 1: Authorized access to HYPOTHETICAL tool")
    try:
        result = await orchestrator.handoff_async(
            source_message=task_payload,
            source_protocol="MCP",
            target_protocol="HYPOTHETICAL",
            eat=eat_success
        )
        print(f"Result Status: {result.translated_message.get('status')}")
        print(f"Result Payload: {result.translated_message.get('payload')}")
        assert result.translated_message.get("status") == "success"
        assert "hypothetical_ack" in result.translated_message.get("payload", {}).get("coord", "")
        print("OK: Authorized access worked as expected.")
    except Exception as e:
        print(f"ERROR: Unexpected error in authorized scenario: {str(e)}")
        import traceback
        traceback.print_exc()

    # 2. Test Failure: User WITHOUT HYPOTHETICAL permission
    permissions_without = {
        "CLAUDE": ["execute"],
        "SLACK": ["read"]
    }
    eat_failure = create_engram_access_token(user_id, permissions_without)
    
    print("\nScenario 2: Unauthorized access to HYPOTHETICAL tool")
    try:
        await orchestrator.handoff_async(
            source_message=task_payload,
            source_protocol="MCP",
            target_protocol="HYPOTHETICAL",
            eat=eat_failure
        )
        print("ERROR: Hypothetical tool was accessed without permission!")
    except HandoffAuthorizationError as e:
        print(f"Caught Expected Error: {str(e)}")
        print("OK: Unauthorized access was correctly blocked.")
    except Exception as e:
        print(f"ERROR: Wrong exception type caught: {type(e).__name__}: {str(e)}")

    # 3. Test Broad 'TRANSLATOR' permission
    permissions_broad = {
        "TRANSLATOR": ["HYPOTHETICAL", "MCP:*"]
    }
    eat_broad = create_engram_access_token(user_id, permissions_broad)
    
    print("\nScenario 3: Access via broad TRANSLATOR scope")
    try:
        result = await orchestrator.handoff_async(
            source_message=task_payload,
            source_protocol="MCP",
            target_protocol="HYPOTHETICAL",
            eat=eat_broad
        )
        print(f"Result Status: {result.translated_message.get('status')}")
        assert result.translated_message.get("status") == "success"
        print("OK: Broad TRANSLATOR scope worked.")
    except Exception as e:
        print(f"ERROR: Unexpected error in broad scope scenario: {str(e)}")

    print("\n--- Extensibility Test Completed ---")

if __name__ == "__main__":
    asyncio.run(test_extensibility())
