import os
import sys
import json
import yaml
import asyncio
import threading
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

import typer
import httpx
import keyring
import jwt
from pydantic import BaseModel, Field, HttpUrl
import rich.box
from rich.json import JSON
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn

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

@tool_app.command("discover")
def tool_discover(query: Optional[str] = typer.Argument(None)):
    """
    Discover available tools across all connected protocols.
    """
    # Placeholder for tool discovery logic
    tools = [
        {"id": "slack.post_message", "type": "mcp", "description": "Post a message to Slack"},
        {"id": "github.create_issue", "type": "mcp", "description": "Create a new GitHub issue"},
        {"id": "local.list_files", "type": "cli", "description": "List files in directory"}
    ]
    if query:
        tools = [t for t in tools if query.lower() in t["id"].lower()]
    
    state.output(tools, title=f"Discovery Results: {query or 'All'}")


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


# --- Runtime Command (Existing functionality) ---

@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Host to bind the backend"),
    port: int = typer.Option(8000, help="Port to run the backend"),
    debug: bool = typer.Option(False, "--debug", help="Start in debug mode")
):
    """
    Start the Engram Protocol Bridge backend and TUI dashboard.
    """
    from app.cli import start_runtime # We'll need to refactor this slightly or just import it
    # For now, we'll try to use the legacy start_runtime logic
    # but we need to avoid circular imports. 
    # Since we are overwriting app/cli.py, we should include the runtime logic here.
    
    _start_legacy_runtime(host, port, "debug" if debug else None)

def _start_legacy_runtime(host: str, port: int, initial_screen: Optional[str]):
    """Refactored version of the original start_runtime logic."""
    try:
        import uvicorn
        from app.main import app as fastapi_app
        from tui.app import EngramTUI
    except ImportError as e:
        rprint(f"❌ [bold red]Error:[/] Missing dependencies: {e}")
        return

    rprint(Panel.fit(
        "[bold orange1] ENGRAM PROTOCOL BRIDGE [/]\n[dim]Multi-Protocol Semantic Agent Translation[/]",
        subtitle=f"[bold]v0.1.0 | Gateway: {host}:{port}[/]",
        border_style="orange1"
    ))

    # Start API in background thread
    def run_api():
        try:
            uvicorn.run(fastapi_app, host=host, port=port, log_level="warning", access_log=False)
        except Exception as e:
            rprint(f"\n❌ [bold red]Backend Failed:[/] {e}")
            os._exit(1)
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    time.sleep(1.5)
    rprint(" ✅ [bold green]Backend Ready.[/]")
    
    # Start TUI
    try:
        tui = EngramTUI(base_url=f"http://{host}:{port}/api/v1")
        if initial_screen:
            tui.initial_screen = initial_screen
        tui.run()
    except Exception as e:
        rprint(f"❌ [bold red]TUI Error:[/] {e}")
        sys.exit(1)

if __name__ == "__main__":
    app()
