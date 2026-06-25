"""CLI entry point for the AI Research Analyst pipeline.

Usage:
    python main.py ingest --pdfs paper1.pdf paper2.pdf
    python main.py query --question "What are the key findings on X?"
"""

import sys
import os
import time
import json
import argparse
from typing import Dict, List

import yaml

# Add project root to path so all internal imports resolve
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.chunker import chunk_documents
from ingestion.embedder import Embedder
from ingestion.vector_store import VectorStore
from retrieval.dense import DenseRetriever
from retrieval.sparse import SparseRetriever
from retrieval.reranker import HybridReranker
from agents.orchestrator import ReActOrchestrator
from agents.report_writer import ReportWriter
from guardrails.input_guard import InputGuard
from guardrails.output_guard import OutputGuard
from eval.ragas_eval import RAGASEvaluator
from eval.golden_set import GOLDEN_SET, load_golden_set, save_golden_set
from mlflow_tracker import MLflowTracker


def load_config(config_path: str = None) -> dict:
    """Load pipeline configuration from configs/config.yaml.

    Args:
        config_path: Optional override path. Defaults to configs/config.yaml
                     relative to this script's directory.

    Returns:
        Configuration dict.
    """
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "configs",
            "config.yaml",
        )

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # Allow the container/runtime to override the Ollama endpoint. This keeps
    # the CLI working inside Docker (where Ollama lives at http://ollama:11434)
    # without editing the YAML.
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL")
    if ollama_base_url:
        config["llm_base_url"] = ollama_base_url

    return config


def setup_pipeline(config: dict) -> Dict:
    """Initialise all pipeline components from config.

    Returns:
        Dict of named components: embedder, vector_store, dense, sparse,
        reranker, orchestrator, tracker.
    """
    print("[Setup] Initialising embedder...")
    embedder = Embedder(model_name=config["embedding_model"])

    print("[Setup] Initialising vector store...")
    vector_store = VectorStore(
        persist_dir=config["chroma_persist_dir"],
        collection_name="research_docs",
    )

    print("[Setup] Initialising dense retriever...")
    dense = DenseRetriever(vector_store=vector_store, embedder=embedder)

    print("[Setup] Initialising sparse retriever...")
    sparse = SparseRetriever(vector_store=vector_store)

    # Build BM25 index if there are documents in the store
    if vector_store.count() > 0:
        print("[Setup] Building BM25 index...")
        sparse.build_index()

    print("[Setup] Initialising hybrid reranker...")
    reranker = HybridReranker(
        dense=dense,
        sparse=sparse,
        reranker_model_name=config["reranker_model"],
    )

    print("[Setup] Initialising ReAct orchestrator...")
    orchestrator = ReActOrchestrator(config=config, reranker=reranker)

    print("[Setup] Initialising input guard...")
    input_guard = InputGuard(
        config=config, embedder=embedder, vector_store=vector_store
    )

    print("[Setup] Initialising output guard...")
    output_guard = OutputGuard(config=config, embedder=embedder)

    print("[Setup] Initialising report writer...")
    report_writer = ReportWriter(config=config)

    print("[Setup] Initialising RAGAS evaluator...")
    ragas_eval = RAGASEvaluator(config=config)

    print("[Setup] Initialising MLflow tracker...")
    tracker = MLflowTracker(experiment_name=config["mlflow_experiment_name"])

    print("[Setup] Pipeline ready.\n")

    return {
        "embedder": embedder,
        "vector_store": vector_store,
        "dense": dense,
        "sparse": sparse,
        "reranker": reranker,
        "orchestrator": orchestrator,
        "input_guard": input_guard,
        "output_guard": output_guard,
        "report_writer": report_writer,
        "ragas_eval": ragas_eval,
        "tracker": tracker,
    }


