# -----------------------------------------------------------------------------
# MULTI-STAGE BUILD
#
# We use two stages — builder and final.
# WHY? The builder stage installs all build tools and dependencies.
# The final stage copies only what's needed to actually RUN the app.
#
# Result: final image is much smaller (no compilers, no build tools).
# Smaller image = faster deploys, less attack surface, less storage cost.
#
# This is standard practice for production Docker images.
# -----------------------------------------------------------------------------

# Stage 1 — Builder
FROM python:3.11-slim AS builder

# Set working directory inside the container
WORKDIR /app

# Install uv — the fast Python package manager you're already using
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first — before copying your code.
# WHY? Docker caches each layer. If you copy code first, every code change
# invalidates the dependency cache and reinstalls everything from scratch.
# By copying pyproject.toml first, dependencies only reinstall when
# pyproject.toml changes — not on every code change. Faster builds.
COPY pyproject.toml .

# Install dependencies into a local folder (not system Python)
RUN uv pip install --system .


# Stage 2 — Final (what actually runs in production)
FROM python:3.11-slim AS final

WORKDIR /app

# Create a non-root user — running as root inside a container is a security risk.
# If someone exploits your app, they get root inside the container.
# With a dedicated user, blast radius is limited.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy your application code
COPY ./app ./app
COPY ./alembic ./alembic
COPY alembic.ini .

# Own all files as appuser — not root
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Tell Docker which port this container listens on (documentation only — doesn't publish it)
EXPOSE 8000

COPY server.sh .
CMD ["sh", "server.sh"]