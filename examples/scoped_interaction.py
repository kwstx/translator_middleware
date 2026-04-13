import asyncio
from engram_sdk import EngramSDK, Scope

async def main():
    # Initialize the SDK
    sdk = EngramSDK(base_url="http://localhost:8000/api/v1")
    
    # Define a scope for a specific turn
    # This explicit list of tools prevents the agent from 
    # hallucinating or using unauthorized tools in this state.
    search_scope = Scope(
        tools=["web_search", "get_company_info"],
        step_id="search-phase-1"
    )
    
    print(f"Created scope: {search_scope}")
    
    # In a real scenario, the developer would pass this scope 
    # to the agent orchestration layer or task submission.
    # For example:
    # await sdk.tasks.submit_task(
    #     command="Find recent news about Google",
    #     scope=search_scope
    # )
    
    # Later in the conversation, the developer can change the scope
    # to progress the state machine.
    action_scope = Scope(
        tools=["send_email", "write_to_slack"],
        step_id="report-phase-2"
    )
    
    print(f"Moved to next step with scope: {action_scope}")

if __name__ == "__main__":
    asyncio.run(main())
