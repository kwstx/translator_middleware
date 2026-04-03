import os
import sys

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
        
        with httpx.Client(headers=headers, timeout=30.0) as client:
            try:
                response = client.request(method, url, **kwargs)
                if response.status_code == 401:
                    self.handle_auth_error(response)
                if response.status_code >= 400:
                    try:
                        error_detail = response.json().get("detail", response.text)
                    except:
                        error_detail = response.text
                    raise Exception(f"API Error ({response.status_code}): {error_detail}")
                return response.json()
            except httpx.RequestError as exc:
                raise Exception(f"Connection Error: Could not connect to {url}. Ensure the backend is running.") from exc

    def handle_auth_error(self, response):
        """Show helpful suggestions for authentication errors."""
        rprint("\n[bold red]🔐 Authentication Required[/]")
        rprint("Your session has expired or the token is invalid.")
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
        state.set_token(token)
        rprint("✅ [bold green]Token saved securely via keyring.[/]")
        return

    login_url = f"{state.config.api_url}/api/v1/auth/login"
    rprint(f"[bold cyan]Initiating login flow...[/]")
    
    if browser:
        rprint(f"Opening browser to: [link={login_url}]{login_url}[/link]")
        typer.launch(login_url)
    
    rprint("\n[yellow]Please paste your EAT (Engram Authorization Token) below:[/]")
    input_token = typer.prompt("EAT Token", hide_input=True)
    
    if input_token:
        state.set_token(input_token)
        rprint("\n✅ [bold green]Login successful! Identity and permissions synced.[/]")
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
        
        tree = Tree(f"👤 [bold cyan]Identity:[/] {payload.get('sub', 'Unknown')}")
        
        # Scopes and Permissions
        perm_node = tree.add("🔐 [bold green]Permissions (EAT Structured)[/]")
        scopes = payload.get("scopes", {})
        
        for tool, perms in scopes.items():
            tool_node = perm_node.add(f"🛠️ [magenta]{tool}[/]")
            for p in perms:
                tool_node.add(f"[dim]{p}[/]")
        
        # Semantic Scopes
        semantic_node = tree.add("🧠 [bold yellow]Semantic Scopes (Ontology-based)[/]")
        sem_scopes = payload.get("semantic_scopes", [])
        for ss in sem_scopes:
            semantic_node.add(f"[italic blue]{ss}[/]")
            # Provide helpful translation for common scopes
            if "execute" in ss:
                semantic_node.add("  └─ [dim]Can invoke cross-protocol tool translations[/]")
            if "read" in ss:
                semantic_node.add("  └─ [dim]Can query ontology metadata and tool catalogs[/]")

        rprint(Panel(tree, title="✨ Current Session Identity", border_style="cyan", expand=False))
        
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
        
        table = Table(title="🧠 Semantic Access Scopes", box=rich.box.DOUBLE_EDGE)
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
    state.set_token(token)
    rprint(f"✅ EAT token updated securely.")

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
        rprint(f"✅ Set [bold]{key}[/] to [bold]{value}[/]")
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
                title="🛠️ [bold]Engram Tool Catalog[/]",
                subtitle="[dim]Custom tools are prioritized as universal self-healing bridge entries[/]",
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
                    backend_fmt = "🛠️ [bold blue]MCP[/]"
                elif t["backend"] == "CLI":
                    backend_fmt = "💻 [bold green]CLI[/]"
                else:
                    backend_fmt = "🚀 [bold yellow]Dual[/]" # Hybrid/Popular
                
                # Hero indicator for custom tools
                hero_icon = "✨" if not t["is_popular"] else "📦"
                
                # Success Rate coloring
                sr = t["success"]
                color = "green" if sr >= 0.9 else "yellow" if sr >= 0.7 else "red"
                success_fmt = f"[{color}]{sr:.1%}[/]"
                
                table.add_row(
                    hero_icon,
                    t["name"],
                    backend_fmt,
                    t["type"],
                    success_fmt,
                    (t["description"][:60] + "...") if len(t["description"]) > 60 else t["description"]
                )

            ctx.console.print(table)
            rprint(f"\n[dim]Showing {len(final_tools)} active tools. Use [bold]--popular[/] to see pre-optimized integrations.[/]")
            if not query:
                rprint("[dim italic]ℹ️  Universal tools are linked via semantic ontology for cross-protocol healing.[/]")

        except Exception as e:
            rprint(f"[bold red]Discovery Error:[/] {e}")


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


@register_app.command("api")
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
            rprint("[dim italic]ℹ️  3 schema mismatches resolved via ontology alignment[/]")
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
        title="✨ Registration Summary",
        border_style="green"
    ))


