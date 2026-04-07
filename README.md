# FreelanceTrack API

A production-ready REST API for freelancers to track projects, log billable 
hours, and generate invoice reports.

Built as a deliberate showcase of modern async Python backend patterns — not 
just a CRUD app, but an API with the same production concerns a real product 
would need.

![CI](https://github.com/rajandevstudio/FreelanceTrack-API/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Coverage](https://img.shields.io/badge/coverage-81%25-brightgreen)

---

## What it does

A freelancer registers, creates projects with an hourly rate, logs time against 
each project, and pulls an earnings summary or genreate invoice pdf per project. Every 
resource is user-scoped — no user can access another's data.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Framework | FastAPI | Native async, auto OpenAPI docs, Pydantic v2 integration |
| Database | PostgreSQL + asyncpg | asyncpg is 3–5x faster than psycopg2 for async workloads |
| ORM | SQLAlchemy 2.0 (async) | Industry standard, full async support since 2.0 |
| Migrations | Alembic | Version-controlled schema changes |
| Auth | JWT (python-jose) + Argon2 | Argon2 is the current password hashing standard, better than bcrypt |
| Validation | Pydantic v2 | Faster than v1, stricter, TypeScript-like field validation |
| PDF | ReportLab | Invoice generation without external services |
| Testing | pytest + httpx + aiosqlite | In-memory SQLite for fast isolated tests, no Docker needed in CI |
| CI | GitHub Actions | Runs full test suite on every push |
| Container | Docker + docker-compose | One command to run app + PostgreSQL + Redis |

---

## Architecture decisions worth noting

**Async throughout** — every DB call uses `await`. No thread blocking, no 
sync SQLAlchemy calls. The entire stack from HTTP request to DB query is 
non-blocking.

**Soft delete** — records are never hard-deleted. Every model has a `deleted` 
boolean. This preserves invoice history even if a project is "removed".

**Pydantic settings** — all config lives in a typed `Settings` class. Missing 
env vars crash loudly on startup, not silently mid-request.

**Object-level authorization** — JWT proves who you are. Every DB query also 
filters by `owner_id = current_user.id`. Two separate layers of protection.

**Rate limiting on auth endpoints** — `/auth/*` routes are limited to 10 
requests per 60s per IP. Prevents brute force without Redis dependency.

**Separation of models and schemas** — SQLAlchemy models define the DB shape. 
Pydantic schemas define what the API accepts and returns. `hashed_password` 
exists in the model but never appears in any response schema.

---

## Project structure
```
app/
├── main.py              # Entry point, middleware, lifespan
├── config.py            # Typed settings via pydantic-settings
├── database.py          # Async SQLAlchemy engine + session
├── security.py          # Rate limiting + security headers middleware
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic v2 request/response schemas
├── routers/             # Route handlers (auth, projects, timelogs, reports)
├── services/            # Business logic (auth, PDF generation)
├── dependencies/        # FastAPI Depends() — auth guard, DB session
├── helpers/             # Reusable DB query functions
└── tests/               # pytest — 81% coverage
```

---

## Quick start

**With Docker (recommended):**
```bash
git clone https://github.com/rajandevstudio/FreelanceTrack-API.git
cd FreelanceTrack-API
cp .env.example .env          # fill in your values
docker compose up --build
docker compose exec app alembic upgrade head
```

API is live at `http://localhost:8000`

**Without Docker:**
```bash
git clone https://github.com/rajandevstudio/FreelanceTrack-API.git
cd FreelanceTrack-API
cp .env.example .env

uv sync
source .venv/bin/activate

alembic upgrade head
uvicorn app.main:app --reload
```

---

## Environment variables
```bash
# .env.example
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/freelancetrack
SECRET_KEY=your-secret-key-here          # openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REDIS_URL=redis://localhost:6379
```

---

## API overview

Interactive docs at `http://localhost:8000/docs`

**Auth**

```
POST   /api/v1/auth/register     Create account
POST   /api/v1/auth/login        Get JWT token
GET    /api/v1/auth/me           Get current user
```

**Projects**

```GET    /api/v1/projects/              List your projects
POST   /api/v1/projects/              Create project
GET    /api/v1/projects/{id}          Get project detail
PATCH  /api/v1/projects/{id}          Update project
DELETE /api/v1/projects/{id}          Soft delete project
```

**Time Logs**

```
POST   /api/v1/projects/{id}/logs     Log hours worked
GET    /api/v1/projects/{id}/logs     List time entries
```

**Reports**
```
GET    /api/v1/reports/earnings               Earnings summary
GET    /api/v1/reports/invoice/{project_id}   Download PDF invoice
```

---

## Running tests
```bash
# Run all tests
uv run pytest -v

# With coverage report
uv run pytest --cov=app --cov-report=term-missing -v
```

Tests use an in-memory SQLite database — no PostgreSQL or Docker needed to 
run the test suite. CI runs automatically on every push to main.

---

## What's intentionally not included

**No frontend** — this is an API. Use the Swagger UI at `/docs` to explore 
every endpoint interactively, or connect any frontend or mobile client.

**No Redis-backed rate limiting** — current in-memory rate limiting works for 
single-instance deployments. A Redis-backed store would be the next step for 
horizontal scaling.

