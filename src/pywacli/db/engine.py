from sqlalchemy import create_engine, text as sa_text, event
from sqlalchemy.engine import Engine, CursorResult
from pywacli.cli.config_manager import get_db_url, get_db_type
import logging

logger = logging.getLogger(__name__)

_engine = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        db_url = get_db_url()
        db_type = get_db_type()

        connect_args = {}
        if db_type == "sqlite":
            connect_args["check_same_thread"] = False

        _engine = create_engine(db_url, pool_pre_ping=True, connect_args=connect_args)

        if db_type == "sqlite":
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        logger.info("DB engine created: %s", db_url)
    return _engine


def get_db_driver() -> str:
    return get_db_type()


def fetchall(sql: str, params: list | None = None) -> list:
    """Execute a SELECT and return all rows."""
    with get_engine().connect() as conn:
        return conn.execute(sa_text(sql), params or []).fetchall()


def fetchone(sql: str, params: list | None = None):
    """Execute a SELECT and return the first row (or None)."""
    with get_engine().connect() as conn:
        return conn.execute(sa_text(sql), params or []).fetchone()


def execute(sql: str, params: list | None = None) -> CursorResult:
    """Execute an INSERT/UPDATE/DELETE and commit."""
    with get_engine().connect() as conn:
        result = conn.execute(sa_text(sql), params or [])
        conn.commit()
        return result


def insert_and_get_id(sql: str, params: list | None = None):
    """Execute an INSERT and return the last inserted row id."""
    with get_engine().connect() as conn:
        result = conn.execute(sa_text(sql), params or [])
        conn.commit()
        return result.inserted_primary_key[0] if result.inserted_primary_key else None