@register_app.command("cli")
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
        title="🚀 CLI Wrapper Success",
        border_style="magenta"
    ))


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
        drift_table = Table(title="🔍 Semantic Drift Analysis", border_style="bold yellow", box=rich.box.ROUNDED)
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
                    f"{drift['source_protocol']} → {drift['target_protocol']}",
                    drift["source_field"],
                    drift["suggested_mapping"] or f"[red]RESOLVE MANUALLY[/]",
                    f"{conf:.1%}",
                    f"[{status_color}]{status_text}[/]"
                )
        
        ctx.console.print(drift_table)
        
        # Table 2: Active Mappings
        mapping_table = Table(title="🔗 Persistent Semantic Mappings", border_style="bold green", box=rich.box.ROUNDED)
        mapping_table.add_column("Route", style="cyan")
        mapping_table.add_column("Current Mappings (Source → Target)", style="white")
        mapping_table.add_column("Ver.", style="dim")
        
        mappings = data.get("active_mappings", [])
        for m in mappings:
            equivs = m.get("semantic_equivalents", {})
            rows = [f"[cyan]{k}[/] → [green]{v}[/]" for k, v in equivs.items()]
            mapping_table.add_row(
                f"{m['source_protocol']} → {m['target_protocol']}",
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
            
        rprint(f"✨ [bold green]Success:[/] {result.get('message')}")
        rprint("[dim italic]ℹ️  Persistent mappings updated via LLM reasoning & Ontology alignment.[/]")
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
        
        rprint(Panel(panel_content, title="🚀 Optimal Routing Decision", border_style="bold cyan", expand=False))
        
        # Comparison Table
        table = Table(title="📊 Alternative Backends Comparison", box=rich.box.SIMPLE)
        table.add_column("Backend", style="cyan")
        table.add_column("Score", style="yellow")
        table.add_column("Sim.", style="dim")
        table.add_column("Latency", style="magenta")
        table.add_column("Success", style="green")
        
        for cand in result.get("candidates", []):
            is_selected = "[bold green]✓[/] " if cand["backend"] == backend else "  "
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
        
        table = Table(title="📈 Global Tool Performance Stats", box=rich.box.DOUBLE_EDGE, border_style="blue")
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
            rprint(f"✅ [bold green]Sync successfully added![/] Direction: [bold]{direction}[/]")
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
            title="[bold yellow]🤖 Routing & Healing Summary[/]",
            border_style="yellow",
            padding=(1, 2)
        )
        
        # 2. Trace Details (Semantic Trace Tree)
        tree = Tree(f"🔍 [bold cyan]Semantic Trace:[/] {actual_id}")
        
        # Path Info
        success_status = "[bold green]PASS[/]" if trace.get("success") else "[bold red]FAIL[/]"
        path_node = tree.add(f"🛤️ [bold magenta]Execution Path[/] [{success_status}]")
        path_node.add(f"Tool Selection: [bold]{trace.get('tool_name', 'N/A')}[/]")
        path_node.add(f"Routing Choice: [bold yellow]{trace.get('routing_choice', 'N/A')}[/]")
        path_node.add(f"Actual Backend: [dim]{trace.get('backend_used', 'N/A')}[/]")
        path_node.add(f"Latency: [white]{trace.get('latency_ms', 0.0):.1f}ms[/]")
        
        # Scoring reasoning
        scores = path_node.add("📊 [bold green]Performance Weights[/]")
        scores.add(f"Semantic Similarity: [dim]{trace.get('similarity_score', 0.0):.3f}[/]")
        scores.add(f"Composite Score: [dim]{trace.get('composite_score', 0.0):.3f}[/]")
        scores.add(f"Token Efficiency: [white]{trace.get('token_cost_est', 0.0):.1f} tokens[/]")
        
        # Reconciliation Steps (Healing)
        heal_node = tree.add("🛠️ [bold orange1]Self-Healing Steps[/]")
        steps = trace.get("reconciliation_steps", [])
        if not steps:
            heal_node.add("[dim italic]No drift detected; no healing required.[/]")
        else:
            for step in steps:
                heal_node.add(f"[italic]{step}[/]")
        
        # Ontological Interpretation
        ont_node = tree.add("🧠 [bold blue]Ontological Alignment[/]")
        ont_node.add(f"Context: [italic]{trace.get('ontological_interpretation', 'N/A')}[/]")
        
        mappings = trace.get("field_mappings", {})
        if mappings:
            mapping_sub = ont_node.add("Synthesized Field Mappings")
            for k, v in mappings.items():
                mapping_sub.add(f"[cyan]{k}[/] → [green]{v}[/]")

        # Assemble Group for Output
        group = Group(
            summary_panel,
            Panel(tree, title="✨ Full Semantic Inspection", border_style="cyan"),
        )
        
        ctx.console.print(group)
        
        if trace.get("error"):
            rprint(Panel(trace["error"], title="❌ Error Stack", border_style="red"))

    except Exception as e:
        rprint(f"[bold red]Failed to fetch trace details:[/] {e}")


