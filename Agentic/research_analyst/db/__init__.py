"""Database package: SQLAlchemy engine, session, and ORM models.

A single SQLite file (configured via ``paths.metadata_db``) holds all
operational state for the production system: tenants, users, documents,
async jobs, the compliance audit log, and the human review queue.

Why SQLite + SQLAlchemy (and not Postgres directly):
    The whole point of this build is "runs on my laptop". SQLite needs zero
    server, zero install, and lives in one file we can inspect with any tool.
    Because every query goes through SQLAlchemy's ORM, swapping to Postgres in
    production is a one-line change to the connection URL -- no model changes.
"""

from db.database import (  # noqa: F401
    Base,
    configure_database,
    get_engine,
    get_session,
    init_db,
    session_scope,
)
from db.models import (  # noqa: F401
    AuditLog,
    Document,
    Job,
    ReviewItem,
    Tenant,
    User,
)
