import logging
from engram_sdk import ControlPlane, Step, GlobalData, adapter

# Configure logging for orchestrated output
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

def research_company_workflow():
    """
    A multi-step agent workflow that enforces strict sequencing for company research.
    
    1. Collect basic company domain (Model input)
    2. Enrich with company data (Governed tool)
    3. Analyze competitors (Governed tool)
    4. Generate summary report (Model output)
    """
    
    # Initialize GlobalData - the single source of truth outside the Model's memory
    data = GlobalData()
    
    # Define the ControlPlane with strict steps
    cp = ControlPlane(
        steps=[
            Step(
                name="collect_target",
                tools=["set_target_domain"],
                next_step="enrich_data",
                description="Prompt the user for a domain and store it in GlobalData."
            ),
            Step(
                name="enrich_data",
                tools=["get_company_enrichment"],
                next_step="analyze_competitors",
                description="Fetch firmographic data based on the stored domain."
            ),
            Step(
                name="analyze_competitors",
                tools=["find_competitors"],
                next_step="finalize",
                description="Identify top competitors based on enriched sector data."
            ),
            Step(
                name="finalize",
                tools=["generate_report"],
                description="Synthesize all collected GlobalData into a final report."
            )
        ]
    )

    # Note: These tools would normally be registered in the Engram Gateway.
    # For this example, we'll mock the tool execution to show the governed pattern.
    
    print("--- Starting Governed Research Workflow ---\n")

    # Step 1: Collect Target Domain
    with cp.step("collect_target") as step:
        # Model decision: What domain are we researching?
        # In a real run, the orchestrator would send the prompt to the LLM.
        # The LLM is restricted to ONLY the 'set_target_domain' tool.
        print(f"Active Step: {step.name}")
        print(f"Allowed Tools: {step.tools}")
        
        # Simulating Model calling the tool
        domain = "google.com"
        adapter.execute_tool("set_target_domain", domain=domain)
        print(f"GlobalData target: {data.read('target_domain')}\n")

    # Step 2: Enrich Data
    # The ControlPlane ensures we cannot skip to Step 3 or 4.
    with cp.step("enrich_data") as step:
        print(f"Active Step: {step.name}")
        # Model only needs to invoke the tool; it doesn't need to pass 'domain'
        # because the tool pulls it from GlobalData internally.
        adapter.execute_tool("get_company_enrichment")
        print(f"GlobalData company_info: {data.read('company_info')}\n")

    # Step 3: Analyze Competitors
    with cp.step("analyze_competitors") as step:
        print(f"Active Step: {step.name}")
        adapter.execute_tool("find_competitors")
        print(f"GlobalData competitors: {data.read('competitors')}\n")

    # Step 4: Finalize
    with cp.step("finalize") as step:
        print(f"Active Step: {step.name}")
        # The final tool reads EVERYTHING from GlobalData and formats it.
        report = adapter.execute_tool("generate_report")
        print(f"Final Report Generation Triggered.\n")

    print("--- Workflow Complete ---")
    print(f"Final Validated State in GlobalData: {data.all_data()}")

if __name__ == "__main__":
    research_company_workflow()
