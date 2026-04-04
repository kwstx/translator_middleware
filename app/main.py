import sentry_sdk
from app.core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of transactions.
        profiles_sample_rate=1.0,
    )

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import (
    endpoints,
    discovery,
    auth,
    permissions,
    credentials,
    orchestration,
    tasks,
    workflows,
    registry,
    events,
    tracing,
    catalog,
    reconciliation,
    routing,
    evolution,
    federation,
)
from bridge.memory import router as memory_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.services.task_worker import TaskWorker
from app.services.workflow_scheduler import WorkflowScheduler
from app.services.event_listener import EventListener
from contextlib import asynccontextmanager
import uuid
from sqlmodel import select
from prometheus_fastapi_instrumentator import Instrumentator

from app.services.discovery import DiscoveryService

configure_logging()
logger = structlog.get_logger(__name__)

discovery_service = DiscoveryService()
task_worker = TaskWorker()
workflow_scheduler = WorkflowScheduler()
event_listener = EventListener()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Store services in app state for access from routers
    app.state.discovery_service = discovery_service
    app.state.task_worker = task_worker
    app.state.workflow_scheduler = workflow_scheduler
    app.state.event_listener = event_listener
    
    # Initialize DB (create tables if they don't exist)
    await init_db()
    
    # Auto-start background services (Orchestration Loop)
    await discovery_service.start_periodic_discovery()
    await task_worker.start()
    await workflow_scheduler.start()
    await event_listener.start()
    
    # Seed the popular apps catalog
    try:
        from app.services.catalog_service import CatalogService
        from app.db.session import get_session
        import os
        async for db in get_session():
            service = CatalogService(db)
            seed_path = os.path.join(os.path.dirname(__file__), "catalog", "seed_data.yaml")
            if os.path.exists(seed_path):
                await service.seed_catalog_from_yaml(seed_path)
            
            # Pre-populate some popular tools for immediate discoverability
            system_agent_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
            from app.db.models import AgentRegistry
            stmt = select(AgentRegistry).where(AgentRegistry.agent_id == system_agent_id)
            result = await db.execute(stmt)
            if not result.scalars().first():
                db.add(AgentRegistry(
                    agent_id=system_agent_id,
                    endpoint_url="http://localhost:8000",
                    supported_protocols=["MCP", "CLI", "HTTP"]
                ))
                await db.commit()
                
            entries = await service.get_entries()
            for entry in entries:
                if not entry.is_cached:
                    await service.warm_up_registry(entry.slug, system_agent_id)
            break # Just need one session
    except Exception as e:
        logger.error("Failed to seed catalog during startup", error=str(e))
    
    logger.info("Engram orchestration services started automatically via lifespan.")
    from rich import print as rprint
    from rich.panel import Panel
    rprint(Panel.fit(
        "[bold green][DONE] GATEWAY ACTIVE[/bold green]\n"
        "[dim]Listening on[/dim] [bold]http://127.0.0.1:8000[/bold]\n"
        "[dim]API docs at[/dim]  [bold]http://127.0.0.1:8000/docs[/bold]\n\n"
        "[dim]Open a new terminal and run[/dim] [bold cyan]./engram <command>[/bold cyan] [dim]to interact.[/dim]\n"
        "[dim]Press[/dim] [bold]CTRL+C[/bold] [dim]here to stop the server.[/dim]",
        border_style="green",
    ))
    
    yield
    
    # Graceful shutdown
    await discovery_service.stop_periodic_discovery()
    await task_worker.stop()
    await workflow_scheduler.stop()
    await event_listener.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Bridge for A2A, MCP, and ACP protocols with semantic mapping.",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.error(
        "Request validation error",
        path=str(request.url.path),
        errors=exc.errors(),
        body=exc.body,
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

if settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

if settings.HTTPS_ONLY:
    # Forces all requests to be redirected to HTTPS
    app.add_middleware(HTTPSRedirectMiddleware)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Agent Translator Middleware is Online", "version": "0.1.0"}

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}

# Include API v1 routers
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["Auth"])
app.include_router(endpoints.router, prefix=settings.API_V1_STR)
app.include_router(discovery.router, prefix=settings.API_V1_STR)
app.include_router(permissions.router, prefix=settings.API_V1_STR + "/permissions", tags=["Permissions"])
app.include_router(credentials.router, prefix=settings.API_V1_STR + "/credentials", tags=["Credentials"])
app.include_router(orchestration.router, prefix=settings.API_V1_STR, tags=["Orchestration"])
app.include_router(tasks.router, prefix=settings.API_V1_STR + "/tasks", tags=["Tasks"])
app.include_router(workflows.router, prefix=settings.API_V1_STR + "/workflows", tags=["Workflows"])
app.include_router(registry.router, prefix=settings.API_V1_STR, tags=["Registry"])
app.include_router(events.router, prefix=settings.API_V1_STR, tags=["Events"])
app.include_router(tracing.router, prefix=settings.API_V1_STR, tags=["Tracing"])
app.include_router(catalog.router, prefix=settings.API_V1_STR, tags=["Catalog"])
app.include_router(reconciliation.router, prefix=settings.API_V1_STR + "/reconciliation", tags=["Reconciliation"])
app.include_router(routing.router, prefix=settings.API_V1_STR, tags=["Routing"])
app.include_router(evolution.router, prefix=settings.API_V1_STR + "/evolution", tags=["Evolution"])
app.include_router(federation.router, prefix=settings.API_V1_STR)
app.include_router(memory_router, prefix=settings.API_V1_STR)

