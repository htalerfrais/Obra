from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

from .config import settings
from .monitoring import configure_logging, metrics
from .middleware import RequestLoggingMiddleware
from .core.container import build_container
from .modules.assistant.api.router import build_router as build_assistant_router
from .modules.identity.api.router import build_router as build_identity_router
from .modules.learning_content.api.router import build_router as build_learning_router
from .modules.recall_engine.api.router import build_router as build_recall_router
from .modules.session_intelligence.api.router import build_router as build_session_router
from .modules.outbox.api.router import build_router as build_outbox_router

# Configure structured logging
configure_logging(log_level=settings.log_level, use_json=settings.log_json_format)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="API for clustering browsing history into thematic sessions",
    version=settings.app_version,
    debug=settings.debug
)

# Configure CORS for Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# Add request logging middleware (runs after CORS)
app.add_middleware(RequestLoggingMiddleware)

container = build_container()


@app.on_event("startup")
async def startup() -> None:
    # Schema migrations are managed by Alembic.
    return None

@app.get("/")
async def root():
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "clustering": "operational",
            "llm": "operational",
            "chat": "operational"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    """
    Get aggregated system metrics and usage statistics.
    
    Returns:
        Dictionary containing:
        - LLM usage (calls, tokens, costs by provider)
        - Chat metrics (requests, turns, tool calls)
        - Clustering metrics (sessions, cache hit rate)
        - Search metrics (queries, results)
        - Embedding metrics (batches, failures)
    """
    return metrics.get_summary()

app.include_router(build_session_router(container))
app.include_router(build_assistant_router(container))
app.include_router(build_identity_router(container))
app.include_router(build_recall_router(container))
app.include_router(build_learning_router(container))
app.include_router(build_outbox_router(container))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
