# Installation

This page covers every way to install Engram — from the one-line installer to a full manual setup. Pick the path that matches your environment and comfort level.

---

## Quick Install

### Linux / macOS / WSL2

```bash
curl -fsSL https://kwstx.github.io/engram_translator/setup.sh | bash
```

This single command handles everything: directory creation, dependency installation, CLI setup, and PATH configuration. Within 60–90 seconds, the `engram` command is available globally.

### Windows

Native Windows is supported for local development via the `engram.bat` self-healing entry point. For production deployments, use WSL2, Docker, or a Linux server.

**Option A — WSL2 (Recommended)**

If you have WSL2 installed, open your WSL2 terminal and run the Linux installer above. This gives you the full Unix experience with no compatibility caveats.

**Option B — Native Windows**

```powershell
git clone https://github.com/kwstx/engram_translator.git
cd engram_translator
.\engram.bat
```

The `.bat` entry point auto-creates a Python virtual environment, installs all dependencies from `requirements.txt`, validates imports, and launches the CLI. It's functionally identical to the Unix `./engram` script.

> **Note:** The native Windows path works for development and testing. Some optional features (systemd services, Unix signal handling) are not available on Windows. Use WSL2 or Docker for production workloads.

---

## What the Installer Does

The one-line installer performs these steps automatically:

1. **Creates `~/.engram/`** — The configuration directory where `config.yaml`, encrypted credentials, and the swarm memory database live
2. **Clones the repository** — Pulls the latest code from `main` into the installation directory
3. **Creates a Python virtual environment** — Isolates Engram's dependencies from your system Python
4. **Installs dependencies** — Runs `pip install -r requirements.txt` to install all core and optional packages
5. **Initializes configuration** — Writes a default `config.yaml` with sensible defaults
6. **Creates CLI wrapper** — Installs an `engram` shell script to `~/bin/` or `~/.local/bin/`
7. **Updates PATH** — Adds the bin directory to your shell profile (`.bashrc`, `.zshrc`, or `.profile`)
8. **Optionally starts the background service** — On Linux, creates a systemd user service; on macOS, creates a launchd plist

By the end, you can run `engram run` from any directory to start the gateway and interactive REPL.

---

## After Installation

Reload your shell and start the gateway:

```bash
source ~/.bashrc   # or: source ~/.zshrc
engram run         # Start the gateway and interactive REPL
```

The gateway binds to `http://127.0.0.1:8000` by default. The REPL drops you into an interactive session where every Engram subcommand is available without typing `engram` as a prefix.

To configure individual settings later, use the dedicated commands:

```bash
engram config set backend_preference mcp   # Set default routing backend
engram config set model_provider openai     # Set AI model provider
engram auth login                          # Authenticate and get an EAT
engram info                                # Check system status
```

> **Tip:** Run `engram info` after installation to verify that the config path, API URL, backend preference, and authentication status are all correct.

---

## Prerequisites

The only prerequisites are **Git** and **Python 3.11+**. The installer and self-healing entry points handle everything else.

| Requirement | Purpose | Notes |
|---|---|---|
| **Python 3.11+** | Gateway, CLI, SDK, and all core services | Required |
| **Git** | Cloning the repository and version management | Required |
| **pip** | Python package management | Installed automatically if missing |
| **Node.js 18+** | Playground frontend and browser automation | Optional |
| **PostgreSQL 15+** | Production database | Optional — SQLite used by default for local dev |
| **Redis 7+** | Event streams, semantic caching, rate limiting | Optional — auto-disabled when not available |
| **Docker** | Containerized deployment | Optional — for production/staging setups |

> **Important:** You do **not** need to install PostgreSQL or Redis for local development. Engram automatically detects the runtime environment and falls back to SQLite and in-memory alternatives when Docker infrastructure isn't available. The smart fallback logic in `app/core/config.py` checks for the presence of `/.dockerenv` and `KUBERNETES_PORT` to decide which backend to use.

Just make sure `git` and `python3` (or `python` on Windows) are on your PATH:

