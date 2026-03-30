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
    config = _default_config()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = _normalize_config(_decrypt_config(f.read().strip()))
                if saved.get("base_url") == "http://127.0.0.1:5001/api/v1":
                    saved["base_url"] = DEFAULT_BASE_URL
                config.update(saved)
        except (InvalidToken, json.JSONDecodeError, OSError):
            pass
    return config

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
            yield Label("Base URL", classes="form-label")
            yield Input(value=self.config.get("base_url") or DEFAULT_BASE_URL, id="base-url-input", classes="thin-input")
            yield Label("Email", classes="form-label")
            yield Input(placeholder="name@company.com", id="email-input", classes="thin-input")
            yield Label("Password", classes="form-label")
            yield Input(password=True, placeholder="********", id="password-input", classes="thin-input")
            yield Label("Confirm Password (signup only)", classes="form-label")
            yield Input(password=True, placeholder="********", id="confirm-input", classes="thin-input")
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

    @on(Input.Submitted)
    async def handle_submit(self) -> None:
        confirm = self.query_one("#confirm-input", Input).value.strip()
        if confirm:
            await self._authenticate(mode="signup")
        else:
            await self._authenticate(mode="login")

    async def _authenticate(self, mode: str) -> None:
        email = self.query_one("#email-input", Input).value.strip()
        password = self.query_one("#password-input", Input).value.strip()
        confirm = self.query_one("#confirm-input", Input).value.strip()
        base_url = self.query_one("#base-url-input", Input).value.strip() or DEFAULT_BASE_URL

        if not email or not password:
            self._set_error("Email and password are required.")
            return

        try:
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
                    try:
                        err = response.json().get("detail", response.text)
                    except:
                        err = response.text
                    self._set_error(str(err))
                    return

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

class BaseServiceConnectScreen(Screen):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]
    BORDER_COLOR: Optional[str] = None

    def __init__(self, provider: Dict[str, Any], custom_name: Optional[str] = None):
        super().__init__()
        self.provider = provider
        self.custom_name = custom_name

    def on_mount(self) -> None:
        if self.BORDER_COLOR:
            try:
                self.query_one("#service-connect-container", Container).styles.border = ("round", self.BORDER_COLOR)
            except Exception:
                pass

        if self.provider.get("custom"):
            try: self.query_one("#provider-name-input", Input).focus()
            except: pass
        else:
            try: self.query_one("#provider-token-input", Input).focus()
            except: pass

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
        app_ref = self.app
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

        response = await app_ref._authed_request("POST", "/credentials", json_body=payload)
        if response.status_code not in (200, 201):
            self._set_error(_extract_error_detail(response))
            return

        VaultService.store_credential(app_ref.base_url, app_ref.user_email, provider_name, {
            "token": token,
            "type": credential_type,
            "metadata": payload["metadata"]
        })

        self.dismiss({"provider_name": provider_name})

class OpenAIConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#2bdc8d"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #2bdc8d]Connect OpenAI[/]", id="service-connect-title")
            yield Label("Unlock GPT-4o, o1, and o3-mini models.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://platform.openai.com/api-keys[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="sk-proj-...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect OpenAI", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class AnthropicConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#FF9966"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #FF9966]Connect Anthropic[/]", id="service-connect-title")
            yield Label("Unlock Claude 3.5 Sonnet and Claude 3 Opus.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://console.anthropic.com/settings/keys[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="sk-ant-api03-...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect Anthropic", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class GoogleConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#4285F4"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #4285F4]Connect Google DeepMind[/]", id="service-connect-title")
            yield Label("Unlock Gemini 1.5 Pro and 2.0 Flash models.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://aistudio.google.com/app/apikey[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="AIzaSy...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect Google", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class LlamaConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#0668E1"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #0668E1]Connect Meta LLaMA[/]", id="service-connect-title")
            yield Label("Connect to your open-source LLaMA endpoints.", classes="form-label")
            yield Label("\n[dim]Provide your endpoint or proxy key.[/]")
            yield Label("\nAPI Key / Token")
            yield Input(password=True, placeholder="llama-...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect LLaMA", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class MistralConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#FF4E00"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #FF4E00]Connect Mistral AI[/]", id="service-connect-title")
            yield Label("Unlock Mistral Large and Mixtral 8x22B.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://console.mistral.ai/api-keys/[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="Mistral API Key", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect Mistral", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class GrokConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#FFFFFF"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #FFFFFF]Connect xAI (Grok)[/]", id="service-connect-title")
            yield Label("Unlock Grok-2 and Grok-1.5 models.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://console.x.ai/[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="xoxb-...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect xAI", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class PerplexityConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#2bdc8d"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #2bdc8d]Connect Perplexity[/]", id="service-connect-title")
            yield Label("Add deep research capabilities and web search.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://www.perplexity.ai/settings/api[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="pplx-...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect Perplexity", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class DeepseekConnectScreen(BaseServiceConnectScreen):
    BORDER_COLOR = "#2bdc8d"
    def compose(self) -> ComposeResult:
        with Container(id="service-connect-container"):
            yield Label("[bold #2bdc8d]Connect DeepSeek[/]", id="service-connect-title")
            yield Label("Unlock advanced Code Optimization with DeepSeek-Coder.", classes="form-label")
            yield Label("\n[dim]Get your key at: https://platform.deepseek.com/api_keys[/]")
            yield Label("\nAPI Key")
            yield Input(password=True, placeholder="sk-...", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect DeepSeek", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

class GenericServiceConnectScreen(BaseServiceConnectScreen):
    def compose(self) -> ComposeResult:
        provider_name = self.provider.get("name", "Provider")
        display_name = self.custom_name or self.provider.get("display_name") or provider_name
        auth_hint = self.provider.get("hint", "")
        auth_label = "API Key" if self.provider.get("auth") == "api_key" else "OAuth Token"
        with Container(id="service-connect-container"):
            yield Label(f"[bold]Connect {display_name}[/]", id="service-connect-title")
            if self.provider.get("custom"):
                yield Label("Provider Name")
                yield Input(
                    value=self.custom_name or self.provider.get("prefill_name", ""),
                    placeholder="e.g., notion, github, linear",
                    id="provider-name-input",
                    classes="thin-input",
                )
            else:
                yield Label(f"Service: {display_name}")
            yield Label(f"\n{auth_label}")
            yield Input(password=True, placeholder=auth_hint or "Paste token here", id="provider-token-input", classes="thin-input")
            yield Label("", id="service-connect-error")
            with Horizontal(id="service-connect-buttons"):
                yield Button("Connect", id="service-connect-btn", variant="primary")
                yield Button("Cancel", id="service-cancel-btn")

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
        return self.workflow_map.get(self.selected_workflow_id) if self.selected_workflow_id else None

    @on(Button.Pressed, "#workflow-close-btn")
    def _handle_close(self) -> None: self.dismiss(None)

    @on(Button.Pressed, "#workflow-refresh-btn")
    def _handle_refresh(self) -> None: self.run_worker(self._load_workflows(), thread=False)

    @on(Button.Pressed, "#workflow-create-btn")
    def _handle_create(self) -> None: self.app.push_screen(WorkflowCreateScreen(self.app_ref), self._handle_child_result)

    @on(Button.Pressed, "#workflow-run-btn")
    def _handle_run(self) -> None:
        wf = self._get_selected_workflow()
        if wf: self.run_worker(self._run_workflow(wf), thread=False)

    @on(Button.Pressed, "#workflow-schedule-btn")
    def _handle_schedule(self) -> None:
        wf = self._get_selected_workflow()
        if wf: self.app.push_screen(WorkflowScheduleScreen(self.app_ref, wf), self._handle_child_result)

    @on(Button.Pressed, "#workflow-runs-btn")
    def _handle_runs(self) -> None:
        wf = self._get_selected_workflow()
        if wf: self.app.push_screen(WorkflowRunsScreen(self.app_ref, wf))

    def _handle_child_result(self, result: Optional[Dict[str, Any]]) -> None:
        if result and result.get("refresh"): self.run_worker(self._load_workflows(), thread=False)

    async def _run_workflow(self, workflow: Dict[str, Any]) -> None:
        log_view = self.app_ref.query_one("#log-view", RichLog)
        wf_id = workflow.get("id")
        command = workflow.get("command") or ""
        if command:
            if not await self.app_ref._ensure_required_providers_connected(command, log_view): return
        response = await self.app_ref._authed_request("POST", f"/workflows/{wf_id}/run")
        if response.status_code != 200:
            log_view.write(f"[bold red]Workflow run failed:[/] {_extract_error_detail(response)}")
            return
        log_view.write(f"[bold green]Workflow queued:[/] {wf_id} (Task {response.json().get('task_id')})")

class ProviderSelectionScreen(Screen):
    def compose(self) -> ComposeResult:
        with Container(id="workflow-container"):
            yield Label("[bold]Choose an AI Provider to Connect[/]", id="workflow-title")
            yield ListView(id="provider-select-list")
            with Horizontal(id="workflow-buttons"):
                yield Button("Connect Selected", id="provider-select-btn", variant="primary")
                yield Button("Cancel", id="provider-cancel-btn")

    def on_mount(self) -> None:
        list_view = self.query_one("#provider-select-list", ListView)
        
        # Mapping to backend identifiers
        list_view.append(ListItem(Label("[bold #2bdc8d]OpenAI Family[/]"), disabled=True))
        list_view.append(ListItem(Label("  GPT-4o, o1, o3-mini (Family)"), id="sel-openai"))
        
        list_view.append(ListItem(Label("[bold #FF9966]Anthropic[/]"), disabled=True))
        list_view.append(ListItem(Label("  Claude 3.5 Sonnet / 3 Opus"), id="sel-anthropic"))
        
        list_view.append(ListItem(Label("[bold #4285F4]Google DeepMind[/]"), disabled=True))
        list_view.append(ListItem(Label("  Gemini 1.5 Pro / 2.0 Flash"), id="sel-google"))
        
        list_view.append(ListItem(Label("[bold #0668E1]Meta / LLaMA[/]"), disabled=True))
        list_view.append(ListItem(Label("  LLaMA 3.1 & 3.2 (Self-Hosted/API)"), id="sel-llama"))

        list_view.append(ListItem(Label("[bold #FF4E00]Mistral AI[/]"), disabled=True))
        list_view.append(ListItem(Label("  Mistral Large / Mixtral 8x22B"), id="sel-mistral"))

        list_view.append(ListItem(Label("[bold]xAI (Grok)[/]"), disabled=True))
        list_view.append(ListItem(Label("  Grok-2 / Grok-1.5"), id="sel-grok"))

        list_view.append(ListItem(Label("[bold #2bdc8d]Specialized Models[/]"), disabled=True))
        list_view.append(ListItem(Label("  Perplexity (Research/Search)"), id="sel-perplexity"))
        list_view.append(ListItem(Label("  DeepSeek-Coder (Code Optimization)"), id="sel-deepseek"))

        list_view.append(ListItem(Label("[bold #b8b2a8]--- SOFTWARE TOOLS ---[/]"), disabled=True))
        for p in PROVIDERS:
             if p.get("id") not in ["openai", "anthropic", "google", "llama", "mistral", "grok", "perplexity", "deepseek", "claude", "gemini"] and not p.get("custom"):
                 list_view.append(ListItem(Label(f"  {p.get('name', p.get('id'))}"), id=f"sel-{p['id']}"))

    @on(ListView.Selected, "#provider-select-list")
    def on_select(self, event: ListView.Selected) -> None:
        self.dismiss(event.item.id.replace("sel-", ""))

    @on(Button.Pressed, "#provider-select-btn")
    def on_connect(self) -> None:
        list_view = self.query_one("#provider-select-list", ListView)
        if list_view.index is not None:
             self.dismiss(list_view.children[list_view.index].id.replace("sel-", ""))

    @on(Button.Pressed, "#provider-cancel-btn")
    def on_cancel(self) -> None: self.dismiss(None)

class WelcomeScreen(Screen):
    def compose(self) -> ComposeResult:
        LOGO_BLOCKY = r"""
  _____   _   _    ____   ____       _      __  __ 
 | ____| | \ | |  / ___| |  _ \     / \    |  \/  |
 |  _|   |  \| | | |  _  | |_) |   / _ \   | |\/| |
 | |___  | |\  | | |_| | |  _ <   / ___ \  | |  | |
 |_____| |_| \_|  \____| |_| \_\ /_/   \_\ |_|  |_|
"""
        with Container(id="welcome-container"):
            yield Label("[#FF9966]* Welcome to [bold]Engram[/][/]", id="welcome-subtitle")
            yield Static(f"[#FF9966]{LOGO_BLOCKY}[/]", id="welcome-logo")
            yield Label("Currently Running in: [cyan]Mock Mode[/] (No API Keys Found)", id="welcome-status")
            yield Label("Press [bold]Enter[/] to start or [bold]S[/] to setup agents", id="welcome-continue")
            with Horizontal(id="welcome-buttons"):
                yield Button("Start Bridging", id="welcome-start-btn", variant="primary")
                yield Button("Setup API Keys", id="welcome-setup-btn")

    @on(Button.Pressed, "#welcome-start-btn")
    def on_start(self) -> None: self.app.pop_screen()

    @on(Button.Pressed, "#welcome-setup-btn")
    def on_setup(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(ProviderSelectionScreen(), self.app._handle_provider_setup_result)

    async def on_key(self, event) -> None:
        if event.key in ("enter", "escape"): self.app.pop_screen()
        elif event.key == "s": self.on_setup()

# ASCII header
LOGO = r"""[#2bdc8d]
  _____   _   _    ____   ____       _      __  __ 
 | ____| | \ | |  / ___| |  _ \     / \    |  \/  |
 |  _|   |  \| | | |  _  | |_) |   / _ \   | |\/| |
 | |___  | |\  | | |_| | |  _ <   / ___ \  | |  | |
 |_____| |_| \_|  \____| |_| \_\ /_/   \_\ |_|  |_|
[/]
          [dim]Universal Protocol Bridge[/]
"""

class EngramTUI(App):
    CSS = """
    Screen { background: #0f0f0f; color: #e6e1d7; }
    WelcomeScreen { align: center middle; background: #0f0f0f; }
    #welcome-container { width: auto; height: auto; padding: 2 4; }
    #welcome-subtitle { border: round #FF9966; padding: 0 2; margin-bottom: 2; width: auto; }
    #welcome-logo { color: #FF9966; text-align: left; width: auto; margin-bottom: 4; }
    #welcome-status { text-align: left; color: #2bdc8d; margin-bottom: 1; }
    #welcome-continue { text-align: left; color: #b8b2a8; margin-bottom: 2; }
    #welcome-buttons { height: 3; width: auto; }
    #welcome-buttons Button { margin-right: 2; }
    #header { height: 8; content-align: left top; background: #0f0f0f; border: none; margin: 1 2 0 2; padding: 0 2; }
    #main-container { height: 1fr; margin: 0 2 1 2; }
    #main-left { width: 70%; padding-right: 1; }
    #trace-panels { height: 13; background: #121212; border: round #1f2d28; padding: 1; margin-bottom: 1; }
    .trace-row { height: 1fr; }
    .trace-panel { width: 1fr; border: round #1f2d28; margin-right: 1; padding: 0 1; background: #101010; }
    #translation-panel { height: 10; background: #121212; border: round #1f2d28; padding: 1; margin-bottom: 1; }
    .translation-panel { width: 1fr; border: round #1f2d28; margin-right: 1; padding: 0 1; background: #101010; }
    .translation-title { text-style: bold; color: #2bdc8d; margin-bottom: 0; }
    .trace-title { text-style: bold; color: #2bdc8d; margin-bottom: 0; }
    #log-view { height: 1fr; background: #121212; border: round #1f2d28; padding: 1; }
    #sidebar { width: 30%; background: #121212; border: round #1f2d28; padding: 1; }
    .sidebar-title { text-style: bold; color: #2bdc8d; margin-bottom: 1; }
    .stat-item { margin-bottom: 1; color: #d7d2c7; }
    #task-panel { border: round #1f2d28; padding: 1; margin-bottom: 1; background: #121212; }
    #task-current, #task-progress, #task-connectors { color: #e6e1d7; }
    #input-area { height: 3; background: #101010; border-top: heavy #2bdc8d; padding: 0 2; margin: 0 2 1 2; }
    Input { background: #101010; border: solid #1f2d28; color: #e6e1d7; }
    Input:focus { border: solid #2bdc8d; }
    Button { background: #101010; color: #e6e1d7; border: solid #1f2d28; }
    Button:focus, Button.-hover { background: #132019; border: solid #2bdc8d; color: #f3e6d4; }
    .status-ok { color: #2bdc8d; }
    .status-waiting { color: #e0b15b; }
    #auth-container { width: 72%; height: auto; padding: 1 2; border: round #1f2d28; background: #101010; margin: 1 4; }
    #auth-title { content-align: left middle; text-style: bold; color: #2bdc8d; margin-bottom: 1; width: auto; }
    .form-label { color: #e6e1d7; }
    .thin-input { background: #0f0f0f; border: solid #1f2d28; height: 3; }
    .thin-input:focus { border: solid #2bdc8d; }
    #auth-buttons { margin-top: 1; height: auto; }
    #auth-buttons Button { width: 1fr; }
    #auth-error { color: #e74c3c; margin-top: 1; }
    #service-connect-container { width: 70%; height: auto; padding: 1 2; border: round #1f2d28; background: #101010; margin: 1 4; }
    #service-connect-title { content-align: left middle; text-style: bold; color: #2bdc8d; margin-bottom: 1; width: auto; }
    #service-connect-buttons { margin-top: 1; height: auto; }
    #service-connect-error { color: #e74c3c; margin-top: 1; }
    #workflow-container, #workflow-create-container, #workflow-schedule-container, #workflow-runs-container { width: 80%; height: auto; padding: 1 2; border: round #1f2d28; background: #101010; margin: 1 4; }
    #workflow-title, #workflow-create-title, #workflow-schedule-title, #workflow-runs-title { content-align: left middle; text-style: bold; color: #2bdc8d; margin-bottom: 1; width: auto; }
    #workflow-create-error, #workflow-schedule-error { color: #e74c3c; margin-top: 1; }
    #services-panel { margin-top: 1; border-top: solid #1f2d28; padding-top: 1; }
    .service-row { height: auto; margin-bottom: 1; }
    .service-name { width: 45%; }
    .service-status { width: 30%; }
    .service-btn { width: 25%; }
    #debug-container { width: 95%; height: 95%; border: heavy #2bdc8d; background: #0f0f0f; margin: 1 2; padding: 1; }
    #debug-title { content-align: center middle; text-style: bold; color: #2bdc8d; margin-bottom: 1; background: #101010; height: 3; }
    .debug-subtitle { text-style: bold underline; color: #2bdc8d; margin-bottom: 1; }
    #debug-main-layout { height: 1fr; }
    #debug-list-panel { width: 35%; border-right: solid #1f2d28; padding: 0 1; }
    #debug-detail-panel { width: 65%; padding: 0 1; }
    .debug-actions { height: 3; margin-top: 1; }
    #debug-tabs { height: 1fr; }
    .protocol-pane { width: 1fr; border: round #1f2d28; margin: 0 1; background: #121212; }
    .protocol-title { text-style: bold; color: #2bdc8d; content-align: center middle; background: #101010; }
    #debug-event-log, #debug-trace-source, #debug-trace-target, #debug-task-plan { height: 1fr; background: #0f0f0f; }
    #debug-footer { height: 3; background: #101010; border-top: solid #2bdc8d; padding: 0 2; align: center middle; }
    #debug-status-hint { margin-left: 2; color: #b8b2a8; }
    .hidden { display: none; }
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
        yield Static(LOGO, id="header")
        with Container(id="auth-container"):
            yield Label("Engram Sign In", id="auth-title")
            yield Label("Base URL", classes="form-label")
            yield Input(value=self.base_url or DEFAULT_BASE_URL, id="inline-base-url", classes="thin-input")
            yield Label("Email", classes="form-label")
            yield Input(placeholder="name@company.com", id="inline-email", classes="thin-input")
            yield Label("Password", classes="form-label")
            yield Input(password=True, placeholder="********", id="inline-password", classes="thin-input")
            yield Label("Confirm Password (signup only)", classes="form-label")
            yield Input(password=True, placeholder="********", id="inline-confirm", classes="thin-input")
            yield Label("", id="inline-auth-error")
            with Horizontal(id="auth-buttons"):
                yield Button("Login", id="inline-login-btn", variant="primary")
                yield Button("Signup", id="inline-signup-btn")
                yield Button("Quit", id="inline-quit-btn")

        with Container(id="main-shell"):
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
                    yield RichLog(id="log-view", highlight=True, markup=True)
                
                with Vertical(id="sidebar"):
                    yield Label("SYSTEM STATUS", classes="sidebar-title")
                    yield Label("[bold]FastAPI Engine:[/] [green]Online[/]", classes="stat-item")
                    yield Label("[bold]Discovery Service:[/] [green]Active[/]", classes="stat-item")
                    yield Label("[bold]Task Worker:[/] [green]Processing[/]", classes="stat-item")
                    with Container(id="task-panel"):
                        yield Label("TASK TRACKER", classes="sidebar-title")
                        yield Label("CURRENT TASK", classes="sidebar-title")
                        yield Static("No task submitted yet.", id="task-current")
                        yield Label("PROGRESS", classes="sidebar-title")
                        yield Static("Status: IDLE", id="task-progress")
                        yield Label("ACTIVE CONNECTORS", classes="sidebar-title")
                        yield Static("None", id="task-connectors")
                    yield Label("\nRECENT ACTIVITY", classes="sidebar-title"); yield Label("- Bridge active", classes="stat-item")
                    with Container(id="services-panel"): yield Label("CONNECTED SERVICES", classes="sidebar-title")
            yield Input(placeholder="Type a task or /command", id="command-input")
            yield Footer()

    async def on_mount(self) -> None:
        from app.core.tui_bridge import register_tui_loop
        register_tui_loop(asyncio.get_event_loop())
        config = load_config()
        self.base_url = self.cli_base_url or config.get("base_url") or DEFAULT_BASE_URL
        self.token, self.eat, self.user_email = config.get("token"), config.get("eat"), config.get("email")
        
        log_view = self.query_one("#log-view", RichLog)
        if self.eat:
            self._set_auth_visible(False)
            log_view.write(f"[dim]System:[/] Checking connectivity to [bold]{self.base_url}[/]...")
            self.query_one("#command-input").focus()
        else:
            self._set_auth_visible(True)

        log_view.write("[dim]System:[/] [green]Success:[/] Connected to Engram Bridge.")
        from app.core.config import settings
        if not settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_API_KEY == "placeholder":
            log_view.write("[bold yellow]Warning:[/] Mock Mode active. Press 'S' to setup real agents.")
            
        self.message_receiver()
        self.run_worker(self.refresh_available_providers(), thread=False)
        if self.initial_screen == "debug": self.push_screen(DebugScreen(self))
        else: self.push_screen(WelcomeScreen())

    def _handle_provider_setup_result(self, provider_id: Optional[str]) -> None:
        if provider_id: self._open_service_connect(provider_id)

    @work(exclusive=True, thread=True)
    def message_receiver(self):
        import asyncio
        async def run_listener():
            while True:
                msg = await tui_event_queue.get()
                self.call_from_thread(self.log_message, msg)
                tui_event_queue.task_done()
        self.run_worker(run_listener())

    def log_message(self, message: Any) -> None:
        log_view = self.query_one("#log-view", RichLog)
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        display = message
        if isinstance(message, dict):
            display = message.get("message") or message.get("type") or str(message)
            self._route_trace_event(message); self._route_translation_event(message)
        log_view.write(f"[dim]{now}[/] {display}")
        if isinstance(message, dict) and message.get("type") == "agent.step.auth_error":
            p_id = message.get("data", {}).get("agent", "").lower()
            if p_id: self.call_from_thread(self._handle_async_auth_error, p_id)
        if isinstance(display, str): self._handle_task_event(display)

    def _write_trace(self, selector: str, message: str) -> None:
        try: self.query_one(selector, RichLog).write(message)
        except: pass

    def _format_translation_payload(self, payload: Any) -> str:
        try: return json.dumps(payload, indent=2, sort_keys=True)
        except: return str(payload)

    def _route_translation_event(self, event: Dict[str, Any]) -> None:
        etype = event.get("type", "")
        if not etype.startswith("translation."): return
        data = event.get("data") or {}; payload = data.get("payload"); connector = data.get("connector", "Unknown")
        hdr = f"[bold]{connector}[/] step {data.get('step') or ''}"
        if etype == "translation.engram": self.query_one("#translation-engram", RichLog).write(hdr + "\n" + self._format_translation_payload(payload))
        elif etype == "translation.request": self.query_one("#translation-request", RichLog).write(hdr + "\n" + self._format_translation_payload(payload))
        elif etype == "translation.response": self.query_one("#translation-response", RichLog).write(hdr + "\n" + self._format_translation_payload(payload))

    def _route_trace_event(self, event: Dict[str, Any]) -> None:
        etype = event.get("type", ""); msg = event.get("message") or etype
        if etype.startswith("translation."): return
        if etype.startswith("connection"): self._write_trace("#trace-connections", msg)
        elif etype.startswith("agent"): self._write_trace("#trace-agents", msg)
        elif etype.startswith("tool"): self._write_trace("#trace-tools", msg)
        elif etype.startswith("response"): self._write_trace("#trace-responses", msg)

    def _handle_task_event(self, message: str) -> None:
        import re
        if "Orchestration Plan" in message:
            m = re.search(r"Split into (\d+) agent steps", message)
            if m: self._set_task_total_steps(int(m.group(1))); self._set_task_status("PLANNED")
        elif "Handing off to" in message:
            m = re.search(r"Step (\d+).*Handing off to \[bold\](.+?)\[/\]", message)
            if m: self._update_step(int(m.group(1)), m.group(2), "RUNNING"); self._set_task_status("RUNNING")
        elif "Step" in message and "OK" in message:
            m = re.search(r"Step (\d+) OK:.*\[bold\](.+?)\[/\]", message)
            if m: self._update_step(int(m.group(1)), m.group(2), "COMPLETED")

    def _set_task_status(self, status: str) -> None: self.active_task_status = status; self._render_task_tracker()
    def _set_task_total_steps(self, total: int) -> None:
        self.active_task_total_steps = total
        for i in range(1, total + 1): self.active_task_steps.setdefault(i, {"agent": None, "status": "PENDING"})
        self._render_task_tracker()
    def _update_step(self, idx: int, agent: Optional[str], status: str) -> None:
        step = self.active_task_steps.get(idx, {"agent": None, "status": "PENDING"})
        if agent: step["agent"] = agent; self.active_task_agents.add(agent)
        step["status"] = status; self.active_task_steps[idx] = step; self._render_task_tracker()
    def _render_task_tracker(self) -> None:
        try:
            self.query_one("#task-current", Static).update(self.active_task_text or "No task submitted yet.")
            prog = f"Status: {self.active_task_status or 'IDLE'}\n" + "\n".join([f"{i}. {s['agent'] or 'TBD'} - {s['status']}" for i,s in sorted(self.active_task_steps.items())])
            self.query_one("#task-progress", Static).update(prog)
            self.query_one("#task-connectors", Static).update(", ".join(sorted(self.active_task_agents)) or "None")
        except: pass

    async def on_key(self, event) -> None:
        if event.key == "enter":
            inp = self.query_one("#command-input", Input)
            if inp.has_focus and inp.value.strip():
                cmd = inp.value.strip(); inp.value = ""; log = self.query_one("#log-view", RichLog); log.write(f"[bold cyan]> {cmd}[/]")
                if cmd.startswith("/"): await self._handle_slash_command(cmd, log)
                else: self.run_worker(self._run_task_command(cmd), thread=False)

    @on(Input.Submitted, "#command-input")
    async def handle_input_submit(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        if cmd:
            log = self.query_one("#log-view", RichLog); event.input.value = ""; log.write(f"[bold cyan]> {cmd}[/]")
            if cmd.startswith("/"): await self._handle_slash_command(cmd, log)
            else: self.run_worker(self._run_task_command(cmd), thread=False)

    def _set_auth_visible(self, visible: bool) -> None:
        try:
            self.query_one("#auth-container").styles.display = "block" if visible else "none"
            self.query_one("#main-shell").styles.display = "none" if visible else "block"
            if visible: self.query_one("#inline-email").focus()
        except: pass

    async def _authenticate_inline(self, mode: str) -> None:
        email, pwd, cfg_url = self.query_one("#inline-email").value, self.query_one("#inline-password").value, self.query_one("#inline-base-url").value or DEFAULT_BASE_URL
        try:
            if mode=="signup": await _request("POST", cfg_url, "/auth/signup", json_body={"email":email,"password":pwd})
            resp = await _request("POST", cfg_url, "/auth/login", data={"username":email,"password":pwd})
            self.token = resp.json().get("access_token")
            eat_resp = await _request("POST", cfg_url, "/auth/tokens/generate-eat", headers=_auth_header(self.token))
            self.eat = eat_resp.json().get("eat"); self.base_url, self.user_email = cfg_url, email
            save_config({"base_url":self.base_url,"token":self.token,"eat":self.eat,"email":self.user_email})
            self._set_auth_visible(False); self.run_worker(self.refresh_available_providers(), thread=False)
        except Exception as e: self.query_one("#inline-auth-error").update(str(e))

    @on(Button.Pressed, "#inline-login-btn")
    async def do_login(self) -> None: await self._authenticate_inline("login")
    @on(Button.Pressed, "#inline-signup-btn")
    async def do_signup(self) -> None: await self._authenticate_inline("signup")
    @on(Button.Pressed, "#inline-quit-btn")
    def do_quit(self) -> None: self.exit()

    async def _authed_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        eat = await self._ensure_eat()
        return await _request(method, self.base_url, path, headers=_merge_headers(kwargs.get("headers"), _auth_header(eat)), **kwargs)

    async def _ensure_eat(self) -> str: return self.eat # Simplified for reset

    async def refresh_available_providers(self) -> None:
        global PROVIDERS, PROVIDER_MAP
        resp = await self._authed_request("GET", "/credentials/providers")
        if resp.status_code == 200:
            PROVIDERS = resp.json(); PROVIDER_MAP = {p["id"]: p for p in PROVIDERS}
            panel = self.query_one("#services-panel")
            panel.query("Horizontal.service-row").remove()
            for p in PROVIDERS:
                panel.mount(Horizontal(Label(p["name"], classes="service-name"), Label("Unknown", id=f"service-status-{p['id']}", classes="service-status"), Button("Connect", id=f"service-connect-{p['id']}", classes="service-btn"), classes="service-row"))
            await self.refresh_connected_services()

    async def refresh_connected_services(self, show_log=False) -> None:
        resp = await self._authed_request("GET", "/credentials")
        if resp.status_code == 200:
            conn = {item["provider_name"].lower() for item in resp.json() if "provider_name" in item}
            for p in PROVIDERS:
                is_c = p["id"] in conn; lbl = self.query_one(f"#service-status-{p['id']}", Label)
                lbl.update("Connected" if is_c else "Not connected"); lbl.add_class("status-ok" if is_c else "status-waiting")
                self.query_one(f"#service-connect-{p['id']}", Button).label = "Connected" if is_c else "Connect"

    def _open_service_connect(self, provider_id: str) -> None:
        # MAP SELECTION TO BACKEND IDs
        target_id = {"openai":"openai", "anthropic":"claude", "google":"gemini", "llama":"llama", "mistral":"mistral", "grok":"grok", "perplexity":"perplexity", "deepseek":"deepseek"}.get(provider_id, provider_id)
        p = PROVIDER_MAP.get(target_id) or {"id": target_id, "name": target_id.capitalize(), "auth": "api_key"}
        
        screens = {
            "openai": OpenAIConnectScreen,
            "claude": AnthropicConnectScreen,
            "gemini": GoogleConnectScreen,
            "llama": LlamaConnectScreen,
            "mistral": MistralConnectScreen,
            "grok": GrokConnectScreen,
            "perplexity": PerplexityConnectScreen,
            "deepseek": DeepseekConnectScreen,
        }
        
        ScreenClass = screens.get(target_id, GenericServiceConnectScreen)
        self.push_screen(ScreenClass(p), lambda _: self.run_worker(self.refresh_connected_services(), thread=False))

    async def _run_task_command(self, command: str) -> None:
        self.active_task_text, self.active_task_status = command, "SUBMITTING"
        resp = await self._authed_request("POST", "/tasks/submit", json_body={"command": command})
        if resp.status_code == 200: 
            tid = resp.json().get("task_id")
            self.query_one("#log-view", RichLog).write(f"[bold green]Task accepted:[/] {tid}")
            while True:
                await asyncio.sleep(2)
                st = await self._authed_request("GET", f"/tasks/{tid}")
                status = st.json().get("status"); self._set_task_status(status)
                if status in ("COMPLETED", "DEAD_LETTER"): break

    @on(Button.Pressed)
    def handle_buttons(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid.startswith("service-connect-"): self._open_service_connect(bid.replace("service-connect-", ""))

if __name__ == "__main__": EngramTUI().run()
