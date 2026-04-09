import os
import uvicorn
import structlog
from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1 import (
    auth,
    catalog,
    credentials,
    discovery,
    endpoints,
    events,
    evolution,
    orchestration,
    permissions,
    reconciliation,
    registry,
    routing,
    tasks,
    tracing,
    workflows,
    federation,
)
from bridge.memory import router as memory_router
from app.core.config import settings
from app.core.exceptions import TranslatorError, ValidationError
from app.core.logging import configure_logging
from app.db.session import init_db
from contextlib import asynccontextmanager

# Configure structured logging
try:
    configure_logging()
    logger = structlog.get_logger(__name__)
    logger.info("Application starting version 1.0.0", env=settings.ENVIRONMENT)
except Exception as e:
    print(f"CRITICAL: Logging configuration failed: {e}")
    import sys
    sys.exit(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Starting Engram Middleware...")
    
    # 1. Initialize Database & Run Migrations
    try:
        await init_db()
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        # Don't raise here if we want to allow the app to start even with DB issues (e.g. for health checks)
        # But for middleware, DB is usually critical.
    
    # 2. Start Background Services
    global discovery_service, event_listener, task_worker, workflow_scheduler
    
    from app.services.discovery import DiscoveryService
    from app.services.event_listener import EventListener
    from app.services.task_worker import TaskWorker
    from app.services.workflow_scheduler import WorkflowScheduler
    
    discovery_service = DiscoveryService()
    task_worker = TaskWorker()
    workflow_scheduler = WorkflowScheduler()
    event_listener = EventListener()
    
    await discovery_service.start_periodic_discovery()
    await event_listener.start()
    await task_worker.start()
    await workflow_scheduler.start()
    
    # 3. Seed Catalog (optional, for demo/dev)
    if not settings.LOW_MEMORY_MODE:
        from app.services.catalog_service import CatalogService
        from app.db.session import engine
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker
        
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            catalog_svc = CatalogService(session)
            await catalog_svc.seed_default_catalog()
            
        # 4. Warm up registry (Optional: caches agent capabilities)
        from app.services.registry_service import RegistryService
        async with async_session() as session:
            registry_svc = RegistryService(session)
            await registry_svc.warm_up()
            
    logger.info("Engram Middleware ready.")
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down Engram Middleware...")
    from app.main import discovery_service, event_listener, task_worker, workflow_scheduler
    await discovery_service.stop_periodic_discovery()
    await event_listener.stop()
    await task_worker.stop()
    await workflow_scheduler.stop()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Services will be initialized in the lifespan handler to save memory during import
discovery_service = None
task_worker = None
workflow_scheduler = None
event_listener = None

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
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

@app.exception_handler(TranslatorError)
async def translator_exception_handler(request, exc: TranslatorError):
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    
    logger.warning(
        "Translator logic error handled",
        error_type=type(exc).__name__,
        detail=str(exc),
        path=str(request.url.path)
    )
    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)}
    )

if settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_DEFAULT])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

if settings.HTTPS_ONLY:
    app.add_middleware(HTTPSRedirectMiddleware)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "frame-src 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
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

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=int(os.getenv("UVICORN_WORKERS", 1)),
        log_config=None,
        lifespan="on",
    )
