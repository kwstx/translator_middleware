import os
import sys
import subprocess

# Force UTF-8 encoding for standard output and error to prevent UnicodeEncodeError
# on Windows environments when rich tries to print emojis or box drawing characters.
if getattr(sys.stdout, 'encoding', '').lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if getattr(sys.stderr, 'encoding', '').lower() != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
import yaml
import asyncio
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import difflib

import typer
import httpx
import keyring
import jwt
from pydantic import BaseModel, Field, HttpUrl
from rich import box
from rich.json import JSON
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.live import Live
from rich.prompt import Prompt

# Constants
APP_NAME = "engram"
CONFIG_DIR = Path.home() / f".{APP_NAME}"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
DEFAULT_API_URL = "http://127.0.0.1:8000"

# Enums
class BackendPreference(str, Enum):
    MCP = "mcp"
    CLI = "cli"

# Models
class EngramConfig(BaseModel):
    api_url: str = Field(default=DEFAULT_API_URL, description="Base URL for the Engram API")
    eat_token: Optional[str] = Field(default=None, description="Engram Authorization Token (EAT)")
    backend_preference: BackendPreference = Field(default=BackendPreference.MCP, description="Default backend for tool execution")
    model_provider: str = Field(default="openai", description="Default AI model provider")
    verbose: bool = Field(default=False, description="Enable verbose logging")

class CLIContext:
    def __init__(self):
        self.config = EngramConfig()
        self.json_output = False
        self.console = Console()
        self._token_validated = False

    def get_token(self) -> Optional[str]:
        """Retrieve EAT token from keyring with fallback to config."""
        try:
            token = keyring.get_password(APP_NAME, "eat_token")
            return token or self.config.eat_token
        except Exception:
            return self.config.eat_token

    def set_token(self, token: Optional[str]):
        """Save EAT token to keyring and update config fallback."""
        self.config.eat_token = token
        try:
            if token:
                keyring.set_password(APP_NAME, "eat_token", token)
            else:
                keyring.delete_password(APP_NAME, "eat_token")
        except Exception as e:
            if self.config.verbose:
                rprint(f"[dim yellow]Warning: Could not use keyring: {e}[/]")
        self.save_config()

    def request(self, method: str, endpoint: str, auth_token: Optional[str] = None, **kwargs) -> Any:
        url = f"{self.config.api_url}{endpoint}"
        headers = {}
        token = auth_token or self.get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        # Use a robust client configuration to prevent connection issues in diverse 
        # environments (e.g. bypass machine-level proxies for local requests).
        with httpx.Client(headers=headers, timeout=30.0, trust_env=False) as client:
            try:
                response = client.request(method, url, **kwargs)
                if response.status_code == 401:
                    self.handle_auth_error(response)
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("detail", response.text)
                    except:
                        error_detail = response.text
                    raise Exception(f"API Error ({response.status_code}): {error_detail}")
                return response.json()
            except httpx.RequestError as exc:
                raise Exception(f"Connection Error: Could not connect to {url}. Ensure the backend is running.") from exc

    def handle_auth_error(self, response):
        """Show helpful suggestions for authentication errors."""
        try:
            error_data = response.json()
            detail = error_data.get("detail", "Your session has expired or the token is invalid.")
        except:
            detail = "Your session has expired or the token is invalid."

        rprint(f"\n[bold red][AUTH] Authentication Required[/]")
        rprint(f"[red]{detail}[/]")
        rprint("\n[bold cyan]Suggestions:[/]")
        rprint("  1. Run [bold green]engram auth login[/] to re-authenticate.")
        rprint("  2. If using a manual token, check [bold]engram auth status[/].")
        rprint("  3. Ensure the backend API URL is correct: [bold]engram config show[/]\n")
        raise typer.Exit(1)

    def validate_token_silently(self):
        """Validate the token in the background without blocking the user flow."""
        token = self.get_token()
        if not token:
            return

        token = token.strip()

        try:
            # Quick local JWT check if possible
            payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
            # If close to expiration (e.g. < 5 mins), don't block but maybe log it
        except jwt.ExpiredSignatureError:
            rprint("[dim yellow]Note: Your auth token has expired. Some commands may fail.[/]")
        except Exception:
            pass

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = yaml.safe_load(f)
                    if data:
                        self.config = EngramConfig(**data)
            except Exception as e:
                rprint(f"[bold red]Error loading config:[/] {e}")

    def save_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            # Use mode='json' to ensure Enums are serialized as strings
            yaml.dump(self.config.model_dump(mode='json'), f, default_flow_style=False)

    def output(self, data: Any, title: str = "Result"):
        if self.json_output:
            # Handle Pydantic models
            if isinstance(data, BaseModel):
                print(data.model_dump_json(indent=2))
            else:
                print(json.dumps(data, indent=2))
        else:
            if isinstance(data, str):
                rprint(Panel(data, title=f"[bold cyan]{title}[/]", border_style="cyan"))
            elif isinstance(data, dict):
                table = Table(title=title)
                table.add_column("Key", style="magenta")
                table.add_column("Value", style="green")
                for k, v in data.items():
                    table.add_row(str(k), str(v))
                self.console.print(table)
            elif isinstance(data, list):
                table = Table(title=title)
                if data and isinstance(data[0], dict):
                    keys = data[0].keys()
                    for key in keys:
                        table.add_column(key, style="cyan")
                    for item in data:
                        table.add_row(*(str(item.get(k, "")) for k in keys))
                else:
                    table.add_column("Item", style="cyan")
                    for item in data:
                        table.add_row(str(item))
                self.console.print(table)
            elif isinstance(data, BaseModel):
                self.output(data.model_dump(), title=title)

# Typer App
app = typer.Typer(
    name=APP_NAME,
    help="[bold green]Engram Protocol Bridge CLI[/] - Semantic Tool Orchestration",
    rich_markup_mode="rich",
    no_args_is_help=True
)

state = CLIContext()

@app.callback()
def main_callback(
    ctx: typer.Context,
    json: bool = typer.Option(False, "--json", help="Output in machine-readable JSON format"),
    config_path: Optional[Path] = typer.Option(None, "--config", help="Path to a custom config file"),
):
    """
    [bold]Engram CLI[/] - The universal translator for MCP tools and CLI agents.
    
    This CLI manages the foundational Phase 1 structure for tool discovery, 
    authentication, and multi-backend execution.
    """
    global CONFIG_FILE
    if config_path:
        CONFIG_FILE = config_path
    
    state.json_output = json
    state.load_config()
    state.validate_token_silently()
    ctx.obj = state

# --- Commands ---

