from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import auth, project, reports, timelog
from app.logger import get_logger
from app.security import RateLimitMiddleware, SecurityHeadersMiddleware

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# LIFESPAN — startup and shutdown logic
#
# In older FastAPI you'd use @app.on_event("startup") and @app.on_event("shutdown")
# Those are now deprecated. The modern way is `lifespan` — a single async
# context manager that handles both.
#
# Everything BEFORE `yield` runs on startup.
# Everything AFTER `yield` runs on shutdown.
#
# Right now we don't need startup logic because:
#   - SQLAlchemy creates connections lazily (on first request, not on startup)
#   - We use Alembic for migrations (run separately, not on startup)
#
# But the lifespan is here ready for when you need it — e.g. connecting to
# Redis on startup, or closing a connection pool cleanly on shutdown.
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info("🚀 FreelanceTrack API is starting up...")
    yield
    # shutdown
    logger.info("👋 FreelanceTrack API is shutting down...")


# -----------------------------------------------------------------------------
# THE FASTAPI APP INSTANCE
#
# This is the core object — everything attaches to this.
# `docs_url="/docs"` → Swagger UI (interactive, try endpoints in browser)
# `redoc_url="/redoc"` → ReDoc (cleaner read-only docs)
# Both are auto-generated from your schemas and route definitions.
# This is one of FastAPI's biggest advantages over Django REST Framework.
# -----------------------------------------------------------------------------

app = FastAPI(
    title="FreelanceTrack API",
    description="Track your freelance projects, log hours, and generate invoices.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)



# -----------------------------------------------------------------------------
# GLOBAL EXCEPTION HANDLERS
#
# These catch exceptions anywhere in the app and return structured JSON.
# Without these, unhandled exceptions return a raw 500 with no useful info
# to the client — just "Internal Server Error".
#
# Three types we handle:
#
# 1. RequestValidationError — Pydantic rejected the request body/params
#    e.g. missing field, wrong type, failed validator
#    FastAPI raises this automatically before your route even runs.
#
# 2. HTTPException — exceptions we raise deliberately in our code
#    e.g. raise HTTPException(status_code=404, detail="Not found")
#
# 3. Exception — anything else (true unexpected errors / bugs)
#    We log the real error server-side but return a clean message to client.
#    NEVER send internal error details to the client — that's a security risk.
# -----------------------------------------------------------------------------
 
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Pydantic validation failed — wrong type, missing field, failed validator.
    Returns 422 with a structured list of exactly what failed and where.
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " → ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
 
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation failed",
            "details": errors,
        },
    )
 
 
@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """
    Deliberate HTTP exceptions we raise in our code.
    e.g. 401 Unauthorized, 404 Not Found, 400 Bad Request.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
        },
    )
 
 
@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catches anything we didn't expect — true bugs.
    We print the real error to server logs (visible in your terminal),
    but the client only gets a clean generic message.
    In production you'd send this to Sentry or a logging service.
    """
    logger.exception(f"❌ Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An unexpected error occurred. Please try again later.",
        },
    )
 

# -----------------------------------------------------------------------------
# CORS MIDDLEWARE
#
# CORS = Cross-Origin Resource Sharing.
# Browsers block requests from one domain to another by default (security).
# If your Next.js frontend (localhost:3000) calls this API (localhost:8000),
# the browser blocks it — unless the API says "I allow localhost:3000".
#
# allow_origins → which frontends can call this API
# allow_methods → which HTTP methods are allowed
# allow_headers → which headers can be sent (Authorization is critical for JWT)
#
# In production: replace "*" in origins with your actual frontend domain.
# Never use allow_origins=["*"] in production — that allows ANY website
# to call your API using your logged-in users' credentials.
# -----------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)


# -----------------------------------------------------------------------------
# REGISTER ROUTERS
#
# This is where the routers we built plug into the app.
# Each router's prefix is already defined inside the router file.
# `api_prefix` here gives everything a /api/v1 base — clean versioning.
#
# Final URLs:
#   POST /api/v1/auth/register
#   POST /api/v1/auth/login
#   GET  /api/v1/projects/
#   POST /api/v1/projects/
#   GET  /api/v1/projects/{id}/logs
#   GET  /api/v1/reports/earnings
# -----------------------------------------------------------------------------

api_prefix = "/api/v1"

app.include_router(auth.router, prefix=api_prefix)
app.include_router(project.router, prefix=api_prefix)
app.include_router(timelog.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)


# -----------------------------------------------------------------------------
# HEALTH CHECK
#
# A simple endpoint that returns 200 OK.
# Used by Docker, Railway, Render, and load balancers to check if your
# app is alive. If this returns anything other than 200, the platform
# knows something is wrong and can restart your container.
#
# No auth required — monitoring tools don't have JWT tokens.
# -----------------------------------------------------------------------------

@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}