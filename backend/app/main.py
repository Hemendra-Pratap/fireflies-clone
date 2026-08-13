import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.middleware import CorrelationIdMiddleware, StructuredLogFilter

# Configure root logger with structured correlation ID log filter
log_filter = StructuredLogFilter()
logging.getLogger().addFilter(log_filter)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan context managing startup validation and shutdown hooks."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version} (Environment: {settings.environment})")
    settings.validate_production_config()
    yield
    logger.info(f"Shutting down {settings.app_name}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add correlation ID middleware first
app.add_middleware(CorrelationIdMiddleware)

# Add CORS middleware
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardized HTTP Exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Standardized Validation Exception handler."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Global fallback exception handler preventing stack trace or internal path leakage."""
    corr_id = getattr(request.state, "correlation_id", "N/A")
    logger.error(f"Unhandled exception [Correlation ID: {corr_id}]: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal error occurred."},
    )


app.include_router(api_router, prefix=settings.api_prefix)
