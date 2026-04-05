import subprocess
import json
import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import structlog
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
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
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMService()

    async def ingest_openapi(self, url_or_path: str, agent_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> ToolRegistry:
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
            HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head", "trace"}
            for path, methods in spec.get("paths", {}).items():
                if not isinstance(methods, dict):
                    continue
                for method, details in methods.items():
                    if method.lower() not in HTTP_METHODS or not isinstance(details, dict):
                        continue
                        
                    action = {
                        "name": f"{method.upper()} {path}",
                        "description": details.get("summary") or details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "request_body": details.get("requestBody", {}),
                    }
                    actions.append(action)
            
            tool = ToolRegistry(
                agent_id=agent_id,
                user_id=user_id,
                name=tool_name,
                description=description,
                actions=actions
            )
            self.db.add(tool)
            await self.db.flush()

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
            await self.db.commit()
            await self.db.refresh(tool)
            return tool
        except Exception as e:
            logger.error("Failed to ingest OpenAPI", error=str(e))
            raise ValidationError(f"OpenAPI ingestion failed: {str(e)}")

    async def ingest_graphql(self, url: str, agent_id: uuid.UUID, auth_details: Optional[Dict[str, Any]] = None, user_id: Optional[uuid.UUID] = None) -> ToolRegistry:
        """Ingest tools from a GraphQL service via introspection."""
        # For simplicity, we create a generic GraphQL tool entry.
        # In a real implementation, we would perform an introspection query and populate actions.
        
        tool = ToolRegistry(
            agent_id=agent_id,
            user_id=user_id,
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

    async def ingest_url_with_auth(self, url: str, agent_id: uuid.UUID, auth: Dict[str, Any], user_id: Optional[uuid.UUID] = None) -> ToolRegistry:
        """Onboard a raw URL with specified auth details."""
        tool = ToolRegistry(
            agent_id=agent_id,
            user_id=user_id,
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

    async def ingest_cli_help(self, command: str, agent_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> ToolRegistry:
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
                user_id=user_id,
                name=command,
                description=f"CLI wrapper for {command}",
                actions=actions
            )
            self.db.add(tool)
            await self.db.flush()

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
            await self.db.commit()
            await self.db.refresh(tool)
            return tool
        except Exception as e:
            logger.error("CLI help ingestion failed", command=command, error=str(e))
            raise ValidationError(f"CLI ingestion failed: {str(e)}")

    async def create_manual_tool(self, data: ManualToolCreate, agent_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> ToolRegistry:
        """Manually register a tool with a synthetic OpenAPI schema."""
        try:
            # Generate synthetic OpenAPI spec
            synthetic_spec = self._generate_synthetic_openapi(data)
            
            # Map parameters to action-style schema (consistent with ingest_openapi)
            path_item = synthetic_spec["paths"][data.endpoint_path][data.method.lower()]
            actions = [{
                "name": f"{data.method.upper()} {data.endpoint_path}",
                "description": path_item.get("summary") or path_item.get("description", ""),
                "parameters": path_item.get("parameters", []),
                "request_body": path_item.get("requestBody", {}),
            }]
            
            tool = ToolRegistry(
                agent_id=agent_id,
                user_id=user_id,
                name=data.name,
                description=data.description,
                actions=actions
            )
            self.db.add(tool)
            await self.db.flush()

            execution_metadata = ToolExecutionMetadata(
                tool_id=tool.id,
                execution_type=ExecutionType.HTTP,
                exec_params={
                    "openapi_spec": synthetic_spec,  # Synthetic spec for standard discovery
                    "base_url": data.base_url,
                    "endpoint_path": data.endpoint_path,
                    "method": data.method,
                    "source_protocol": "HTTP",
                },
            )
            self.db.add(execution_metadata)
            await self.db.commit()
            await self.db.refresh(tool)
            return tool
        except Exception as e:
            logger.error("Manual tool registration failed", error=str(e))
            raise ValidationError(f"Manual registration failed: {str(e)}")

    def _generate_synthetic_openapi(self, data: ManualToolCreate) -> Dict[str, Any]:
        """Generate a synthetic OpenAPI 3.0 spec for a manual tool."""
        
        # Map manual parameters to OpenAPI-style parameters
        openapi_parameters = []
        for p in data.parameters:
            openapi_parameters.append({
                "name": p.name,
                "in": "query",  # Default to query parameters for manual tools
                "description": p.description,
                "required": p.required,
                "schema": {
                    "type": p.type
                }
            })

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": data.name,
                "version": "1.0.0",
                "description": data.description
            },
            "servers": [{"url": data.base_url.rstrip("/")}],
            "paths": {
                data.endpoint_path: {
                    data.method.lower(): {
                        "summary": data.name,
                        "description": data.description,
                        "parameters": openapi_parameters,
                        "responses": {
                            "200": {
                                "description": "Successful response",
                                "content": {
                                    "application/json": {
                                        "schema": {"type": "object"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        return spec

    async def extract_from_docs(self, docs_text: str, agent_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> ToolRegistry:
        """Use LLM-assisted extraction (Phi-3/LLMService) to register a tool from partial docs."""
        extracted = await self.llm.extract_tool_schema(docs_text)
        
        tool = ToolRegistry(
            agent_id=agent_id,
            user_id=user_id,
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
        if servers and isinstance(servers, list) and isinstance(servers[0], dict):
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
            if not isinstance(methods, dict):
                continue
            for method, details in methods.items():
                if not isinstance(details, dict) or method.lower() != "get":
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
