"""Thread-pool job backend -- the laptop default (zero external infra).

Why a thread backend at all (vs always Celery+Redis):
    Celery + Redis is the right answer for a real deployment, but it needs a
    Redis server and a separate worker process. For "runs on my laptop" that is
    friction. A ``ThreadPoolExecutor`` gives the *same async API contract* --
    submit returns immediately, status is polled from the DB, the ReAct trace
    streams over SSE -- with nothing to install. Set ``JOB_BACKEND=celery`` to
    switch to the scale-out backend without changing any endpoint code.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional

from jobs.runners import run_ingest_job, run_query_job


class ThreadBackend:
    """Runs job functions on a bounded in-process thread pool."""

    name = "thread"

    def __init__(self, config: Dict, registry) -> None:
        self.config = config
        self.registry = registry
        workers = int(config.get("jobs", {}).get("thread_workers", 2))
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="job")

    def submit_query(
        self, *, job_id: str, tenant_id: str, user_id: Optional[int],
        username: str, question: str, include_eval: bool,
    ) -> None:
        self._pool.submit(
            run_query_job,
            registry=self.registry,
            config=self.config,
            job_id=job_id,
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            question=question,
            include_eval=include_eval,
        )

    def submit_ingest(
        self, *, job_id: str, tenant_id: str, pdf_paths: List[str],
        document_id: Optional[str] = None,
    ) -> None:
        self._pool.submit(
            run_ingest_job,
            registry=self.registry,
            config=self.config,
            job_id=job_id,
            tenant_id=tenant_id,
            pdf_paths=pdf_paths,
            document_id=document_id,
        )

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