```bash
git --version    # Should print git version 2.x+
python3 --version # Should print Python 3.11+
```

---

## Manual Installation

If you prefer full control over the installation process — or you're setting up a development environment — follow these steps.

### Step 1: Clone the Repository

```bash
git clone https://github.com/kwstx/engram_translator.git
cd engram_translator
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate   # Linux/macOS
# or: .\venv\Scripts\activate   # Windows PowerShell
```

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

The `requirements.txt` includes all core and optional dependencies:

| Category | Key Packages |
|---|---|
| **Web framework** | `fastapi`, `uvicorn[standard]`, `httpx` |
| **Database** | `sqlalchemy[asyncio]`, `sqlmodel`, `asyncpg`, `aiosqlite`, `alembic` |
| **Semantic layer** | `rdflib`, `owlready2`, `pyswip`, `pyDatalog` |
| **ML / Embeddings** | `scikit-learn`, `sentence-transformers`, `torch`, `joblib` |
| **CLI / TUI** | `typer[all]`, `rich`, `textual` |
| **Auth / Security** | `python-jose[cryptography]`, `passlib[bcrypt]`, `keyring`, `cryptography` |
| **MCP** | `mcp` (Model Context Protocol SDK) |
| **Monitoring** | `prometheus-fastapi-instrumentator`, `sentry-sdk`, `structlog` |
| **Task queue** | `celery` (for evolution pipeline) |
| **Config** | `pydantic-settings`, `pyyaml` |

> **Tip:** For a minimal installation without ML features (`sentence-transformers`, `torch`, `celery`), install only the core dependencies listed in `pyproject.toml`. This reduces the installation footprint from ~2GB to ~200MB, suitable for constrained environments or CI pipelines.

### Step 4: Initialize Configuration

```bash
mkdir -p ~/.engram
engram init   # Or: python -m app.cli init
```

This creates the configuration directory at `~/.engram/` and writes the default `config.yaml`:

```yaml
# ~/.engram/config.yaml
api_url: http://127.0.0.1:8000
backend_preference: mcp
model_provider: openai
verbose: false
```

Each field is explained in the [Configuration](./07-configuration.md) guide. You can also set values via the CLI:

```bash
engram config set api_url http://my-server:8000
engram config set backend_preference cli
```

### Step 5: Add API Keys

Provider credentials can be configured in three ways:

**Option A — Environment variables (`.env` file)**

Create a `.env` file at the project root:

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
SLACK_API_TOKEN=xoxb-...
```

This is the simplest approach for local development and Docker deployments.

**Option B — System keyring**

```bash
engram auth login --token <your-eat-token>
```

EAT tokens are stored in the system keyring (macOS Keychain, Windows Credential Locker, or Linux Secret Service) for maximum security. Falls back to `config.yaml` if the keyring is unavailable.

**Option C — TUI service connection**

Launch the TUI dashboard (`engram run --debug`) and use the service connection screens to input API keys for each provider. Credentials are encrypted with Fernet symmetric encryption and stored in `~/.engram/config.enc`.

### Step 6: Start the Gateway

```bash
engram run
```

Or start the backend directly with uvicorn for more control:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables hot-reloading during development. The FastAPI application initializes the orchestration services, database connections, API routers, and background workers automatically via the lifespan handler.

### Step 7: Verify the Installation

```bash
engram info      # Check CLI configuration and connection status
engram tools list   # Verify tool registry is accessible
```

Successful output from `engram info` shows:

```
╭──── System Information ──────────────────╮
│ Config Path   ~/.engram/config.yaml      │
│ API URL       http://127.0.0.1:8000      │
│ Backend       mcp                        │
│ Auth Status   Authenticated              │
│ EAT Token     ****abc1                   │
╰──────────────────────────────────────────╯
```

---

## Quick-Reference: Manual Install (Condensed)

For those who just want the commands:

```bash
# Clone & enter
git clone https://github.com/kwstx/engram_translator.git
cd engram_translator

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install everything
pip install --upgrade pip
pip install -r requirements.txt

