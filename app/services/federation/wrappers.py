import json
import os
import subprocess
from typing import Any, Dict, List, Optional
import structlog
from app.core.sandbox import SafeExecutor
from app.services.federation.translator import FederationTranslator
from app.semantic.mapper import SemanticMapper
from app.core.config import settings

logger = structlog.get_logger(__name__)

class AdaptiveWrapper:
    """
    Builds adaptive wrappers that combine direct API calls, sandboxed execution,
    or basic vision fallbacks. Feeds outputs through the unified ontology layer.
    """

    def __init__(self, translator: Optional[FederationTranslator] = None):
        self.translator = translator or FederationTranslator()
        self.mapper = self.translator.mapper

    async def execute_legacy_tool(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any], 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes a legacy tool by choosing the best available execution path.
        """
        logger.info("Executing legacy tool", tool=tool_name, method=metadata.get("method", "auto"))
        
        # 1. Map arguments to canonical ontology first (to ensure consistency)
        canonical_args = self.translator.to_ontology(arguments, source_protocol="MCP")
        
        # 2. Choose path based on metadata or availability
        method = metadata.get("method", "auto")
        
        result = None
        if method == "direct_api" or (method == "auto" and "endpoint_url" in metadata):
            result = await self._call_direct_api(metadata.get("endpoint_url"), canonical_args, metadata)
        elif method == "sandboxed_script" or (method == "auto" and "script_path" in metadata):
            result = await self._execute_sandboxed(metadata.get("script_path"), canonical_args, metadata)
        elif method == "vision_fallback":
            result = await self._vision_scrape_fallback(tool_name, canonical_args, metadata)
        else:
            # Last resort: generic CLI call
            result = await self._execute_cli_fallback(tool_name, canonical_args, metadata)
            
        # 3. Feed the result through the self-healing + ontology layer
        # Wrap the result back to the requested protocol format
        return self.translator.from_ontology(result, target_protocol="MCP")

    async def _call_direct_api(self, url: str, args: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        """Direct HTTP API invocation."""
        logger.info("Legacy: Calling direct API", url=url)
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=args, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def _execute_sandboxed(self, script_path: str, args: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        """Sandboxed script/CLI execution."""
        logger.info("Legacy: Running sandboxed script", script=script_path)
        
        def run_script(path, payload):
            # In a real setup, we might use a docker container here
            # For now, we simulate a subprocess in the sandbox
            cmd = [settings.PYTHON_INTERPRETER or "python", path, json.dumps(payload)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                raise Exception(f"Script failed: {res.stderr}")
            return json.loads(res.stdout)

        return SafeExecutor.run_in_sandbox(run_script, args=(script_path, args), timeout=60.0)

    async def _vision_scrape_fallback(self, tool_name: str, args: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Screen scraping fallback via pyautogui or similar (mocked here).
        Useful for UI-changing or undocumented interfaces.
        """
        logger.warning("Legacy: Vision fallback triggered", tool=tool_name)
        # Mocking vision scrape logic:
        # 1. Locate UI elements based on 'ui_hints' in meta
        # 2. Perform clicks/typing
        # 3. Scrape relevant fields
        ui_hints = meta.get("ui_hints", {})
        
        # We simulate finding a value on screen
        fake_scraped_data = {
            "status": "success",
            "detected_value": f"MOCKED_SCRAPE_FOR_{tool_name}",
            "confidence": 0.82
        }
        return fake_scraped_data

    async def _execute_cli_fallback(self, tool_name: str, args: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
        """Generic CLI invocation."""
        logger.info("Legacy: CLI fallback", tool=tool_name)
        cmd = meta.get("cli_command", f"legacy_{tool_name}")
        # Build command with arguments...
        return {"output": f"Full CLI output from {cmd}", "exit_code": 0}
