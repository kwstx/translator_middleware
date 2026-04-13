"""
Example demonstrating Programmatic Governed Inference (PGI) using the ControlPlane.

In this pattern, the developer defines a strict state machine in code.
The model is only allowed to see specific tools at each step, and the 
transitions between steps are decided by code (thick functions), 
not by the LLM's own intent.
"""

from engram_sdk import EngramSDK, ControlPlane, Scope
import json

def mock_inference_fn(step_name, scope, data):
    """
    A mock inference function that simulates an LLM response.
    In a real app, this would call OpenAI, Anthropic, or Gemini.
    """
    print(f"\n[LLM Turn] Step: {step_name}")
    print(f"Allowed Tools: {scope.tools}")
    print(f"Input Data: {data}")
    
    if step_name == "identify_user":
        # Simulate LLM extracting an email 
        return {"email": "alice@example.com"}
    elif step_name == "get_orders":
        # Simulate LLM using tools to find order IDs
        return {"order_ids": ["ORD-123", "ORD-456"]}
    elif step_name == "analyze_orders":
        return "The user Alice has 2 orders and is a VIP."
    
    return {}

def handle_identification(model_output, context):
    """
    Thick function for the identification step.
    Enforces that after identification, we ALWAYS go to 'get_orders'.
    """
    email = model_output.get("email")
    context["user_email"] = email
    print(f"[Thick Function] Identified user: {email}. Forcing transition to 'get_orders'.")
    return "get_orders", email

def handle_orders(model_output, context):
    """
    Thick function for the orders step.
    Decides the next transition based on whether orders were found.
    """
    orders = model_output.get("order_ids", [])
    context["orders"] = orders
    if orders:
        print(f"[Thick Function] Found {len(orders)} orders. Proceeding to analysis.")
        return "analyze_orders", orders
    else:
        print("[Thick Function] No orders found. Ending workflow.")
        return None, None

def handle_analysis(model_output, context):
    """
    Final step handler. Returns None to signify the end of the workflow.
    """
    print(f"[Thick Function] Final Analysis Result: {model_output}")
    return None, model_output

def main():
    # 1. Initialize SDK
    sdk = EngramSDK(agent_id="support_bot")
    
    # 2. Initialize ControlPlane
    cp = ControlPlane(sdk)
    
    # 3. Define the Strict Sequence (Governed Data Collection)
    # Step 1: Force identification. Must return an 'email'.
    cp.add_step(
        name="identify_user",
        tools=["search_contacts"],
        required_fields=["email"],
        handler=handle_identification,
        next_step="get_orders",
        description="Must collect user email first."
    )
    
    # Step 2: Force order gathering. Must return 'order_ids'.
    # Requires 'user_email' to be in context (provided by identify_user's handler).
    cp.add_step(
        name="get_orders",
        tools=["query_database"],
        required_fields=["order_ids"],
        handler=handle_orders,
        preconditions=["user_email"],
        description="Gather orders for the identified user."
    )
    
    # Step 3: Analysis.
    # Requires 'orders' to be in context.
    cp.add_step(
        name="analyze_orders",
        tools=["segmentation_tool"],
        handler=handle_analysis,
        preconditions=["orders"],
        description="Final governed analysis step."
    )
    
    # 4. Run the sequence
    print("Starting Strict Governed Sequence...")
    try:
        final_result = cp.run(
            initial_step="identify_user",
            initial_data="I am Alice, check my orders.",
            inference_fn=mock_inference_fn
        )
        print(f"\nSequence Finished. Final Output: {final_result}")
    except ValueError as e:
        print(f"\nSequence Blocked: {e}")

if __name__ == "__main__":
    main()
