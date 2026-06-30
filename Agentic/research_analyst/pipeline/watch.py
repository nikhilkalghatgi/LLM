"""Standalone entry point for the watched-folder ingestion pipeline.

Run it in its own terminal::

    python -m pipeline.watch

It builds the tenant registry + a thread-backed job manager and watches
``inbox/<tenant_id>/`` for new PDFs, ingesting each automatically. Stop with
Ctrl+C. This process is independent of the API server -- it is its own
long-running data-pipeline service.
"""

import os
import sys
import time

# Make the research_analyst root importable when run as a script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import load_config
from db.database import configure_database, init_db
from tenancy.registry import TenantRegistry
from jobs.manager import JobManager
from pipeline.watcher import FolderWatcher


def main() -> None:
    config = load_config()

    print("[Watch] Configuring metadata database...")
    configure_database(config["paths"]["metadata_db"])
    init_db()

    print("[Watch] Building tenant registry (loads models once)...")
    registry = TenantRegistry(config)

    # Force the thread backend for the standalone watcher so ingestion runs
    # in-process without needing a separate Celery worker.
    os.environ.setdefault("JOB_BACKEND", "thread")
    job_manager = JobManager(config, registry)

    watcher = FolderWatcher(config, job_manager)
    watcher.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[Watch] Shutting down...")
        watcher.stop()
        job_manager.shutdown()


if __name__ == "__main__":
    main()
