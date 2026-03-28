import os
import yaml
import sys
import argparse

def init_config():
    """Generates the initial config.yaml in ~/.engram/."""
    config_dir = os.path.expanduser("~/.engram/")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, "config.yaml")
    
    config_content = {
        "model_provider": "openai",
        "base_url": "http://localhost:8000",
        "default_personality": "optimistic"
    }
    
    with open(config_path, "w") as f:
        yaml.dump(config_content, f, default_flow_style=False)
    
    print(f"Initialized Engram config at {config_path}")

def start_runtime():
    """Launches the unified Engram runtime (API + TUI)."""
    try:
        import uvicorn
        import threading
        import time
        from rich import print as rprint
        from rich.panel import Panel
        from rich.console import Console
    except ImportError as e:
        print(f"❌ Error: Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

    try:
        from app.main import app
        from textual import run
        from tui.app import EngramTUI, load_config
    except ImportError as e:
        print(f"❌ Error: Could not load Engram modules: {e}")
        print("Ensure you are running from the project root.")
        sys.exit(1)

    console = Console()
    
    # 1. Display Brand Banner
    rprint("\n")
    rprint(Panel.fit(
        "[bold orange1] ENGRAM PROTOCOL BRIDGE [/]\n[dim]Multi-Protocol Semantic Agent Translation[/]",
        subtitle="[bold]Runtime Environment v0.1.0[/]",
        border_style="orange1"
    ))
    
    # 2. Load Session Info
    config = load_config()
    email = config.get("email")
    if email:
        rprint(f" 👤 Session: [bold green]Logged in as {email}[/]")
    else:
        rprint(" 👤 Session: [dim]No active session found. Authentication required.[/]")
    
    rprint(" 📡 [cyan]Initializing Backend Engine...[/]")

    # 3. Start API in background thread
    def run_api():
        # Using warning log level to reduce noise while starting
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning", access_log=False)
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # 4. Give API a short head start
    time.sleep(1.2)
    rprint(" ✅ [bold green]Backend Ready.[/]")
    rprint(" 🖥️  [cyan]Launching TUI Environment...[/]")
    time.sleep(0.5)
    
    # 5. Start TUI in main thread
    try:
        run(EngramTUI())
    except Exception as e:
        rprint(f"❌ [bold red]TUI Error:[/] {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Engram CLI tool.")
    subparsers = parser.add_subparsers(dest="command")
    
    # Explicit commands
    subparsers.add_parser("init", help="Initialize configuration and directories")
    subparsers.add_parser("run", help="Start the Engram daemon and TUI dashboard")
    
    # Handle help and empty args
    if len(sys.argv) == 1:
        # Default behavior: Single command runtime
        start_runtime()
        return

    args = parser.parse_args()
    
    if args.command == "init":
        init_config()
    elif args.command == "run":
        start_runtime()
    else:
        # argparse handles the rest
        if not args.command:
            start_runtime()

if __name__ == "__main__":
    main()


