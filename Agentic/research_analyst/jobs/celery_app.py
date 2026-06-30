"""Celery application + tasks -- the optional scale-out job backend.

Activate with::

    # 1. start Redis (Docker): docker run -p 6379:6379 redis:7-alpine
    # 2. start a worker (Windows needs --pool=solo):
    #    set JOB_BACKEND=celery
    #    celery -A jobs.celery_app.celery_app worker --loglevel=info --pool=solo
    # 3. start the API with JOB_BACKEND=celery

The worker process builds its **own** :class:`TenantRegistry` lazily (models are
loaded once per worker). Tasks delegate to the same :mod:`jobs.runners` used by
the thread backend, so behaviour and audit semantics are identical.
"""

import os
from typing import Dict, List, Optional

from celery import Celery

from main import load_config

_config: Dict = load_config()
_jobs_cfg = _config.get("jobs", {})

broker = os.environ.get("CELERY_BROKER_URL") or _jobs_cfg.get(
    "celery_broker_url", "redis://localhost:6379/0"
)
backend = os.environ.get("CELERY_RESULT_BACKEND") or _jobs_cfg.get(
    "celery_result_backend", "redis://localhost:6379/1"
)

celery_app = Celery("research_analyst", broker=broker, backend=backend)
celery_app.conf.update(task_track_started=True, task_serializer="json")

# Lazily-built, worker-local singletons (avoid reloading models per task).
_registry = None
_db_ready = False


def _ensure_worker_context():
    """Build the DB connection + tenant registry once inside the worker."""
    global _registry, _db_ready
    if not _db_ready:
        from db.database import configure_database, init_db

        configure_database(_config["paths"]["metadata_db"])
        init_db()
        _db_ready = True
    if _registry is None:
        from tenancy.registry import TenantRegistry

        _registry = TenantRegistry(_config)
    return _registry


@celery_app.task(name="jobs.run_query")
def run_query_task(
    job_id: str,
    tenant_id: str,
    user_id: Optional[int],
    username: str,
    question: str,
    include_eval: bool,
) -> Dict:
    from jobs.runners import run_query_job

    registry = _ensure_worker_context()
    return run_query_job(
        registry=registry,
        config=_config,
        job_id=job_id,
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        question=question,
        include_eval=include_eval,
    )


@celery_app.task(name="jobs.run_ingest")
def run_ingest_task(
    job_id: str,
    tenant_id: str,
    pdf_paths: List[str],
    document_id: Optional[str] = None,
) -> Dict:
    from jobs.runners import run_ingest_job

    registry = _ensure_worker_context()
    return run_ingest_job(
        registry=registry,
        config=_config,
        job_id=job_id,
        tenant_id=tenant_id,
        pdf_paths=pdf_paths,
        document_id=document_id,
    )


class CeleryBackend:
    """Submits jobs to Celery workers via Redis."""

    name = "celery"

    def __init__(self, config: Dict, registry=None) -> None:
        self.config = config

    def submit_query(
        self, *, job_id: str, tenant_id: str, user_id: Optional[int],
        username: str, question: str, include_eval: bool,
    ) -> None:
        run_query_task.delay(
            job_id, tenant_id, user_id, username, question, include_eval
        )

    def submit_ingest(
        self, *, job_id: str, tenant_id: str, pdf_paths: List[str],
        document_id: Optional[str] = None,
    ) -> None:
        run_ingest_task.delay(job_id, tenant_id, pdf_paths, document_id)

    def shutdown(self) -> None:  # pragma: no cover - nothing to clean up
        pass
