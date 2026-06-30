"""CRUD helpers for the ``jobs`` table.

The job store is the source of truth for async task state. ``POST /jobs/...``
creates a ``pending`` row and returns its id immediately; a worker (thread or
Celery) flips it to ``running`` then ``complete``/``failed`` while ``GET
/jobs/{id}`` polls it.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from db.database import session_scope
from db.models import Job


def create_job(*, job_type: str, tenant_id: str, user_id: Optional[int],
               payload: Dict) -> str:
    """Insert a new ``pending`` job and return its generated id."""
    job_id = uuid.uuid4().hex
    with session_scope() as session:
        session.add(
            Job(
                id=job_id,
                type=job_type,
                tenant_id=tenant_id,
                user_id=user_id,
                status="pending",
                payload_json=json.dumps(payload, default=str),
            )
        )
    return job_id


def mark_running(job_id: str) -> None:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is not None:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)


def mark_complete(job_id: str, result: Dict) -> None:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is not None:
            job.status = "complete"
            job.result_json = json.dumps(result, default=str)
            job.finished_at = datetime.now(timezone.utc)


def mark_failed(job_id: str, error: str) -> None:
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is not None:
            job.status = "failed"
            job.error = error
            job.finished_at = datetime.now(timezone.utc)


def _to_dict(job: Job) -> Dict:
    return {
        "job_id": job.id,
        "type": job.type,
        "tenant_id": job.tenant_id,
        "status": job.status,
        "payload": json.loads(job.payload_json or "{}"),
        "result": json.loads(job.result_json or "{}"),
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


def get_job(job_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
    """Fetch a job, optionally enforcing tenant ownership."""
    with session_scope() as session:
        job = session.get(Job, job_id)
        if job is None:
            return None
        if tenant_id is not None and job.tenant_id != tenant_id:
            return None
        return _to_dict(job)


def list_jobs(tenant_id: str, limit: int = 50) -> List[Dict]:
    """List the most recent jobs for a tenant."""
    with session_scope() as session:
        rows = (
            session.query(Job)
            .filter(Job.tenant_id == tenant_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_to_dict(j) for j in rows]
