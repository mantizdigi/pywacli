from sqlalchemy import create_engine, text as sa_text, event
from sqlalchemy.engine import Engine, CursorResult
from pywacli.cli.config_manager import get_db_url, get_db_type
import logging
import re

logger = logging.getLogger(__name__)

_engine = None

_qmark_re = re.compile(r"\?")


def _convert_params(sql: str, params: list | None = None):
    """Convert ? placeholders to :0, :1, ... named params for SQLAlchemy 2.0."""
    if not params:
        return sql, {}
    it = iter(range(len(params)))
    named_sql = _qmark_re.sub(lambda m: f":{next(it)}", sql)
    named_params = {str(i): v for i, v in enumerate(params)}
    return named_sql, named_params


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
    named_sql, named_params = _convert_params(sql, params)
    with get_engine().connect() as conn:
        return conn.execute(sa_text(named_sql), named_params).fetchall()


def fetchone(sql: str, params: list | None = None):
    """Execute a SELECT and return the first row (or None)."""
    named_sql, named_params = _convert_params(sql, params)
    with get_engine().connect() as conn:
        return conn.execute(sa_text(named_sql), named_params).fetchone()


def execute(sql: str, params: list | None = None) -> CursorResult:
    """Execute an INSERT/UPDATE/DELETE and commit."""
    named_sql, named_params = _convert_params(sql, params)
    with get_engine().connect() as conn:
        result = conn.execute(sa_text(named_sql), named_params)
        conn.commit()
        return result


def insert_and_get_id(sql: str, params: list | None = None):
    """Execute an INSERT and return the last inserted row id."""
    named_sql, named_params = _convert_params(sql, params)
    with get_engine().connect() as conn:
        if get_db_driver() == "postgresql":
            result = conn.execute(sa_text(named_sql + " RETURNING *"), named_params)
            conn.commit()
            row = result.fetchone()
            return row[0] if row else None
        result = conn.execute(sa_text(named_sql), named_params)
        conn.commit()
        return result.lastrowid
