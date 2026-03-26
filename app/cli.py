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
    # Import here to avoid circular dependencies or heavy startup if not running the daemon
    import uvicorn
    import threading
    import time
    from app.main import app
    from textual import run
    from tui.app import EngramTUI

    print("🚀 Starting Engram Protocol Bridge...")
    
    # 1. Start API in background thread
    def run_api():
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error", access_log=False)
    
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # 2. Give API a head start
    time.sleep(1.5)
    
    # 3. Start TUI in main thread
    run(EngramTUI)

def main():
    parser = argparse.ArgumentParser(description="Engram CLI tool.")
    subparsers = parser.add_subparsers(dest="command")
    
    # Init command
    subparsers.add_parser("init", help="Initialize configuration")
    
    # Run command
    subparsers.add_parser("run", help="Start the Engram daemon and TUI dashboard")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_config()
    elif args.command == "run":
        start_runtime()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
