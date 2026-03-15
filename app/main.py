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
from app.api.v1 import endpoints, discovery
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db
from app.services.task_worker import TaskWorker
from contextlib import asynccontextmanager
from prometheus_fastapi_instrumentator import Instrumentator

from app.services.discovery import DiscoveryService

configure_logging()
logger = structlog.get_logger(__name__)

discovery_service = DiscoveryService()
task_worker = TaskWorker()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (create tables if they don't exist)
    await init_db()
    # Start Discovery Service
    await discovery_service.start_periodic_discovery()
    # Start Task Worker
    await task_worker.start()
    yield
    # Stop Task Worker
    await task_worker.stop()
    # Stop Discovery Service
    await discovery_service.stop_periodic_discovery()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Bridge for A2A, MCP, and ACP protocols with semantic mapping.",
    version="0.1.0",
    lifespan=lifespan
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
    app.add_middleware(HTTPSRedirectMiddleware)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Agent Translator Middleware is Online", "version": "0.1.0"}

# Include API v1 routers
app.include_router(endpoints.router, prefix=settings.API_V1_STR)
app.include_router(discovery.router, prefix=settings.API_V1_STR)
