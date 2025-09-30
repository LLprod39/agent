"""Main FastAPI application for DevOps LLM Agent."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .routers import conversation, tasks, health, environments, admin
from .dependencies import get_settings
from .models import ErrorResponse
from .middleware import PrometheusMiddleware
from .logging_setup import setup_structured_logging, get_structured_logger
from ..orchestrator import Orchestrator
from ..orchestrator.llm_router import LLMRouter
from ..database.connection import DatabaseManager
from ..database.migrations import MigrationManager
from ..cache import RedisManager, SessionManager, LLMCache, RateLimiter, RateLimitMiddleware
from sqlalchemy.engine import make_url

# Configure basic logging (fallback)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Structured logger will be initialized in lifespan
structured_logger = None

# Global instances
orchestrator: Orchestrator = None
db_manager: DatabaseManager = None
redis_manager: RedisManager = None
session_manager: SessionManager = None
llm_cache: LLMCache = None
rate_limiter: RateLimiter = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestrator, db_manager, redis_manager, session_manager, llm_cache, rate_limiter, structured_logger

    # Startup
    logger.info("Starting DevOps LLM Agent API...")

    try:
        # Initialize structured logging first
        structured_logger = setup_structured_logging()
        structured_logger.info("Starting DevOps LLM Agent API", component="main")
        
        # Load settings
        settings = get_settings()
        
        # Configure logging level
        logging.getLogger().setLevel(settings.log_level)

        # Initialize Database
        structured_logger.info("Initializing database connection", component="database")
        database_url = settings.database_url
        url = make_url(database_url)
        skip_migrations = url.get_backend_name() == "sqlite"

        db_manager = DatabaseManager(
            database_url=database_url,
            echo=settings.database_echo
        )
        await db_manager.initialize()

        if skip_migrations:
            structured_logger.info("Skipping migrations for SQLite", component="database")
        else:
            structured_logger.info("Running database migrations", component="database")
            migration_manager = MigrationManager(db_manager.engine)
            await migration_manager.migrate()
            migration_status = await migration_manager.status()
            structured_logger.info("Migration complete", component="database", status=migration_status)

        # Initialize Redis
        structured_logger.info("Initializing Redis connection", component="redis")
        redis_manager = RedisManager(redis_url=settings.redis_url)
        await redis_manager.initialize()
        
        # Initialize Session Manager
        structured_logger.info("Initializing session manager", component="session")
        session_manager = SessionManager(
            redis_manager=redis_manager,
            ttl=3600  # 1 hour session TTL
        )
        
        # Initialize LLM Cache
        structured_logger.info("Initializing LLM cache", component="cache")
        llm_cache = LLMCache(
            redis_manager=redis_manager,
            ttl=3600  # 1 hour cache TTL
        )
        
        # Initialize Rate Limiter
        structured_logger.info("Initializing rate limiter", component="rate_limiter")
        rate_limiter = RateLimiter(
            redis_manager=redis_manager,
            requests_per_minute=60,
            requests_per_hour=1000
        )

        # Initialize LLM router with cache
        structured_logger.info("Initializing LLM router", component="llm_router")
        provider_configs = [provider.model_dump() for provider in settings.llm_providers]
        llm_router = LLMRouter(provider_configs, llm_cache=llm_cache)

        # Initialize orchestrator
        structured_logger.info("Initializing orchestrator", component="orchestrator")
        orchestrator = Orchestrator(settings.orchestrator.model_dump(), llm_router)

        # Store in app state
        app.state.orchestrator = orchestrator
        app.state.settings = settings
        app.state.db_manager = db_manager
        app.state.redis_manager = redis_manager
        app.state.session_manager = session_manager
        app.state.llm_cache = llm_cache
        app.state.rate_limiter = rate_limiter
        app.state.structured_logger = structured_logger

        structured_logger.info("DevOps LLM Agent API started successfully", component="main", status="running")

    except Exception as e:
        if structured_logger:
            structured_logger.error("Failed to start API", component="main", error=str(e))
        logger.error(f"Failed to start API: {str(e)}")
        raise

    yield

    # Shutdown
    if structured_logger:
        structured_logger.info("Shutting down DevOps LLM Agent API", component="main")
    logger.info("Shutting down DevOps LLM Agent API...")
    
    # Close Redis connections
    if redis_manager:
        if structured_logger:
            structured_logger.info("Closing Redis connections", component="redis")
        await redis_manager.close()
    
    # Close database connections
    if db_manager:
        if structured_logger:
            structured_logger.info("Closing database connections", component="database")
        await db_manager.close()
    
    if orchestrator:
        # Cleanup other resources
        if structured_logger:
            structured_logger.info("Orchestrator cleanup complete", component="orchestrator")


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

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)

# Note: RateLimitMiddleware will be added after lifespan initialization
# See the on_startup event below for dynamic middleware addition


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Handle HTTP exceptions."""
    error_msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=error_msg, status_code=exc.status_code).model_dump(mode='json'),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", status_code=500).model_dump(mode='json'),
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
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])


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
