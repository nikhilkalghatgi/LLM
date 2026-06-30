"""Watched-folder ingestion pipeline (the "real data pipeline, not manual ingest").

Drop a PDF into ``inbox/<tenant_id>/`` and it is automatically ingested into that
tenant's collection, with a :class:`Document` metadata row tracking its status.
This replaces the manual ``python main.py ingest --pdfs ...`` step with an
event-driven pipeline that has state.

Why watchdog (vs a cron/polling loop):
    watchdog uses native OS filesystem events (ReadDirectoryChangesW on Windows),
    so ingestion fires the instant a file lands -- no polling latency, no busy
    loop. It is cross-platform, which matters for "runs on my laptop".
"""

import os
import threading
import time
from typing import Dict, Optional, Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class _PdfDropHandler(FileSystemEventHandler):
    """Submits an ingestion job whenever a stable PDF appears under the inbox."""

    def __init__(self, inbox_dir: str, job_manager, patterns) -> None:
        self.inbox_dir = os.path.abspath(inbox_dir)
        self.job_manager = job_manager
        self.patterns = [p.lower().lstrip("*") for p in (patterns or [".pdf"])]
        self._seen: Set[str] = set()
        self._lock = threading.Lock()

    # -- helpers -----------------------------------------------------------
    def _is_pdf(self, path: str) -> bool:
        lower = path.lower()
        return any(lower.endswith(ext) for ext in self.patterns)

    def _tenant_for(self, path: str) -> Optional[str]:
        """Derive the tenant id from the first path segment under the inbox."""
        rel = os.path.relpath(os.path.abspath(path), self.inbox_dir)
        parts = rel.replace("\\", "/").split("/")
        if len(parts) < 2:
            # File dropped directly in inbox root -> no tenant, ignore.
            return None
        return parts[0]

    def _wait_until_stable(self, path: str, timeout: float = 10.0) -> bool:
        """Wait for the file size to stop changing (upload finished)."""
        last = -1
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                size = os.path.getsize(path)
            except OSError:
                return False
            if size == last and size > 0:
                return True
            last = size
            time.sleep(0.5)
        return os.path.exists(path)

    def _handle(self, path: str) -> None:
        if not self._is_pdf(path):
            return
        tenant_id = self._tenant_for(path)
        if tenant_id is None:
            print(f"[Watcher] Ignored '{path}' (drop files in inbox/<tenant_id>/).")
            return

        abspath = os.path.abspath(path)
        with self._lock:
            if abspath in self._seen:
                return
            self._seen.add(abspath)

        if not self._wait_until_stable(abspath):
            print(f"[Watcher] File never stabilised, skipping: {abspath}")
            return

        job_id = self.job_manager.submit_ingest(
            tenant_id=tenant_id, user_id=None, pdf_paths=[abspath]
        )
        print(f"[Watcher] tenant='{tenant_id}' file='{os.path.basename(abspath)}' "
              f"-> ingest job {job_id}")

    # -- watchdog events ---------------------------------------------------
    def on_created(self, event) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def on_moved(self, event) -> None:
        if not event.is_directory:
            self._handle(event.dest_path)


class FolderWatcher:
    """Owns a watchdog Observer over the inbox folder."""

    def __init__(self, config: Dict, job_manager) -> None:
        self.config = config
        self.inbox_dir = config["paths"]["inbox"]
        patterns = config.get("watcher", {}).get("patterns", ["*.pdf"])
        os.makedirs(self.inbox_dir, exist_ok=True)
        self._handler = _PdfDropHandler(self.inbox_dir, job_manager, patterns)
        self._observer = Observer()

    def start(self) -> None:
        self._observer.schedule(self._handler, self.inbox_dir, recursive=True)
        self._observer.start()
        print(f"[Watcher] Watching '{os.path.abspath(self.inbox_dir)}' "
              f"(drop PDFs in <inbox>/<tenant_id>/).")

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=5)
        print("[Watcher] Stopped.")
