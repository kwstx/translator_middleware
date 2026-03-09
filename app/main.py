from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session, select
from app.api.v1 import endpoints, discovery
from app.core.config import settings
from app.db.session import init_db
from app.messaging.events import rabbitmq
from contextlib import asynccontextmanager
from typing import List, Dict, Any

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB (create tables if they don't exist)
    await init_db()
    # Initialize RabbitMQ
    await rabbitmq.connect()
    yield
    # Cleanup RabbitMQ
    await rabbitmq.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Bridge for A2A, MCP, and ACP protocols with semantic mapping.",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Agent Translator Middleware is Online", "version": "0.1.0"}

# Include API v1 routers
app.include_router(endpoints.router, prefix=settings.API_V1_STR)
app.include_router(discovery.router, prefix=settings.API_V1_STR)
