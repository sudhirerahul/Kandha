# Kandha API — FastAPI application factory
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from config import get_settings
from database import engine
from middleware.observability import (
    ObservabilityMiddleware,
    format_prometheus_metrics,
    get_metrics_snapshot,
)

settings = get_settings()


def configure_structlog() -> None:
    """Configure structlog for JSON output in production, pretty output in dev."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.stdlib.NAME_TO_LEVEL.get(settings.log_level.upper(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup checks and graceful shutdown."""
    configure_structlog()
    log = structlog.get_logger()

    # Startup: verify database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        log.info("database.connected")
    except Exception as exc:
        log.error("database.connection_failed", error=str(exc))
        raise

    log.info("kandha_api.started", env=settings.log_level)
    yield

    # Shutdown: dispose connection pool
    await engine.dispose()
    log.info("kandha_api.stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Kandha API",
        description="Cloud repatriation platform API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Observability — must be added before CORS (outermost middleware runs first)
    app.add_middleware(ObservabilityMiddleware)

    # CORS — allow Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        """Returns API health status."""
        return {"status": "ok", "service": "kandha-api"}

    # Metrics endpoint (Prometheus-compatible)
    @app.get("/metrics", tags=["observability"])
    async def metrics() -> PlainTextResponse:
        """Return metrics in Prometheus text exposition format."""
        return PlainTextResponse(
            content=format_prometheus_metrics(),
            media_type="text/plain; version=0.0.4",
        )

    # Metrics JSON endpoint (for frontend dashboard)
    @app.get("/api/v1/metrics/json", tags=["observability"])
    async def metrics_json() -> dict:
        """Return metrics as JSON for the frontend eval dashboard."""
        return {"metrics": get_metrics_snapshot()}

    # Routers — imported lazily to avoid circular imports at startup
    from routers.analyze import router as analyze_router
    from routers.agent import router as agent_router
    from routers.infra import router as infra_router

    app.include_router(analyze_router, prefix="/api/v1")
    app.include_router(agent_router, prefix="/api/v1")
    app.include_router(infra_router, prefix="/api/v1")

    # Evals router (lazy import — only exists after Phase 6)
    try:
        from routers.evals import router as evals_router
        app.include_router(evals_router, prefix="/api/v1")
    except ImportError:
        pass

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