# Configure
mkdir -p ~/.engram
engram init
engram config set model_provider openai

# Start
engram run
```

---

## Self-Healing Entry Points

Engram ships with self-healing bootstrap scripts that automatically manage the virtual environment and dependencies on every launch:

| Platform | Entry Point | What it does |
|---|---|---|
| Linux / macOS | `./engram` | Checks venv, validates imports, installs missing deps, then launches CLI |
| Windows | `.\engram.bat` | Same as above for Windows Command Prompt and PowerShell |

These scripts eliminate "it worked on my machine" problems. The startup sequence is:

1. **Check for virtual environment** — Creates one if missing
2. **Fast import test** — Attempts to import critical modules (`fastapi`, `rich`, `typer`, `rdflib`)
3. **Auto-repair** — If any import fails, runs `pip install -r requirements.txt` automatically
4. **Launch** — Passes all arguments to the Engram CLI

If a dependency breaks after an update — say a new version of `rdflib` introduces an incompatibility — the entry point detects the failure via the import test and automatically re-synchronizes the environment before launching. No manual `pip install` required.

---

## Runtime Environment Detection

Engram's configuration layer includes smart fallback logic that adapts to your runtime environment automatically:

```python
# Simplified logic from app/core/config.py
if not os.path.exists("/.dockerenv") and not os.environ.get("KUBERNETES_PORT"):
    # Running locally — use SQLite instead of PostgreSQL
    if "db:5432" in DATABASE_URL or POSTGRES_SERVER == "db":
        DATABASE_URL = "sqlite+aiosqlite:///./engram.db"
    # Disable Redis if the default Docker hostname is configured
    if REDIS_HOST == "redis":
        REDIS_ENABLED = False
```

This means:

| Environment | Database | Redis | Behavior |
|---|---|---|---|
| **Docker Compose** | PostgreSQL (via `db:5432`) | Redis (via `redis:6379`) | Full production stack |
| **Kubernetes** | PostgreSQL (managed RDS) | Redis (managed ElastiCache) | Full production stack |
| **Local development** | SQLite (`./engram.db`) | Disabled (in-memory fallback) | Zero-dependency startup |

You never need to install PostgreSQL or Redis for local development. The smart fallback makes `engram run` work immediately after cloning.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `engram: command not found` | Reload your shell (`source ~/.bashrc`) or add `~/bin` to your PATH. On Windows, restart your terminal. |
| `Connection Error: Could not connect` | Start the backend first: `engram run` or `uvicorn app.main:app`. The gateway must be running for CLI commands to work. |
| API key errors | Run `engram auth login` to authenticate, or check `engram config show` for the current API URL. |
| Import errors on launch | The self-healing entry point should fix this automatically. If not, run `pip install -r requirements.txt` manually in the venv. |
| Database migration errors | Run `alembic upgrade head` to apply pending migrations. This is needed after updates that change the database schema. |
| Redis connection refused | Redis is optional for local dev. Engram auto-disables it when unavailable. No action needed. |
| `ModuleNotFoundError: No module named 'app'` | Make sure you're running from the project root directory (`translator_middleware/`), not a subdirectory. |
| Port 8000 already in use | Another service is using that port. Either stop it, or start Engram on a different port: `engram run --port 8001`. |
| `jwt.exceptions.DecodeError` | Your EAT token is malformed. Run `engram auth login` to get a fresh token. |
| Slow first startup | The initial launch downloads ML models (~400MB for sentence-transformers) and initializes the database. Subsequent starts are fast. |

---

## What's Next

- **[Quickstart](./01-quickstart.md)** — Register your first tool and test routing (5 minutes)
- **[Docker & Kubernetes Setup](./03-docker-kubernetes.md)** — Deploy with containers for production
- **[CLI Reference](./06-cli-reference.md)** — Master every command and flag
- **[Configuration](./07-configuration.md)** — Customize every setting
