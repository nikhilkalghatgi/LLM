"""Exact-match query cache.

Why this exists
---------------
An LLM/ReAct query is the most expensive thing the system does (multiple model
calls + RAGAS scoring). For repeated, identical questions that work is pure
waste. This module short-circuits the pipeline by caching the *answer*.

Correctness rules (so a hit is never wrong)
-------------------------------------------
1. **Only auto-approved answers are cached.** Blocked (guard-failed) or
   review-flagged (low-confidence / low-faithfulness) answers are never stored,
   so a cache hit can only ever return an answer that already passed every gate.
2. **Per-tenant invalidation on ingest.** When a tenant ingests new documents
   its corpus changes, so all of that tenant's cached answers are dropped --
   a hit can never reflect a stale corpus.
3. **Tenant-scoped keys.** The cache key includes the tenant id, so tenants can
   never read each other's cached answers (same isolation guarantee as the
   per-tenant Chroma collections).

The store is the same SQLite metadata DB used everywhere else, so it survives
restarts and works for both the thread and Celery backends with no extra infra.
Hit/miss counters are kept in process memory for the ``/cache/stats`` endpoint.
"""

import hashlib
import json
import threading
from datetime import datetime
from typing import Dict, Optional

from db.database import session_scope
from db.models import QueryCache

# In-process counters (reset on restart) surfaced via GET /cache/stats.
_counter_lock = threading.Lock()
_counters: Dict[str, int] = {"hits": 0, "misses": 0}


def _normalize(question: str) -> str:
    """Collapse whitespace and lowercase so trivially different phrasings of
    the *same* string share a key (e.g. extra spaces / casing)."""
    return " ".join(question.lower().split())


def make_key(tenant_id: str, question: str, include_eval: bool) -> str:
    """Deterministic SHA-256 key for ``(tenant, question, include_eval)``.

    ``include_eval`` is part of the key because a result computed without RAGAS
    scoring is not interchangeable with one computed with it.
    """
    raw = f"{tenant_id}\x00{int(include_eval)}\x00{_normalize(question)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _expired(created_at: Optional[datetime], ttl_seconds: int) -> bool:
    """True if a row is older than ``ttl_seconds`` (0 disables time expiry)."""
    if ttl_seconds <= 0 or created_at is None:
        return False
    created = created_at.replace(tzinfo=None) if created_at.tzinfo else created_at
    return (datetime.utcnow() - created).total_seconds() > ttl_seconds


def get(
    *, tenant_id: str, question: str, include_eval: bool, ttl_seconds: int = 0
) -> Optional[Dict]:
    """Return the cached result dict for this question, or ``None`` on a miss.

    On a hit, bumps the row's hit counter / ``last_hit_at`` and the in-process
    hit counter. Expired rows are deleted and treated as a miss.
    """
    key = make_key(tenant_id, question, include_eval)
    with session_scope() as session:
        row = (
            session.query(QueryCache)
            .filter(QueryCache.cache_key == key)
            .first()
        )
        if row is None:
            _bump("misses")
            return None
        if _expired(row.created_at, ttl_seconds):
            session.delete(row)
            _bump("misses")
            return None
        row.hits += 1
        row.last_hit_at = datetime.utcnow()
        result = json.loads(row.result_json or "{}")
    _bump("hits")
    return result


def set(
    *, tenant_id: str, question: str, include_eval: bool, result: Dict
) -> None:
    """Store (upsert) an auto-approved result for this question."""
    key = make_key(tenant_id, question, include_eval)
    payload = json.dumps(result)
    with session_scope() as session:
        row = (
            session.query(QueryCache)
            .filter(QueryCache.cache_key == key)
            .first()
        )
        if row is None:
            session.add(
                QueryCache(
                    cache_key=key,
                    tenant_id=tenant_id,
                    question=question,
                    result_json=payload,
                )
            )
        else:
            row.result_json = payload
            row.created_at = datetime.utcnow()


def invalidate_tenant(tenant_id: str) -> int:
    """Drop every cached answer for one tenant. Returns the number removed.

    Called after a successful ingest because new documents can change answers.
    """
    with session_scope() as session:
        deleted = (
            session.query(QueryCache)
            .filter(QueryCache.tenant_id == tenant_id)
            .delete(synchronize_session=False)
        )
    return int(deleted or 0)


def _bump(kind: str) -> None:
    with _counter_lock:
        _counters[kind] += 1


def stats(tenant_id: Optional[str] = None) -> Dict:
    """Return hit/miss counters and stored-entry counts (optionally per tenant)."""
    with _counter_lock:
        hits = _counters["hits"]
        misses = _counters["misses"]
    total = hits + misses
    hit_rate = round(hits / total, 3) if total else 0.0

    with session_scope() as session:
        q = session.query(QueryCache)
        if tenant_id is not None:
            q = q.filter(QueryCache.tenant_id == tenant_id)
        entries = q.count()

    return {
        "enabled": True,
        "hits": hits,
        "misses": misses,
        "hit_rate": hit_rate,
        "entries": entries,
        "scope": tenant_id or "all",
    }
