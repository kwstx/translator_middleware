import asyncio
from typing import Any, Dict, Optional

# Shared queue for TUI events
_tui_event_queue: Optional[asyncio.Queue] = None
_tui_loop: Optional[asyncio.AbstractEventLoop] = None

def get_tui_event_queue() -> asyncio.Queue:
    global _tui_event_queue
    if _tui_event_queue is None:
        _tui_event_queue = asyncio.Queue()
    return _tui_event_queue

def register_tui_loop(loop: asyncio.AbstractEventLoop):
    """Register the event loop where the TUI is running."""
    global _tui_loop
    _tui_loop = loop

def tui_logger_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structlog processor that extracts translation events and pushes them to the TUI queue.
    """
    event = event_dict.get("event", "")
    
    # Map technical logs to plain English with emojis
    plain_text = None
    
    if event == "Translating message":
        src = event_dict.get("source_protocol", "???")
        tgt = event_dict.get("target_protocol", "???")
        plain_text = f"🔄 Translating message from [bold cyan]{src}[/] to [bold magenta]{tgt}[/]..."
    
    elif event == "Applied version delta":
        src = event_dict.get("source_protocol", "???")
        from_v = event_dict.get("from_version", "???")
        to_v = event_dict.get("to_version", "???")
        plain_text = f"✨ [yellow]{src}[/] message upgraded: [bold]{from_v}[/] ➡️ [bold]{to_v}[/]"
        
    elif event == "Translation failed":
        err = event_dict.get("error", "Unknown error")
        plain_text = f"❌ [bold red]Translation failed:[/] {err}"
        
    elif event == "No translation rule found":
        src = event_dict.get("source_protocol", "???")
        tgt = event_dict.get("target_protocol", "???")
        plain_text = f"⚠️ [bold yellow]Missing map:[/] No path found for {src} to {tgt}"

    elif event == "Version mismatch detected":
        src = event_dict.get("source_protocol", "???")
        src_v = event_dict.get("source_version", "???")
        exp_v = event_dict.get("expected_version", "???")
        plain_text = f"⚖️ Version mismatch in [bold cyan]{src}[/]: Found [dim]{src_v}[/], expected [bold]{exp_v}[/]"

    if plain_text:
        # We need to push to the queue. 
        if _tui_loop:
            _tui_loop.call_soon_threadsafe(get_tui_event_queue().put_nowait, plain_text)
        else:
            # Fallback if loop not registered yet
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon_threadsafe(get_tui_event_queue().put_nowait, plain_text)
            except (RuntimeError, ValueError):
                pass 

    return event_dict
