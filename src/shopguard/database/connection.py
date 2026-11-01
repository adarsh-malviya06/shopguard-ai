"""Database connection management for both databases."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from src.shopguard.config import settings
from src.shopguard.logging_config import logger


def _get_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row factory and FK enforcement."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = DELETE")
    return conn


@contextmanager
def get_simulator_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for simulator.db connections."""
    conn = _get_connection(settings.SIMULATOR_DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_shopguard_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for shopguard.db connections."""
    conn = _get_connection(settings.SHOPGUARD_DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
