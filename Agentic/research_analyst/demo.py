"""Standalone live-demo script for the AI Research Analyst.

Run with:  python demo.py

Downloads two well-known ArXiv papers, ingests them, runs five research queries
end-to-end (input guard -> ReAct orchestrator -> report writer -> output guard ->
RAGAS), then runs a batch evaluation and prints a summary table. The demo is
resilient: network failures during download and RAGAS failures are caught and
reported rather than crashing the run.
"""

import os
import re
import sys
import time
import urllib.request

# Make the package importable when run as `python demo.py` from this directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import load_config, setup_pipeline, ingest
from eval.golden_set import GOLDEN_SET  # noqa: F401  (kept for parity/imports)


SAMPLE_PDFS = [
    (
        "https://arxiv.org/pdf/1706.03762",
        "attention_is_all_you_need.pdf",
        "Attention Is All You Need (Transformer)",
    ),
    (
        "https://arxiv.org/pdf/2005.11401",
        "rag_paper.pdf",
        "Retrieval-Augmented Generation (RAG)",
    ),
]

QUESTIONS = [
    "What is the core architecture proposed in the Transformer paper?",
    "How does RAG combine retrieval with generation?",
    "What attention mechanism is used and how does it work?",
    "What datasets were used to evaluate these models?",
    "What are the limitations discussed by the authors?",
]

_GENERIC_GROUND_TRUTH = (
    "The document should contain relevant information about this topic."
)


def banner(text: str) -> None:
    """Print a centred banner line."""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def download_samples(sample_dir: str) -> list:
    """Download the sample PDFs, skipping any that already exist.

    Returns the list of local PDF paths that are available on disk.
    """
    os.makedirs(sample_dir, exist_ok=True)
    available = []

    for url, filename, title in SAMPLE_PDFS:
        path = os.path.join(sample_dir, filename)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"[Download] Skipping (exists): {filename}")
            available.append(path)
            continue

        print(f"[Download] Fetching '{title}' from {url} ...")
        try:
            urllib.request.urlretrieve(url, path)
            size_kb = os.path.getsize(path) / 1024
            print(f"[Download] Saved {filename} ({size_kb:.0f} KB)")
            available.append(path)
        except Exception as exc:
            print(f"[Download] WARNING: failed to download {filename}: {exc}")

    return available


def print_trace(trace: list) -> None:
    """Print a ReAct trace step by step."""
    for step in trace:
        thought = (step.get("thought") or "").strip()
        action = (step.get("action") or "").strip()
        observation = (step.get("observation") or "").strip().replace("\n", " ")
        if len(observation) > 200:
            observation = observation[:200] + "..."
        print(
            f"Step {step.get('step')} | Thought: {thought} | "
            f"Action: {action} | Observation: {observation}"
        )


