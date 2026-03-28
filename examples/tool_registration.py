import uuid
from engram_sdk import EngramSDK
from engram_sdk.types import ToolDefinition, ToolAction

def main():
    # 1. Initialize SDK
    # Replace with your actual backend URL if different
    sdk = EngramSDK(
        base_url="http://localhost:8000/api/v1",
        agent_id=str(uuid.uuid4()),
        endpoint_url="http://localhost:8080",
        supported_protocols=["MCP", "A2A"],
        semantic_tags=["productivity", "slack", "communication"]
    )

    print(f"Agent ID: {sdk.agent_id}")

    # 2. Define a complex tool with multiple actions
    slack_tool = ToolDefinition(
        name="SlackTool",
        description="A bridge to Slack for sending messages and listing channels.",
        version="1.0.0",
        tags=["communication", "collaboration"],
        actions=[
            ToolAction(
                name="send_message",
                description="Sends a text message to a Slack channel.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or name"},
                        "text": {"type": "string", "description": "Message content"}
                    },
                    "required": ["channel", "text"]
                },
                required_permissions=["slack:write"]
            ),
            ToolAction(
                name="list_channels",
                description="Lists available public channels.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 10}
                    }
                },
                required_permissions=["slack:read"]
            )
        ],
        required_permissions=["slack:base"]
    )

    # 3. Register tool in the local SDK registry
    sdk.register_tool(slack_tool)

    # 4. Declare capabilities to Engram Backend
    print("Registering agent and tools with Engram...")
    try:
        # Note: In a real scenario, you'd need to be logged in to register if the endpoint is protected
        # For local development, it might be open or use a default session
        result = sdk.register_agent()
        print("Registration successful!")
        print(f"Registry Response: {result}")
        
    except Exception as e:
        print(f"Registration failed: {e}")

if __name__ == "__main__":
    main()
