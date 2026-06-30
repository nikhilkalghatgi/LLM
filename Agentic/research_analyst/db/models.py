"""ORM models for the operational metadata database.

Six tables back the production system:

* ``Tenant`` / ``User`` -- multi-tenancy + JWT auth.
* ``Document``           -- data-pipeline state (what was ingested, when, status).
* ``Job``                -- async job queue records (ingest / query).
* ``AuditLog``           -- one immutable row per query for compliance & debug.
* ``ReviewItem``         -- human-in-the-loop queue for low-confidence reports.
* ``QueryCache``         -- exact-match answer cache (per-tenant, ingest-invalidated).

JSON-ish columns are stored as ``Text`` containing ``json.dumps(...)`` so the
schema stays portable across SQLite and Postgres without a JSON column type.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp (audit logs must be unambiguous)."""
    return datetime.now(timezone.utc)


class Tenant(Base):
    """A logically isolated customer/team. Owns its own Chroma collection."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    users: Mapped[list["User"]] = relationship(back_populates="tenant")


class User(Base):
    """An authenticated principal scoped to exactly one tenant."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="analyst")  # analyst|reviewer|admin
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    tenant: Mapped["Tenant"] = relationship(back_populates="users")


class Document(Base):
    """Metadata for one ingested PDF -- the data-pipeline's state table."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # uuid4 hex
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    source_path: Mapped[str] = mapped_column(String(1024), default="")
    status: Mapped[str] = mapped_column(
        String(32), default="pending"  # pending|ingesting|ingested|failed
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    ingested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Job(Base):
    """An async task record (ingest or query) tracked end to end."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # uuid4 hex
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # ingest|query
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="pending"  # pending|running|complete|failed
    )
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    """One immutable compliance record per query -- the heart of "auditability".

    Separate from MLflow: MLflow is for *ML experiment* tracking; this table is
    for *compliance and debugging*. A bank auditor can pull any ``query_id`` and
    see the full decision trail: who asked what, what the guards decided, which
    chunks were used, the final report, the RAGAS faithfulness, and the latency.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    question: Mapped[str] = mapped_column(Text, nullable=False)

    input_guard_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    input_guard_json: Mapped[str] = mapped_column(Text, default="{}")
    react_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    retrieved_chunk_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    final_report: Mapped[str] = mapped_column(Text, default="")

    output_guard_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    ragas_faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    review_status: Mapped[str] = mapped_column(
        String(32), default="auto_approved"  # auto_approved|pending|approved|rejected
    )
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)


class QueryCache(Base):
    """Exact-match answer cache keyed by ``(tenant, normalized question)``.

    Skips the entire expensive pipeline (ReAct + LLM + RAGAS) on repeat
    questions. Only *auto-approved* (non-blocked, non-flagged) answers are
    cached, and a tenant's entries are invalidated whenever it ingests new
    documents -- so a cache hit can never serve a stale or unreviewed answer.
    """

    __tablename__ = "query_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    hits: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ReviewItem(Base):
    """A low-confidence report awaiting a human checkpoint before release."""

    __tablename__ = "review_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(64), index=True)
    flagged_reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(32), default="pending"  # pending|approved|rejected
    )
    reviewer: Mapped[str] = mapped_column(String(64), default="")
    reviewer_comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
