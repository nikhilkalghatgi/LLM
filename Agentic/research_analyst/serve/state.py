"""Shared application state set at API startup and read by the routers.

Keeping these as module globals (populated in the lifespan handler) lets the
feature routers stay import-light and avoids threading the registry / job
manager through every dependency signature.
"""

from typing import Dict, Optional

# Populated by serve/api.py lifespan.
config: Dict = {}
registry = None          # tenancy.registry.TenantRegistry
job_manager = None       # jobs.manager.JobManager


def set_state(*, app_config: Dict, tenant_registry, jobs_manager) -> None:
    global config, registry, job_manager
    config = app_config
    registry = tenant_registry
    job_manager = jobs_manager


def get_registry():
    if registry is None:
        raise RuntimeError("Registry not initialised.")
    return registry


def get_job_manager():
    if job_manager is None:
        raise RuntimeError("Job manager not initialised.")
    return job_manager
