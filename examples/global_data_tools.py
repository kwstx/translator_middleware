"""
Example demonstrating the model interacting with the GlobalData store via tool calls.
This ensures the model never holds raw state directly, but instead treats the 
GlobalData store as its memory bank.
"""

from engram_sdk import EngramSDK, ControlPlane
from engram_sdk.global_data import store_data, retrieve_data
import json

def mock_inference_fn(step_name, scope, data, system_prompt):
    """
    Simulates an LLM that uses tool calls to manage its memory.
    """
    print(f"\n[LLM Turn] Step: {step_name}")
    print(f"System Prompt: {system_prompt}")
    print(f"Allowed Tools: {scope.tools}")
    
    if step_name == "collect_info":
        # Simulate LLM deciding to store data
        print("[LLM Logic] Decided to store user preference in GlobalData.")
        store_data("user_theme", "dark_mode")
        return {"status": "preference_stored"}
    
    elif step_name == "use_info":
        # Simulate LLM deciding to retrieve data
        print("[LLM Logic] Retrieving user preference from GlobalData.")
        theme = retrieve_data("user_theme")
        print(f"[LLM Logic] Found theme: {theme}")
        return {"result": f"Applied {theme} to the dashboard."}
    
    return {}

def main():
    sdk = EngramSDK(agent_id="memory_bot")
    cp = ControlPlane(sdk)
    
    # Define a workflow where information is stored in one step and used in another
    cp.add_step(
        name="collect_info",
        tools=["store_data"],
        next_step="use_info",
        description="Write state to the global store."
    )
    
    cp.add_step(
        name="use_info",
        tools=["retrieve_data"],
        next_step=None,
        preconditions=["user_theme"],
        description="Read state from the global store."
    )
    
    print("Starting GlobalData Tool Interaction Sequence...")
    try:
        final_result = cp.run(
            initial_step="collect_info",
            initial_data="Getting started.",
            inference_fn=mock_inference_fn
        )
        print(f"\nSequence Finished. Final Result: {final_result}")
    except ValueError as e:
        print(f"\nSequence Blocked: {e}")

if __name__ == "__main__":
    main()