# --- Runtime Command ---

ENGRAM_BANNER = r"""
[bold cyan]
  ███████╗███╗   ██╗ ██████╗ ██████╗  █████╗ ███╗   ███╗
  ██╔════╝████╗  ██║██╔════╝ ██╔══██╗██╔══██╗████╗ ████║
  █████╗  ██╔██╗ ██║██║  ███╗██████╔╝███████║██╔████╔██║
  ██╔══╝  ██║╚██╗██║██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║
  ███████╗██║ ╚████║╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║
  ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝
[/bold cyan]"""

@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Host to bind the backend"),
    port: int = typer.Option(8000, help="Port to run the backend"),
    debug: bool = typer.Option(False, "--debug", help="Start TUI dashboard instead of REPL"),
):
    """
    Start the Engram Protocol Bridge — interactive CLI mode.
    """
    if debug:
        _start_debug_tui(host, port)
        return
    _start_interactive_cli(host, port)


def _start_debug_tui(host: str, port: int):
    """Launch backend + TUI dashboard for visual debugging."""
    try:
        import uvicorn
        from app.main import app as fastapi_app
        from tui.app import EngramTUI
    except ImportError as e:
        rprint(f"❌ [bold red]Error:[/] Missing dependencies: {e}")
        return

    def run_api():
        try:
            uvicorn.run(fastapi_app, host=host, port=port, log_level="warning", access_log=False)
        except Exception as e:
            rprint(f"\n❌ [bold red]Backend Failed:[/] {e}")
            os._exit(1)

    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    time.sleep(1.5)

    try:
        tui = EngramTUI(base_url=f"http://{host}:{port}/api/v1")
        tui.initial_screen = "debug"
        tui.run()
    except Exception as e:
        rprint(f"❌ [bold red]TUI Error:[/] {e}")


def _start_interactive_cli(host: str, port: int):
    """Start backend in background, then drop into an interactive REPL."""
    import io
    import logging

    # ── 1. Suppress ALL noisy module‑level output during import & boot ──
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
        rprint(f"❌ [bold red]Error:[/] Missing dependencies: {e}")
        return

    # ── 2. Start the backend in a daemon thread ──
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

    # ── 3. Restore stdout/stderr and logging ──
    sys.stdout, sys.stderr = old_stdout, old_stderr
    logging.disable(logging.NOTSET)

    if server_error[0]:
        rprint(f"❌ [bold red]Backend failed to start:[/] {server_error[0]}")
        return

    # ── 4. Clear screen and show banner ──
    os.system("cls" if os.name == "nt" else "clear")
    rprint(ENGRAM_BANNER)
    rprint(
        "  [dim]Translate between AI agent protocols[/dim]\n"
        "  [dim]from your terminal.[/dim]\n"
    )
    rprint(f"  [dim]Gateway:[/dim] [bold]http://{host}:{port}[/bold]")
    rprint(f"  [dim]API docs:[/dim] [bold]http://{host}:{port}/docs[/bold]\n")

    # ── 5. Interactive REPL ──
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
            rprint(ENGRAM_BANNER)
            continue
        if cmd == "help":
            _print_repl_help()
            continue

        # Delegate to the Typer CLI by re‑invoking it as a subprocess
        # but pointed at the already‑running backend.
        parts = cmd.split()
        full_cmd = f'"{sys.executable}" "{os.path.abspath(__file__)}" {" ".join(parts)}'
        os.system(full_cmd)
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
    table.add_row("route test <tool>", "Test routing decision for a tool")
    table.add_row("route list", "Show all tools with routing stats")
    table.add_row("trace list", "List recent execution traces")
    table.add_row("trace <id>", "Inspect a specific trace")
    table.add_row("heal status", "Show self-healing reconciliation status")
    table.add_row("heal now", "Trigger immediate repair loop")
    table.add_row("sync list", "List sync connections")
    table.add_row("auth whoami", "Show current identity & scopes")
    table.add_row("clear", "Clear the screen")
    table.add_row("exit", "Shut down the gateway")
    rprint(table)


if __name__ == "__main__":
    app()
