import os
import yaml
import sys
import argparse
import threading
import time
from pathlib import Path
from typing import Optional

def get_config_dir() -> Path:
    """Returns the Engram config directory (~/.engram/)."""
    return Path.home() / ".engram"

def init_config():
    """Generates the initial config.yaml in ~/.engram/."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = config_dir / "config.yaml"
    
    config_content = {
        "model_provider": "openai",
        "base_url": os.getenv("ENGRAM_BASE_URL", "http://127.0.0.1:8000"),
        "default_personality": "optimistic"
    }
    
    # Do not overwrite if exists
    if not config_path.exists():
        with open(config_path, "w") as f:
            yaml.dump(config_content, f, default_flow_style=False)
        print(f"✅ Initialized Engram config at {config_path}")
    else:
        print(f"ℹ️ Config already exists at {config_path}")

def check_external_dependencies():
    """Checks for important but potentially problematic external dependencies."""
    from rich import print as rprint
    
    # 1. SWI-Prolog check (pyswip requirement)
    try:
        import pyswip
        # Try a dummy query or just import? Import is usually enough to catch missing libswipl
    except (ImportError, OSError):
        rprint("\n[bold yellow]⚠️  Warning: SWI-Prolog Shared Library Not Found[/]")
        rprint("[dim]Prolog-based semantic rules will be disabled. To enable them:[/]")
        if sys.platform == "win32":
            rprint("[dim]1. Install SWI-Prolog: https://www.swi-prolog.org/download/stable[/]")
            rprint("[dim]2. Add bin folder to Path (e.g. C:\\Program Files\\swipl\\bin)[/]")
        elif sys.platform == "darwin":
            rprint("[dim]Install via brew: 'brew install swi-prolog'[/]")
        else:
            rprint("[dim]Install via apt: 'sudo apt install swi-prolog'[/]")
        rprint("")

def start_runtime(host: str = "127.0.0.1", port: int = 8000, initial_screen: Optional[str] = None):
    """Launches the unified Engram runtime (API + TUI)."""
    try:
        from rich import print as rprint
        from rich.panel import Panel
        from rich.console import Console
        import uvicorn
    except ImportError as e:
        print(f"❌ Error: Missing core dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

    try:
        from app.main import app
        from textual import run
        from tui.app import EngramTUI, load_config
    except ImportError as e:
        rprint(f"❌ [bold red]Error:[/] Could not load Engram modules: {e}")
        rprint("[dim]Ensure you are running from the project root or PYTHONPATH is set.[/]")
        sys.exit(1)

    console = Console()
    
    # Check for library issues (like pyswip) but don't crash
    check_external_dependencies()
    
    # 1. Display Brand Banner
    rprint(Panel.fit(
        "[bold orange1] ENGRAM DEBUG CONSOLE [/]" if initial_screen == "debug" else "[bold orange1] ENGRAM PROTOCOL BRIDGE [/]\n[dim]Multi-Protocol Semantic Agent Translation[/]",
        subtitle=f"[bold]v0.1.0 | Gateway: {host}:{port}[/]",
        border_style="orange1"
    ))
    
    # 2. Load Session Info
    config = load_config()
    email = config.get("email")
    if email:
        rprint(f" 👤 Session: [bold green]Logged in as {email}[/]")
    else:
        rprint(" 👤 Session: [dim]No active session found. Authentication required.[/]")
    
    rprint(f" 📡 [cyan]Initializing Backend Engine on {host}:{port}...[/]")

    # 3. Start API in background thread
    def run_api():
        try:
            # Using warning log level to reduce noise while starting
            uvicorn.run(app, host=host, port=port, log_level="warning", access_log=False)
        except Exception as e:
            rprint(f"\n❌ [bold red]Backend Failed:[/] {e}")
            os._exit(1) # Kill the whole process if backend fails to bind
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # 4. Give API a short head start
    time.sleep(1.5)
    rprint(" ✅ [bold green]Backend Ready.[/]")
    rprint(f" 🖥️  [cyan]Launching {'Debug Console' if initial_screen == 'debug' else 'TUI Environment'}...[/]")
    time.sleep(0.5)
    
    # 5. Start TUI in main thread
    try:
        # EngramTUI uses this for its API calls
        tui = EngramTUI(base_url=f"http://{host}:{port}/api/v1")
        if initial_screen:
            tui.initial_screen = initial_screen
        run(tui)
    except Exception as e:
        rprint(f"❌ [bold red]TUI Error:[/] {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Engram Protocol Bridge CLI")
    parser.add_argument("--host", default=os.getenv("ENGRAM_HOST", "127.0.0.1"), help="Host to bind backend")
    parser.add_argument("--port", type=int, default=int(os.getenv("ENGRAM_PORT", 8000)), help="Port for backend")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Commands
    subparsers.add_parser("init", help="Initialize configuration and directories")
    subparsers.add_parser("run", help="Start the Engram daemon and TUI dashboard (default)")
    subparsers.add_parser("debug", help="Launch the developer debug/monitoring dashboard")
    
    # Default behavior if no command or just help
    if len(sys.argv) == 1:
        start_runtime()
        return

    # Handle case where user might just do 'engram --port 8080' without 'run'
    # We want to still start the runtime
    args, unknown = parser.parse_known_args()
    
    if args.command == "init":
        init_config()
    elif args.command == "run" or not args.command:
        # If unknown args exist and command is None, it might be just flags
        start_runtime(host=args.host, port=args.port)
    elif args.command == "debug":
        # Launch directly into debug mode if requested
        start_runtime(host=args.host, port=args.port, initial_screen="debug")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
