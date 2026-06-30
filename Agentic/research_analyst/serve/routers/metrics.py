"""Metrics + audit router: powers the ops dashboard and compliance retrieval.

* ``GET /metrics/summary`` -- aggregated counters the dashboard charts read.
* ``GET /audit/{query_id}`` -- pull the full decision trail for any past query.
* ``GET /dashboard``        -- the single-file Chart.js ops dashboard.
"""

import json
import os
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func

from auth.dependencies import get_current_principal
from auth.security import Principal
from cache import query_cache
from db.database import session_scope
from db.models import AuditLog, ReviewItem
from serve import state

router = APIRouter(tags=["metrics"])


class MetricsSummary(BaseModel):
    tenant_id: str
    total_queries: int
    queries_per_hour: Dict[str, int]
    mean_faithfulness_7d: Optional[float]
    input_guard_block_rate: float
    review_queue_length: int
    avg_latency_ms: float
    review_breakdown: Dict[str, int]


@router.get("/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    principal: Principal = Depends(get_current_principal),
) -> MetricsSummary:
    """Aggregate audit-log counters for the caller's tenant."""
    tenant = principal.tenant_id
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    with session_scope() as session:
        base = session.query(AuditLog).filter(AuditLog.tenant_id == tenant)

        total = base.count()

        # Queries per hour bucket over the last 24h.
        recent = base.filter(AuditLog.created_at >= since_24h).all()
        buckets: "OrderedDict[str, int]" = OrderedDict()
        for i in range(23, -1, -1):
            label = (now - timedelta(hours=i)).strftime("%H:00")
            buckets[label] = 0
        for row in recent:
            if row.created_at:
                label = row.created_at.strftime("%H:00")
                if label in buckets:
                    buckets[label] += 1

        # Mean RAGAS faithfulness over 7 days.
        faith_rows = (
            session.query(AuditLog.ragas_faithfulness)
            .filter(
                AuditLog.tenant_id == tenant,
                AuditLog.created_at >= since_7d,
                AuditLog.ragas_faithfulness.isnot(None),
            )
            .all()
        )
        faith_vals = [r[0] for r in faith_rows if r[0] is not None]
        mean_faith = round(sum(faith_vals) / len(faith_vals), 3) if faith_vals else None

        blocked = base.filter(AuditLog.input_guard_passed.is_(False)).count()
        block_rate = round(blocked / total, 3) if total else 0.0

        avg_latency = (
            session.query(func.avg(AuditLog.latency_ms))
            .filter(AuditLog.tenant_id == tenant)
            .scalar()
        )
        avg_latency = round(float(avg_latency), 1) if avg_latency else 0.0

        pending = (
            session.query(ReviewItem)
            .filter(ReviewItem.tenant_id == tenant, ReviewItem.status == "pending")
            .count()
        )

        breakdown_rows = (
            session.query(AuditLog.review_status, func.count(AuditLog.id))
            .filter(AuditLog.tenant_id == tenant)
            .group_by(AuditLog.review_status)
            .all()
        )
        breakdown = {status: count for status, count in breakdown_rows}

    return MetricsSummary(
        tenant_id=tenant,
        total_queries=total,
        queries_per_hour=dict(buckets),
        mean_faithfulness_7d=mean_faith,
        input_guard_block_rate=block_rate,
        review_queue_length=pending,
        avg_latency_ms=avg_latency,
        review_breakdown=breakdown,
    )


@router.get("/audit/{query_id}")
def get_audit(
    query_id: str, principal: Principal = Depends(get_current_principal)
) -> dict:
    """Retrieve the full compliance record for a single query (tenant-scoped)."""
    with session_scope() as session:
        row = (
            session.query(AuditLog)
            .filter(AuditLog.query_id == query_id)
            .first()
        )
        if row is None or row.tenant_id != principal.tenant_id:
            raise HTTPException(status_code=404, detail="Audit record not found.")
        return {
            "query_id": row.query_id,
            "tenant_id": row.tenant_id,
            "username": row.username,
            "question": row.question,
            "input_guard_passed": row.input_guard_passed,
            "input_guard": json.loads(row.input_guard_json or "{}"),
            "react_steps": json.loads(row.react_steps_json or "[]"),
            "retrieved_chunk_ids": json.loads(row.retrieved_chunk_ids_json or "[]"),
            "final_report": row.final_report,
            "output_guard_passed": row.output_guard_passed,
            "ragas_faithfulness": row.ragas_faithfulness,
            "confidence_score": row.confidence_score,
            "review_status": row.review_status,
            "latency_ms": row.latency_ms,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


@router.get("/cache/stats")
def cache_stats(
    principal: Principal = Depends(get_current_principal),
) -> dict:
    """Query-cache hit/miss counters and stored-entry count for the tenant.

    ``hits``/``misses`` are process-wide (reset on restart); ``entries`` is the
    number of cached answers currently stored for the caller's tenant.
    """
    cfg = state.config.get("cache", {}) if state.config else {}
    result = query_cache.stats(tenant_id=principal.tenant_id)
    result["enabled"] = bool(cfg.get("enabled", True))
    result["ttl_seconds"] = int(cfg.get("ttl_seconds", 0))
    return result


@router.get("/dashboard")
def dashboard() -> FileResponse:
    """Serve the single-file Chart.js operations dashboard."""
    static_dir = state.config.get("paths", {}).get(
        "dashboard_static", "./serve/static"
    )
    path = os.path.join(static_dir, "dashboard.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dashboard not found.")
    return FileResponse(path, media_type="text/html")
