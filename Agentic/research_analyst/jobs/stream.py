"""In-process pub/sub bus for streaming ReAct trace steps over SSE.

Each running query job publishes its steps to a per-job queue. The
``GET /jobs/{id}/stream`` endpoint drains that queue and forwards each step as a
Server-Sent Event. A sentinel (``None``) marks completion.

Scope note: this bus lives in the API process, so it works with the **thread**
job backend (default). With the Celery backend the worker runs in a separate
process, so live streaming would need a Redis pub/sub bus instead -- the final
trace is still available via ``GET /jobs/{id}`` on completion either way.
"""

import queue
import threading
from typing import Dict, Optional

_DONE = object()  # sentinel pushed when a job finishes


class StreamBus:
    """Thread-safe registry of per-job event queues."""

    def __init__(self) -> None:
        self._queues: Dict[str, "queue.Queue"] = {}
        self._lock = threading.Lock()

    def register(self, job_id: str) -> "queue.Queue":
        with self._lock:
            q: queue.Queue = queue.Queue()
            self._queues[job_id] = q
            return q

    def publish(self, job_id: str, event: Dict) -> None:
        with self._lock:
            q = self._queues.get(job_id)
        if q is not None:
            q.put(event)

    def close(self, job_id: str) -> None:
        with self._lock:
            q = self._queues.get(job_id)
        if q is not None:
            q.put(_DONE)

    def drain(self, job_id: str, timeout: float = 0.5) -> Optional[object]:
        """Block up to ``timeout`` for the next event. Returns ``_DONE`` sentinel
        on completion or ``None`` on timeout (so the SSE loop can keep-alive)."""
        with self._lock:
            q = self._queues.get(job_id)
        if q is None:
            return _DONE
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    def cleanup(self, job_id: str) -> None:
        with self._lock:
            self._queues.pop(job_id, None)


# Process-wide singleton used by the thread backend + SSE endpoint.
bus = StreamBus()
DONE = _DONE
