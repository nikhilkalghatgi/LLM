"""FastAPI application exposing the AI Research Analyst pipeline.

Reuses the pipeline logic from ``main.py`` (``load_config``, ``setup_pipeline``,
``ingest``) so there is a single source of truth for ingestion and component
wiring. Query/eval flows are composed here directly from the initialised
components so that per-request flags (``include_trace``, ``include_eval``) can be
honoured without running unnecessary work.
"""

import os
import re
import sys
import time
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

# Ensure the research_analyst root is importable (for `main`, `eval`, etc.)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from main import load_config, setup_pipeline, ingest
from eval.golden_set import GOLDEN_SET
from serve.middleware import RequestTimingMiddleware, RequestSizeLimitMiddleware
from serve.schemas import (
    EvalRequest,
    EvalResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    UploadResponse,
)


# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
components: Dict = {}  # populated at startup by the lifespan handler

# Loaded once at import time so middleware can read serve settings. The lifespan
# handler reuses this same dict (after applying any env overrides) for setup.
app_config: Dict = load_config()

_GENERIC_GROUND_TRUTH = "The document should contain relevant information about this topic."


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise pipeline components on startup; nothing to tear down on exit."""
    # The OLLAMA_BASE_URL env var (set by docker-compose) must win over the YAML
    # value. load_config already applies this, but we re-apply defensively in
    # case the config was constructed differently.
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL")
    if ollama_base_url:
        app_config["llm_base_url"] = ollama_base_url
        print(f"[API] Overriding llm_base_url from env: {ollama_base_url}")

    print("[API] Starting pipeline setup...")
    components.update(setup_pipeline(app_config))

    os.makedirs(app_config["paths"]["uploads"], exist_ok=True)
    os.makedirs(app_config["paths"]["eval_reports"], exist_ok=True)
    print("[API] Pipeline ready. Serving requests.")

    yield

    # Shutdown: ChromaDB uses a persistent client — nothing to clean up.
    print("[API] Shutting down.")


# ---------------------------------------------------------------------------
# App + middleware
# ---------------------------------------------------------------------------
app = FastAPI(title="AI Research Analyst", version="1.0.0", lifespan=lifespan)

# Added innermost-first: CORS (innermost) → size limit → timing (outermost),
# so the timing middleware logs every request, including rejected 413s.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_upload_size_mb=app_config["serve"]["max_upload_size_mb"],
)
app.add_middleware(RequestTimingMiddleware)


# ---------------------------------------------------------------------------
# Blocking pipeline helpers (run via run_in_executor so the event loop is free)
# ---------------------------------------------------------------------------
def _run_query_blocking(question: str, include_eval: bool) -> Dict:
    """Run the full query pipeline synchronously and return a result dict.

    Flow: input guard → orchestrator → report writer → output guard → (RAGAS).
    """
    input_guard = components["input_guard"]
    orchestrator = components["orchestrator"]
    report_writer = components["report_writer"]
    output_guard = components["output_guard"]
    ragas_eval = components["ragas_eval"]
    tracker = components["tracker"]

    # 1. INPUT GUARDRAIL — fail fast before any expensive work.
    input_result = input_guard.run(question)
    if not input_result["passed"]:
        return {"blocked": True, "input_result": input_result}

    clean_query = input_result["clean_query"]

    with tracker:
        tracker.start_run(query=question, config=app_config)
        tracker.log_guardrail_input(input_result)

        # 2. ORCHESTRATOR (ReAct loop)
        t0 = time.time()
        result = orchestrator.run(query=clean_query)
        orchestrator_time = time.time() - t0
        tracker.log_agent_trace(
            steps_taken=result["steps_taken"], total_time=orchestrator_time
        )

        retrieved_chunks = result.get("retrieved_chunks", [])
        analysis = result.get("analysis") or result.get("report", "")
        critic_feedback = result.get("feedback") or ""

        # 3. REPORT WRITER
        report_result = report_writer.run(
            query=question,
            analysis=analysis,
            critic_feedback=critic_feedback,
            retrieved_chunks=retrieved_chunks,
        )
        report = report_result["report"]
        tracker.log_report(report)

        # 4. OUTPUT GUARDRAIL
        output_result = output_guard.run(report, retrieved_chunks)
        tracker.log_guardrail_output(output_result)
        citation_count = (
            output_result["checks"].get("citations", {}).get("citation_count", 0)
        )
        tracker.log_report_metadata(
            word_count=report_result["word_count"],
            confidence_score=report_result["confidence_score"],
            citation_count=citation_count,
        )

        # 5. RAGAS EVALUATION (optional)
        ragas_scores: Optional[Dict] = None
        if include_eval:
            context_texts = [c["text"] for c in retrieved_chunks]
            ragas_scores = ragas_eval.evaluate_single(
                question=question,
                answer=report,
                contexts=context_texts,
                ground_truth=_GENERIC_GROUND_TRUTH,
            )
            tracker.log_ragas_scores(ragas_scores)

    return {
        "blocked": False,
        "input_result": input_result,
        "result": result,
        "report": report,
        "report_result": report_result,
        "output_result": output_result,
        "ragas_scores": ragas_scores,
        "retrieved_chunks": retrieved_chunks,
    }


def _run_eval_blocking(questions: Optional[List[str]]) -> Dict:
    """Run a batch RAGAS evaluation synchronously and save a timestamped report."""
    orchestrator = components["orchestrator"]
    report_writer = components["report_writer"]
    ragas_eval = components["ragas_eval"]

    if questions:
        golden_set = [
            {"question": q, "ground_truth": _GENERIC_GROUND_TRUTH} for q in questions
        ]
    else:
        golden_set = GOLDEN_SET

    answers: List[str] = []
    contexts: List[List[str]] = []

    for item in golden_set:
        q = item["question"]
        result = orchestrator.run(query=q)
        retrieved_chunks = result.get("retrieved_chunks", [])
        analysis = result.get("analysis") or result.get("report", "")
        critic_feedback = result.get("feedback") or ""

        report_result = report_writer.run(
            query=q,
            analysis=analysis,
            critic_feedback=critic_feedback,
            retrieved_chunks=retrieved_chunks,
        )
        answers.append(report_result["report"])
        contexts.append([c["text"] for c in retrieved_chunks])

    batch = ragas_eval.evaluate_batch(
        golden_set=golden_set, answers=answers, contexts=contexts
    )

    eval_dir = app_config["paths"]["eval_reports"]
    os.makedirs(eval_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(eval_dir, f"eval_report_{timestamp}.json")
    ragas_eval.generate_eval_report(batch, output_path=report_path)

    batch["_report_path"] = report_path
    return batch


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness/info endpoint: vector store size and configured model."""
    try:
        vector_store = components.get("vector_store")
        count = vector_store.count() if vector_store is not None else 0
        return HealthResponse(
            status="healthy",
            vector_store_count=count,
            model=app_config.get("llm_model", "mistral"),
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(req: IngestRequest) -> IngestResponse:
    """Ingest PDFs that already exist on the server filesystem."""
    try:
        for path in req.pdf_paths:
            if not os.path.exists(path):
                raise HTTPException(
                    status_code=400, detail=f"File not found: {path}"
                )

        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None, ingest, req.pdf_paths, components, app_config
        )

        return IngestResponse(
            success=stats["success"],
            chunks_ingested=stats["chunks_ingested"],
            documents_processed=stats["documents_processed"],
            embedding_dim=stats["embedding_dim"],
            message=stats["message"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/ingest/upload", response_model=UploadResponse)
async def ingest_upload(file: UploadFile = File(...)) -> UploadResponse:
    """Accept a multipart PDF upload, persist it, then ingest it."""
    try:
        filename = file.filename or "upload.pdf"
        is_pdf = filename.lower().endswith(".pdf") or (
            file.content_type == "application/pdf"
        )
        if not is_pdf:
            raise HTTPException(
                status_code=400, detail="Only PDF files are accepted."
            )

        uploads_dir = app_config["paths"]["uploads"]
        os.makedirs(uploads_dir, exist_ok=True)
        saved_path = os.path.join(uploads_dir, os.path.basename(filename))

        content = await file.read()
        with open(saved_path, "wb") as f:
            f.write(content)

        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None, ingest, [saved_path], components, app_config
        )

        message = (
            f"Uploaded and ingested '{os.path.basename(filename)}'. "
            f"{stats['message']}"
        )
        return UploadResponse(
            success=stats["success"],
            filename=os.path.basename(filename),
            saved_path=saved_path,
            message=message,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest) -> QueryResponse:
    """Run the full research pipeline for a single question."""
    start = time.time()
    try:
        loop = asyncio.get_event_loop()
        outcome = await loop.run_in_executor(
            None, _run_query_blocking, req.question, req.include_eval
        )
        elapsed = time.time() - start

        # Input guardrail blocked the request — return a structured failure.
        if outcome["blocked"]:
            input_result = outcome["input_result"]
            return QueryResponse(
                success=False,
                question=req.question,
                report="",
                confidence_score=0.0,
                word_count=0,
                steps_taken=0,
                guardrail_passed=False,
                guardrail_blocked_reason=input_result.get("blocked_reason"),
                output_guard_passed=False,
                output_guard_warnings=[],
                ragas_scores=None,
                trace=None,
                citations=[],
                processing_time_seconds=elapsed,
            )

        report = outcome["report"]
        report_result = outcome["report_result"]
        result = outcome["result"]
        output_result = outcome["output_result"]

        citations = list(set(re.findall(r"\[Source:[^\]]+\]", report)))

        return QueryResponse(
            success=True,
            question=req.question,
            report=report,
            confidence_score=report_result["confidence_score"],
            word_count=report_result["word_count"],
            steps_taken=result["steps_taken"],
            guardrail_passed=True,
            guardrail_blocked_reason=None,
            output_guard_passed=output_result["passed"],
            output_guard_warnings=output_result.get("warnings", []),
            ragas_scores=outcome["ragas_scores"] if req.include_eval else None,
            trace=result["trace"] if req.include_trace else None,
            citations=citations,
            processing_time_seconds=elapsed,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/eval", response_model=EvalResponse)
async def eval_endpoint(req: EvalRequest) -> EvalResponse:
    """Run a batch RAGAS evaluation over supplied questions or the golden set."""
    try:
        loop = asyncio.get_event_loop()
        batch = await loop.run_in_executor(None, _run_eval_blocking, req.questions)

        return EvalResponse(
            success=True,
            questions_evaluated=len(batch.get("per_question", [])),
            mean_faithfulness=batch["mean_faithfulness"],
            mean_answer_relevance=batch["mean_answer_relevance"],
            mean_context_precision=batch["mean_context_precision"],
            passed=batch["passed"],
            report_path=batch["_report_path"],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/trace/{run_id}")
async def get_trace(run_id: str) -> Dict:
    """Placeholder for future MLflow run-trace retrieval."""
    return {
        "message": "MLflow UI available at http://localhost:5000",
        "run_id": run_id,
    }