def ingest(pdf_paths: List[str], components: Dict, config: dict) -> Dict:
    """Full ingestion pipeline: chunk → embed → store → rebuild sparse index.

    Args:
        pdf_paths: List of paths to PDF files to ingest.
        components: Initialised pipeline components from setup_pipeline().
        config: Pipeline configuration dict.

    Returns:
        Stats dict with keys: success, chunks_ingested, documents_processed,
        embedding_dim, message. The CLI ignores this; the API consumes it.
    """
    embedder: Embedder = components["embedder"]
    vector_store: VectorStore = components["vector_store"]
    sparse: SparseRetriever = components["sparse"]

    # Validate paths
    for path in pdf_paths:
        if not os.path.exists(path):
            msg = f"File not found: {path}"
            print(f"[Ingest] ERROR: {msg}")
            return {
                "success": False,
                "chunks_ingested": 0,
                "documents_processed": 0,
                "embedding_dim": 0,
                "message": msg,
            }

    print(f"[Ingest] Processing {len(pdf_paths)} PDF(s)...")

    # Step 1: Chunk all PDFs
    t0 = time.time()
    chunks = chunk_documents(
        pdf_paths=pdf_paths,
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
    )
    chunk_time = time.time() - t0
    print(f"[Ingest] Created {len(chunks)} chunks in {chunk_time:.2f}s")

    if not chunks:
        msg = "No chunks created. Check your PDFs."
        print(f"[Ingest] {msg}")
        return {
            "success": False,
            "chunks_ingested": 0,
            "documents_processed": len(pdf_paths),
            "embedding_dim": 0,
            "message": msg,
        }

    # Step 2: Embed all chunks
    t0 = time.time()
    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed(texts)
    embed_time = time.time() - t0
    embedding_dim = int(embeddings.shape[1]) if embeddings.ndim == 2 else 0
    print(f"[Ingest] Embedded {len(texts)} chunks in {embed_time:.2f}s")

    # Step 3: Store in ChromaDB
    t0 = time.time()
    vector_store.add_chunks(chunks, embeddings)
    store_time = time.time() - t0
    print(f"[Ingest] Stored chunks in {store_time:.2f}s")

    # Step 4: Rebuild BM25 index
    t0 = time.time()
    sparse.build_index()
    bm25_time = time.time() - t0
    print(f"[Ingest] Rebuilt BM25 index in {bm25_time:.2f}s")

    # Stats
    total = vector_store.count()
    print(f"\n[Ingest] Done. Total chunks in store: {total}")
    print(f"[Ingest] Timings: chunk={chunk_time:.2f}s, embed={embed_time:.2f}s, "
          f"store={store_time:.2f}s, bm25={bm25_time:.2f}s")

    return {
        "success": True,
        "chunks_ingested": len(chunks),
        "documents_processed": len(pdf_paths),
        "embedding_dim": embedding_dim,
        "message": f"Ingested {len(chunks)} chunks from {len(pdf_paths)} document(s). "
                   f"Total in store: {total}.",
    }


