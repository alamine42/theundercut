import logging
import warnings

logger = logging.getLogger(__name__)

# Ensure SQLite attachment for inline unique constraints
try:
    from sqlite3 import Connection as SQLite3Connection
    SQLite3Connection.execute("ATTACH DATABASE ':memory:' AS core")
except ImportError:
    warnings.warn(
        "sqlite3 module not available; SQLite ATTACH setup skipped",
        stacklevel=1,
    )
except Exception as exc:
    logger.warning("SQLite ATTACH setup failed: %s", exc)
