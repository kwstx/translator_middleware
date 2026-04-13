"""
Example: Strict Governed Orchestration.

This example demonstrates the new 'drive' orchestrator in the ControlPlane.
The orchestrator drives the workflow turn-by-turn, supplying only validated 
tools for each step, executing the chosen tool, writing results to GlobalData, 
and automatically advancing the state.
"""

from engram_sdk import (
    EngramSDK, 
    ControlPlane, 
    get_global_data,
    ToolCall,
    PROCESS_IDENTITY_TOOL,
    VERIFY_CLEARANCE_TOOL,
    GENERATE_REPORT_TOOL,
    process_raw_identification,
    verify_security_clearance,
    generate_access_report
)

def mock_llm_orchestration_fn(step_name, scope, system_prompt):
    """
    Simulates an LLM that only returns a ToolCall.
    The orchestrator handles the execution and state transitions.
    """
    print(f"\n--- [LLM Orchestration Turn] Step: {step_name} ---")
    print(f"[LLM] System Prompt: {system_prompt}")
    print(f"[LLM] Active Tools in Scope: {scope.tools}")
    
    if step_name == "ingest_raw":
        # Simulate LLM choosing to process raw identification
        # In a real scenario, this would be the model's tool_call response.
        return ToolCall(name="process_raw_identification")

    elif step_name == "verify_security":
        # Simulate LLM choosing to verify clearance
        return ToolCall(name="verify_security_clearance")

    elif step_name == "final_report":
        # Simulate LLM choosing to generate report
        return ToolCall(name="generate_access_report")
    
    return ToolCall(name="unknown")

def main():
    # Setup SDK
    sdk = EngramSDK(agent_id="orchestrated_agent")
    
    # 1. Setup Control Plane and Register Tool Handlers
    cp = ControlPlane(sdk)
    cp.register_tool_handler("process_raw_identification", process_raw_identification)
    cp.register_tool_handler("verify_security_clearance", verify_security_clearance)
    cp.register_tool_handler("generate_access_report", generate_access_report)

    # 2. Register tool definitions in the SDK for discovery/scope
    sdk.tools.register_many([
        PROCESS_IDENTITY_TOOL,
        VERIFY_CLEARANCE_TOOL,
        GENERATE_REPORT_TOOL
    ])

    # 3. Define the Governed Workflow
    cp.add_step(
        name="ingest_raw",
        tools=["process_raw_identification"],
        next_step="verify_security",
        description="Receive raw text and extract identity components into state."
    )

    cp.add_step(
        name="verify_security",
        tools=["verify_security_clearance"],
        next_step="final_report",
        preconditions=["user_email"],
        description="Verify clearance levels based on the extracted email."
    )

    cp.add_step(
        name="final_report",
        tools=["generate_access_report"],
        next_step=None,
        preconditions=["clearance_level", "user_name"],
        description="Generate a unified access report from validated state."
    )

    # 4. Initial data setup (outside the turn loop)
    get_global_data().set("raw_input", "System Administrator <admin@engram.io>")
    
    print("Starting Governed Orchestration...")
    
    try:
        # The 'drive' method is the strict orchestrator
        final_global_state = cp.drive(
            initial_step="ingest_raw",
            inference_fn=mock_llm_orchestration_fn
        )
        
        print("\n" + "="*40)
        print("ORCHESTRATION COMPLETE")
        print("Final Report in GlobalData:")
        print(final_global_state.get('final_report'))
        print("="*40)
        
    except Exception as e:
        print(f"\nOrchestration Aborted: {e}")

if __name__ == "__main__":
    main()
