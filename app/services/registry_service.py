import subprocess
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import structlog
from sqlmodel import Session, select
from prance import ResolvingParser
from openapi_spec_validator import validate_spec
import strawberry
from graphql import parse, build_ast_schema

from app.db.models import ToolRegistry, ToolExecutionMetadata, ExecutionType, AgentRegistry
from app.schemas.tool import ManualToolCreate
from app.core.exceptions import ValidationError
from app.services.llm import LLMService

logger = structlog.get_logger(__name__)

class RegistryService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = LLMService()

    async def ingest_openapi(self, url_or_path: str, agent_id: uuid.UUID) -> ToolRegistry:
        """Ingest tools from an OpenAPI spec."""
        try:
            parser = ResolvingParser(url_or_path)
            spec = parser.specification
            event_sources = self._detect_openapi_event_sources(spec)
            base_url = self._extract_openapi_base_url(spec)
            if base_url:
                for poll in event_sources.get("polling", []):
                    if poll.get("path"):
                        poll["url"] = f"{base_url.rstrip('/')}{poll['path']}"
            
            tool_name = spec.get("info", {}).get("title", "OpenAPI Tool")
            description = spec.get("info", {}).get("description", "No description provided")
            
            # Map paths to actions
            actions = []
            for path, methods in spec.get("paths", {}).items():
                for method, details in methods.items():
                    action = {
                        "name": f"{method.upper()} {path}",
                        "description": details.get("summary") or details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "request_body": details.get("requestBody", {}),
                    }
                    actions.append(action)
            
            tool = ToolRegistry(
                agent_id=agent_id,
                name=tool_name,
                description=description,
                actions=actions
            )
            self.db.add(tool)
            self.db.flush()

            execution_metadata = ToolExecutionMetadata(
                tool_id=tool.id,
                execution_type=ExecutionType.HTTP,
                exec_params={
                    "openapi_spec": spec,
                    "source_url": url_or_path,
                    "base_url": base_url,
                    "event_sources": event_sources,
                    "source_protocol": "HTTP",
                },
            )
            self.db.add(execution_metadata)
            self.db.commit()
            self.db.refresh(tool)
            return tool
        except Exception as e:
            logger.error("Failed to ingest OpenAPI", error=str(e))
            raise ValidationError(f"OpenAPI ingestion failed: {str(e)}")

    async def ingest_graphql(self, url: str, agent_id: uuid.UUID, auth_details: Optional[Dict[str, Any]] = None) -> ToolRegistry:
        """Ingest tools from a GraphQL service via introspection."""
        # For simplicity, we create a generic GraphQL tool entry.
        # In a real implementation, we would perform an introspection query and populate actions.
        
        tool = ToolRegistry(
            agent_id=agent_id,
            name=f"GraphQL Service ({url})",
            description="Auto-onboarded GraphQL API",
            actions=[{"name": "query", "description": "Generic GraphQL query execution"}]
        )
        self.db.add(tool)
        await self.db.flush()

        execution_metadata = ToolExecutionMetadata(
            tool_id=tool.id,
            execution_type=ExecutionType.HTTP,
            exec_params={"graphql_url": url, "source_protocol": "HTTP"},
            auth_config=auth_details or {}
        )
        self.db.add(execution_metadata)
        await self.db.commit()
        return tool

    async def ingest_url_with_auth(self, url: str, agent_id: uuid.UUID, auth: Dict[str, Any]) -> ToolRegistry:
        """Onboard a raw URL with specified auth details."""
        tool = ToolRegistry(
            agent_id=agent_id,
            name=f"HTTP Endpoint ({url})",
            description="Manually onboarded URL",
            actions=[{"name": "call", "description": "Call the specific URL"}]
        )
        self.db.add(tool)
        await self.db.flush()

        execution_metadata = ToolExecutionMetadata(
            tool_id=tool.id,
            execution_type=ExecutionType.HTTP,
            exec_params={"endpoint_url": url, "source_protocol": "HTTP"},
            auth_config=auth
        )
        self.db.add(execution_metadata)
        await self.db.commit()
        return tool

    async def ingest_cli_help(self, command: str, agent_id: uuid.UUID) -> ToolRegistry:
        """Parse --help output of a CLI tool and create a thin wrapper."""
        try:
            result = subprocess.run([command, "--help"], capture_output=True, text=True, check=True)
            help_text = result.stdout
            
            # Use regex/LLM to extract argument structure
            args = re.findall(r"(--\w+)\s+(\w+)?", help_text)
            actions = [{"name": command, "description": help_text[:500], "args": [a[0] for a in args]}]
            cli_args = [a[0] for a in args]
            event_sources = self._detect_cli_event_sources(help_text, command, cli_args)

            tool = ToolRegistry(
                agent_id=agent_id,
                name=command,
                description=f"CLI wrapper for {command}",
                actions=actions
            )
            self.db.add(tool)
            self.db.flush()

            # Python template for the thin wrapper
            cli_wrapper_script = (
                "#!/usr/bin/env python\n"
                "import os, subprocess, sys\n"
                "def run():\n"
                "    # Credentials injected via env vars from EAT\n"
                f"    base_cmd = '{command}'\n"
                "    subprocess.run([base_cmd] + sys.argv[1:])\n"
                "if __name__ == '__main__':\n"
                "    run()"
            )

            execution_metadata = ToolExecutionMetadata(
                tool_id=tool.id,
                execution_type=ExecutionType.CLI,
                cli_wrapper=cli_wrapper_script,
                exec_params={
                    "cli_command": command,
                    "help_output": help_text,
                    "cli_args": cli_args,
                    "event_sources": event_sources,
                    "source_protocol": "CLI",
                },
            )
            self.db.add(execution_metadata)
            self.db.commit()
            return tool
        except Exception as e:
            logger.error("CLI help ingestion failed", command=command, error=str(e))
            raise ValidationError(f"CLI ingestion failed: {str(e)}")

    async def register_manual(self, data: ManualToolCreate, agent_id: uuid.UUID) -> ToolRegistry:
        """Manually register a tool."""
        try:
            # Map parameters to action-style schema
            parameters = [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required
                } for p in data.parameters
            ]
            
            actions = [{
                "name": data.name,
                "description": data.description,
                "method": data.method,
                "path": data.endpoint_path,
                "parameters": parameters
            }]
            
            tool = ToolRegistry(
                agent_id=agent_id,
                name=data.name,
                description=data.description,
                actions=actions
            )
            self.db.add(tool)
            self.db.flush()

            execution_metadata = ToolExecutionMetadata(
                tool_id=tool.id,
                execution_type=ExecutionType.HTTP,
                exec_params={
                    "base_url": data.base_url,
                    "endpoint_path": data.endpoint_path,
                    "method": data.method,
                    "parameters": parameters,
                    "source_protocol": "HTTP",
                },
            )
            self.db.add(execution_metadata)
            self.db.commit()
            self.db.refresh(tool)
            return tool
        except Exception as e:
            logger.error("Manual tool registration failed", error=str(e))
            raise ValidationError(f"Manual registration failed: {str(e)}")

    async def extract_from_docs(self, docs_text: str, agent_id: uuid.UUID) -> ToolRegistry:
        """Use LLM-assisted extraction (Phi-3/LLMService) to register a tool from partial docs."""
        extracted = await self.llm.extract_tool_schema(docs_text)
        
        tool = ToolRegistry(
            agent_id=agent_id,
            name=extracted["name"],
            description=extracted["description"],
            actions=extracted["actions"]
        )
        self.db.add(tool)
        await self.db.flush()

        execution_metadata = ToolExecutionMetadata(
            tool_id=tool.id,
            execution_type=ExecutionType.MCP,
            exec_params={"extracted_from": "docs", "raw_content_preview": docs_text[:200]},
        )
        self.db.add(execution_metadata)
        await self.db.commit()
        return tool

    def _extract_openapi_base_url(self, spec: Dict[str, Any]) -> Optional[str]:
        servers = spec.get("servers") or []
        if servers and isinstance(servers, list):
            return servers[0].get("url")
        return None

    def _detect_openapi_event_sources(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        webhooks: List[Dict[str, Any]] = []
        polling: List[Dict[str, Any]] = []

        for webhook_path, webhook_def in (spec.get("webhooks") or {}).items():
            if isinstance(webhook_def, dict):
                for method, details in webhook_def.items():
                    webhooks.append(
                        {
                            "path": webhook_path,
                            "method": method.upper(),
                            "description": details.get("summary") or details.get("description", ""),
                        }
                    )

        polling_terms = {"events", "changes", "updates", "poll", "stream"}
        poll_param_terms = {"since", "cursor", "updated_after", "updated_at", "timestamp", "page_token", "offset"}

        for path, methods in (spec.get("paths") or {}).items():
            for method, details in methods.items():
                if method.lower() != "get":
                    continue
                path_lower = path.lower()
                params = details.get("parameters", [])
                param_names = {p.get("name", "").lower() for p in params if isinstance(p, dict)}
                if any(term in path_lower for term in polling_terms) or param_names.intersection(poll_param_terms):
                    polling.append(
                        {
                            "path": path,
                            "method": method.upper(),
                            "params": {name: None for name in param_names},
                        }
                    )

        return {"webhooks": webhooks, "polling": polling}

    def _detect_cli_event_sources(
        self,
        help_text: str,
        command: str,
        cli_args: List[str],
    ) -> Dict[str, Any]:
        watch_terms = {"watch", "tail", "stream", "listen", "follow"}
        flag_terms = {"--watch", "--tail", "--follow", "--stream", "--poll", "--on-change", "--interval"}

        detected = [term for term in watch_terms if re.search(rf"\\b{term}\\b", help_text, re.IGNORECASE)]
        flags = [flag for flag in flag_terms if flag in cli_args or flag in help_text]

        cli_watch = []
        if detected or flags:
            args = []
            for flag in flags:
                args.append(flag)
            cli_watch.append(
                {
                    "name": "stdout-watch",
                    "command": command,
                    "args": args,
                }
            )

        return {"cli_watch": cli_watch}
