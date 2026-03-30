import asyncio
from tui.app import EngramTUI

async def test_run():
    app = EngramTUI(base_url="http://localhost:8000/api/v1")
    # inject directly to invoke the function after mounting
    async def mock_mount():
        try:
            app._open_service_connect("openai")
            with open("test_result.txt", "w") as f:
                f.write("Success")
        except Exception as e:
            with open("test_result.txt", "w") as f:
                import traceback
                f.write(traceback.format_exc())
    
    app.on_mount = mock_mount
    await app.run_async(headless=True)

asyncio.run(test_run())
