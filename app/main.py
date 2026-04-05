from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, project, reports, timelog


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
    print("🚀 FreelanceTrack API is starting up...")
    yield
    # shutdown
    print("👋 FreelanceTrack API is shutting down...")


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