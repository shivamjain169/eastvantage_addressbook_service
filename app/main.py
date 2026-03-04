# Application entry point — creates the FastAPI app, registers middleware,
# exception handlers, and mounts the versioned router.

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.address_routes import router as address_router
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db.base import Base
from app.db.session import engine

# Initialise logging before any module-level logger is used
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Create DB tables on startup; yield control; log shutdown
    logger.info("Starting Address Book Service — creating database tables")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready. LOG_LEVEL=%s", settings.LOG_LEVEL)
    yield
    logger.info("Address Book Service shutting down")


app = FastAPI(
    title="Address Book Service",
    description="Production-grade REST API for managing addresses with geospatial search.",
    version="1.0.0",
    lifespan=lifespan,
)


# Handles Pydantic / JSON validation errors — logs and returns 422
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning(
        "Validation error on %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


# Catches any unhandled exception — prevents stack traces from reaching the client
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."},
    )


# Mount address routes under the /api/v1 prefix
app.include_router(address_router, prefix="/api/v1")


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check() -> dict[str, str]:
    return {"status": "ok"}
