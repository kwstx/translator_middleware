import httpx
import time
import argparse
import sys
import json
import uuid
from rich.console import Console
from rich.table import Table
from rich.live import Live

console = Console()

def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

async def list_tasks(base_url, token):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/tasks", headers=get_auth_header(token))
        if response.status_code != 200:
            console.print(f"[bold red]Error listing tasks:[/] {response.text}")
            return []
        return response.json()

async def monitor_task(base_url, token, task_id):
    console.print(f"[bold cyan]Monitoring Task:[/] [white]{task_id}[/]")
    
    seen_ids = set()
    try:
        while True:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url}/tasks/{task_id}/events", 
                    headers=get_auth_header(token)
                )
                if response.status_code != 200:
                    console.print(f"[bold red]Error fetching events:[/] {response.text}")
                    break
                
                events = response.json()
                for event in events:
                    eid = str(event.get("id"))
                    if eid not in seen_ids:
                        seen_ids.add(eid)
                        ts = event.get("created_at")[11:19]
                        etype = event.get("event_type", "INFO")
                        msg = event.get("message", "")
                        
                        color = "white"
                        if "error" in etype.lower(): color = "red"
                        elif "translation" in etype.lower(): color = "magenta"
                        elif "handoff" in etype.lower(): color = "cyan"
                        
                        console.print(f"[{ts}] [[bold {color}]{etype:^18}[/]] {msg}")
                        
                        # Check for completion
                        if "synchronize" in msg.lower() or "aborted" in msg.lower():
                            console.print("\n[bold green]Task reached terminal state.[/]")
                            return

            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped.[/]")

async def main():
    parser = argparse.ArgumentParser(description="Engram Task Monitor Utility")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/api/v1", help="Backend API base URL")
    parser.add_argument("--token", help="Engram Access Token (EAT)")
    parser.add_argument("--task-id", help="Task UUID to monitor")
    parser.add_argument("--list", action="store_true", help="List recent tasks and exit")
    
    args = parser.parse_args()
    
    # Try to load token from ~/.engram/config.yaml or similar if needed
    # (For this utility, we expect the token to be provided or in ENV)
    token = args.token or "DEBUG_TOKEN" 
    
    if args.list:
        tasks = await list_tasks(args.base_url, token)
        table = Table(title="Recent Engram Tasks")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Command")
        table.add_column("Created")
        
        for t in tasks:
            table.add_row(
                str(t.get("id")),
                t.get("status"),
                t.get("source_message", {}).get("command", "N/A")[:50],
                t.get("created_at")[:19]
            )
        console.print(table)
        return

    if not args.task_id:
        # Prompt for task selection from list
        tasks = await list_tasks(args.base_url, token)
        if not tasks:
            console.print("[yellow]No tasks found to monitor.[/]")
            return
        
        console.print("[bold yellow]Available Tasks:[/]")
        for i, t in enumerate(tasks[:5]):
            console.print(f"  {i+1}. [bold cyan]{t.get('id')}[/] - {t.get('source_message', {}).get('command', 'N/A')[:40]}...")
        
        choice = console.input("\nEnter number to monitor (or UUID): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(tasks):
            task_id = tasks[int(choice)-1].get("id")
        else:
            task_id = choice
    else:
        task_id = args.task_id

    if task_id:
        await monitor_task(args.base_url, token, task_id)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
