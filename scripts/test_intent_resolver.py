import asyncio
import structlog
from app.messaging.intent_resolver import IntentResolver

async def test_resolver():
    resolver = IntentResolver()
    
    prompts = [
        "Please translate this research paper to MCP and also predict the market price for BTC.",
        "Can you check the status of my task 550e8400-e29b-41d4-a716-446655440000 then find a collaborator for A2A?",
        "I want to convert the following data into ACP format."
    ]
    
    print("\n--- Testing Intent Resolution Layer ---\n")
    for prompt in prompts:
        print(f"User Input: '{prompt}'")
        result = await resolver.resolve(prompt)
        print(f"Decomposed into {len(result.tasks)} tasks:")
        for i, task in enumerate(result.tasks):
            print(f"  [{i+1}] Intent: {task.intent}")
            print(f"      Capability Tag: {task.capability_tag}")
            print(f"      Parameters: {task.parameters}")
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(test_resolver())
