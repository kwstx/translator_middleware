"""
Example: Governed Data Collection using Thick Controlled Tools.

This example demonstrates how an LLM can trigger complex data processing 
and validation by calling "zero-argument" tools. The tools directly 
interact with the GlobalData store, pulling state gathered in previous 
steps and writing back refined updates.
"""

from engram_sdk import (
    EngramSDK, 
    ControlPlane, 
    get_global_data,
    PROCESS_IDENTITY_TOOL,
    VERIFY_CLEARANCE_TOOL,
    GENERATE_REPORT_TOOL,
    process_raw_identification,
    verify_security_clearance,
    generate_access_report
)

def mock_inference_fn(step_name, scope, data):
    """
    Simulates an LLM in a governed sequence.
    The LLM doesn't need to 'collect' and 'pass' data, just trigger the right tools.
    """
    print(f"\n--- [LLM Turn] Step: {step_name} ---")
    
    if step_name == "ingest_raw":
        print("[LLM] User provided raw identity string. Storing it and triggering processing.")
        # Step 1: LLM stores raw input
        get_global_data().set("raw_input", data)
        # Step 2: LLM triggers the thick function (zero args)
        result = process_raw_identification()
        print(f"[Tool Result] {result}")
        return {"status": "identity_processed"}

    elif step_name == "verify_security":
        print("[LLM] Triggering security clearance check based on previously processed identity.")
        # Triggering another thick function (zero args)
        result = verify_security_clearance()
        print(f"[Tool Result] {result}")
        return {"status": "security_verified"}

    elif step_name == "final_report":
        print("[LLM] Compiling final report from all validated state.")
        # Triggering the final thick function (zero args)
        result = generate_access_report()
        print(f"[Tool Result] {result}")
        return {"status": "report_ready"}

    return {}

def main():
    # Setup SDK and Control Plane
    sdk = EngramSDK(agent_id="security_governor")
    cp = ControlPlane(sdk)
    
    # 1. Register the controlled tools
    sdk.tools.register_many([
        PROCESS_IDENTITY_TOOL,
        VERIFY_CLEARANCE_TOOL,
        GENERATE_REPORT_TOOL
    ])

    # 2. Define the Governed Workflow
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

    # 3. Execution
    raw_user_data = "Alice Admin <alice.admin@company.com>"
    print(f"Starting Governed Workflow for: {raw_user_data}")
    
    try:
        final_state = cp.run(
            initial_step="ingest_raw",
            initial_data=raw_user_data,
            inference_fn=mock_inference_fn
        )
        
        print("\n" + "="*40)
        print("WORKFLOW COMPLETE")
        print("Final Report in GlobalData:")
        print(get_global_data().get("final_report"))
        print("="*40)
        
    except Exception as e:
        print(f"\nWorkflow Aborted: {e}")

if __name__ == "__main__":
    main()
