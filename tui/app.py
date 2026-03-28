from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, RichLog, Input, Label, Button, ListView, ListItem, DataTable, TabbedContent, TabPane
from textual.binding import Binding
from textual import on, work
from textual.screen import Screen
import asyncio
import os
import json
import httpx
import time
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet, InvalidToken
from app.core.tui_bridge import tui_event_queue
from tui.vault_service import VaultService

CONFIG_DIR = os.path.expanduser("~/.engram")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.enc")
KEY_FILE = os.path.join(CONFIG_DIR, "key")
DEFAULT_BASE_URL = "http://127.0.0.1:8000/api/v1"

# We'll fetch the real provider list from the backend on startup
# to ensure the TUI is always in sync with the backend's capabilities.
PROVIDERS = []
PROVIDER_MAP = {}

async def _infer_required_providers_via_backend(base_url: str, eat: str, command: str) -> list:
    """
    Asks the backend to determine which tools are needed for a command.
    Maintains the rule that 'execution workflows' are managed by the backend.
    """
    try:
        # We use a dedicated analysis endpoint that doesn't trigger execution
        headers = {"Authorization": f"Bearer {eat}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            # We use the existing /tasks/submit endpoint's planner but with a 'dry_run' or similar param
            # Or if that's not available, use the/discovery endpoint to list potential agents.
            # For now, we perform a lightweight fetch from /credentials/providers to know what's possible
            # and let the backend's main orchestration loop catch missing creds if we skip the proactive check.
            response = await client.get(f"{base_url}/credentials/providers", headers=headers)
            if response.status_code != 200:
                return []
            
            all_possible = response.json()
            command_lower = command.lower()
            required = []
            
            # Simple keyword matching for UX (the backend still enforces this during execution)
            for p in all_possible:
                aliases = p.get("aliases") or [p["id"], p.get("name", "").lower()]
                if any(alias in command_lower for alias in aliases):
                    required.append(p)
                elif p["id"] == "slack" and ("post" in command_lower or "send" in command_lower):
                    required.append(p)
                elif p["id"] == "perplexity" and ("search" in command_lower or "research" in command_lower):
                    required.append(p)
                    
            return required
    except Exception:
        return []

def _ensure_key() -> bytes:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()
    key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
    return key

def _get_fernet() -> Fernet:
    return Fernet(_ensure_key())

def _encrypt_config(config: Dict[str, Any]) -> str:
    payload = json.dumps(config).encode("utf-8")
    return _get_fernet().encrypt(payload).decode("utf-8")

def _decrypt_config(token: str) -> Dict[str, Any]:
    payload = _get_fernet().decrypt(token.encode("utf-8"))
    return json.loads(payload.decode("utf-8"))

def _default_config() -> Dict[str, Any]:
    return {
        "base_url": DEFAULT_BASE_URL, 
        "token": None, 
        "eat": None, 
        "email": None,
        "vault": {} 
    }

def _normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
    base = _default_config()
    base.update(config or {})
    return base

def load_config() -> Dict[str, Any]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return _normalize_config(_decrypt_config(f.read().strip()))
        except (InvalidToken, json.JSONDecodeError, OSError):
            return _default_config()
    return _default_config()

def save_config(config: Dict[str, Any]) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write(_encrypt_config(config))

async def _request(
    method: str,
    base_url: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    url = f"{base_url}{path}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await client.request(method, url, json=json_body, data=data, headers=headers)

def _auth_header(token: Optional[str]) -> Dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}

def _merge_headers(base: Optional[Dict[str, str]], extra: Optional[Dict[str, str]]) -> Dict[str, str]:
    merged: Dict[str, str] = {}
    if base:
        merged.update(base)
    if extra:
        merged.update(extra)
    return merged

def _extract_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("detail") or payload.get("error") or response.text)
    except Exception:
        pass
    return response.text

def _response_indicates_token_issue(response: httpx.Response) -> bool:
    if response.status_code not in (401, 403):
        return False
    detail = _extract_error_detail(response).lower()
    markers = ("expired", "revoked", "invalid", "unauthorized", "missing", "session")
    return any(marker in detail for marker in markers)

class AuthScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        with Container(id="auth-container"):
            yield Label("Engram Sign In", id="auth-title")
            yield Label("Base URL")
            yield Input(value=self.config.get("base_url") or DEFAULT_BASE_URL, id="base-url-input")
            yield Label("Email")
            yield Input(placeholder="name@company.com", id="email-input")
            yield Label("Password")
            yield Input(password=True, placeholder="********", id="password-input")
            yield Label("Confirm Password (signup only)")
            yield Input(password=True, placeholder="********", id="confirm-input")
            yield Label("", id="auth-error")
            with Horizontal(id="auth-buttons"):
                yield Button("Login", id="login-btn", variant="primary")
                yield Button("Signup", id="signup-btn")
                yield Button("Quit", id="quit-btn")

    def on_mount(self) -> None:
        self.query_one("#email-input", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    async def _do_login(self, email: str, password: str, base_url: str) -> Optional[Dict[str, Any]]:
        response = await _request(
            "POST",
            base_url,
            "/auth/login",
            data={"username": email, "password": password},
            headers=_auth_header(self.config.get("eat")),
        )
        if response.status_code != 200:
            raise RuntimeError(response.json().get("detail", response.text))
        return response.json()

    async def _generate_eat(self, token: str, base_url: str) -> str:
        response = await _request(
            "POST",
            base_url,
            "/auth/tokens/generate-eat",
            headers=_auth_header(token),
        )
        if response.status_code != 200:
            raise RuntimeError(response.json().get("detail", response.text))
        return response.json().get("eat")

    def _set_error(self, message: str) -> None:
        label = self.query_one("#auth-error", Label)
        label.update(message)

    @on(Button.Pressed, "#quit-btn")
    def handle_quit(self) -> None:
        self.app.exit()

    @on(Button.Pressed, "#login-btn")
    async def handle_login(self) -> None:
        await self._authenticate(mode="login")

    @on(Button.Pressed, "#signup-btn")
    async def handle_signup(self) -> None:
        await self._authenticate(mode="signup")

    async def _authenticate(self, mode: str) -> None:
        email = self.query_one("#email-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value.strip()
        confirm = self.query_one("#confirm-input", Input).value.strip()
        base_url = self.query_one("#base-url-input", Input).value.strip() or DEFAULT_BASE_URL

        if not email or not password:
            self._set_error("Email and password are required.")
            return

        if mode == "signup":
            if password != confirm:
                self._set_error("Passwords do not match.")
                return
            response = await _request(
                "POST",
                base_url,
                "/auth/signup",
                json_body={"email": email, "password": password, "user_metadata": {"source": "tui_client"}},
                headers=_auth_header(self.config.get("eat")),
            )
            if response.status_code != 201:
                self._set_error(response.json().get("detail", response.text))
                return

        try:
            login_payload = await self._do_login(email, password, base_url)
            token = login_payload.get("access_token")
            eat = await self._generate_eat(token, base_url)
        except Exception as exc:
            self._set_error(str(exc))
            return

        config = {
            "base_url": base_url,
            "token": token,
            "eat": eat,
            "email": email,
        }
        save_config(config)
        self.dismiss(config)

class ServiceConnectScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, provider: Dict[str, Any]):
        super().__init__()
        self.provider = provider

    def compose(self) -> ComposeResult:
        provider_name = self.provider.get("name", "Provider")
        display_name = self.provider.get("display_name") or provider_name
        auth_hint = self.provider.get("hint", "")
        auth_label = "API Key" if self.provider.get("auth") == "api_key" else "OAuth Token"
        with Container(id="service-connect-container"):
            yield Label(f"Connect {display_name}", id="service-connect-title")
            if self.provider.get("custom"):
                yield Label("Provider Name")
                yield Input(
                    value=self.provider.get("prefill_name", ""),
                    placeholder="e.g., notion, github, linear",
                    id="provider-name-input",
                )
            else:
                yield Label("Provider")
                yield Label(display_name, id="provider-name-label")
            yield Label(f"{auth_label}")
            yield Input(password=True, placeholder=auth_hint or "Paste token", id="provider-token-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

    def on_mount(self) -> None:
        if self.provider.get("custom"):
            self.query_one("#provider-name-input", Input).focus()
        else:
            self.query_one("#provider-token-input", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _set_error(self, message: str) -> None:
        label = self.query_one("#service-connect-error", Label)
        label.update(message)

    @on(Button.Pressed, "#service-cancel-btn")
    def handle_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#service-connect-btn")
    async def handle_connect(self) -> None:
        app = self.app
        provider_id = self.provider.get("id")
        if self.provider.get("custom"):
            provider_name = self.query_one("#provider-name-input", Input).value.strip().lower()
        else:
            provider_name = provider_id or ""

        token = self.query_one("#provider-token-input", Input).value.strip()
        if not provider_name:
            self._set_error("Provider name is required.")
            return
        if not token:
            self._set_error("Token is required.")
            return

        credential_type = "API_KEY" if self.provider.get("auth") == "api_key" else "OAUTH_TOKEN"
        payload = {
            "provider_name": provider_name,
            "token": token,
            "credential_type": credential_type,
            "metadata": {
                "source": "tui",
                "display_name": self.provider.get("name"),
                "flow": self.provider.get("auth"),
            },
        }

        response = await app._authed_request("POST", "/credentials", json_body=payload)
        if response.status_code not in (200, 201):
            self._set_error(_extract_error_detail(response))
            return

        # NEW: Store in local vault
        VaultService.store_credential(app.base_url, app.user_email, provider_name, {
            "token": token,
            "type": credential_type,
            "metadata": payload["metadata"]
        })

        self.dismiss({"provider_name": provider_name})

class WorkflowListScreen(Screen):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, app_ref: "EngramTUI"):
        super().__init__()
        self.app_ref = app_ref
        self.workflow_map: Dict[str, Dict[str, Any]] = {}
        self.selected_workflow_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        with Container(id="workflow-container"):
            yield Label("Workflows", id="workflow-title")
            yield ListView(id="workflow-list")
            with Horizontal(id="workflow-buttons"):
                yield Button("Create", id="workflow-create-btn", variant="primary")
                yield Button("Run", id="workflow-run-btn")
                yield Button("Schedule", id="workflow-schedule-btn")
                yield Button("Runs", id="workflow-runs-btn")
                yield Button("Refresh", id="workflow-refresh-btn")
                yield Button("Close", id="workflow-close-btn")

    def on_mount(self) -> None:
        self.run_worker(self._load_workflows(), thread=False)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_refresh(self) -> None:
        self.run_worker(self._load_workflows(), thread=False)

    async def _load_workflows(self) -> None:
        list_view = self.query_one("#workflow-list", ListView)
        list_view.clear()
        self.workflow_map = {}
        response = await self.app_ref._authed_request("GET", "/workflows?limit=100")
        if response.status_code != 200:
            list_view.append(ListItem(Label(f"Error: {_extract_error_detail(response)}")))
            return
        workflows = response.json()
        if not workflows:
            list_view.append(ListItem(Label("No workflows created yet.")))
            return
        for wf in workflows:
            wf_id = str(wf.get("id"))
            name = wf.get("name") or "Untitled"
            updated = wf.get("updated_at") or ""
            active = "ACTIVE" if wf.get("is_active") else "PAUSED"
            line = f"{name} | {wf_id} | {active} | {updated}"
            item = ListItem(Label(line))
            item.id = f"workflow-{wf_id}"
            list_view.append(item)
            self.workflow_map[wf_id] = wf

    @on(ListView.Selected, "#workflow-list")
    def _select_workflow(self, event: ListView.Selected) -> None:
        item = event.item
        if not item or not item.id:
            self.selected_workflow_id = None
            return
        self.selected_workflow_id = item.id.replace("workflow-", "")

    def _get_selected_workflow(self) -> Optional[Dict[str, Any]]:
        if not self.selected_workflow_id:
            return None
        return self.workflow_map.get(self.selected_workflow_id)

    @on(Button.Pressed, "#workflow-close-btn")
    def _handle_close(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#workflow-refresh-btn")
    def _handle_refresh(self) -> None:
        self.run_worker(self._load_workflows(), thread=False)

    @on(Button.Pressed, "#workflow-create-btn")
    def _handle_create(self) -> None:
        self.app.push_screen(WorkflowCreateScreen(self.app_ref), self._handle_child_result)

    @on(Button.Pressed, "#workflow-run-btn")
    def _handle_run(self) -> None:
        workflow = self._get_selected_workflow()
        if not workflow:
            return
        self.run_worker(self._run_workflow(workflow), thread=False)

    @on(Button.Pressed, "#workflow-schedule-btn")
    def _handle_schedule(self) -> None:
        workflow = self._get_selected_workflow()
        if not workflow:
            return
        self.app.push_screen(WorkflowScheduleScreen(self.app_ref, workflow), self._handle_child_result)

    @on(Button.Pressed, "#workflow-runs-btn")
    def _handle_runs(self) -> None:
        workflow = self._get_selected_workflow()
        if not workflow:
            return
        self.app.push_screen(WorkflowRunsScreen(self.app_ref, workflow))

    def _handle_child_result(self, result: Optional[Dict[str, Any]]) -> None:
        if result and result.get("refresh"):
            self.run_worker(self._load_workflows(), thread=False)

    async def _run_workflow(self, workflow: Dict[str, Any]) -> None:
        log_view = self.app_ref.query_one("#log-view", RichLog)
        wf_id = workflow.get("id")
        command = workflow.get("command") or ""
        if command:
            ok = await self.app_ref._ensure_required_providers_connected(command, log_view)
            if not ok:
                return
        response = await self.app_ref._authed_request("POST", f"/workflows/{wf_id}/run")
        if response.status_code != 200:
            log_view.write(f"[bold red]Workflow run failed:[/] {_extract_error_detail(response)}")
            return
        payload = response.json()
        log_view.write(f"[bold green]Workflow queued:[/] {wf_id} (Task {payload.get('task_id')})")


class WorkflowCreateScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, app_ref: "EngramTUI"):
        super().__init__()
        self.app_ref = app_ref

    def compose(self) -> ComposeResult:
        with Container(id="workflow-create-container"):
            yield Label("Create Workflow", id="workflow-create-title")
            yield Label("Name")
            yield Input(placeholder="e.g., Daily Research Digest", id="workflow-name-input")
            yield Label("Description")
            yield Input(placeholder="Optional description", id="workflow-desc-input")
            yield Label("Command")
            yield Input(placeholder="e.g., Perplexity research ... then Slack post ...", id="workflow-command-input")
            yield Label("Metadata (JSON, optional)")
            yield Input(placeholder="{\"priority\": \"high\"}", id="workflow-metadata-input")
            yield Label("", id="workflow-create-error")
            with Horizontal(id="workflow-create-buttons"):
                yield Button("Create", id="workflow-create-btn", variant="primary")
                yield Button("Cancel", id="workflow-cancel-btn")

    def on_mount(self) -> None:
        self.query_one("#workflow-name-input", Input).focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _set_error(self, message: str) -> None:
        label = self.query_one("#workflow-create-error", Label)
        label.update(message)

    @on(Button.Pressed, "#workflow-cancel-btn")
    def _handle_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#workflow-create-btn")
    async def _handle_create(self) -> None:
        name = self.query_one("#workflow-name-input", Input).value.strip()
        description = self.query_one("#workflow-desc-input", Input).value.strip()
        command = self.query_one("#workflow-command-input", Input).value.strip()
        metadata_raw = self.query_one("#workflow-metadata-input", Input).value.strip()

        if not name or not command:
            self._set_error("Name and command are required.")
            return

        metadata = None
        if metadata_raw:
            try:
                metadata = json.loads(metadata_raw)
            except Exception:
                self._set_error("Metadata must be valid JSON.")
                return

        response = await self.app_ref._authed_request(
            "POST",
            "/workflows",
            json_body={
                "name": name,
                "description": description or None,
                "command": command,
                "metadata": metadata,
            },
        )
        if response.status_code not in (200, 201):
            self._set_error(_extract_error_detail(response))
            return
        self.dismiss({"refresh": True})


class WorkflowScheduleScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, app_ref: "EngramTUI", workflow: Dict[str, Any]):
        super().__init__()
        self.app_ref = app_ref
        self.workflow = workflow

    def compose(self) -> ComposeResult:
        with Container(id="workflow-schedule-container"):
            yield Label("Schedule Workflow", id="workflow-schedule-title")
            yield Label("Interval Minutes")
            yield Input(placeholder="e.g., 60", id="workflow-interval-input")
            yield Label("Enabled (yes/no)")
            yield Input(value="yes", id="workflow-enabled-input")
            yield Label("", id="workflow-schedule-error")
            with Horizontal(id="workflow-schedule-buttons"):
                yield Button("Save", id="workflow-schedule-save-btn", variant="primary")
                yield Button("Remove", id="workflow-schedule-remove-btn")
                yield Button("Cancel", id="workflow-schedule-cancel-btn")

    def on_mount(self) -> None:
        self.run_worker(self._load_schedule(), thread=False)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def _set_error(self, message: str) -> None:
        label = self.query_one("#workflow-schedule-error", Label)
        label.update(message)

    async def _load_schedule(self) -> None:
        wf_id = self.workflow.get("id")
        response = await self.app_ref._authed_request("GET", f"/workflows/{wf_id}/schedule")
        if response.status_code == 200:
            schedule = response.json()
            interval_minutes = int(schedule.get("interval_seconds", 0)) // 60
            self.query_one("#workflow-interval-input", Input).value = str(interval_minutes)
            enabled = "yes" if schedule.get("enabled") else "no"
            self.query_one("#workflow-enabled-input", Input).value = enabled

    @on(Button.Pressed, "#workflow-schedule-cancel-btn")
    def _handle_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#workflow-schedule-remove-btn")
    async def _handle_remove(self) -> None:
        wf_id = self.workflow.get("id")
        response = await self.app_ref._authed_request("DELETE", f"/workflows/{wf_id}/schedule")
        if response.status_code != 204:
            self._set_error(_extract_error_detail(response))
            return
        self.dismiss({"refresh": True})

    @on(Button.Pressed, "#workflow-schedule-save-btn")
    async def _handle_save(self) -> None:
        wf_id = self.workflow.get("id")
        interval_raw = self.query_one("#workflow-interval-input", Input).value.strip()
        enabled_raw = self.query_one("#workflow-enabled-input", Input).value.strip().lower()
        if not interval_raw.isdigit():
            self._set_error("Interval must be a positive integer.")
            return
        interval_minutes = int(interval_raw)
        if interval_minutes <= 0:
            self._set_error("Interval must be greater than zero.")
            return
        enabled = enabled_raw in ("yes", "true", "1", "y")
        response = await self.app_ref._authed_request(
            "POST",
            f"/workflows/{wf_id}/schedule",
            json_body={"interval_minutes": interval_minutes, "enabled": enabled},
        )
        if response.status_code != 200:
            self._set_error(_extract_error_detail(response))
            return
        self.dismiss({"refresh": True})


class DebugScreen(Screen):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("r", "refresh", "Refresh Task List"),
        Binding("t", "tail", "Tail Current Task"),
    ]

    def __init__(self, app_ref: "EngramTUI"):
        super().__init__()
        self.app_ref = app_ref
        self.selected_task_id = None
        self.last_event_timestamp = 0
        self.tailing = False

    def compose(self) -> ComposeResult:
        with Container(id="debug-container"):
            yield Label("Developer Debug Console", id="debug-title")
            with Horizontal(id="debug-main-layout"):
                with Vertical(id="debug-list-panel"):
                    yield Label("Recent Tasks", classes="debug-subtitle")
                    yield DataTable(id="task-debug-table")
                    with Horizontal(classes="debug-actions"):
                        yield Button("Refresh", id="debug-refresh-btn")
                        yield Button("Inspect", id="debug-inspect-btn", variant="primary")
                
                with Vertical(id="debug-detail-panel"):
                    yield Label("Task details (Select a task)", id="debug-detail-header", classes="debug-subtitle")
                    with TabbedContent(id="debug-tabs"):
                        with TabPane("Execution Log", id="tab-log"):
                            yield RichLog(id="debug-event-log", highlight=True, markup=True)
                        with TabPane("Protocol Trace", id="tab-trace"):
                            with Horizontal():
                                with Vertical(classes="protocol-pane"):
                                    yield Label("Engram (Source)", classes="protocol-title")
                                    yield RichLog(id="debug-trace-source")
                                with Vertical(classes="protocol-pane"):
                                    yield Label("Tool (Target)", classes="protocol-title")
                                    yield RichLog(id="debug-trace-target")
                        with TabPane("Plan", id="tab-plan"):
                            yield RichLog(id="debug-task-plan")
            
            with Horizontal(id="debug-footer"):
                yield Button("Close", id="debug-close-btn")
                yield Label("Press [bold]R[/] to refresh list | [bold]T[/] to toggle live tail", id="debug-status-hint")

    def on_mount(self) -> None:
        table = self.query_one("#task-debug-table", DataTable)
        table.add_columns("ID", "Command", "Status", "Updated")
        table.cursor_type = "row"
        self.run_worker(self._load_tasks(), thread=False)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_refresh(self) -> None:
        self.run_worker(self._load_tasks(), thread=False)

    @work(exclusive=True)
    async def _load_tasks(self) -> None:
        table = self.query_one("#task-debug-table", DataTable)
        table.clear()
        
        response = await self.app_ref._authed_request("GET", "/tasks?limit=25")
        if response.status_code != 200:
            return
            
        tasks = response.json()
        for t in tasks:
            tid = str(t.get("id"))
            cmd = t.get("source_message", {}).get("command", "N/A")
            if len(cmd) > 30: cmd = cmd[:27] + "..."
            status = t.get("status", "unknown")
            updated = t.get("updated_at", "")[:19].replace("T", " ")
            table.add_row(tid, cmd, status, updated, key=tid)

    @on(DataTable.RowSelected, "#task-debug-table")
    def _row_selected(self, event: DataTable.RowSelected) -> None:
        self.selected_task_id = event.row_key.value
        self.run_worker(self._inspect_task(self.selected_task_id), thread=False)

    @on(Button.Pressed, "#debug-refresh-btn")
    def _handle_refresh(self) -> None:
        self.action_refresh()

    @on(Button.Pressed, "#debug-inspect-btn")
    def _handle_inspect(self) -> None:
        table = self.query_one("#task-debug-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            self.selected_task_id = row_key
            self.run_worker(self._inspect_task(self.selected_task_id), thread=False)

    @on(Button.Pressed, "#debug-close-btn")
    def _handle_close(self) -> None:
        self.action_close()

    async def _inspect_task(self, task_id: str) -> None:
        self.query_one("#debug-detail-header", Label).update(f"Inspecting Task: [bold cyan]{task_id}[/]")
        
        # Reset logs
        self.query_one("#debug-event-log", RichLog).clear()
        self.query_one("#debug-trace-source", RichLog).clear()
        self.query_one("#debug-trace-target", RichLog).clear()
        self.query_one("#debug-task-plan", RichLog).clear()
        
        # Load task details
        response = await self.app_ref._authed_request("GET", f"/tasks/{task_id}")
        if response.status_code == 200:
            task = response.json()
            plan = task.get("source_message", {}).get("plan")
            if plan:
                plan_log = self.query_one("#debug-task-plan", RichLog)
                plan_log.write(json.dumps(plan, indent=2))
        
        # Load events
        await self._load_events(task_id)

    async def _load_events(self, task_id: str) -> None:
        log = self.query_one("#debug-event-log", RichLog)
        response = await self.app_ref._authed_request("GET", f"/tasks/{task_id}/events")
        if response.status_code == 200:
            events = response.json()
            for ev in events:
                self._render_event(ev)
                
    def _render_event(self, event: Dict[str, Any]) -> None:
        log = self.query_one("#debug-event-log", RichLog)
        etype = event.get("event_type", "INFO")
        msg = event.get("message", "")
        ts = event.get("created_at", "")[11:19]
        
        color = "white"
        if "error" in etype.lower(): color = "red"
        elif "translation" in etype.lower(): color = "magenta"
        elif "handoff" in etype.lower(): color = "cyan"
        
        log.write(f"[[dim]{ts}[/]] [[bold {color}]{etype.upper()}[/]] {msg}")
        
        # Also route to traces if it's a translation event
        data = event.get("data") or {}
        if "translation" in etype.lower() and "payload" in data:
            if "engram" in etype.lower():
                src_log = self.query_one("#debug-trace-source", RichLog)
                src_log.clear()
                src_log.write(json.dumps(data.get("payload"), indent=2))
            else:
                tgt_log = self.query_one("#debug-trace-target", RichLog)
                tgt_log.clear()
                tgt_log.write(json.dumps(data.get("payload"), indent=2))

    def action_tail(self) -> None:
        if not self.selected_task_id:
            return
        self.tailing = not self.tailing
        hint = self.query_one("#debug-status-hint", Label)
        if self.tailing:
            hint.update("LIVE TAIL: [bold green]ACTIVE[/] | Press [bold]T[/] to stop")
            self.run_worker(self._tail_worker(), thread=False)
        else:
            hint.update("Press [bold]R[/] to refresh list | [bold]T[/] to toggle live tail")

    async def _tail_worker(self) -> None:
        while self.tailing and self.selected_task_id:
            # Get only new events
            # We'd need accurate 'since' logic, for now we just refresh all
            await self._load_events(self.selected_task_id)
            await asyncio.sleep(2)


class WorkflowRunsScreen(Screen):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, app_ref: "EngramTUI", workflow: Dict[str, Any]):
        super().__init__()
        self.app_ref = app_ref
        self.workflow = workflow

    def compose(self) -> ComposeResult:
        with Container(id="workflow-runs-container"):
            yield Label("Workflow Runs", id="workflow-runs-title")
            yield ListView(id="workflow-runs-list")
            with Horizontal(id="workflow-runs-buttons"):
                yield Button("Refresh", id="workflow-runs-refresh-btn")
                yield Button("Close", id="workflow-runs-close-btn")

    def on_mount(self) -> None:
        self.run_worker(self._load_runs(), thread=False)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_refresh(self) -> None:
        self.run_worker(self._load_runs(), thread=False)

    async def _load_runs(self) -> None:
        list_view = self.query_one("#workflow-runs-list", ListView)
        list_view.clear()
        wf_id = self.workflow.get("id")
        response = await self.app_ref._authed_request("GET", f"/workflows/{wf_id}/tasks?limit=20")
        if response.status_code != 200:
            list_view.append(ListItem(Label(f"Error: {_extract_error_detail(response)}")))
            return
        rows = response.json()
        if not rows:
            list_view.append(ListItem(Label("No runs yet.")))
            return
        for row in rows:
            line = f"{row.get('id')} | {row.get('status')} | {row.get('updated_at')}"
            list_view.append(ListItem(Label(line)))

    @on(Button.Pressed, "#workflow-runs-refresh-btn")
    def _handle_refresh(self) -> None:
        self.run_worker(self._load_runs(), thread=False)

    @on(Button.Pressed, "#workflow-runs-close-btn")
    def _handle_close(self) -> None:
        self.dismiss(None)

