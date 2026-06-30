"""Review router: the human-in-the-loop checkpoint for low-confidence reports.

Reports whose confidence or RAGAS faithfulness fall below the configured
thresholds are held in the review queue with their report withheld from the
requester. A user with the ``reviewer`` (or ``admin``) role inspects the full
report + audit trail and approves or rejects it.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from audit.logger import resolve_review
from auth.dependencies import require_reviewer
from auth.security import Principal
from db.database import session_scope
from db.models import AuditLog, ReviewItem

router = APIRouter(prefix="/review", tags=["review"])


class ReviewItemOut(BaseModel):
    query_id: str
    tenant_id: str
    flagged_reason: str
    status: str
    created_at: Optional[str] = None


class ReviewDetailOut(ReviewItemOut):
    question: str
    report: str
    confidence_score: Optional[float] = None
    ragas_faithfulness: Optional[float] = None


class ReviewDecision(BaseModel):
    comment: str = ""


@router.get("/queue", response_model=List[ReviewItemOut])
def review_queue(
    reviewer: Principal = Depends(require_reviewer),
) -> List[ReviewItemOut]:
    """List pending review items for the reviewer's tenant."""
    with session_scope() as session:
        rows = (
            session.query(ReviewItem)
            .filter(
                ReviewItem.tenant_id == reviewer.tenant_id,
                ReviewItem.status == "pending",
            )
            .order_by(ReviewItem.created_at.asc())
            .all()
        )
        return [
            ReviewItemOut(
                query_id=r.query_id,
                tenant_id=r.tenant_id,
                flagged_reason=r.flagged_reason,
                status=r.status,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in rows
        ]


@router.get("/{query_id}", response_model=ReviewDetailOut)
def review_detail(
    query_id: str, reviewer: Principal = Depends(require_reviewer)
) -> ReviewDetailOut:
    """Return the full withheld report + scores for a flagged query."""
    with session_scope() as session:
        item = (
            session.query(ReviewItem)
            .filter(ReviewItem.query_id == query_id)
            .first()
        )
        if item is None or item.tenant_id != reviewer.tenant_id:
            raise HTTPException(status_code=404, detail="Review item not found.")
        audit = (
            session.query(AuditLog)
            .filter(AuditLog.query_id == query_id)
            .first()
        )
        return ReviewDetailOut(
            query_id=query_id,
            tenant_id=item.tenant_id,
            flagged_reason=item.flagged_reason,
            status=item.status,
            created_at=item.created_at.isoformat() if item.created_at else None,
            question=audit.question if audit else "",
            report=audit.final_report if audit else "",
            confidence_score=audit.confidence_score if audit else None,
            ragas_faithfulness=audit.ragas_faithfulness if audit else None,
        )


@router.post("/{query_id}/approve")
def approve(
    query_id: str,
    decision: ReviewDecision,
    reviewer: Principal = Depends(require_reviewer),
) -> dict:
    """Approve a flagged report so it can be released to the requester."""
    _ensure_tenant_owns(query_id, reviewer.tenant_id)
    ok = resolve_review(
        query_id=query_id, decision="approved",
        reviewer=reviewer.username, comment=decision.comment,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="No pending review item.")
    return {"query_id": query_id, "status": "approved"}


@router.post("/{query_id}/reject")
def reject(
    query_id: str,
    decision: ReviewDecision,
    reviewer: Principal = Depends(require_reviewer),
) -> dict:
    """Reject a flagged report; it is never released to the requester."""
    _ensure_tenant_owns(query_id, reviewer.tenant_id)
    ok = resolve_review(
        query_id=query_id, decision="rejected",
        reviewer=reviewer.username, comment=decision.comment,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="No pending review item.")
    return {"query_id": query_id, "status": "rejected"}


def _ensure_tenant_owns(query_id: str, tenant_id: str) -> None:
    with session_scope() as session:
        item = (
            session.query(ReviewItem)
            .filter(ReviewItem.query_id == query_id)
            .first()
        )
        if item is None or item.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Review item not found.")