def query(question: str, components: Dict, config: dict = None) -> Dict:
    """Run the full ReAct + guardrails + evaluation pipeline for a question.

    Flow: input guard → orchestrator → report writer → output guard →
    MLflow logging → RAGAS evaluation.

    Args:
        question: The research question to answer.
        components: Initialised pipeline components from setup_pipeline().
        config: Pipeline config (for MLflow logging).

    Returns:
        Result dict with report, trace, guardrail results, and RAGAS scores.
    """
    orchestrator: ReActOrchestrator = components["orchestrator"]
    input_guard: InputGuard = components["input_guard"]
    output_guard: OutputGuard = components["output_guard"]
    report_writer: ReportWriter = components["report_writer"]
    ragas_eval: RAGASEvaluator = components["ragas_eval"]
    tracker: MLflowTracker = components["tracker"]

    if config is None:
        config = {}

    print(f"\n{'#'*60}")
    print(f"  Research Question: {question}")
    print(f"{'#'*60}\n")

    # ------------------------------------------------------------------
    # 1. INPUT GUARDRAIL
    # ------------------------------------------------------------------
    print("[Guardrail] Running input checks...")
    input_result = input_guard.run(question)

    if not input_result["passed"]:
        print(f"\n[BLOCKED] Input guardrail rejected the query.")
        print(f"  Reason: {input_result['blocked_reason']}")
        return {
            "report": None,
            "blocked": True,
            "blocked_reason": input_result["blocked_reason"],
            "input_guard": input_result,
        }

    print("[Guardrail] Input checks passed.")

    # 2. Use the cleaned (PII-scrubbed) query for the orchestrator
    clean_query = input_result["clean_query"]

    with tracker:
        tracker.start_run(query=question, config=config)

        # Log input guardrail outcome
        tracker.log_guardrail_input(input_result)

        # --------------------------------------------------------------
        # 3. ORCHESTRATOR (ReAct loop)
        # --------------------------------------------------------------
        t0 = time.time()
        result = orchestrator.run(query=clean_query)
        total_time = time.time() - t0

        tracker.log_agent_trace(
            steps_taken=result["steps_taken"],
            total_time=total_time,
        )

        # Extract retrieved chunks produced by the retriever step
        retrieved_chunks = result.get("retrieved_chunks", [])
        analysis = result.get("analysis") or result.get("report", "")
        critic_feedback = result.get("feedback") or ""

        # --------------------------------------------------------------
        # 4. REPORT WRITER
        # --------------------------------------------------------------
        print("\n[ReportWriter] Generating structured report...")
        report_result = report_writer.run(
            query=question,
            analysis=analysis,
            critic_feedback=critic_feedback,
            retrieved_chunks=retrieved_chunks,
        )
        report = report_result["report"]

        tracker.log_report(report)

        # --------------------------------------------------------------
        # 5. OUTPUT GUARDRAIL
        # --------------------------------------------------------------
        print("[Guardrail] Running output checks...")
        output_result = output_guard.run(report, retrieved_chunks)
        output_flagged = not output_result["passed"]
        if output_flagged:
            print(f"[WARNING] Output guardrail flagged the report.")
            print(f"  Reason: {output_result['blocked_reason']}")

        # --------------------------------------------------------------
        # 6. LOG GUARDRAIL + REPORT METADATA TO MLFLOW
        # --------------------------------------------------------------
        tracker.log_guardrail_output(output_result)
        citation_count = output_result["checks"].get("citations", {}).get(
            "citation_count", 0
        )
        tracker.log_report_metadata(
            word_count=report_result["word_count"],
            confidence_score=report_result["confidence_score"],
            citation_count=citation_count,
        )

        # --------------------------------------------------------------
        # 7. RAGAS EVALUATION (single question)
        # --------------------------------------------------------------
        print("[RAGAS] Evaluating report quality...")
        context_texts = [c["text"] for c in retrieved_chunks]
        ragas_scores = ragas_eval.evaluate_single(
            question=question,
            answer=report,
            contexts=context_texts,
            ground_truth="The document should contain relevant information about this topic.",
        )

        # 8. Log RAGAS scores
        tracker.log_ragas_scores(ragas_scores)

    # ------------------------------------------------------------------
    # 9. PRINT EVERYTHING
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  GUARDRAIL RESULTS")
    print(f"{'='*60}")
    print(f"Input guard:  PASSED")
    topic = input_result["checks"].get("topic_relevance", {})
    if "similarity" in topic:
        print(f"  Topic similarity: {topic['similarity']:.3f}")
    print(f"Output guard: {'PASSED' if output_result['passed'] else 'FLAGGED'}")
    if output_result["warnings"]:
        for w in output_result["warnings"]:
            print(f"  Warning: {w}")
    grounding = output_result["checks"].get("grounding", {})
    if "ungrounded_claims" in grounding:
        print(f"  Ungrounded claims: {len(grounding['ungrounded_claims'])}")

    print(f"\n{'='*60}")
    print("  RAGAS SCORES")
    print(f"{'='*60}")
    print(f"Faithfulness:      {ragas_scores['faithfulness']:.3f}")
    print(f"Answer relevance:  {ragas_scores['answer_relevance']:.3f}")
    print(f"Context precision: {ragas_scores['context_precision']:.3f}")

    print(f"\n{'='*60}")
    print("  FINAL REPORT")
    print(f"{'='*60}")
    print(report)
    print(f"\n[Stats] Steps: {result['steps_taken']} | "
          f"Time: {total_time:.2f}s | "
          f"Words: {report_result['word_count']} | "
          f"Confidence: {report_result['confidence_score']:.2f}")
    if output_flagged:
        print(f"\n[NOTE] This report was FLAGGED by the output guardrail "
              f"and should be reviewed.")

    return {
        "report": report,
        "blocked": False,
        "flagged": output_flagged,
        "trace": result["trace"],
        "steps_taken": result["steps_taken"],
        "retrieved_chunks": retrieved_chunks,
        "report_metadata": report_result,
        "input_guard": input_result,
        "output_guard": output_result,
        "ragas_scores": ragas_scores,
    }


