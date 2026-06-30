"""Backend-agnostic job runners.

Both the thread backend and the Celery worker call these two functions. They own
the job lifecycle transitions (running -> complete/failed), delegate the actual
work to :mod:`core.service`, and (for queries) stream each ReAct step onto the
:data:`jobs.stream.bus`.
"""

from typing import Dict, List, Optional

from core.service import run_ingest, run_query
from jobs import store
from jobs.stream import bus


def run_query_job(
    *,
    registry,
    config: Dict,
    job_id: str,
    tenant_id: str,
    user_id: Optional[int],
    username: str,
    question: str,
    include_eval: bool,
) -> Dict:
    """Execute a query job end to end, streaming steps and recording state."""
    store.mark_running(job_id)
    bus.register(job_id)

    def _on_step(step: Dict) -> None:
        bus.publish(job_id, {"type": "step", **step})

    try:
        components = registry.get(tenant_id)
        # Reuse the job id as the query/audit id so a job and its compliance
        # record share one identifier -- crucial for traceability.
        result = run_query(
            components=components,
            config=config,
            question=question,
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            query_id=job_id,
            include_eval=include_eval,
            step_callback=_on_step,
        )
        # Trim the heavy trace out of the job result payload (it lives in audit).
        summary = {
            "query_id": result["query_id"],
            "blocked": result.get("blocked", False),
            "blocked_reason": result.get("blocked_reason"),
            "cached": result.get("cached", False),
            "review_status": result.get("review_status"),
            "needs_review": result.get("needs_review", False),
            "flagged_reason": result.get("flagged_reason", ""),
            "confidence_score": result.get("confidence_score"),
            "ragas_scores": result.get("ragas_scores"),
            "report": result.get("report"),  # None when held for review
            "latency_ms": result.get("latency_ms"),
        }
        bus.publish(job_id, {"type": "done", **summary})
        store.mark_complete(job_id, summary)
        return summary
    except Exception as exc:
        bus.publish(job_id, {"type": "error", "error": str(exc)})
        store.mark_failed(job_id, str(exc))
        raise
    finally:
        bus.close(job_id)


def run_ingest_job(
    *,
    registry,
    config: Dict,
    job_id: str,
    tenant_id: str,
    pdf_paths: List[str],
    document_id: Optional[str] = None,
) -> Dict:
    """Execute an ingestion job and record document + job state."""
    store.mark_running(job_id)
    try:
        components = registry.get(tenant_id)
        stats = run_ingest(
            components=components,
            config=config,
            pdf_paths=pdf_paths,
            tenant_id=tenant_id,
            document_id=document_id,
        )
        store.mark_complete(job_id, stats)
        return stats
    except Exception as exc:
        store.mark_failed(job_id, str(exc))
        raise