# ASCII header
LOGO = """
  [bold orange1]______ _   _  _____ _____            __  __ [/]
 [bold orange1]|  ____| \ | |/ ____|  __ \     /\   |  \/  |[/]
 [bold orange1]| |__  |  \| | |  __| |__) |   /  \  | \  / |[/]
 [bold orange1]|  __| | . ` | | |_ |  _  /   / /\ \ | |\/| |[/]
 [bold orange1]| |____| |\  | |__| | | \ \  / ____ \| |  | |[/]
 [bold orange1]|______|_| \_|\_____|_|  \_\/_/    \_\_|  |_|[/]
             [italic white]PROTOCOL BRIDGE[/] [bold dim]v0.1.0[/]
"""

class EngramTUI(App):
    """
    A terminal-based interface for the Engram Protocol Bridge.
    """
    CSS = """
    """
    
    def __init__(self, base_url: Optional[str] = None):
        super().__init__()
        self.cli_base_url = base_url
        self.base_url = None
        self.token = None
        self.eat = None
        self.user_email = None
        
        # State trackers
        self.active_task_id = None
        self.active_task_text = None
        self.active_task_status = None
        self.active_task_total_steps = 0
        self.active_task_steps = {}
        self.active_task_agents = set()

    CSS = """
    Screen {
        background: #0f1115;
    }

    #header {
        height: 10;
        content-align: center middle;
        background: #1a1e26;
        border-bottom: double #d35400;
        margin-bottom: 1;
    }

    #main-container {
        height: 1fr;
    }

    #main-left {
        width: 70%;
    }

    #trace-panels {
        height: 13;
        background: #12151c;
        border: solid #2c3e50;
        padding: 1;
        margin-bottom: 1;
    }

    .trace-row {
        height: 1fr;
    }

    .trace-panel {
        width: 1fr;
        border: solid #2c3e50;
        margin-right: 1;
        padding: 0 1;
        background: #0f1115;
    }

    #translation-panel {
        height: 10;
        background: #12151c;
        border: solid #2c3e50;
        padding: 1;
        margin-bottom: 1;
    }

    .translation-panel {
        width: 1fr;
        border: solid #2c3e50;
        margin-right: 1;
        padding: 0 1;
        background: #0f1115;
    }

    .translation-title {
        text-style: bold;
        color: #f39c12;
        margin-bottom: 0;
    }


    .trace-title {
        text-style: bold;
        color: #f39c12;
        margin-bottom: 0;
    }

    #log-view {
        height: 1fr;
        background: #12151c;
        border: solid #2c3e50;
        padding: 1;
    }

    #sidebar {
        width: 30%;
        background: #1a1e26;
        border-left: solid #2c3e50;
        padding: 1;
    }

    .sidebar-title {
        text-style: bold;
        color: #d35400;
        margin-bottom: 1;
    }

    .stat-item {
        margin-bottom: 1;
        color: #ecf0f1;
    }

    #task-panel {
        border: solid #2c3e50;
        padding: 1;
        margin-bottom: 1;
        background: #12151c;
    }

    #task-current, #task-progress, #task-connectors {
        color: #ecf0f1;
    }

    #input-area {
        height: 3;
        background: #1a1e26;
        border-top: solid #d35400;
        padding: 0 1;
    }

    Input {
        background: #1a1e26;
        border: none;
        color: #ecf0f1;
    }
    
    .status-ok {
        color: #2ecc71;
    }
    
    .status-waiting {
        color: #f1c40f;
    }

    #auth-container {
        width: 60%;
        height: auto;
        padding: 2 3;
        border: solid #d35400;
        background: #1a1e26;
        margin: 2 auto;
    }

    #auth-title {
        content-align: center middle;
        text-style: bold;
        color: #d35400;
        margin-bottom: 1;
    }

    #auth-buttons {
        margin-top: 1;
        height: auto;
    }

    #auth-error {
        color: #e74c3c;
        margin-top: 1;
    }

    #service-connect-container {
        width: 70%;
        height: auto;
        padding: 2 3;
        border: solid #d35400;
        background: #1a1e26;
        margin: 2 auto;
    }

    #service-connect-title {
        content-align: center middle;
        text-style: bold;
        color: #d35400;
        margin-bottom: 1;
    }

    #service-connect-buttons {
        margin-top: 1;
        height: auto;
    }

    #service-connect-error {
        color: #e74c3c;
        margin-top: 1;
    }

    #workflow-container, #workflow-create-container, #workflow-schedule-container, #workflow-runs-container {
        width: 80%;
        height: auto;
        padding: 2 3;
        border: solid #d35400;
        background: #1a1e26;
        margin: 2 auto;
    }

    #workflow-title, #workflow-create-title, #workflow-schedule-title, #workflow-runs-title {
        content-align: center middle;
        text-style: bold;
        color: #d35400;
        margin-bottom: 1;
    }

    #workflow-buttons, #workflow-create-buttons, #workflow-schedule-buttons, #workflow-runs-buttons {
        margin-top: 1;
        height: auto;
    }

    #workflow-create-error, #workflow-schedule-error {
        color: #e74c3c;
        margin-top: 1;
    }

    #services-panel {
        margin-top: 1;
        border-top: solid #2c3e50;
        padding-top: 1;
    }

    .service-row {
        height: auto;
        margin-bottom: 1;
    }

    .service-name {
        width: 45%;
    }

    .service-status {
        width: 30%;
    }

    .service-btn {
        width: 25%;
    }

    #debug-container {
        width: 95%;
        height: 95%;
        border: double #d35400;
        background: #0f1115;
        margin: 1 auto;
        padding: 1;
    }

    #debug-title {
        content-align: center middle;
        text-style: bold;
        color: #d35400;
        margin-bottom: 1;
        background: #1a1e26;
        height: 3;
    }

    .debug-subtitle {
        text-style: bold underline;
        color: #f39c12;
        margin-bottom: 1;
    }

    #debug-main-layout {
        height: 1fr;
    }

    #debug-list-panel {
        width: 35%;
        border-right: solid #2c3e50;
        padding: 0 1;
    }

    #debug-detail-panel {
        width: 65%;
        padding: 0 1;
    }

    .debug-actions {
        height: 3;
        margin-top: 1;
    }

    #debug-tabs {
        height: 1fr;
    }

    .protocol-pane {
        width: 1fr;
        border: solid #2c3e50;
        margin: 0 1;
        background: #12151c;
    }

    .protocol-title {
        text-style: bold;
        color: #3498db;
        content-align: center middle;
        background: #1a1e26;
    }

    #debug-event-log, #debug-trace-source, #debug-trace-target, #debug-task-plan {
        height: 1fr;
        background: #0f1115;
    }

    #debug-footer {
        height: 3;
        background: #1a1e26;
        border-top: solid #d35400;
        padding: 0 2;
        align: middle;
    }

    #debug-status-hint {
        margin-left: 2;
        color: #bdc3c7;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("c", "clear", "Clear Logs", show=True),
        Binding("r", "refresh", "Refresh Stats", show=True),
        Binding("s", "services", "Services", show=True),
        Binding("w", "workflows", "Workflows", show=True),
    ]

    def __init__(self, base_url: Optional[str] = None):
        super().__init__()
        self.cli_base_url = base_url
        self.initial_screen = None
        self.token: Optional[str] = None
        self.eat: Optional[str] = None
        self.base_url: str = DEFAULT_BASE_URL
        self.user_email: Optional[str] = None
        self.connected_providers = set()
        self.active_task_id: Optional[str] = None
        self.active_task_text: Optional[str] = None
        self.active_task_status: Optional[str] = None
        self.active_task_steps: Dict[int, Dict[str, Any]] = {}
        self.active_task_agents = set()
        self.active_task_total_steps: Optional[int] = None

    def compose(self) -> ComposeResult:
        # Header with Logo
        yield Static(LOGO, id="header")

        # Main Layout
        with Horizontal(id="main-container"):
            with Vertical(id="main-left"):
                with Container(id="trace-panels"):
                    with Horizontal(classes="trace-row"):
                        with Vertical(classes="trace-panel"):
                            yield Label("CONNECTIONS", classes="trace-title")
                            yield RichLog(id="trace-connections", highlight=True, markup=True)
                        with Vertical(classes="trace-panel"):
                            yield Label("AGENT EXECUTION", classes="trace-title")
                            yield RichLog(id="trace-agents", highlight=True, markup=True)
                    with Horizontal(classes="trace-row"):
                        with Vertical(classes="trace-panel"):
                            yield Label("TOOL USAGE", classes="trace-title")
                            yield RichLog(id="trace-tools", highlight=True, markup=True)
                        with Vertical(classes="trace-panel"):
                            yield Label("RESPONSES", classes="trace-title")
                            yield RichLog(id="trace-responses", highlight=True, markup=True)

                with Container(id="translation-panel"):
                    with Horizontal():
                        with Vertical(classes="translation-panel"):
                            yield Label("ENGRAM TASK", classes="translation-title")
                            yield RichLog(id="translation-engram", highlight=True, markup=True)
                        with Vertical(classes="translation-panel"):
                            yield Label("TOOL REQUEST", classes="translation-title")
                            yield RichLog(id="translation-request", highlight=True, markup=True)
                        with Vertical(classes="translation-panel"):
                            yield Label("TOOL RESPONSE", classes="translation-title")
                            yield RichLog(id="translation-response", highlight=True, markup=True)

                # Translation Log
                yield RichLog(id="log-view", highlight=True, markup=True)
            
            # Sidebar info
            with Vertical(id="sidebar"):
                yield Label("📊 SYSTEM STATUS", classes="sidebar-title")
                yield Label("✅ [bold]FastAPI Engine:[/] [green]Online[/]", classes="stat-item")
                yield Label("✅ [bold]Discovery Service:[/] [green]Active[/]", classes="stat-item")
                yield Label("⚡ [bold]Task Worker:[/] [green]Processing[/]", classes="stat-item")

                with Container(id="task-panel"):
                    yield Label("TASK TRACKER", classes="sidebar-title")
                    yield Label("CURRENT TASK", classes="sidebar-title")
                    yield Static("No task submitted yet.", id="task-current")
                    yield Label("PROGRESS", classes="sidebar-title")
                    yield Static("Status: IDLE", id="task-progress")
                    yield Label("ACTIVE CONNECTORS", classes="sidebar-title")
                    yield Static("None", id="task-connectors")
                
                yield Label("\n🛰️ RECENT ACTIVITY", classes="sidebar-title")
                yield Label("• A2A Protocol registered", classes="stat-item")
                yield Label("• MCP Mapping loaded", classes="stat-item")
                yield Label("• Bridge listener started", classes="stat-item")
                
                yield Label("\n💡 COMMANDS", classes="sidebar-title")
                yield Label("/status - Check bridge health", classes="stat-item")
                yield Label("/agents - List connected agents", classes="stat-item")
                yield Label("/login  - Sign in", classes="stat-item")
                yield Label("/logout - Sign out", classes="stat-item")
                yield Label("/services - Refresh services", classes="stat-item")
                yield Label("/connect <provider> - Connect service", classes="stat-item")
                yield Label("/tasks [limit] - View recent tasks", classes="stat-item")
                yield Label("/debug - Open developer console", classes="stat-item")

                with Container(id="services-panel"):
                    yield Label("CONNECTED SERVICES", classes="sidebar-title")
                    # Services will be dynamically populated in on_mount

        # Input Area (Command prompt)
        yield Input(placeholder="Type a task or /command (e.g., 'Prepare a report from Slack then send to Notion')", id="command-input")
        
        # Footer
        yield Footer()

    async def on_mount(self) -> None:
        """Start listening for bridge events when the UI is ready."""
        from app.core.tui_bridge import register_tui_loop
        register_tui_loop(asyncio.get_event_loop())

        config = load_config()
        self.base_url = self.cli_base_url or config.get("base_url") or DEFAULT_BASE_URL
        self.token = config.get("token")
        self.eat = config.get("eat")
        self.user_email = config.get("email")
        if not self.eat:
            self.push_screen(AuthScreen(config), self._handle_auth_result)

        log_view = self.query_one("#log-view", RichLog)
        log_view.write("🚀 [bold orange1]Engram Protocol Bridge initialized.[/]")
        log_view.write("📡 [dim]Waiting for protocol events on shared queue...[/]\n")
        
        # Start background listener
        self.message_receiver()
        
        # Initial discovery
        self.run_worker(self.refresh_available_providers(), thread=False)
        
        # NEW: Handle initial screen (e.g. from 'engram debug')
        if self.initial_screen == "debug":
            self.push_screen(DebugScreen(self))

    @work(exclusive=True, thread=True)
    def message_receiver(self):
        """Worker task to pull messages from the bridge queue and post them to UI."""
        import asyncio
        import time
        
        # We need a new loop here or access the main one since textual works on its own loop.
        # However, textual's @work allows us to run async or sync.
        # The tui_event_queue is an asyncio.Queue from the app's main thread (probably).
        
        # Since I used call_soon_threadsafe in the logger, it should be fine.
        # But wait, tui_event_queue.get() is an async call.
        
        async def run_listener():
            while True:
                msg = await tui_event_queue.get()
                self.call_from_thread(self.log_message, msg)
                tui_event_queue.task_done()
        
        # Ensure there's an event loop for this thread if needed, or just use the app's loop
        self.run_worker(run_listener())

    def log_message(self, message: Any) -> None:
        """Update the log view with a new message."""
        log_view = self.query_one("#log-view", RichLog)
        # Add timestamp
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")

        display = message
        if isinstance(message, dict):
            display = message.get("message") or message.get("type") or str(message)
            self._route_trace_event(message)
            self._route_translation_event(message)
        log_view.write(f"[dim]{now}[/] {display}")
        
        # PROMPT: Reaction to orchestration auth errors
        if isinstance(message, dict) and message.get("type") == "agent.step.auth_error":
            # Extract provider from message if possible
            data = message.get("data", {})
            provider_id = data.get("agent", "").lower()
            if provider_id:
                # We show a focused connect prompt
                self.call_from_thread(self._handle_async_auth_error, provider_id)

        if isinstance(display, str):
            self._handle_task_event(display)

    def _write_trace(self, selector: str, message: str) -> None:
        try:
            panel = self.query_one(selector, RichLog)
            panel.write(message)
        except Exception:
            pass

    def _format_translation_payload(self, payload: Any) -> str:
        try:
            formatted = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
        except Exception:
            formatted = str(payload)
        return self._truncate_translation_payload(formatted)

    def _truncate_translation_payload(self, text: str, max_chars: int = 3000) -> str:
        if len(text) <= max_chars:
            return text
        return f"{text[:max_chars]}\n...[truncated]"

    def _set_translation_panel(self, selector: str, header: str, payload: Any) -> None:
        try:
            panel = self.query_one(selector, RichLog)
            panel.clear()
            panel.write(header)
            panel.write(self._format_translation_payload(payload))
        except Exception:
            pass

    def _route_translation_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type", "")
        if not event_type.startswith("translation."):
            return

        data = event.get("data") or {}
        payload = data.get("payload")
        connector = data.get("connector", "Unknown")
        step = data.get("step")
        step_label = f" step {step}" if step else ""
        header = f"[bold]{connector}[/]{step_label}"

        if event_type == "translation.engram":
            self._set_translation_panel("#translation-engram", header, payload)
        elif event_type == "translation.request":
            self._set_translation_panel("#translation-request", header, payload)
        elif event_type == "translation.response":
            self._set_translation_panel("#translation-response", header, payload)
        else:
            self._set_translation_panel("#translation-request", header, payload)

    def _route_trace_event(self, event: Dict[str, Any]) -> None:
        event_type = event.get("type", "")
        message = event.get("message") or event_type
        if event_type.startswith("translation."):
            return

        if event_type.startswith("connection"):
            self._write_trace("#trace-connections", message)
            return
        if event_type.startswith("agent"):
            self._write_trace("#trace-agents", message)
            return
        if event_type.startswith("tool"):
            self._write_trace("#trace-tools", message)
            return
        if event_type.startswith("response"):
            self._write_trace("#trace-responses", message)
            return

        # Fallback: try to route by keywords
        msg_lower = str(message).lower()
        if "handing off" in msg_lower or "orchestration plan" in msg_lower:
            self._write_trace("#trace-agents", message)
        elif "response" in msg_lower:
            self._write_trace("#trace-responses", message)
        elif "connect" in msg_lower or "connector" in msg_lower:
            self._write_trace("#trace-connections", message)
        else:
            self._write_trace("#trace-tools", message)

    def _handle_task_event(self, message: str) -> None:
        """Parse orchestration events and update the task tracker panel."""
        import re

        if "Orchestration Plan" in message and "Split into" in message:
            match = re.search(r"Split into (\d+) agent steps", message)
            if match:
                self._set_task_total_steps(int(match.group(1)))
                self._set_task_status("PLANNED")
            return

        if "Step" in message and "Handing off to" in message:
            match = re.search(r"Step (\d+) \(Att (\d+)\):.*Handing off to \[bold\](.+?)\[/\]", message)
            if match:
                step_index = int(match.group(1))
                agent_name = match.group(3)
                self._update_step(step_index, agent_name, "RUNNING")
                self._set_task_status("RUNNING")
            return

        if "Step" in message and "OK" in message:
            match = re.search(r"Step (\d+) OK:.*\[bold\](.+?)\[/\]", message)
            if match:
                step_index = int(match.group(1))
                agent_name = match.group(2)
                self._update_step(step_index, agent_name, "COMPLETED")
            return

        if "failed after retries" in message:
            match = re.search(r"Step (\d+) failed after retries:.*", message)
            if match:
                step_index = int(match.group(1))
                self._update_step(step_index, None, "FAILED")
                self._set_task_status("FAILED")
            return

        if "Orchestration aborted" in message or "Planner:" in message:
            self._set_task_status("FAILED")
            return

        if "Complex task synchronized successfully" in message:
            self._set_task_status("COMPLETED")
            return

    def _reset_task_tracker(self, task_text: str, task_id: Optional[str]) -> None:
        self.active_task_text = task_text
        self.active_task_id = task_id
        self.active_task_status = "SUBMITTED"
        self.active_task_steps = {}
        self.active_task_agents = set()
        self.active_task_total_steps = None
        self._render_task_tracker()

    def _set_task_status(self, status: str) -> None:
        self.active_task_status = status
        self._render_task_tracker()

    def _set_task_total_steps(self, total_steps: int) -> None:
        self.active_task_total_steps = total_steps
        for i in range(1, total_steps + 1):
            self.active_task_steps.setdefault(i, {"agent": None, "status": "PENDING"})
        self._render_task_tracker()

    def _update_step(self, step_index: int, agent_name: Optional[str], status: str) -> None:
        step = self.active_task_steps.get(step_index, {"agent": None, "status": "PENDING"})
        if agent_name:
            step["agent"] = agent_name
            self.active_task_agents.add(agent_name)
        step["status"] = status
        self.active_task_steps[step_index] = step
        self._render_task_tracker()

    def _render_task_tracker(self) -> None:
        try:
            task_current = self.query_one("#task-current", Static)
            task_progress = self.query_one("#task-progress", Static)
            task_connectors = self.query_one("#task-connectors", Static)
        except Exception:
            return

        task_text = self.active_task_text or "No task submitted yet."
        task_current.update(task_text)

        status_line = f"Status: {self.active_task_status or 'IDLE'}"
        if self.active_task_id:
            status_line += f"\nTask ID: {self.active_task_id}"

        steps_lines = []
        if self.active_task_steps:
            for idx in sorted(self.active_task_steps.keys()):
                step = self.active_task_steps[idx]
                agent = step.get("agent") or "TBD"
                step_status = step.get("status") or "PENDING"
                steps_lines.append(f"{idx}. {agent} - {step_status}")
        elif self.active_task_total_steps:
            steps_lines.append(f"Steps: {self.active_task_total_steps} (awaiting plan)")

        progress_text = status_line
        if steps_lines:
            progress_text += "\n" + "\n".join(steps_lines)
        task_progress.update(progress_text)

        if self.active_task_agents:
            task_connectors.update(", ".join(sorted(self.active_task_agents)))
        else:
            task_connectors.update("None")


    @on(Input.Submitted)
    def handle_command(self, event: Input.Submitted) -> None:
        """Handle command input."""
        cmd = event.value.strip()
        if not cmd:
            return

        log_view = self.query_one("#log-view", RichLog)
        log_view.write(f"[bold cyan]> {cmd}[/]")
        
        # Process command (simple router)
        if cmd == "/clear":
            log_view.clear()
        elif cmd == "/status":
            log_view.write("Ã¢ÂÂ¹Ã¯Â¸Â [bold green]System Status:[/] All services operating within normal parameters.")
        elif cmd == "/login":
            config = load_config()
            self.push_screen(AuthScreen(config), self._handle_auth_result)
        elif cmd == "/logout":
            self.token = None
            self.eat = None
            self.user_email = None
            save_config({"base_url": self.base_url, "token": None, "eat": None, "email": None})
            log_view.write("[yellow]Logged out. Please login again.[/]")
            self.push_screen(AuthScreen(load_config()), self._handle_auth_result)
        elif cmd == "/agents":
            log_view.write("Ã¢ÂÂ¹Ã¯Â¸Â [bold yellow]Agents:[/] No active agent connections yet.")
        elif cmd == "/services":
            self.run_worker(self.refresh_connected_services(show_log=True), thread=False)
        elif cmd == "/workflows":
            self.push_screen(WorkflowListScreen(self))
        elif cmd == "/debug":
            self.push_screen(DebugScreen(self))
        elif cmd.startswith("/tasks"):
            parts = cmd.split()
            limit = 10
            if len(parts) > 1 and parts[1].isdigit():
                limit = int(parts[1])
            self.run_worker(self._list_tasks(limit), thread=False)
        elif cmd.startswith("/connect"):
            parts = cmd.split()
            if len(parts) < 2:
                log_view.write("[yellow]Usage:[/] /connect <provider>")
            else:
                provider_id = parts[1].strip().lower()
                if provider_id in PROVIDER_MAP:
                    self._open_service_connect(provider_id)
                else:
                    self._open_service_connect("custom", custom_name=provider_id)
        elif cmd.startswith("/vault"):
            parts = cmd.split()
            if len(parts) == 1 or parts[1] == "list":
                vault = VaultService.list_credentials(self.base_url, self.user_email)
                if not vault:
                    log_view.write("[dim]Local vault is empty for current session.[/]")
                else:
                    log_view.write("[bold yellow]Local Vault Contents:[/]")
                    for pid, data in vault.items():
                        log_view.write(f"  - {pid}: {data.get('type')} (Synced: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data.get('last_synced', 0)))})")
            elif parts[1] == "clear":
                if len(parts) > 2 and parts[2] == "all":
                    VaultService.clear_vault()
                    log_view.write("[green]OK:[/] Entire local vault cleared.")
                else:
                    VaultService.clear_vault(self.base_url, self.user_email)
                    log_view.write(f"[green]OK:[/] Vault cleared for session.")
            else:
                log_view.write("[yellow]Usage:[/] /vault [list|clear|clear all]")
        elif cmd.startswith("/"):
            log_view.write(f"Ã¢ÂšÂ Ã¯Â¸Â  Unknown command: [dim]{cmd}[/]")
        else:
            self.run_worker(self._run_task_command(cmd), thread=False)
            
        self.query_one("#command-input", Input).value = ""

    def action_clear(self) -> None:
        self.query_one("#log-view", RichLog).clear()

    def action_services(self) -> None:
        self.run_worker(self.refresh_connected_services(show_log=True), thread=False)

    def action_workflows(self) -> None:
        self.push_screen(WorkflowListScreen(self))

    def _handle_auth_result(self, result: Optional[Dict[str, Any]]) -> None:
        if not result:
            return
        self.base_url = result.get("base_url") or DEFAULT_BASE_URL
        self.token = result.get("token")
        self.eat = result.get("eat")
        self.user_email = result.get("email")
        self.run_worker(self.refresh_connected_services(), thread=False)

    async def _prompt_reauth(self) -> bool:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        def _handle(result: Optional[Dict[str, Any]]) -> None:
            if result:
                self._handle_auth_result(result)
                future.set_result(True)
            else:
                future.set_result(False)

        self.push_screen(AuthScreen(load_config()), _handle)
        return await future

    async def _ensure_eat(self) -> Optional[str]:
        if self.eat:
            return self.eat
        if not self.token:
            ok = await self._prompt_reauth()
            if not ok:
                return None
        response = await _request(
            "POST",
            self.base_url,
            "/auth/tokens/generate-eat",
            headers=_auth_header(self.token),
        )
        if response.status_code == 200:
            self.eat = response.json().get("eat")
            save_config({
                "base_url": self.base_url,
                "token": self.token,
                "eat": self.eat,
                "email": self.user_email,
            })
            return self.eat
        if _response_indicates_token_issue(response):
            ok = await self._prompt_reauth()
            if ok:
                return await self._ensure_eat()
        return None

    async def _authed_request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        use_session_token: bool = False,
        allow_retry: bool = True,
    ) -> httpx.Response:
        token = self.token if use_session_token else await self._ensure_eat()
        request_headers = _merge_headers(headers, _auth_header(token))
        response = await _request(
            method,
            self.base_url,
            path,
            json_body=json_body,
            data=data,
            headers=request_headers,
        )
        if allow_retry and _response_indicates_token_issue(response):
            if await self._prompt_reauth():
                token = self.token if use_session_token else await self._ensure_eat()
                retry_headers = _merge_headers(headers, _auth_header(token))
                return await _request(
                    method,
                    self.base_url,
                    path,
                    json_body=json_body,
                    data=data,
                    headers=retry_headers,
                )
        return response

    async def _get_connected_providers(self) -> Optional[set]:
        eat = await self._ensure_eat()
        if not eat:
            return None
        response = await self._authed_request("GET", "/credentials")
        if response.status_code != 200:
            return None
        payload = response.json()
        connected = {item.get("provider_name", "").lower() for item in payload if item.get("provider_name")}
        self.connected_providers = connected
        return connected

    async def _prompt_connect_provider(self, provider: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        def _handle_result(result: Optional[Dict[str, Any]]) -> None:
            if not future.done():
                future.set_result(result)

        self.push_screen(ServiceConnectScreen(provider), _handle_result)
        return await future

    async def _connect_provider_from_vault(self, provider: Dict[str, Any], vault_entry: Dict[str, Any]) -> bool:
        """Re-applies a local vault credential to the current backend session."""
        log_view = self.query_one("#log-view", RichLog)
        display_name = provider.get("name", provider.get("id", "Provider"))
        payload = {
            "provider_name": provider.get("id"),
            "credential_type": vault_entry["type"],
            "token": vault_entry["token"],
            "metadata": vault_entry.get("metadata") or {},
        }
        if "metadata" in payload:
            payload["metadata"]["sync_from"] = "tui_vault"
            payload["metadata"]["sync_at"] = time.time()

        response = await self._authed_request("POST", "/credentials", json_body=payload)
        if response.status_code not in (200, 201):
            log_view.write(f"[bold yellow]Vault sync failed for {display_name}:[/] {_extract_error_detail(response)}")
            return False
            
        log_view.write(f"[bold green]Auto-Connected:[/] {display_name} from local vault.")
        return True

    async def _ensure_required_providers_connected(self, command: str, log_view: RichLog) -> bool:
        eat = await self._ensure_eat()
        if not eat:
            return False
            
        required = await _infer_required_providers_via_backend(self.base_url, eat, command)
        if not required:
            return True

        connected_set = await self._get_connected_providers()
        if connected_set is None:
            log_view.write("[bold red]Unable to check connected providers. Please login again.[/]")
            return False

        missing = [provider for provider in required if provider.get("id") not in connected_set]
        if not missing:
            return True
            
        # Try local vault first
        vault = VaultService.list_credentials(self.base_url, self.user_email)
        
        still_missing = []
        for provider in missing:
            provider_id = provider.get("id")
            if provider_id in vault:
                if await self._connect_provider_from_vault(provider, vault[provider_id]):
                    connected_set.add(provider_id)
                    continue
            still_missing.append(provider)

        for provider in still_missing:
            display_name = provider.get("name", provider.get("id", "Provider"))
            log_view.write(f"[bold yellow]Connection required:[/] {display_name}")
            result = await self._prompt_connect_provider(provider)
            if not result or not result.get("provider_name"):
                log_view.write("[yellow]Connection cancelled. Task aborted.[/]")
                return False
            await self.refresh_connected_services(show_log=True)
            if provider.get("id") not in self.connected_providers:
                log_view.write(f"[bold red]Connection failed:[/] {display_name} still not connected.")
                return False

        return True

    async def _run_task_command(self, command: str) -> None:
        log_view = self.query_one("#log-view", RichLog)
        eat = await self._ensure_eat()
        if not eat:
            log_view.write("[bold red]Auth required:[/] Please login to continue.")
            return

        ok = await self._ensure_required_providers_connected(command, log_view)
        if not ok:
            return

        self._reset_task_tracker(command, None)

        request_body = {
            "command": command,
            "metadata": {
                "client": "engram-tui",
                "timestamp": time.time(),
            },
        }

        log_view.write("[dim]Submitting task to Engram backend...[/]")
        try:
            response = await self._authed_request(
                "POST",
                "/tasks/submit",
                json_body=request_body,
            )
        except Exception as exc:
            log_view.write(f"[bold red]Submission error:[/] {str(exc)}")
            return
        if response.status_code != 200:
            log_view.write(f"[bold red]Submission failed:[/] {_extract_error_detail(response)}")
            return

        payload = response.json()
        task_id = payload.get("task_id")
        log_view.write(f"[bold green]Task accepted:[/] {task_id}")
        self._reset_task_tracker(command, str(task_id))


        last_status = None
        while True:
            await asyncio.sleep(2.0)
            try:
                status_resp = await self._authed_request(
                    "GET",
                    f"/tasks/{task_id}",
                )
            except Exception as exc:
                log_view.write(f"[bold red]Status check error:[/] {str(exc)}")
                return
            if status_resp.status_code != 200:
                log_view.write(f"[bold red]Status check failed:[/] {_extract_error_detail(status_resp)}")
                return
            task_status = status_resp.json()
            status = task_status.get("status")
            if status != last_status:
                last_status = status
                log_view.write(f"[dim]Status:[/] {status}")
                self._set_task_status(status)
            if status in ("COMPLETED", "DEAD_LETTER"):
                if task_status.get("last_error"):
                    log_view.write(f"[bold red]Last Error:[/] {task_status['last_error']}")
                results = task_status.get("results")
                if results:
                    log_view.write(f"[bold]Results:[/]\n{json.dumps(results, indent=2)}")
                else:
                    log_view.write("[dim]No workflow results recorded yet.[/]")
                break

    async def _list_tasks(self, limit: int = 10) -> None:
        log_view = self.query_one("#log-view", RichLog)
        response = await self._authed_request("GET", f"/tasks?limit={limit}")
        if response.status_code != 200:
            log_view.write(f"[bold red]Task list failed:[/] {_extract_error_detail(response)}")
            return
        rows = response.json()
        if not rows:
            log_view.write("[dim]No tasks found.[/]")
            return
        log_view.write("[bold]Recent Tasks:[/]")
        for row in rows:
            log_view.write(f"{row.get('id')} | {row.get('status')} | {row.get('updated_at')}")

    async def refresh_available_providers(self) -> None:
        """Fetches the list of supported providers from the backend and updates the UI."""
        global PROVIDERS, PROVIDER_MAP
        response = await self._authed_request("GET", "/credentials/providers")
        if response.status_code == 200:
            PROVIDERS = response.json()
            PROVIDER_MAP = {p["id"]: p for p in PROVIDERS}
            
            # Rebuild the services panel
            panel = self.query_one("#services-panel", Container)
            # Remove existing dynamic rows (keep the title)
            for child in panel.children[1:]:
                child.remove()
            
            for provider in PROVIDERS:
                row = Horizontal(classes="service-row")
                row.mount(Label(provider["name"], id=f"service-name-{provider['id']}", classes="service-name"))
                row.mount(Label("Checking...", id=f"service-status-{provider['id']}", classes="service-status status-waiting"))
                row.mount(Button("Connect", id=f"service-connect-{provider['id']}", classes="service-btn"))
                panel.mount(row)
            
            await self.refresh_connected_services()

    def _set_service_status(self, provider_id: str, status: str, connected: bool) -> None:
        try:
            label = self.query_one(f"#service-status-{provider_id}", Label)
            label.update(status)
            label.remove_class("status-ok")
            label.remove_class("status-waiting")
            label.remove_class("status-error")
            if connected:
                label.add_class("status-ok")
            else:
                label.add_class("status-waiting")

            button = self.query_one(f"#service-connect-{provider_id}", Button)
            if provider_id == "custom":
                button.disabled = False
                button.label = "Add"
            else:
                button.disabled = connected
                button.label = "Connected" if connected else "Connect"
        except Exception:
            pass # Panel might not be fully mounted or refreshed yet

    async def _handle_async_auth_error(self, provider_id: str):
        """Handle auth errors emitted by the backend background worker."""
        provider = PROVIDER_MAP.get(provider_id)
        if provider:
            log_view = self.query_one("#log-view", RichLog)
            log_view.write(f"[bold yellow]Triggering re-authentication for {provider['name']}...[/]")
            await self._prompt_connect_provider(provider)
            await self.refresh_connected_services(show_log=True)

    async def refresh_connected_services(self, show_log: bool = False) -> None:
        log_view = self.query_one("#log-view", RichLog)
        if show_log:
            log_view.write("[dim]Refreshing connected services...[/]")

        if not self.token and not self.eat:
            for provider in PROVIDERS:
                self._set_service_status(provider["id"], "Login required", False)
            return

        eat = await self._ensure_eat()
        if not eat:
            for provider in PROVIDERS:
                self._set_service_status(provider["id"], "Auth required", False)
            return

        response = await self._authed_request("GET", "/credentials")
        if response.status_code != 200:
            for provider in PROVIDERS:
                self._set_service_status(provider["id"], "Unavailable", False)
            if show_log:
                log_view.write(f"[bold red]Credential fetch failed:[/] {_extract_error_detail(response)}")
            return

        payload = response.json()
        connected = {item.get("provider_name", "").lower() for item in payload if item.get("provider_name")}
        self.connected_providers = connected

        known = {provider["id"] for provider in PROVIDERS if not provider.get("custom")}
        for provider in PROVIDERS:
            if provider.get("custom"):
                extras = [name for name in connected if name not in known]
                if extras:
                    self._set_service_status(provider["id"], f"Connected ({len(extras)})", True)
                else:
                    self._set_service_status(provider["id"], "Not connected", False)
                continue
            is_connected = provider["id"] in connected
            self._set_service_status(provider["id"], "Connected" if is_connected else "Not connected", is_connected)

    def _open_service_connect(self, provider_id: str, custom_name: Optional[str] = None) -> None:
        provider = PROVIDER_MAP.get(provider_id)
        if not provider:
            return
        if provider.get("custom") and custom_name:
            provider = {
                **provider,
                "prefill_name": custom_name,
                "display_name": custom_name,
            }
        self.push_screen(ServiceConnectScreen(provider), self._handle_service_connect_result)

    def _handle_service_connect_result(self, result: Optional[Dict[str, Any]]) -> None:
        if not result:
            return
        self.run_worker(self.refresh_connected_services(show_log=True), thread=False)

    @on(Button.Pressed)
    def handle_service_button(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id.startswith("service-connect-"):
            provider_id = button_id.replace("service-connect-", "")
            self._open_service_connect(provider_id)

if __name__ == "__main__":
    from textual import run
    run(EngramTUI)
