"""Structured audit logging -- the compliance & traceability backbone.

Every query writes exactly one immutable :class:`AuditLog` row capturing the
full decision trail. When a report is low-confidence it additionally creates a
:class:`ReviewItem`. These writes are deliberately separate from MLflow: MLflow
answers "how is the model performing over time?", the audit log answers "what
exactly did the system do for query X, and who asked it?".
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from db.database import session_scope
from db.models import AuditLog, ReviewItem


def _safe_json(obj) -> str:
    """Serialise to JSON, never raising on odd types."""
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return "{}"


def write_audit_log(
    *,
    query_id: str,
    tenant_id: str,
    user_id: Optional[int],
    username: str,
    question: str,
    input_guard: Dict,
    react_steps: List[Dict],
    retrieved_chunk_ids: List[str],
    final_report: str,
    output_guard_passed: bool,
    ragas_faithfulness: Optional[float],
    confidence_score: Optional[float],
    review_status: str,
    latency_ms: int,
) -> None:
    """Persist one compliance record for a completed query."""
    with session_scope() as session:
        session.add(
            AuditLog(
                query_id=query_id,
                tenant_id=tenant_id,
                user_id=user_id,
                username=username,
                question=question,
                input_guard_passed=bool(input_guard.get("passed", True)),
                input_guard_json=_safe_json(input_guard),
                react_steps_json=_safe_json(react_steps),
                retrieved_chunk_ids_json=_safe_json(retrieved_chunk_ids),
                final_report=final_report,
                output_guard_passed=output_guard_passed,
                ragas_faithfulness=ragas_faithfulness,
                confidence_score=confidence_score,
                review_status=review_status,
                latency_ms=latency_ms,
            )
        )


def enqueue_review(
    *, query_id: str, tenant_id: str, flagged_reason: str
) -> None:
    """Add a low-confidence report to the human review queue."""
    with session_scope() as session:
        session.add(
            ReviewItem(
                query_id=query_id,
                tenant_id=tenant_id,
                flagged_reason=flagged_reason,
                status="pending",
            )
        )


def resolve_review(
    *, query_id: str, decision: str, reviewer: str, comment: str
) -> bool:
    """Approve or reject a review item and sync the audit row.

    Args:
        query_id: The query under review.
        decision: ``"approved"`` or ``"rejected"``.
        reviewer: Username of the reviewer.
        comment: Free-text reviewer note.

    Returns:
        True if a pending review item was found and updated.
    """
    with session_scope() as session:
        item = (
            session.query(ReviewItem)
            .filter(ReviewItem.query_id == query_id, ReviewItem.status == "pending")
            .first()
        )
        if item is None:
            return False

        item.status = decision
        item.reviewer = reviewer
        item.reviewer_comment = comment
        item.reviewed_at = datetime.now(timezone.utc)

        audit = (
            session.query(AuditLog)
            .filter(AuditLog.query_id == query_id)
            .first()
        )
        if audit is not None:
            audit.review_status = decision
        return True
