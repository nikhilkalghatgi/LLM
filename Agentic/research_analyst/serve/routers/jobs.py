"""Jobs router: async submit, poll, list, and SSE trace streaming.

The ``POST`` endpoints return a ``job_id`` immediately (HTTP 202) -- the heavy
ReAct work runs on the job backend. Clients poll ``GET /jobs/{id}`` or subscribe
to ``GET /jobs/{id}/stream`` to watch the ReAct trace arrive live.
"""

import json
import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from auth.dependencies import get_current_principal
from auth.security import Principal
from serve import state
from jobs.stream import DONE, bus

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str = "pending"
    poll_url: str
    stream_url: str


class AsyncQueryRequest(BaseModel):
    question: str = Field(..., description="The research question to answer.")
    include_eval: bool = Field(default=True, description="Run RAGAS faithfulness.")


@router.post("/query", response_model=JobSubmitResponse, status_code=202)
def submit_query(
    req: AsyncQueryRequest,
    principal: Principal = Depends(get_current_principal),
) -> JobSubmitResponse:
    """Queue a research query against the caller's tenant; returns a job id."""
    jm = state.get_job_manager()
    job_id = jm.submit_query(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        username=principal.username,
        question=req.question,
        include_eval=req.include_eval,
    )
    return JobSubmitResponse(
        job_id=job_id,
        poll_url=f"/jobs/{job_id}",
        stream_url=f"/jobs/{job_id}/stream",
    )


@router.post("/ingest/upload", response_model=JobSubmitResponse, status_code=202)
async def submit_ingest_upload(
    file: UploadFile = File(...),
    principal: Principal = Depends(get_current_principal),
) -> JobSubmitResponse:
    """Upload a PDF and queue tenant-scoped ingestion; returns a job id."""
    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    uploads_dir = os.path.join(state.config["paths"]["uploads"], principal.tenant_id)
    os.makedirs(uploads_dir, exist_ok=True)
    saved = os.path.join(uploads_dir, f"{uuid.uuid4().hex}_{os.path.basename(filename)}")
    content = await file.read()
    with open(saved, "wb") as fh:
        fh.write(content)

    jm = state.get_job_manager()
    job_id = jm.submit_ingest(
        tenant_id=principal.tenant_id, user_id=principal.user_id, pdf_paths=[saved]
    )
    return JobSubmitResponse(
        job_id=job_id,
        poll_url=f"/jobs/{job_id}",
        stream_url=f"/jobs/{job_id}/stream",
    )


@router.get("/{job_id}")
def get_job(
    job_id: str, principal: Principal = Depends(get_current_principal)
) -> dict:
    """Return job status/result, enforcing tenant ownership."""
    jm = state.get_job_manager()
    job = jm.get_job(job_id, tenant_id=principal.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.get("")
def list_jobs(
    limit: int = 50, principal: Principal = Depends(get_current_principal)
) -> List[dict]:
    """List recent jobs for the caller's tenant."""
    jm = state.get_job_manager()
    return jm.list_jobs(principal.tenant_id, limit=limit)


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: str, principal: Principal = Depends(get_current_principal)
):
    """Stream the ReAct trace of a running query job as Server-Sent Events.

    Each event payload is a JSON object: ``{type: step|done|error, ...}``.
    Works with the thread backend; with Celery the trace is delivered on
    completion via ``GET /jobs/{id}`` instead.
    """
    jm = state.get_job_manager()
    job = jm.get_job(job_id, tenant_id=principal.tenant_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")

    poll = float(state.config.get("jobs", {}).get("stream_poll_interval", 0.5))

    async def event_generator():
        while True:
            event = bus.drain(job_id, timeout=poll)
            if event is DONE:
                yield {"event": "end", "data": json.dumps({"type": "end"})}
                break
            if event is None:
                # keep-alive comment so proxies don't time out
                yield {"event": "ping", "data": "{}"}
                continue
            yield {"event": "message", "data": json.dumps(event)}
        bus.cleanup(job_id)

    return EventSourceResponse(event_generator())