def run_eval(questions: List[str], components: Dict, config: dict) -> Dict:
    """Run batch RAGAS evaluation over a set of questions (or the golden set).

    For each question the full pipeline is executed to collect an answer and
    its retrieved context, then RAGAS metrics are computed for the batch and a
    JSON report is written.

    Args:
        questions: Explicit questions to evaluate. If empty, the golden set is used.
        components: Initialised pipeline components from setup_pipeline().
        config: Pipeline configuration dict.

    Returns:
        The batch evaluation results dict from RAGASEvaluator.evaluate_batch().
    """
    orchestrator: ReActOrchestrator = components["orchestrator"]
    report_writer: ReportWriter = components["report_writer"]
    ragas_eval: RAGASEvaluator = components["ragas_eval"]
    tracker: MLflowTracker = components["tracker"]

    # Build the golden set: explicit questions or the default GOLDEN_SET
    if questions:
        golden_set = [
            {
                "question": q,
                "ground_truth": "The document should contain relevant information about this topic.",
            }
            for q in questions
        ]
    else:
        golden_set = GOLDEN_SET

    print(f"\n{'#'*60}")
    print(f"  Running evaluation over {len(golden_set)} question(s)")
    print(f"{'#'*60}\n")

    answers: List[str] = []
    contexts: List[List[str]] = []

    for i, item in enumerate(golden_set, start=1):
        q = item["question"]
        print(f"\n[Eval {i}/{len(golden_set)}] {q}")

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

    # Run batch RAGAS evaluation
    print(f"\n[Eval] Computing RAGAS metrics for the batch...")
    batch_results = ragas_eval.evaluate_batch(
        golden_set=golden_set,
        answers=answers,
        contexts=contexts,
    )

    # Save the JSON report
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "eval_report.json"
    )
    ragas_eval.generate_eval_report(batch_results, output_path=output_path)

    # Log to MLflow
    with tracker:
        tracker.start_run(query=f"eval_batch_{len(golden_set)}q", config=config)
        tracker.log_eval_batch(batch_results)

    # Print summary table
    print(f"\n{'='*72}")
    print("  EVALUATION SUMMARY")
    print(f"{'='*72}")
    print(f"{'#':<3} {'Faith.':>8} {'AnsRel.':>8} {'CtxPrec.':>9}  Question")
    print(f"{'-'*72}")
    for i, pq in enumerate(batch_results["per_question"], start=1):
        q_short = (pq.get("question", "")[:40] + "...") if len(
            pq.get("question", "")
        ) > 40 else pq.get("question", "")
        print(
            f"{i:<3} {pq['faithfulness']:>8.3f} {pq['answer_relevance']:>8.3f} "
            f"{pq['context_precision']:>9.3f}  {q_short}"
        )
    print(f"{'-'*72}")
    print(
        f"{'AVG':<3} {batch_results['mean_faithfulness']:>8.3f} "
        f"{batch_results['mean_answer_relevance']:>8.3f} "
        f"{batch_results['mean_context_precision']:>9.3f}"
    )
    print(f"{'='*72}")
    print(f"Overall: {'PASSED' if batch_results['passed'] else 'FAILED'} "
          f"(thresholds: faith>={ragas_eval.faithfulness_threshold}, "
          f"ans_rel>={ragas_eval.answer_relevance_threshold}, "
          f"ctx_prec>={ragas_eval.context_precision_threshold})")
    print(f"Report saved to: {output_path}")

    return batch_results


def main() -> None:
    """Parse CLI arguments and run the appropriate pipeline command."""
    parser = argparse.ArgumentParser(
        description="AI Research Analyst — multi-agent PDF analysis pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingest PDF documents into the vector store"
    )
    ingest_parser.add_argument(
        "--pdfs", nargs="+", required=True,
        help="Paths to PDF files to ingest"
    )

    # Query command
    query_parser = subparsers.add_parser(
        "query", help="Ask a research question"
    )
    query_parser.add_argument(
        "--question", type=str, required=True,
        help="The research question to answer"
    )

    # Eval command
    eval_parser = subparsers.add_parser(
        "eval", help="Run RAGAS evaluation over questions or the golden set"
    )
    eval_parser.add_argument(
        "--questions", nargs="+", default=None,
        help="Questions to evaluate. Omit to use the built-in golden set."
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Load config and set up
    config = load_config()
    components = setup_pipeline(config)

    if args.command == "ingest":
        ingest(pdf_paths=args.pdfs, components=components, config=config)

    elif args.command == "query":
        query(
            question=args.question,
            components=components,
            config=config,
        )

    elif args.command == "eval":
        run_eval(
            questions=args.questions or [],
            components=components,
            config=config,
        )


if __name__ == "__main__":
    main()
