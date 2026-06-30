"""Core pipeline service: tenant-aware query and ingestion orchestration.

This is the single place where a query flows through
``input guard -> ReAct -> report writer -> output guard -> RAGAS`` and then gets
**audited** and, when low-confidence, **routed to human review**. Both the async
job tasks and any synchronous caller use these functions so the compliance
behaviour is identical regardless of entry point.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from audit.logger import enqueue_review, write_audit_log
from cache import query_cache
from db.database import session_scope
from db.models import Document

_GENERIC_GROUND_TRUTH = (
    "The document should contain relevant information about this topic."
)


def _chunk_id(chunk: Dict) -> str:
    """Reconstruct the stable chunk id used by the vector store."""
    return f"{chunk.get('source', 'unknown')}_chunk_{chunk.get('chunk_index', 0)}"


def run_query(
    *,
    components: Dict,
    config: Dict,
    question: str,
    tenant_id: str,
    user_id: Optional[int] = None,
    username: str = "",
    query_id: Optional[str] = None,
    include_eval: bool = True,
    step_callback: Optional[Callable[[Dict], None]] = None,
    use_cache: bool = True,
) -> Dict:
    """Run the full guarded pipeline for one question and audit the result.

    Args:
        components: A tenant bundle from :class:`TenantRegistry`.
        config: Full pipeline config.
        question: The research question.
        tenant_id / user_id / username: Caller identity for the audit record.
        query_id: Optional pre-allocated id (the job id is reused so a job and
            its audit row share one identifier). Generated when omitted.
        include_eval: Run RAGAS faithfulness scoring.
        step_callback: Optional callback streamed each ReAct step (SSE).

    Returns:
        A result dict with the report, guard outcomes, scores, and review state.
    """
    query_id = query_id or uuid.uuid4().hex
    t_start = time.time()

    input_guard = components["input_guard"]
    orchestrator = components["orchestrator"]
    report_writer = components["report_writer"]
    output_guard = components["output_guard"]
    ragas_eval = components["ragas_eval"]
    tracker = components["tracker"]

    review_cfg = config.get("review", {})
    conf_threshold = float(review_cfg.get("confidence_threshold", 0.60))
    faith_threshold = float(review_cfg.get("faithfulness_threshold", 0.50))

    cache_cfg = config.get("cache", {})
    cache_enabled = bool(cache_cfg.get("enabled", True)) and use_cache
    cache_ttl = int(cache_cfg.get("ttl_seconds", 0))

    # 1. INPUT GUARD -- fail fast, still audited.
    input_result = input_guard.run(question)
    if not input_result["passed"]:
        latency_ms = int((time.time() - t_start) * 1000)
        write_audit_log(
            query_id=query_id,
            tenant_id=tenant_id,
            user_id=user_id,
            username=username,
            question=question,
            input_guard=input_result,
            react_steps=[],
            retrieved_chunk_ids=[],
            final_report="",
            output_guard_passed=False,
            ragas_faithfulness=None,
            confidence_score=None,
            review_status="blocked",
            latency_ms=latency_ms,
        )
        return {
            "query_id": query_id,
            "blocked": True,
            "blocked_reason": input_result.get("blocked_reason"),
            "input_guard": input_result,
            "review_status": "blocked",
        }

    clean_query = input_result["clean_query"]

    # 1b. QUERY CACHE -- skip the whole pipeline on a repeat question.
    # Only auto-approved answers are ever stored, so a hit is always safe.
    if cache_enabled:
        cached = query_cache.get(
            tenant_id=tenant_id,
            question=question,
            include_eval=include_eval,
            ttl_seconds=cache_ttl,
        )
        if cached is not None:
            latency_ms = int((time.time() - t_start) * 1000)
            write_audit_log(
                query_id=query_id,
                tenant_id=tenant_id,
                user_id=user_id,
                username=username,
                question=question,
                input_guard=input_result,
                react_steps=cached.get("trace", []),
                retrieved_chunk_ids=cached.get("retrieved_chunk_ids", []),
                final_report=cached.get("report_full", ""),
                output_guard_passed=True,
                ragas_faithfulness=cached.get("faithfulness"),
                confidence_score=cached.get("confidence_score"),
                review_status="auto_approved",
                latency_ms=latency_ms,
            )
            return {
                "query_id": query_id,
                "blocked": False,
                "cached": True,
                "report": cached.get("report"),
                "report_full": cached.get("report_full"),
                "confidence_score": cached.get("confidence_score"),
                "word_count": cached.get("word_count"),
                "steps_taken": cached.get("steps_taken"),
                "trace": cached.get("trace", []),
                "retrieved_chunk_ids": cached.get("retrieved_chunk_ids", []),
                "input_guard": input_result,
                "output_guard": cached.get("output_guard"),
                "ragas_scores": cached.get("ragas_scores"),
                "review_status": "auto_approved",
                "needs_review": False,
                "flagged_reason": "",
                "latency_ms": latency_ms,
            }

    with tracker:
        tracker.start_run(query=question, config=config)
        tracker.log_guardrail_input(input_result)

        # 2. ReAct ORCHESTRATOR (streamed step-by-step if a callback is given)
        t0 = time.time()
        result = orchestrator.run_with_callback(
            query=clean_query, step_callback=step_callback
        )
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
        confidence_score = report_result["confidence_score"]
        tracker.log_report(report)

        # 4. OUTPUT GUARD
        output_result = output_guard.run(report, retrieved_chunks)
        tracker.log_guardrail_output(output_result)
        citation_count = (
            output_result["checks"].get("citations", {}).get("citation_count", 0)
        )
        tracker.log_report_metadata(
            word_count=report_result["word_count"],
            confidence_score=confidence_score,
            citation_count=citation_count,
        )

        # 5. RAGAS (optional)
        ragas_scores: Optional[Dict] = None
        faithfulness: Optional[float] = None
        if include_eval:
            context_texts = [c["text"] for c in retrieved_chunks]
            ragas_scores = ragas_eval.evaluate_single(
                question=question,
                answer=report,
                contexts=context_texts,
                ground_truth=_GENERIC_GROUND_TRUTH,
            )
            tracker.log_ragas_scores(ragas_scores)
            faithfulness = float(ragas_scores.get("faithfulness", 0.0))

    # 6. HUMAN-IN-THE-LOOP DECISION
    flagged_reasons: List[str] = []
    if confidence_score is not None and confidence_score < conf_threshold:
        flagged_reasons.append(
            f"confidence {confidence_score:.2f} < {conf_threshold:.2f}"
        )
    if faithfulness is not None and faithfulness < faith_threshold:
        flagged_reasons.append(
            f"faithfulness {faithfulness:.2f} < {faith_threshold:.2f}"
        )
    if not output_result["passed"]:
        flagged_reasons.append(
            f"output guard flagged: {output_result.get('blocked_reason')}"
        )

    needs_review = bool(flagged_reasons)
    review_status = "pending" if needs_review else "auto_approved"
    latency_ms = int((time.time() - t_start) * 1000)

    chunk_ids = [_chunk_id(c) for c in retrieved_chunks]

    # 7. AUDIT (always) + REVIEW (only when flagged)
    write_audit_log(
        query_id=query_id,
        tenant_id=tenant_id,
        user_id=user_id,
        username=username,
        question=question,
        input_guard=input_result,
        react_steps=result["trace"],
        retrieved_chunk_ids=chunk_ids,
        final_report=report,
        output_guard_passed=output_result["passed"],
        ragas_faithfulness=faithfulness,
        confidence_score=confidence_score,
        review_status=review_status,
        latency_ms=latency_ms,
    )
    if needs_review:
        enqueue_review(
            query_id=query_id,
            tenant_id=tenant_id,
            flagged_reason="; ".join(flagged_reasons),
        )

    # 8. CACHE -- store only clean, auto-approved answers for future repeats.
    if cache_enabled and not needs_review:
        query_cache.set(
            tenant_id=tenant_id,
            question=question,
            include_eval=include_eval,
            result={
                "report": report,
                "report_full": report,
                "confidence_score": confidence_score,
                "word_count": report_result["word_count"],
                "steps_taken": result["steps_taken"],
                "trace": result["trace"],
                "retrieved_chunk_ids": chunk_ids,
                "output_guard": output_result,
                "ragas_scores": ragas_scores,
                "faithfulness": faithfulness,
                "review_status": "auto_approved",
            },
        )

    return {
        "query_id": query_id,
        "blocked": False,
        "cached": False,
        "report": report if not needs_review else None,
        "report_full": report,  # always present for reviewers/audit
        "confidence_score": confidence_score,
        "word_count": report_result["word_count"],
        "steps_taken": result["steps_taken"],
        "trace": result["trace"],
        "retrieved_chunk_ids": chunk_ids,
        "input_guard": input_result,
        "output_guard": output_result,
        "ragas_scores": ragas_scores,
        "review_status": review_status,
        "needs_review": needs_review,
        "flagged_reason": "; ".join(flagged_reasons),
        "latency_ms": latency_ms,
    }


def run_ingest(
    *,
    components: Dict,
    config: Dict,
    pdf_paths: List[str],
    tenant_id: str,
    document_id: Optional[str] = None,
) -> Dict:
    """Ingest PDFs into a tenant's collection and record document metadata.

    Reuses ``main.ingest`` for the heavy lifting (chunk -> embed -> store ->
    rebuild BM25), then updates the :class:`Document` state table.
    """
    # Imported lazily to avoid a circular import at module load time.
    from main import ingest as _pipeline_ingest

    document_id = document_id or uuid.uuid4().hex
    filename = ", ".join(p.split("/")[-1].split("\\")[-1] for p in pdf_paths)

    # Upsert a 'ingesting' document row.
    with session_scope() as session:
        doc = session.get(Document, document_id)
        if doc is None:
            doc = Document(
                id=document_id,
                filename=filename,
                tenant_id=tenant_id,
                source_path=pdf_paths[0] if pdf_paths else "",
                status="ingesting",
            )
            session.add(doc)
        else:
            doc.status = "ingesting"

    try:
        stats = _pipeline_ingest(pdf_paths, components, config)
    except Exception as exc:  # mark failed, re-raise for the job layer
        with session_scope() as session:
            doc = session.get(Document, document_id)
            if doc is not None:
                doc.status = "failed"
                doc.error = str(exc)
        raise

    status = "ingested" if stats.get("success") else "failed"
    with session_scope() as session:
        doc = session.get(Document, document_id)
        if doc is not None:
            doc.status = status
            doc.chunk_count = stats.get("chunks_ingested", 0)
            doc.error = "" if stats.get("success") else stats.get("message", "")
            doc.ingested_at = datetime.now(timezone.utc)

    # New documents can change answers -> drop this tenant's cached answers.
    if stats.get("success"):
        invalidated = query_cache.invalidate_tenant(tenant_id)
        stats["cache_invalidated"] = invalidated

    stats["document_id"] = document_id
    return stats


def core_service_init() -> None:
    """No-op placeholder kept for symmetry with other packages' init hooks."""
