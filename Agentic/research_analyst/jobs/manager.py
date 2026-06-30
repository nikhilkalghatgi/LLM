"""Job manager: selects the backend and exposes a uniform submit API."""

import os
from typing import Dict, List, Optional

from jobs import store
from jobs.thread_backend import ThreadBackend


class JobManager:
    """Facade over the configured job backend (thread or Celery)."""

    def __init__(self, config: Dict, registry) -> None:
        self.config = config
        self.registry = registry
        backend_name = os.environ.get("JOB_BACKEND") or config.get("jobs", {}).get(
            "backend", "thread"
        )
        backend_name = backend_name.lower()

        if backend_name == "celery":
            # Imported lazily so the thread default never requires celery/redis.
            from jobs.celery_app import CeleryBackend

            self.backend = CeleryBackend(config, registry)
            print("[Jobs] Using Celery backend (Redis broker).")
        else:
            self.backend = ThreadBackend(config, registry)
            print("[Jobs] Using in-process thread backend.")

    # -- submission --------------------------------------------------------
    def submit_query(
        self, *, tenant_id: str, user_id: Optional[int], username: str,
        question: str, include_eval: bool = True,
    ) -> str:
        job_id = store.create_job(
            job_type="query",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={"question": question, "include_eval": include_eval},
        )
        self.backend.submit_query(
            job_id=job_id,
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            question=question,
            include_eval=include_eval,
        )
        return job_id

    def submit_ingest(
        self, *, tenant_id: str, user_id: Optional[int], pdf_paths: List[str],
        document_id: Optional[str] = None,
    ) -> str:
        job_id = store.create_job(
            job_type="ingest",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={"pdf_paths": pdf_paths, "document_id": document_id},
        )
        self.backend.submit_ingest(
            job_id=job_id,
            tenant_id=tenant_id,
            pdf_paths=pdf_paths,
            document_id=document_id,
        )
        return job_id

    # -- passthrough queries ----------------------------------------------
    def get_job(self, job_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        return store.get_job(job_id, tenant_id=tenant_id)

    def list_jobs(self, tenant_id: str, limit: int = 50) -> List[Dict]:
        return store.list_jobs(tenant_id, limit=limit)

    def shutdown(self) -> None:
        self.backend.shutdown()
