"""Main FastAPI application for DevOps LLM Agent."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .routers import conversation, tasks, health, environments
from .dependencies import get_settings
from .models import ErrorResponse
from ..orchestrator import Orchestrator
from ..orchestrator.llm_router import LLMRouter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator: Orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestrator

    # Startup
    logger.info("Starting DevOps LLM Agent API...")

    try:
        # Load settings
        settings = get_settings()

        # Initialize LLM router
        provider_configs = [provider.model_dump() for provider in settings.llm_providers]
        llm_router = LLMRouter(provider_configs)

        # Initialize orchestrator
        orchestrator = Orchestrator(settings.orchestrator.model_dump(), llm_router)

        # Store in app state
        app.state.orchestrator = orchestrator
        app.state.settings = settings

        logger.info("DevOps LLM Agent API started successfully")

    except Exception as e:
        logger.error(f"Failed to start API: {str(e)}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down DevOps LLM Agent API...")
    if orchestrator:
        # Cleanup resources
        pass


# Create FastAPI app
app = FastAPI(
    title="DevOps LLM Agent API",
    description="API for autonomous DevOps assistant",
    version="0.1.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],  # Configure properly for production
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.detail, status_code=exc.status_code).dict(),
        default=str,  # Handle datetime serialization
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", status_code=500).dict(),
        default=str,  # Handle datetime serialization
    )


# Include routers
app.include_router(
    conversation.router, prefix="/api/v1/conversation", tags=["conversation"]
)
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(
    environments.router, prefix="/api/v1/environments", tags=["environments"]
)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "DevOps LLM Agent API", "version": "0.1.0", "status": "running"}


# Health check endpoint
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