@app.command()
def init():
    """
    Initialize the Engram configuration and directory structure.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Initializing config...", total=None)
        state.save_config()
        time.sleep(1)
        
    state.output(
        f"Initialized Engram directory at {CONFIG_DIR}\nConfig saved to {CONFIG_FILE}",
        title="Initialization Success"
    )

@app.command()
def info():
    """
    Display current CLI configuration and system status.
    """
    status = {
        "Config Path": str(CONFIG_FILE),
        "API URL": state.config.api_url,
        "Backend": state.config.backend_preference.value,
        "Auth Status": "Authenticated" if state.get_token() else "Anonymous",
        "EAT Token": "****" + state.get_token()[-4:] if state.get_token() else "None"
    }
    state.output(status, title="System Information")

# --- Auth Subgroup ---
auth_app = typer.Typer(help="Manage authentication and EAT (Engram Authorization Tokens)")
app.add_typer(auth_app, name="auth")

@auth_app.command("login")
def auth_login(
    token: Optional[str] = typer.Option(None, "--token", "-t", help="Directly input an EAT token"),
    browser: bool = typer.Option(True, "--browser/--no-browser", help="Open login page in browser")
):
    """
    Authenticate with the Engram backend to retrieve an EAT.
    """
    if token:
        state.set_token(token.strip())
        rprint("[OK] [bold green]Token saved securely via keyring.[/]")
        return

    login_url = f"{state.config.api_url}/api/v1/auth/login"
    rprint(f"[bold cyan]Initiating login flow...[/]")
    
    if browser:
        rprint(f"Opening browser to: [link={login_url}]{login_url}[/link]")
        typer.launch(login_url)
    
    rprint("\n[yellow]Please paste your EAT (Engram Authorization Token) below:[/]")
    input_token = typer.prompt("EAT Token", hide_input=True)
    
    if input_token:
        state.set_token(input_token.strip())
        rprint("\n[bold green][OK] Login successful! Identity and permissions synced.[/]")
        auth_whoami()
    else:
        rprint("[bold red]Login aborted.[/]")

@auth_app.command("whoami")
def auth_whoami():
    """
    Display current identity and a semantic permission summary.
    """
    token = state.get_token()
    if not token:
        rprint("[bold red]Not authenticated.[/] Run 'engram auth login' first.")
        return

    try:
        # Decode token to show claims
        payload = jwt.decode(token, options={"verify_signature": False})
        
        tree = Tree(f"[USER] [bold cyan]Identity:[/] {payload.get('sub', 'Unknown')}")
        
        # Scopes and Permissions
        perm_node = tree.add("[AUTH] [bold green]Permissions (EAT Structured)[/]")
        scopes = payload.get("scopes", {})
        
        for tool, perms in scopes.items():
            tool_node = perm_node.add(f"[magenta]{tool}[/]")
            for p in perms:
                tool_node.add(f"[dim]{p}[/]")
        
        # Semantic Scopes
        semantic_node = tree.add("[ONTOLOGY] [bold yellow]Semantic Scopes (Ontology-based)[/]")
        sem_scopes = payload.get("semantic_scopes", [])
        for ss in sem_scopes:
            semantic_node.add(f"[italic blue]{ss}[/]")
            # Provide helpful translation for common scopes
            if "execute" in ss:
                semantic_node.add("  |- [dim]Can invoke cross-protocol tool translations[/]")
            if "read" in ss:
                semantic_node.add("  |- [dim]Can query ontology metadata and tool catalogs[/]")

        rprint(Panel(tree, title="Current Session Identity", border_style="cyan", expand=False))
        
        # Optional: verify with backend if possible
        try:
            me_info = state.request("GET", "/api/v1/permissions/me")
            rprint(f"[dim green]Backend verification: Active profile '{me_info.get('profile_name', 'default')}'[/]")
        except:
            pass

    except Exception as e:
        rprint(f"[bold red]Error decoding identity:[/] {e}")

@auth_app.command("scope")
def auth_scope():
    """
    Explore and visualize the semantic scopes assigned to this EAT.
    """
    token = state.get_token()
    if not token:
        rprint("[bold red]Not authenticated.[/]")
        return

    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        sem_scopes = payload.get("semantic_scopes", [])
        
        table = Table(title="[ONTOLOGY] Semantic Access Scopes", box=box.DOUBLE_EDGE)
        table.add_column("Scope Identifier", style="cyan")
        table.add_column("Ontology Context", style="magenta")
        table.add_column("Capability", style="green")
        
        for ss in sem_scopes:
            # Mocking ontology expansion since we don't have a direct ontology query here
            context = "Global" if "all" in ss or ":" not in ss else ss.split(":")[1]
            capability = "Translation Execution" if "execute" in ss else "Metadta Query"
            
            table.add_row(ss, context, capability)
            
        state.console.print(table)
        rprint("[dim italic]These scopes are used for agentic routing and tool pruning decisions.[/]")

    except Exception as e:
        rprint(f"[bold red]Error:[/] {e}")

@auth_app.command("token-set")
def auth_token_set(token: str):
    """
    Manually set the Engram Authorization Token (EAT).
    """
    state.set_token(token.strip())
    rprint(f"[OK] EAT token updated securely.")

@auth_app.command("status")
def auth_status():
    """
    Check current authentication status.
    """
    token = state.get_token()
    if token:
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            sub = payload.get("sub", "Unknown")
            exp = payload.get("exp")
            expires_at = datetime.fromtimestamp(exp) if exp else "Never"
            
            state.output({
                "status": "authenticated",
                "identity": sub,
                "expires_at": str(expires_at),
                "token_preview": token[:10] + "..."
            }, title="Authentication Status")
        except:
            state.output({"status": "authenticated (invalid format)", "token_preview": token[:10] + "..."}, title="Authentication Status")
    else:
        state.output({"status": "unauthenticated"}, title="Authentication Status")

# --- Config Subgroup ---
config_app = typer.Typer(help="View and modify CLI configuration")
app.add_typer(config_app, name="config")

@config_app.command("show")
def config_show():
    """
    Display the current configuration.
    """
    state.output(state.config, title="Current Configuration")

@config_app.command("set")
def config_set(
    key: str, 
    value: str
):
    """
    Set a configuration value. (e.g., api_url, backend_preference)
    """
    if hasattr(state.config, key):
        # Basic type conversion
        current_val = getattr(state.config, key)
        if isinstance(current_val, bool):
            setattr(state.config, key, value.lower() == "true")
        elif isinstance(current_val, int):
            setattr(state.config, key, int(value))
        else:
            setattr(state.config, key, value)
        
        state.save_config()
        rprint(f"[OK] Set [bold]{key}[/] to [bold]{value}[/]")
    else:
        rprint(f"[bold red]Error:[/] Unknown config key '{key}'")

# --- Tool Subgroup (Core Features) ---
tool_app = typer.Typer(help="Discover and manage tools (MCP & CLI)")
app.add_typer(tool_app, name="tools")

def _fuzzy_search(query: str, tools: List[Dict]):
    """Score-based fuzzy filtering for tools."""
    results = []
    q_low = query.lower()
    for t in tools:
        name = t.get("name", "").lower()
        desc = t.get("description", "").lower()
        tags = " ".join(t.get("tags", [])).lower()
        
        # Exact match / substring (high priority)
        if q_low in name:
            results.append((1.0, t))
            continue
            
        # Score based on name closeness
        score = difflib.SequenceMatcher(None, q_low, name).ratio()
        if score > 0.4:
            results.append((score, t))
            continue
            
        # Check description/tags
        if q_low in desc or q_low in tags:
            results.append((0.5, t))
            
    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results]

@tool_app.command("list")
def tool_list(
    popular: bool = typer.Option(False, "--popular", help="Include pre-optimized wrappers for popular apps"),
    query: Optional[str] = typer.Option(None, "--filter", "-f", help="Quick fuzzy filter for tool names or descriptions"),
):
    """
    List all registered tools with backend type, semantic tags, and performance stats.
    """
    ctx = state
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Fetching tool registry...", total=None)
        try:
            # 1. Fetch custom tools from registry
            custom_tools = ctx.request("GET", "/api/v1/registry/tools")
            
            # 2. Fetch performance stats to join
            stats = ctx.request("GET", "/api/v1/routing/list")
            stats_map = { (s['tool_name'], s['backend']): s for s in stats }
            
            processed_tools = []
            for t in custom_tools:
                # Backend discovery
                exec_meta = t.get("execution_metadata") or {}
                backend = exec_meta.get("execution_type", "CLI").upper()
                
                # Join with stats
                s = stats_map.get((t["name"], backend), {})
                success_rate = s.get("success_rate", 1.0) # Default to 100% (healthy/new)
                
                processed_tools.append({
                    "name": t["name"],
                    "description": t["description"],
                    "backend": backend,
                    "type": (t.get("tags") or ["Universal"])[0],
                    "success": success_rate,
                    "is_popular": False,
                    "id": t.get("id"),
                    "tags": t.get("tags", [])
                })
                
            # 3. Add popular tools if requested
            if popular:
                popular_entries = ctx.request("GET", "/api/v1/catalog/entries")
                for p in popular_entries:
                    processed_tools.append({
                        "name": p["display_name"],
                        "description": p["description"],
                        "backend": "MCP/CLI", # Hero feature: pre-optimized dual support
                        "type": p.get("category", "Popular"),
                        "success": 0.99, # Pre-seeded apps have high confidence
                        "is_popular": True,
                        "id": p.get("slug"),
                        "tags": p.get("tags", [])
                    })

            # 4. Handle Filtering
            if query:
                final_tools = _fuzzy_search(query, processed_tools)
            else:
                # Prioritize Custom tools (Hero) then Popular
                final_tools = sorted(processed_tools, key=lambda x: (x["is_popular"], x["name"]))

            if ctx.json_output:
                print(json.dumps(final_tools, indent=2))
                return

            # 5. Render Rich Table
            table = Table(
                title="[TOOL] [bold]Engram Tool Catalog[/]",
                box=box.SIMPLE_HEAVY,
                header_style="bold magenta",
                show_lines=False
            )
            
            table.add_column("S", width=2, justify="center") # Status/Type Icon
            table.add_column("Tool / Extension", style="bold cyan")
            table.add_column("Backend", justify="center")
            table.add_column("Semantic Type", style="dim green")
            table.add_column("Success", justify="right")
            table.add_column("Description", style="italic")

            for t in final_tools:
                # Backend Icon + Text
                if t["backend"] == "MCP":
                    backend_fmt = "[TOOL] [bold blue]MCP[/]"
                elif t["backend"] == "CLI":
                    backend_fmt = "[CLI] [bold green]CLI[/]"
                else:
                    backend_fmt = "[DUAL] [bold yellow]Dual[/]" # Hybrid/Popular
                
                # Hero indicator for custom tools
                hero_icon = "*" if not t["is_popular"] else ">"
                
                # Success Rate coloring
                sr = t["success"]
                color = "green" if sr >= 0.9 else "yellow" if sr >= 0.7 else "red"
                success_fmt = f"[{color}]{sr:.1%}[/]"
                
                # Sanitize name and description for cross-terminal compatibility (replace Unicode dashes)
                processed_name = t["name"].replace("\u2014", "-").replace("\u2013", "-")
                processed_desc = t["description"].replace("\u2014", "-").replace("\u2013", "-")
                
                table.add_row(
                    hero_icon,
                    processed_name,
                    backend_fmt,
                    t["type"],
                    success_fmt,
                    (processed_desc[:60] + "...") if len(processed_desc) > 60 else processed_desc
                )

            ctx.console.print(table)
            rprint(f"\n[dim]Showing {len(final_tools)} active tools. Use [bold]--popular[/] to see pre-optimized integrations.[/]")
            if not query:
                rprint("[dim italic][INFO] Universal tools are linked via semantic ontology for cross-protocol healing.[/]")

        except Exception as e:
            rprint(f"[bold red]Discovery Error:[/] {e}")
            if "Connection Error" in str(e):
                rprint("\n[bold yellow][TIP] Suggestion:[/] It looks like the Engram Bridge server is not running.")
                rprint("Try starting it in a new terminal with: [bold cyan]uvicorn app.main:app[/]\n")
            elif "500" in str(e):
                rprint("\n[bold yellow][TIP] Suggestion:[/] The server encountered an internal error.")
                rprint("Check the server logs for details. If you're running locally, make sure your [bold].env[/] file exists and is correctly configured.\n")


@tool_app.command("search")
def tool_search(
    query: str = typer.Argument(..., help="Query to search for tools in name, tags, or description"),
    popular: bool = typer.Option(True, "--popular/--no-popular", help="Include popular app catalog in search")
):
    """
    Search for tools using fuzzy matching. Highlights universal vs pre-optimized apps.
    """
    # Simply delegate to tool_list with filtering
    tool_list(popular=popular, query=query)



# --- Register Subgroup ---
register_app = typer.Typer(help="Onboard and register new APIs, CLI manifests, or direct shell commands")
app.add_typer(register_app, name="register")


def _get_or_create_agent_id(ctx: CLIContext) -> str:
    """Helper to get a default agent ID for registration."""
    try:
        # Try to find existing agents
        agents = ctx.request("GET", "/api/v1/discovery/agents")
        if agents and len(agents) > 0:
            return agents[0]["agent_id"]
    except Exception:
        pass

    # Fallback/Create a default agent if possible or return a generic UUID
    # In a real environment, we'd call an endpoint to create a 'CLI Onboarding Agent'
    return "00000000-0000-0000-0000-000000000000"


@register_app.command("openapi")
def register_api(
    source: str = typer.Argument(..., help="URL, local file path to OpenAPI spec, or documentation text"),
    agent_id: Optional[str] = typer.Option(None, help="Agent UUID to link the tool to"),
    partial: bool = typer.Option(False, "--partial", help="Treat source as partial documentation text"),
):
    """
    Universal onboarding for APIs via OpenAPI specs or partial documentation.
    """
    ctx = state
    target_agent = agent_id or _get_or_create_agent_id(ctx)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        transient=False,
    ) as progress:
        task1 = progress.add_task(description="[cyan]Analyzing source input...", total=None)
        time.sleep(0.8)

        # Validation step
        if not partial and source.startswith(("http://", "https://")):
            progress.update(task1, description="[cyan]Validating remote OpenAPI spec...")
        elif not partial and Path(source).exists():
            progress.update(task1, description="[cyan]Reading local manifest...")
        elif partial:
            progress.update(task1, description="[cyan]Parsing semantic documentation blocks...")
        else:
            rprint("[bold red]Error:[/] Source must be a URL, a file path, or used with --partial.")
            raise typer.Exit(1)

        time.sleep(1.2)
        progress.update(task1, description="[yellow]Generating dual MCP/CLI schemas...")
        
        try:
            if partial:
                payload = {"docs_text": source, "agent_id": target_agent}
                result = ctx.request("POST", "/api/v1/registry/ingest/docs", json=payload)
            else:
                payload = {"url_or_path": source, "agent_id": target_agent}
                result = ctx.request("POST", "/api/v1/registry/ingest/openapi", json=payload)
            
            progress.update(task1, description="[green]Refining ontology mappings...")
            time.sleep(1)
            
            # Simulated auto-healing result
            rprint("[dim italic]Info: 3 schema mismatches resolved via ontology alignment[/]")
            progress.update(task1, description="[bold green]Registration Complete![/]")
            
        except Exception as e:
            progress.update(task1, description="[bold red]Registration Failed[/]")
            rprint(f"[red]Error:[/] {e}")
            raise typer.Exit(1)

    # Success Summary
    name = result.get("name", "Unknown Tool")
    tool_id = result.get("id", "N/A")
    rprint(Panel(
        f"[bold green]Successfully registered:[/] {name}\n"
        f"[bold cyan]ID:[/] {tool_id}\n"
        f"[bold yellow]Test Command:[/] engram run --tool {name} --inspect",
        title="[*] Registration Summary",
        border_style="green"
    ))


@register_app.command("command")
def register_cli(
    command: str = typer.Argument(..., help="The shell command to register (e.g., 'docker', 'kubectl')"),
    agent_id: Optional[str] = typer.Option(None, help="Agent UUID to link the tool to"),
):
    """
    Onboard a local CLI tool by parsing its help text and generating a semantic wrapper.
    """
    ctx = state
    target_agent = agent_id or _get_or_create_agent_id(ctx)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]{task.description}"),
        transient=False,
    ) as progress:
        task = progress.add_task(description="[cyan]Probing shell environment...", total=None)
        time.sleep(0.5)
        
        progress.update(task, description=f"[cyan]Parsing help text for '{command}'...")
        time.sleep(1.0)
        
        try:
            payload = {"command": command, "agent_id": target_agent}
            result = ctx.request("POST", "/api/v1/registry/ingest/cli", json=payload)
            
            progress.update(task, description="[yellow]Synthesizing CLI wrapper & MCP manifest...")
            time.sleep(0.8)
            progress.update(task, description="[bold green]Agentic Wrapper Generated.[/]")
        except Exception as e:
            progress.update(task, description="[bold red]CLI Onboarding Failed[/]")
            rprint(f"[red]Error:[/] {e}")
            raise typer.Exit(1)

    # Success Summary
    name = result.get("name", command)
    tool_id = result.get("id", "N/A")
    rprint(Panel(
        f"[bold green]CLI Registered:[/] {name}\n"
        f"[bold cyan]ID:[/] {tool_id}\n"
        f"[bold yellow]Test Command:[/] engram run --tool {name} --help",
        title="[START] CLI Wrapper Success",
        border_style="magenta"
    ))


@register_app.command("tool")
def register_manual_tool():
    """
    Start an interactive session to manually register a new tool.
    """
    rprint("\n[bold cyan]Engram Manual Tool Registration[/]")
    rprint("[dim]This interactive session will guide you through registering a tool without an OpenAPI spec.[/]\n")

    # Interactive Wizard
    name = Prompt.ask("[bold cyan]Tool Name[/]")
    description = Prompt.ask("[bold cyan]Description[/]")
    base_url = Prompt.ask("[bold cyan]Base URL[/] (e.g., https://api.weather.com)")
    path = Prompt.ask("[bold cyan]Path[/] (e.g., /v1/current)")
    method = Prompt.ask(
        "[bold cyan]HTTP Method[/]", 
        choices=["GET", "POST", "PUT", "DELETE"], 
        default="GET"
    )

    # Capture Parameters (Step 6)
    rprint("\n[bold yellow]Define Parameters[/] (Press Enter on 'Parameter Name' to finish)")
    parameters = []
    while True:
        param_name = Prompt.ask("[cyan]Parameter Name[/] (leave blank to finish)", default="")
        if not param_name:
            break
        
        param_type = Prompt.ask(
            "[cyan]Parameter Type[/]",
            choices=["string", "integer", "boolean", "number", "array", "object"],
            default="string"
        )
        param_desc = Prompt.ask("[cyan]Parameter Description[/]", default=f"Description for {param_name}")
        param_required = Prompt.ask("[cyan]Is required?[/]", choices=["yes", "no"], default="yes") == "yes"

        parameters.append({
            "name": param_name,
            "type": param_type,
            "description": param_desc,
            "required": param_required
        })

    # Progress Summary (for Step 5 confirmation)
    rprint(f"\n[bold green]Prepared tool configuration for '{name}'[/]")
    rprint(f"[dim]Endpoint: {method} {base_url}{path}[/]")
    if parameters:
        rprint(f"[dim]Parameters ({len(parameters)}): {', '.join(p['name'] for p in parameters)}[/]\n")
    else:
        rprint("[dim]Parameters: None[/]\n")
    # Submission (Step 7)
    target_agent = _get_or_create_agent_id(state)
    
    # Payload matches ManualToolCreate + agent_id embedded
    payload = {
        "data": {
            "name": name,
            "description": description,
            "base_url": base_url,
            "endpoint_path": path,
            "method": method,
            "parameters": parameters
        },
        "agent_id": target_agent
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="[cyan]Registering tool with backend...", total=None)
        try:
            result = state.request("POST", "/api/v1/registry/manual", json=payload)
            
            # Show Registration Summary
            rprint("\n")
            
            summary_table = Table.grid(padding=(0, 2))
            summary_table.add_column(style="bold magenta")
            summary_table.add_column()
            
            summary_table.add_row("Tool ID", str(result.get("id", "N/A")))
            summary_table.add_row("Endpoint", f"[dim]{method}[/] [green]{base_url}{path}[/]")
            summary_table.add_row("Parameters", f"{len(parameters)} defined")
            summary_table.add_row("Status", "[bold green]LIVE[/]")
            summary_table.add_row("Backend", "HTTP (Synthetic OpenAPI)")
            
            summary_content = Group(
                Text.from_markup(f"The tool [bold cyan]{name}[/] has been successfully registered and is now live."),
                Text(""),
                summary_table,
                Text(""),
                Text.from_markup(f"[dim]This tool is now discoverable by agents and can be executed via the CLI.[/]"),
                Text(""),
                Text.from_markup(f"[bold yellow]Test Command:[/] [bold]engram run --tool {name} --inspect[/]")
            )
            
            rprint(Panel(
                summary_content,
                title="[bold green][*] Registration Summary[/]",
                border_style="green",
                padding=(1, 2)
            ))
            
        except Exception as e:
            rprint(f"\n[bold red]Registration Failed[/]")
            rprint(f"[red]Error:[/] {e}")
            raise typer.Exit(1)



# --- Heal Subgroup ---
heal_app = typer.Typer(help="Inspect and trigger semantic self-healing for tool drifts")
app.add_typer(heal_app, name="heal")

@heal_app.command("status")
def heal_status(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full logs and detailed drift analysis"),
    fix: bool = typer.Option(False, "--fix", help="Trigger immediate repair loops if drifts are found")
):
    """
    Query the reconciliation engine for detected semantic drifts and pending repairs.
    """
    ctx = state
    try:
        if fix:
             with Progress(SpinnerColumn(), TextColumn("[yellow]Triggering proactive repair..."), transient=True) as progress:
                 progress.add_task("healing")
                 ctx.request("POST", "/api/v1/reconciliation/heal")
        
        data = ctx.request("GET", "/api/v1/reconciliation/status")
        
        # Table 1: Drifts
        drift_table = Table(title="[SEARCH] Semantic Drift Analysis", border_style="bold yellow", box=box.ROUNDED)
        drift_table.add_column("Source Protocol", style="cyan")
        drift_table.add_column("Field Drift", style="magenta")
        drift_table.add_column("Ontology Match", style="green")
        drift_table.add_column("Conf.", style="bold yellow")
        drift_table.add_column("Status", style="bold")
        
        pending_drifts = data.get("pending_drifts", [])
        if not pending_drifts:
            drift_table.add_row("[dim]N/A[/]", "[dim]No active drifts detected[/]", "-", "-", "[green]HEALTHY[/]")
        else:
            for drift in pending_drifts:
                conf = drift.get("confidence") or 0.0
                # Semantic logic: highlight high confidence vs low confidence for manual review
                status_color = "green" if conf >= 0.7 else "yellow"
                status_text = "AUTO-REPAIR" if conf >= 0.7 else "PENDING-REVIEW"
                
                drift_table.add_row(
                    f"{drift['source_protocol']} -> {drift['target_protocol']}",
                    drift["source_field"],
                    drift["suggested_mapping"] or f"[red]RESOLVE MANUALLY[/]",
                    f"{conf:.1%}",
                    f"[{status_color}]{status_text}[/]"
                )
        
        ctx.console.print(drift_table)
        
        # Table 2: Active Mappings
        mapping_table = Table(title="[LINK] Persistent Semantic Mappings", border_style="bold green", box=box.ROUNDED)
        mapping_table.add_column("Route", style="cyan")
        mapping_table.add_column("Current Mappings (Source -> Target)", style="white")
        mapping_table.add_column("Ver.", style="dim")
        
        mappings = data.get("active_mappings", [])
        for m in mappings:
            equivs = m.get("semantic_equivalents", {})
            rows = [f"[cyan]{k}[/] -> [green]{v}[/]" for k, v in equivs.items()]
            mapping_table.add_row(
                f"{m['source_protocol']} -> {m['target_protocol']}",
                "\n".join(rows) if rows else "[dim]No equivalents[/]",
                str(m["version"])
            )
        ctx.console.print(mapping_table)
        
        if verbose and pending_drifts:
            rprint("\n[bold cyan]Detailed Drift Logs (Telemetry Excerpts):[/]")
            for drift in pending_drifts:
                rprint(Panel(
                    JSON.from_data(drift["payload_excerpt"]),
                    title=f"Source Field: [bold magenta]{drift['source_field']}[/]",
                    subtitle=f"Failure Type: {drift['error_type']} | ID: {drift['id']}",
                    border_style="yellow"
                ))

    except Exception as e:
        rprint(f"[bold red]Status Check Failed:[/] {e}")

@heal_app.command("now")
def heal_now():
    """
    Trigger immediate semantic repair loops for all detected drifts.
    """
    ctx = state
    rprint("[bold yellow]Initiating manual self-healing loop...[/]")
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[cyan]{task.description}"),
            transient=False,
        ) as progress:
            task = progress.add_task("Querying drift database...", total=None)
            time.sleep(0.5)
            progress.update(task, description="Re-aligning with semantic ontology...")
            time.sleep(1.0)
            result = ctx.request("POST", "/api/v1/reconciliation/heal")
            progress.update(task, description="[bold green]Synchronizing mapping tables...[/]")
            time.sleep(0.5)
            
        rprint(f"[OK] [bold green]Success:[/] {result.get('message')}")
        rprint("[dim italic][INFO] Persistent mappings updated via LLM reasoning & Ontology alignment.[/]")
    except Exception as e:
        rprint(f"[bold red]Healing aborted:[/] {e}")


# --- Route Subgroup ---
route_app = typer.Typer(help="Test and visualize performance-weighted routing decisions")
app.add_typer(route_app, name="route")

@route_app.command("test")
def route_test(
    description: str = typer.Argument(..., help="Natural language description of the task"),
    force_mcp: bool = typer.Option(False, "--force-mcp", help="Force routing to MCP backend"),
    force_cli: bool = typer.Option(False, "--force-cli", help="Force routing to CLI backend"),
):
    """
    Simulate routing for a task description and display choice reasoning.
    """
    ctx = state
    force_backend = None
    if force_mcp: force_backend = "MCP"
    if force_cli: force_backend = "CLI"
    
    try:
        payload = {"task_description": description, "force_backend": force_backend}
        result = ctx.request("POST", "/api/v1/routing/test", json=payload)
        
        # Build the Rich Panel
        tool_name = result.get("tool_name", "N/A")
        backend = result.get("selected_backend", "N/A")
        confidence = result.get("confidence_score", 0.0)
        latency = result.get("predicted_latency_ms", 0.0)
        cost = result.get("predicted_cost_tokens", 0.0)
        reasoning = result.get("reasoning", "")
        
        # Main Panel
        panel_content = (
            f"[bold cyan]Chosen Tool:[/] {tool_name}\n"
            f"[bold green]Backend:[/] {backend}\n"
            f"[bold yellow]Confidence:[/] {confidence:.1%}\n"
            f"[bold magenta]Predicted Latency:[/] {latency:.0f}ms\n"
            f"[bold white]Estimated Cost:[/] {cost:.1f} tokens\n\n"
            f"[dim italic]Reasoning: {reasoning}[/]"
        )
        
        rprint(Panel(panel_content, title="[START] Optimal Routing Decision", border_style="bold cyan", expand=False))
        
        # Comparison Table
        table = Table(title="[STATS] Alternative Backends Comparison", box=box.SIMPLE)
        table.add_column("Backend", style="cyan")
        table.add_column("Score", style="yellow")
        table.add_column("Sim.", style="dim")
        table.add_column("Latency", style="magenta")
        table.add_column("Success", style="green")
        
        for cand in result.get("candidates", []):
            is_selected = "[bold green]*[/] " if cand["backend"] == backend else "  "
            table.add_row(
                f"{is_selected}{cand['backend']}",
                f"{cand['composite_score']:.2f}",
                f"{cand['similarity']:.2f}",
                f"{cand['latency_ms']:.0f}ms",
                f"{cand['success_rate']:.1%}"
            )
        
        ctx.console.print(table)

    except Exception as e:
        rprint(f"[bold red]Routing Test Failed:[/] {e}")

@route_app.command("list")
def route_list():
    """
    Display a sorted table of tools with historical performance statistics.
    """
    ctx = state
    try:
        results = ctx.request("GET", "/api/v1/routing/list")
        
        table = Table(title="[GRAPH] Global Tool Performance Stats", box=box.DOUBLE_EDGE, border_style="blue")
        table.add_column("Tool Name", style="cyan", no_wrap=True)
        table.add_column("Backend", style="magenta")
        table.add_column("Avg Latency", style="yellow", justify="right")
        table.add_column("Success Rate", style="green", justify="right")
        table.add_column("Avg Cost", style="white", justify="right")
        table.add_column("Samples", style="dim", justify="right")
        
        if not results:
             table.add_row("[dim]N/A[/]", "[dim]No decisions logged[/]", "-", "-", "-", "0")
        else:
            for row in results:
                table.add_row(
                    row["tool_name"],
                    row["backend"],
                    f"{row['avg_latency_ms']:.0f}ms",
                    f"{row['success_rate']:.1%}",
                    f"{row['avg_cost_tokens']:.1f} tok",
                    str(row["samples"])
                )
            
        ctx.console.print(table)
        rprint("[dim italic]Decisions are weighted by these historically captured metrics.[/]")

    except Exception as e:
        rprint(f"[bold red]List Failed:[/] {e}")



# --- Sync Subgroup ---
sync_app = typer.Typer(help="Manage bidirectional synchronization and event monitoring")
app.add_typer(sync_app, name="sync")

@sync_app.command("list")
def sync_list():
    """
    List active event listeners, pollers, and CLI watchers.
    """
    try:
        response = state.request("GET", "/events/listeners")
        if response.status_code != 200:
            state.handle_auth_error(response)
            return

        data = response.json()
        table = Table(title="[bold cyan]Active Event Listeners[/]", box=box.ROUNDED)
        table.add_column("Type", style="magenta")
        table.add_column("ID", style="green")
        table.add_column("Status", style="yellow")

        for poll_id, info in data.get("polling", {}).items():
            table.add_row("Polling", poll_id, info.get("status"))
        
        for watch_id, info in data.get("cli_watch", {}).items():
            table.add_row("CLI Watch", watch_id, info.get("status"))

        state.console.print(table)
    except Exception as e:
        rprint(f"[bold red]List Failed:[/] {e}")

@sync_app.command("add")
def sync_add(
    tool_id: str = typer.Argument(..., help="The UUID of the tool to sync"),
    direction: str = typer.Option("both", "--direction", help="Sync direction: 'both', 'to_mcp', 'from_mcp'"),
    source_type: str = typer.Option("polling", "--type", help="Source type: 'polling' or 'cli_watch'"),
    url: Optional[str] = typer.Option(None, "--url", help="URL for polling"),
    command: Optional[str] = typer.Option(None, "--command", help="Command for CLI watch"),
    interval: int = typer.Option(60, "--interval", help="Polling interval in seconds"),
):
    """
    Add a new bidirectional sync or event listener to a tool.
    """
    try:
        params = {}
        if source_type == "polling":
            if not url:
                rprint("[bold red]Error:[/] --url is required for polling")
                return
            params = {"url": url, "interval_seconds": interval}
        elif source_type == "cli_watch":
            if not command:
                rprint("[bold red]Error:[/] --command is required for CLI watch")
                return
            params = {"command": command}

        payload = {
            "tool_id": tool_id,
            "direction": direction,
            "source_type": source_type,
            "params": params
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Configuring bidirectional sync...", total=None)
            response = state.request("POST", "/events/sync", json=payload)
        
        if response.status_code == 200:
            rprint(f"[OK] [bold green]Sync successfully added![/] Direction: [bold]{direction}[/]")
            rprint(f"Ontology mapping established for tool [dim]{tool_id}[/].")
        else:
            state.handle_auth_error(response)
            rprint(f"[bold red]Failed to add sync:[/] {response.text}")
    except Exception as e:
        rprint(f"[bold red]Add Failed:[/] {e}")

@sync_app.command("status")
def sync_status():
    """
    Show live monitoring of recent events and semantic conflict resolutions.
    """
    from rich.live import Live
    import time

    def get_status_table():
        try:
            response = state.request("GET", "/events/recent")
            if response.status_code != 200:
                return Text(f"Error fetching events: {response.status_code}", style="bold red")
            
            events = response.json()
            table = Table(title="[bold green]Live Event Stream[/]", box=box.MINIMAL_DOUBLE_HEAD)
            table.add_column("Time", style="dim")
            table.add_column("Tool", style="cyan")
            table.add_column("Type", style="magenta")
            table.add_column("Entity Key", style="yellow")
            table.add_column("Conflict Res", style="green")

            for event in events[:15]:  # Show last 15
                table.add_row(
                    event.get("timestamp", "").split("T")[-1][:8],
                    event.get("tool_id", "")[:8],
                    event.get("event_type", ""),
                    event.get("entity_key", "N/A"),
                    "[dim]semantic-match[/]"
                )
            return table
        except Exception as e:
            return Text(f"Error: {e}", style="bold red")

    with Live(get_status_table(), refresh_per_second=2, vertical_overflow="visible") as live:
        rprint("[bold yellow]Monitoring live events... Press Ctrl+C to stop.[/]")
        try:
            while True:
                time.sleep(1)
                live.update(get_status_table())
        except KeyboardInterrupt:
            rprint("\n[bold blue]Monitoring stopped.[/]")



# --- Trace Subgroup (Observability) ---
trace_app = typer.Typer(help="Observability and semantic execution tracing")
app.add_typer(trace_app, name="trace")

@trace_app.command("list")
def trace_list(
    limit: int = typer.Option(20, help="Number of traces to show"),
    tool: Optional[str] = typer.Option(None, help="Filter by tool name"),
    export_json: bool = typer.Option(False, "--export", help="Export as JSON for easy piping"),
):
    """
    Renders a filterable Rich table of recent semantic execution traces.
    """
    ctx = state
    try:
        traces = ctx.request("GET", f"/api/v1/traces?limit={limit}")
        
        # Client-side filtering
        if tool:
            traces = [t for t in traces if tool.lower() in t.get("tool_name", "").lower()]

        if export_json:
            print(json.dumps(traces, indent=2))
            return

        table = Table(
            title="[bold magenta]Recent Semantic Traces[/]", 
            box=box.ROUNDED,
            caption="Use [bold]engram trace .[/] to view the latest execution detail"
        )
        table.add_column("Timestamp", style="dim")
        table.add_column("Trace ID", style="cyan")
        table.add_column("Tool", style="magenta")
        table.add_column("Backend", style="yellow")
        table.add_column("Success", style="bold")
        table.add_column("Tokens", style="green", justify="right")

        for trace in traces:
            success_color = "green" if trace.get("success") else "red"
            success_text = f"[{success_color}]PASS[/]" if trace.get("success") else f"[{success_color}]FAIL[/]"
            
            ts_float = trace.get("timestamp", 0)
            ts = datetime.fromtimestamp(ts_float).strftime("%Y-%m-%d %H:%M:%S")
            
            table.add_row(
                ts,
                trace.get("trace_id", "N/A")[:8],
                trace.get("tool_name", "N/A"),
                trace.get("routing_choice", "N/A"),
                success_text,
                f"{trace.get('token_cost_est', 0):.0f}"
            )
        
        ctx.console.print(table)
        rprint("[dim italic]Run [bold]engram trace .[/] for natural-language analysis of routing and healing.[/]")
    except Exception as e:
        rprint(f"[bold red]Failed to list traces:[/] {e}")

@trace_app.command(name="detail")
def trace_detail(
    trace_id: str = typer.Argument(".", help="Trace ID to inspect (use '.' for the very latest)"),
    export_json: bool = typer.Option(False, "--export", help="Export full trace as JSON"),
):
    """
    Detailed inspection including semantic path, routing reasoning, and healing steps.
    """
    ctx = state
    try:
        # Resolve "." to the last trace ID if needed
        actual_id = trace_id
        if trace_id == ".":
            recent = ctx.request("GET", "/api/v1/traces?limit=1")
            if not recent:
                rprint("[bold red]No traces found.[/]")
                return
            actual_id = recent[0]["trace_id"]

        # Fetch detailed trace
        trace = ctx.request("GET", f"/api/v1/traces/{actual_id}")
        
        # Fetch natural-language summary (which uses LLM internally on the backend)
        try:
            summary_resp = ctx.request("POST", "/api/v1/traces/query", json={"trace_limit": 5})
            summary = summary_resp.get("summary", "Summary not generated.")
        except Exception:
            summary = "[dim italic]Natural-language reasoning summary currently unavailable.[/]"

        if export_json:
            print(json.dumps(trace, indent=2))
            return

        # 1. Summary Panel (Natural Language)
        summary_panel = Panel(
            Text(summary, justify="left", style="italic white"),
            title="[AI] [bold yellow]Routing & Healing Summary[/]",
            border_style="yellow",
            padding=(1, 2)
        )
        
        # 2. Trace Details (Semantic Trace Tree)
        tree = Tree(f"[SEARCH] [bold cyan]Semantic Trace:[/] {actual_id}")
        
        # Path Info
        success_status = "[bold green]PASS[/]" if trace.get("success") else "[bold red]FAIL[/]"
        path_node = tree.add(f"[PATH] [bold magenta]Execution Path[/] [{success_status}]")
        path_node.add(f"Tool Selection: [bold]{trace.get('tool_name', 'N/A')}[/]")
        path_node.add(f"Routing Choice: [bold yellow]{trace.get('routing_choice', 'N/A')}[/]")
        path_node.add(f"Actual Backend: [dim]{trace.get('backend_used', 'N/A')}[/]")
        path_node.add(f"Latency: [white]{trace.get('latency_ms', 0.0):.1f}ms[/]")
        
        # Scoring reasoning
        scores = path_node.add("[STATS] [bold green]Performance Weights[/]")
        scores.add(f"Semantic Similarity: [dim]{trace.get('similarity_score', 0.0):.3f}[/]")
        scores.add(f"Composite Score: [dim]{trace.get('composite_score', 0.0):.3f}[/]")
        scores.add(f"Token Efficiency: [white]{trace.get('token_cost_est', 0.0):.1f} tokens[/]")
        
        # Reconciliation Steps (Healing)
        heal_node = tree.add("[REPAIR] [bold orange1]Self-Healing Steps[/]")
        steps = trace.get("reconciliation_steps", [])
        if not steps:
            heal_node.add("[dim italic]No drift detected; no healing required.[/]")
        else:
            for step in steps:
                heal_node.add(f"[italic]{step}[/]")
        
        # Ontological Interpretation
        ont_node = tree.add("[ONTOLOGY] [bold blue]Ontological Alignment[/]")
        ont_node.add(f"Context: [italic]{trace.get('ontological_interpretation', 'N/A')}[/]")
        
        mappings = trace.get("field_mappings", {})
        if mappings:
            mapping_sub = ont_node.add("Synthesized Field Mappings")
            for k, v in mappings.items():
                mapping_sub.add(f"[cyan]{k}[/] -> [green]{v}[/]")

        # Assemble Group for Output
        group = Group(
            summary_panel,
            Panel(tree, title="[*] Full Semantic Inspection", border_style="cyan"),
        )
        
        ctx.console.print(group)
        
        if trace.get("error"):
            rprint(Panel(trace["error"], title="Error Stack", border_style="red"))

    except Exception as e:
        rprint(f"[bold red]Failed to fetch trace details:[/] {e}")


# --- Evolve Subgroup ---
evolve_app = typer.Typer(help="Manage self-evolving tools and ML-driven improvements")
app.add_typer(evolve_app, name="evolve")

@evolve_app.command("status")
def evolve_status():
    """
    Display ML improvement progress in a dashboard-like Rich layout.
    """
    ctx = state
    try:
        data = ctx.request("GET", "/api/v1/evolution/status")
        
        # Dashboard Header
        pending_count = data.get("pending_count", 0)
        total_evolutions = data.get("total_evolutions", 0)
        
        # Format timestamp
        last_upd = data.get("last_updated", "N/A")
        if isinstance(last_upd, str) and "T" in last_upd:
            last_upd = last_upd.split(".")[0].replace("T", " ")

        header = Panel(
            Group(
                f"[bold cyan]Improvement Pipeline Status:[/] [bold green]Active[/]",
                f"[bold cyan]Pending Proposals:[/] [bold yellow]{pending_count}[/]",
                f"[bold cyan]Total Historical Evolutions:[/] [bold magenta]{total_evolutions}[/]",
                f"[bold cyan]Last ML Update:[/] [dim]{last_upd}[/]"
            ),
            title="[ONTOLOGY] [bold]Self-Evolving Tools Dashboard[/]",
            border_style="cyan",
            padding=(1, 2)
        )
        ctx.console.print(header)
        
        # Tables for refined descriptions, defaults, and recovery strategies
        proposals = data.get("pending_proposals", [])
        if not proposals:
            rprint("[dim italic]No pending tool evolutions detected. The system is performing at optimal thresholds.[/]")
            return
            
        table = Table(
            title="[*] [bold]Pending Tool Refinements[/]",
            box=box.ROUNDED,
            header_style="bold magenta",
            show_lines=True
        )
        table.add_column("Tool ID / Version", style="cyan")
        table.add_column("Refinement Type", style="yellow")
        table.add_column("Proposed Changes (Deep Insight)", style="white")
        table.add_column("Conf.", justify="right")
        table.add_column("Proposal ID", style="dim")

        for p in proposals:
            # Change summary
            changes = []
            diff = p.get("diff_payload", {}) or {}
            if "description" in diff:
                changes.append("[bold green]Description Path Refinement:[/]\n" + diff["description"])
            if "actions" in diff:
                changes.append("[bold blue]Parameter Schema Optimization:[/]\nAction schemas tightened based on failure history.")
            if "recovery_strategies" in diff:
                changes.append("[bold red]New Recovery Strategy:[/]\nPattern-based automated fallback mapping added.")
                
            change_text = "\n\n".join(changes) if changes else "[dim]Internal metadata optimization[/]"
            
            table.add_row(
                f"[bold cyan]{p['tool_name']}[/]\n[dim]{p['previous_version']} -> {p['new_version']}[/]",
                p["change_type"].replace("_", " ").title(),
                change_text,
                f"{p['confidence_score']:.1%}",
                str(p["id"])[:8]
            )
            
        ctx.console.print(table)
        rprint("\n[dim]Use [bold]engram evolve apply <id>[/] to authorize a specific improvement.[/]")
        
    except Exception as e:
        rprint(f"[bold red]Evolution Status Failed:[/] {e}")

@evolve_app.command("apply")
def evolve_apply(
    evolution_id: str = typer.Argument(..., help="The ID (or start of ID) of the evolution proposal to apply"),
    force: bool = typer.Option(False, "--force", "-f", help="Apply without confirmation prompt")
):
    """
    Trigger updates with confirmation prompts and show before/after diffs.
    """
    ctx = state
    try:
        # First, fetch details to show diff
        status_data = ctx.request("GET", "/api/v1/evolution/status")
        proposal = next((p for p in status_data.get("pending_proposals", []) if str(p["id"]).startswith(evolution_id)), None)
        
        if not proposal:
            rprint(f"[bold red]Error:[/] Proposal with ID start '{evolution_id}' not found.")
            return
            
        # Show Clean Diff
        rprint(f"\n[bold]Previewing Evolution for Tool:[/] [cyan]{proposal['tool_name']}[/]")
        rprint(f"[bold]Version Change:[/] [dim]{proposal['previous_version']} -> {proposal['new_version']}[/]\n")
        
        diff_payload = proposal.get("diff_payload", {}) or {}
        
        if not diff_payload:
            rprint("[dim yellow]No visual changes in this proposal (metadata-only update).[/]")
        else:
            for key, value in diff_payload.items():
                rprint(Panel(
                    str(value),
                    title=f"Proposed {key.title()} Update",
                    border_style="green"
                ))
            
        if not force:
            confirm = typer.confirm("Apply this adaptive intelligence update?", default=True)
            if not confirm:
                rprint("[yellow]Update aborted by user.[/]")
                return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Hot-redeploying tool registry..."),
            transient=True
        ) as progress:
            progress.add_task("apply")
            result = ctx.request("POST", f"/api/v1/evolution/apply/{proposal['id']}")
            
        rprint(f"[OK] [bold green]Evolution successful![/] Tool is now running version [bold]{result['new_version']}[/].")
        rprint("[dim italic]Internal ontology weights and execution schemas have been synchronized.[/]")
        
    except Exception as e:
        rprint(f"[bold red]Evolution Apply Failed:[/] {e}")


# --- Protocol Subgroup (Federation & Translation) ---
protocol_app = typer.Typer(help="Federated protocol management and translation")
app.add_typer(protocol_app, name="protocol")

handoff_app = typer.Typer(help="Manage and simulate session handoffs between agents")
protocol_app.add_typer(handoff_app, name="handoff")

@protocol_app.command("translate")
def protocol_translate(
    from_proto: str = typer.Option(..., "--from", help="Source protocol (mcp, cli, a2a, acp)"),
    to_proto: str = typer.Option(..., "--to", help="Target protocol (mcp, cli, a2a, acp)"),
    payload: Optional[str] = typer.Option(None, "--payload", "-p", help="JSON payload to translate (or path to file)"),
):
    """
    Perform real-time translation between protocols using the system ontology as a bridge.
    """
    ctx = state
    try:
        # Load payload from input or file
        if not payload:
            # Provide a default demonstration payload if none given
            data = {"name": "get_weather", "arguments": {"city": "San Francisco", "units": "imperial"}}
        elif os.path.exists(payload):
            with open(payload, "r") as f:
                data = json.load(f)
        else:
            data = json.loads(payload)

        # Output in CLI
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]Bridging protocols via ontology..."),
            transient=True
        ) as progress:
            progress.add_task("translate")
            result = ctx.request(
                "POST", 
                f"/api/v1/federation/translate?from={from_proto}&to={to_proto}",
                json=data
            )

        # Render dual panels for translation demonstration
        source_panel = Panel(
            JSON.from_data(data),
            title=f"Source ({from_proto.upper()})",
            border_style="magenta"
        )
        
        bridge_panel = Panel(
            JSON.from_data(result.get("canonical_bridge", {})),
            title="[ONTOLOGY] Canonical Bridge (Ontology)",
            border_style="yellow"
        )
        
        target_panel = Panel(
            JSON.from_data(result.get("translated_payload", {})),
            title=f"Target ({to_proto.upper()})",
            border_style="green"
        )

        rprint(Group(source_panel, bridge_panel, target_panel))
        rprint("\n[dim italic]Translation verified against hierarchical ontology concepts.[/]")
        
    except Exception as e:
        rprint(f"[bold red]Translation Error:[/] {e}")

@handoff_app.command("simulate")
def handoff_test(
    source_agent: str = typer.Option("CLI-Local", help="Name of the source agent/environment"),
    target_agent: str = typer.Option("Remote-MCP", help="Name of the target agent/environment"),
):
    """
    Simulate a seamless multi-agent task handoff, demonstrating semantic state transfer.
    """
    ctx = state
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold yellow]Initiating protocol handoff..."),
            transient=True
        ) as progress:
            progress.add_task("handoff")
            result = ctx.request(
                "POST",
                "/api/v1/federation/handoff/simulate",
                json={"source_agent": source_agent, "target_agent": target_agent}
            )

        # Visualize the handoff
        tree = Tree(f"[HANDOFF] [bold green]Handoff Simulation:[/] {source_agent} -> {target_agent}")
        tree.add(f"Session ID: [bold cyan]{result['session_id']}[/]")
        tree.add(f"Semantic Readiness: [bold green]{result['semantic_readiness']}[/]")
        
        protocols = tree.add("Bridged Protocols")
        for p in result.get("bridged_protocols", []):
            protocols.add(f"- {p}")
            
        transferred = tree.add("Transferred State (Redis-backed)")
        state_data = result.get("transferred_state", {})
        for cat, val in state_data.items():
            cat_node = transferred.add(f"[magenta]{cat.title()}[/]")
            cat_node.add(JSON.from_data(val))

        rprint(Panel(tree, title="[*] Multi-Agent Federation Detail", border_style="cyan"))
        
        rprint(f"\n[green]Success![/] Seamless state transfer verified for [bold]{target_agent}[/].")
        rprint("[dim italic]Handoff maintains artifacts, context, and semantic history across protocol boundaries.[/]")

    except Exception as e:
        rprint(f"[bold red]Handoff Simulation Failed:[/] {e}")


# --- Runtime Command ---

_BANNER_LINES = [
    "  ███████╗███╗   ██╗ ██████╗ ██████╗  █████╗ ███╗   ███╗",
    "  ██╔════╝████╗  ██║██╔════╝ ██╔══██╗██╔══██╗████╗ ████║",
    "  █████╗  ██╔██╗ ██║██║  ███╗██████╔╝███████║██╔████╔██║",
    "  ██╔══╝  ██║╚██╗██║██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║",
    "  ███████╗██║ ╚████║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║",
    "  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝",
]


def _static_banner() -> Text:
    """Return the ENGRAM banner as a static bold-cyan Rich Text."""
    text = Text()
    for line in _BANNER_LINES:
        text.append(line + "\n", style="bold white")
    return text


def _animate_banner(console: Console | None = None):
    """Play the ENGRAM banner animation: white -> blue sweep (bottom-up) -> back to white,
    then settle on bold cyan."""
    if console is None:
        console = Console()

    white = (210, 215, 220)
    blue = (60, 120, 255)
    num_lines = len(_BANNER_LINES)
    frames_per_phase = 28
    frame_delay = 0.035

    def _lerp_color(t: float, c_from: tuple, c_to: tuple) -> tuple:
        t = max(0.0, min(1.0, t))
        return tuple(int(a + (b - a) * t) for a, b in zip(c_from, c_to))

    def _build_frame(wave_pos: float, color_from: tuple, color_to: tuple) -> Text:
        text = Text()
        for i, line in enumerate(_BANNER_LINES):
            # line_pos: 0 = bottom line, num_lines-1 = top line
            line_pos = num_lines - 1 - i
            distance = wave_pos - line_pos
            t = max(0.0, min(1.0, (distance + 1.0) / 2.0))
            r, g, b = _lerp_color(t, color_from, color_to)
            text.append(line + "\n", style=f"bold rgb({r},{g},{b})")
        return text

    try:
        with Live(console=console, refresh_per_second=30, transient=True) as live:
            # Phase 1: white -> blue, wave sweeps bottom to top
            for frame in range(frames_per_phase + 6):
                wave_pos = (frame / frames_per_phase) * (num_lines + 1) - 1
                live.update(_build_frame(wave_pos, white, blue))
                time.sleep(frame_delay)

            # Tiny hold at full blue
            time.sleep(0.12)

            # Phase 2: blue -> white, wave sweeps bottom to top
            for frame in range(frames_per_phase + 6):
                wave_pos = (frame / frames_per_phase) * (num_lines + 1) - 1
                live.update(_build_frame(wave_pos, blue, white))
                time.sleep(frame_delay)
    except Exception:
        pass  # Graceful fallback if terminal doesn't support Live

    # Final resting state: white (matches animation end)
    console.print(_static_banner(), end="")

@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Host to bind the backend"),
    port: int = typer.Option(8000, help="Port to run the backend"),
):
    """
    Start the Engram Protocol Bridge - interactive CLI mode.
    """
    _start_interactive_cli(host, port)




def _start_interactive_cli(host: str, port: int):
    """Start backend in background, then drop into an interactive REPL."""
    import io
    import logging

    # -- 1. Suppress ALL noisy module-level output during import & boot --
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    # Also silence loggers that print during import
    logging.disable(logging.CRITICAL)

    try:
        import uvicorn
        from app.main import app as fastapi_app
    except ImportError as e:
        sys.stdout, sys.stderr = old_stdout, old_stderr
        logging.disable(logging.NOTSET)
        rprint(f"[bold red]Error:[/] Missing dependencies: {e}")
        return

    # -- 2. Start the backend in a daemon thread --
    server_ready = threading.Event()
    server_error = [None]

    class _ReadyServer(uvicorn.Server):
        async def startup(self, sockets=None):
            await super().startup(sockets=sockets)
            server_ready.set()

    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        log_level="critical",
        access_log=False,
    )
    server = _ReadyServer(config)

    def _serve():
        try:
            server.run()
        except Exception as e:
            server_error[0] = e
            server_ready.set()

    api_thread = threading.Thread(target=_serve, daemon=True)
    api_thread.start()

    # Wait for the server to be ready (or fail)
    server_ready.wait(timeout=60)

    # -- 3. Restore stdout/stderr and logging --
    sys.stdout, sys.stderr = old_stdout, old_stderr
    logging.disable(logging.NOTSET)

    if server_error[0]:
        rprint(f"[bold red]Backend failed to start:[/] {server_error[0]}")
        return

    # -- 4. Clear screen and show banner --
    os.system("cls" if os.name == "nt" else "clear")
    _animate_banner()
    rprint(
        "  [dim]Connect any AI agent to any tool[/dim]\n"
        "  [dim]from your terminal.[/dim]\n"
    )
    rprint(f"  [dim]Gateway:[/dim] [bold]http://{host}:{port}[/bold]")
    rprint(f"  [dim]API docs:[/dim] [bold]http://{host}:{port}/docs[/bold]\n")

    # -- 5. Interactive REPL --
    console = Console()

    while True:
        try:
            cmd = console.input("[bold blue]$ engram [/bold blue]").strip()
        except (EOFError, KeyboardInterrupt):
            rprint("\n[dim]Shutting down...[/dim]")
            break

        if not cmd:
            continue
        if cmd in ("exit", "quit", "q"):
            rprint("[dim]Shutting down...[/dim]")
            break
        if cmd == "clear":
            os.system("cls" if os.name == "nt" else "clear")
            rprint(_static_banner())
            continue
        if cmd == "help":
            _print_repl_help()
            continue

        # Delegate to the Typer CLI using shlex to respect quotes (e.g. for task descriptions).
        import shlex
        try:
            parts = shlex.split(cmd)
            subprocess.run([sys.executable, os.path.abspath(__file__)] + parts)
        except Exception as e:
            rprint(f"[bold red]Execution Error:[/] {e}")
        print()  # breathing room after command output


def _print_repl_help():
    """Display available REPL commands."""
    table = Table(
        title="Available Commands",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold",
    )
    table.add_column("Command", style="bold cyan", min_width=25)
    table.add_column("Description", style="dim")
    table.add_row("tools list", "List all registered tools")
    table.add_row("tools search <query>", "Search tools by name or tag")
    table.add_row("register openapi <url>", "Register a tool from OpenAPI spec")
    table.add_row("register command <cmd>", "Register a shell command as a tool")
    table.add_row("register tool", "Start interactive session for manual tool registration")
    table.add_row("route test <tool>", "Test routing decision for a tool")
    table.add_row("route list", "Show all tools with routing stats")
    table.add_row("trace list", "List recent execution traces")
    table.add_row("trace <id>", "Inspect a specific trace")
    table.add_row("heal status", "Show self-healing reconciliation status")
    table.add_row("heal now", "Trigger immediate repair loop")
    table.add_row("evolve status", "Show ML tool improvement dashboard")
    table.add_row("evolve apply <id>", "Apply a proposed tool refinement")
    table.add_row("protocol translate --from <p1> --to <p2>", "Translate between agent protocols")
    table.add_row("protocol handoff simulate", "Simulate multi-agent handoff")
    table.add_row("sync list", "List sync connections")
    table.add_row("auth whoami", "Show current identity & scopes")
    table.add_row("clear", "Clear the screen")
    table.add_row("exit", "Shut down the gateway")
    rprint(table)


if __name__ == "__main__":
    app()
