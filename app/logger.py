import logging
import sys

from app.config import settings

# -----------------------------------------------------------------------------
# WHY NOT JUST USE print()?
#
# print() has no context — you just get raw text, no timestamp, no severity,
# no idea which part of the app it came from.
#
# A proper logger gives you:
#   2026-04-06 12:30:01 | INFO     | app.routers.auth | User registered: rajan@example.com
#   2026-04-06 12:30:05 | ERROR    | app.routers.auth | Login failed for: wrong@email.com
#   2026-04-06 12:30:10 | WARNING  | app.database     | Slow query detected: 2.3s
#
# LOG LEVELS (in order of severity):
#   DEBUG    → detailed dev info, disabled in production
#   INFO     → normal operations (user registered, project created)
#   WARNING  → something unexpected but not breaking (slow query, deprecated usage)
#   ERROR    → something broke but app is still running (failed DB query)
#   CRITICAL → app is about to crash
#
# In development we show DEBUG and above (everything).
# In production we show INFO and above (no debug noise).
# -----------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the given module name.

    Usage in any file:
        from app.logger import get_logger
        logger = get_logger(__name__)

        logger.info("User registered: %s", email)
        logger.error("Login failed for: %s", email)
        logger.warning("Slow query: %ss", duration)
        logger.debug("DB session opened")   # only shows in development

    `__name__` is a Python built-in that gives the current module's full path,
    e.g. "app.routers.auth" or "app.services.auth_service".
    This tells you exactly WHERE the log came from — very useful when debugging.
    """

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers if get_logger is called multiple times
    if logger.handlers:
        return logger

    # -----------------------------------------------------------------------------
    # LOG LEVEL
    # Development → DEBUG (see everything)
    # Production  → INFO (only meaningful events, no noise)
    # -----------------------------------------------------------------------------
    log_level = logging.DEBUG if settings.is_development else logging.INFO
    logger.setLevel(log_level)

    # -----------------------------------------------------------------------------
    # FORMATTER — what each log line looks like
    #
    # %(asctime)s    → timestamp: 2026-04-06 12:30:01
    # %(levelname)s  → INFO, ERROR, WARNING, DEBUG
    # %(name)s       → module name: app.routers.auth
    # %(message)s    → your actual message
    # -----------------------------------------------------------------------------
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler — where logs go (stdout so Docker/Railway captures them)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Don't propagate to root logger — avoids duplicate log lines
    logger.propagate = False

    return logger