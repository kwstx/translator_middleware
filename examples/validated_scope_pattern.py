import asyncio
import os
import uuid
from engram_sdk import EngramSDK, Scope

async def main():
    """
    This example demonstrates the RECOMMENDED pattern for production agent workflows:
    Per-Step Validated Scopes.
    
    This pattern ensures:
    1. Zero Hallucination: The agent only sees tools relevant to its current state.
    2. Zero Drift: Schemas are validated against the backend BEFORE the agent uses them.
    3. State Ownership: The developer explicitly controls the state machine logic.
    """
    
    # Initialize the SDK
    # In production, use environment variables for sensitive credentials
    sdk = EngramSDK(
        base_url="http://localhost:8000/api/v1",
        email=os.getenv("ENGRAM_EMAIL", "dev@example.com"),
        password=os.getenv("ENGRAM_PASSWORD", "password")
    )
    
    # Authenticate and setup
    sdk.connect()
    try:
        sdk.login()
        sdk.generate_eat()
    except Exception as e:
        print(f"Auth configuration pending: {e}")

    print("\n--- [START] Production Recommended Pattern: Validated Scopes ---")

    # ---------------------------------------------------------
    # STEP 1: Research/Discovery Phase
    # ---------------------------------------------------------
    print("\nPhase 1: Research")
    # We create a scope that only allows discovery and search tools.
    # The 'with' block automatically triggers .validate() and .activate() on the server.
    with sdk.scope("research-phase", tools=["web_search", "get_company_info"]) as scope:
        print(f"  [√] Scope '{scope.name}' activated (ID: {scope.step_id})")
        print(f"  [√] Allowed Tools: {scope.tools}")
        
        # At this point, any tool discovery call (e.g. MCP list_tools) 
        # mediated by Engram will only return these two tools.
        print("  [Action] Agent is performing research...")
        
    # ---------------------------------------------------------
    # STEP 2: Action/Fulfillment Phase
    # ---------------------------------------------------------
    print("\nPhase 2: Fulfillment")
    # Once research is done, we explicitly move the agent to a different state.
    # This prevents the agent from accidentally leaking data or re-searching.
    with sdk.scope("fulfillment-phase", tools=["send_email", "create_ticket"]) as scope:
        print(f"  [√] Scope '{scope.name}' activated (ID: {scope.step_id})")
        print(f"  [√] Allowed Tools: {scope.tools}")
        
        print("  [Action] Agent is sending the summary email...")

    print("\n--- [END] Workflow Complete ---")

    # ---------------------------------------------------------
    # NOTE: Old Ambient Mode (Legacy/Prototyping Only)
    # ---------------------------------------------------------
    # The following usage is discouraged for production as it exposes ALL tools:
    # agents = sdk.tools.list() 
    # result = sdk.tools.execute("any_random_tool")
    # Use per-step scopes instead for robust, predictable agents.

if __name__ == "__main__":
    asyncio.run(main())
