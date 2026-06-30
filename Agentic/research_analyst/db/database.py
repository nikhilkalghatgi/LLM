"""SQLAlchemy engine and session management for the metadata database.

The engine is configured once at startup via :func:`configure_database` (called
from the API lifespan, the CLI, and Celery workers) so every process shares the
same SQLite file. ``check_same_thread=False`` is required because the thread
job backend and FastAPI's executor touch the connection from worker threads.
"""

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


# Module-level singletons set by configure_database().
_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker] = None


def configure_database(db_path: str) -> Engine:
    """Create (or return the existing) engine bound to ``db_path``.

    Args:
        db_path: Filesystem path to the SQLite database file. Parent
            directories are created if missing.

    Returns:
        The configured SQLAlchemy :class:`Engine`.
    """
    global _engine, _SessionFactory

    if _engine is not None:
        return _engine

    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    # future=True -> SQLAlchemy 2.0 style. SQLite needs check_same_thread=False
    # so worker threads (job backend) can reuse the connection pool safely.
    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
    )
    _SessionFactory = sessionmaker(
        bind=_engine, autoflush=False, expire_on_commit=False, future=True
    )
    return _engine


def get_engine() -> Engine:
    """Return the configured engine or raise if configure_database was skipped."""
    if _engine is None:
        raise RuntimeError(
            "Database not configured. Call configure_database(db_path) first."
        )
    return _engine


def init_db() -> None:
    """Create all tables if they do not already exist."""
    # Importing models registers them on Base.metadata.
    from db import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


def get_session() -> Session:
    """Return a new ORM session (caller is responsible for closing it)."""
    if _SessionFactory is None:
        raise RuntimeError(
            "Database not configured. Call configure_database(db_path) first."
        )
    return _SessionFactory()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope: commit on success, rollback on error."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
