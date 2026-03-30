import asyncio
from tui.app import EngramTUI, OpenAIConnectScreen

async def manual_run():
    app = EngramTUI(base_url="http://localhost:8000/api/v1")
    # hook on_mount to immediately push the test screen
    original_mount = app.on_mount
    async def mock_mount():
        await original_mount()
        p = {"id": "openai", "name": "OpenAI", "auth": "api_key"}
        app.push_screen(OpenAIConnectScreen(p))
    app.on_mount = mock_mount

    try:
        await app.run_async()
    except Exception as e:
        with open("crash.txt", "w") as f:
            f.write(str(e))
            import traceback
            f.write(traceback.format_exc())

asyncio.run(manual_run())
