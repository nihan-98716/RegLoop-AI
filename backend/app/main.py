"""RegLoop AI — FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.logging_config import configure_logging, get_logger
from app.routers import (
    gap_analysis,
    health,
    ingestion,
    mappings,
    obligations,
    pull_request,
    workspaces,
)

configure_logging(settings.log_level)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    log.info("app.startup", env=settings.app_env, db=settings.database_url)
    await init_db()
    yield
    log.info("app.shutdown")


app = FastAPI(
    title="RegLoop AI",
    description="Regulatory compliance review package generator.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(workspaces.router, prefix="/api")
app.include_router(ingestion.router, prefix="/api")
app.include_router(obligations.router, prefix="/api")
app.include_router(mappings.router, prefix="/api")
app.include_router(gap_analysis.router, prefix="/api")
app.include_router(pull_request.router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "RegLoop AI API. See /docs for the OpenAPI UI."}