def run_demo() -> None:
    """Execute the full demo flow (steps 1-7)."""
    # STEP 1 ----------------------------------------------------------------
    banner("=== AI Research Analyst - Live Demo ===")

    config = load_config()
    sample_dir = config.get("paths", {}).get("sample_pdfs", "./sample_pdfs")

    # STEP 2 ----------------------------------------------------------------
    banner("STEP 2: Downloading sample ArXiv PDFs")
    pdf_paths = download_samples(sample_dir)
    if not pdf_paths:
        print("[Demo] No PDFs available. Cannot continue. Check your network.")
        return

    # Set up the pipeline once (loads models — can take a moment).
    banner("Initialising pipeline")
    components = setup_pipeline(config)

    # STEP 3 ----------------------------------------------------------------
    banner("STEP 3: Ingesting PDFs")
    stats = ingest(pdf_paths=pdf_paths, components=components, config=config)
    print(
        f"[Demo] Ingested {stats['chunks_ingested']} chunks from "
        f"{stats['documents_processed']} document(s)."
    )

    orchestrator = components["orchestrator"]
    input_guard = components["input_guard"]
    output_guard = components["output_guard"]
    report_writer = components["report_writer"]
    ragas_eval = components["ragas_eval"]

    # STEP 4 ----------------------------------------------------------------
    collected_answers = []
    collected_contexts = []

    for i, question in enumerate(QUESTIONS):
        print(f"\n--- Query {i + 1}/{len(QUESTIONS)}: {question} ---")

        # Input guard
        input_result = input_guard.run(question)
        if not input_result["passed"]:
            print(f"[Guardrail] BLOCKED: {input_result['blocked_reason']}")
            collected_answers.append("")
            collected_contexts.append([])
            continue

        clean_query = input_result["clean_query"]

        # Orchestrator (ReAct loop)
        t0 = time.time()
        result = orchestrator.run(query=clean_query)
        elapsed = time.time() - t0

        retrieved_chunks = result.get("retrieved_chunks", [])
        analysis = result.get("analysis") or result.get("report", "")
        critic_feedback = result.get("feedback") or ""

        # Report writer
        report_result = report_writer.run(
            query=question,
            analysis=analysis,
            critic_feedback=critic_feedback,
            retrieved_chunks=retrieved_chunks,
        )
        report = report_result["report"]

        # Output guard
        output_result = output_guard.run(report, retrieved_chunks)

        # ---- print the ReAct trace ----
        print("\n[ReAct Trace]")
        print_trace(result["trace"])

        # ---- print guardrail results ----
        print("\n[Guardrails]")
        print("  Input guard:  PASSED")
        print(
            f"  Output guard: {'PASSED' if output_result['passed'] else 'FLAGGED'}"
        )
        for warning in output_result.get("warnings", []):
            print(f"    Warning: {warning}")
        if not output_result["passed"]:
            print(f"    Reason: {output_result.get('blocked_reason')}")

        # ---- RAGAS scores (resilient) ----
        context_texts = [c["text"] for c in retrieved_chunks]
        print("\n[RAGAS Scores]")
        try:
            scores = ragas_eval.evaluate_single(
                question=question,
                answer=report,
                contexts=context_texts,
                ground_truth=_GENERIC_GROUND_TRUTH,
            )
            print(f"  Faithfulness:      {scores['faithfulness']:.3f}")
            print(f"  Answer relevance:  {scores['answer_relevance']:.3f}")
            print(f"  Context precision: {scores['context_precision']:.3f}")
        except Exception as exc:
            print(f"  RAGAS eval skipped: {exc}")

        # ---- the full report ----
        print("\n[Final Report]")
        print(report)
        print(
            f"\n[Stats] Steps: {result['steps_taken']} | Time: {elapsed:.2f}s | "
            f"Words: {report_result['word_count']} | "
            f"Confidence: {report_result['confidence_score']:.2f}"
        )
        print("-" * 70)

        collected_answers.append(report)
        collected_contexts.append(context_texts)

    # STEP 5 ----------------------------------------------------------------
    banner("STEP 5: Batch evaluation summary")
    golden = [
        {"question": q, "ground_truth": _GENERIC_GROUND_TRUTH} for q in QUESTIONS
    ]
    try:
        batch = ragas_eval.evaluate_batch(
            golden_set=golden,
            answers=collected_answers,
            contexts=collected_contexts,
        )

        q_w, f_w, a_w, c_w = 44, 13, 12, 14
        header = (
            f"{'Question':<{q_w}}{'Faithfulness':>{f_w}}"
            f"{'Answer Rel.':>{a_w}}{'Context Prec.':>{c_w}}"
        )
        print(header)
        print("-" * len(header))
        for pq in batch["per_question"]:
            q_text = pq.get("question", "")
            if len(q_text) > q_w - 2:
                q_text = q_text[: q_w - 5] + "..."
            print(
                f"{q_text:<{q_w}}"
                f"{pq['faithfulness']:>{f_w}.3f}"
                f"{pq['answer_relevance']:>{a_w}.3f}"
                f"{pq['context_precision']:>{c_w}.3f}"
            )
        print("-" * len(header))
        print(
            f"{'MEAN':<{q_w}}"
            f"{batch['mean_faithfulness']:>{f_w}.3f}"
            f"{batch['mean_answer_relevance']:>{a_w}.3f}"
            f"{batch['mean_context_precision']:>{c_w}.3f}"
        )
        print(f"\nOverall: {'PASSED' if batch['passed'] else 'FAILED'}")
    except Exception as exc:
        print(f"RAGAS eval skipped: {exc}")

    # STEP 6 ----------------------------------------------------------------
    banner("STEP 6: MLflow")
    print("MLflow runs saved. View at: mlflow ui --backend-store-uri ./mlruns")

    # STEP 7 ----------------------------------------------------------------
    banner("STEP 7: API")
    print("Start the API: uvicorn serve.api:app --reload --port 8000")
    print(
        "Then try: curl -X POST http://localhost:8000/query "
        "-H 'Content-Type: application/json' "
        "-d '{\"question\": \"What is attention?\"}'"
    )


if __name__ == "__main__":
    run_demo()

