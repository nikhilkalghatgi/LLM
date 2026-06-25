"""CLI entry point for the AI Research Analyst pipeline.

Usage:
    python main.py ingest --pdfs paper1.pdf paper2.pdf
    python main.py query --question "What are the key findings on X?"
"""

import sys
import os
import time
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

    print("[Setup] Initialising ReAct orchestrator..i"
          ".")
    orchestrator = ReActOrchestrator(config=config, reranker=reranker)

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
        "tracker": tracker,
    }


def ingest(pdf_paths: List[str], components: Dict, config: dict) -> None:
    """Full ingestion pipeline: chunk → embed → store → rebuild sparse index.

    Args:
        pdf_paths: List of paths to PDF files to ingest.
        components: Initialised pipeline components from setup_pipeline().
        config: Pipeline configuration dict.
    """
    embedder: Embedder = components["embedder"]
    vector_store: VectorStore = components["vector_store"]
    sparse: SparseRetriever = components["sparse"]

    # Validate paths
    for path in pdf_paths:
        if not os.path.exists(path):
            print(f"[Ingest] ERROR: File not found: {path}")
            return

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
        print("[Ingest] No chunks created. Check your PDFs.")
        return

    # Step 2: Embed all chunks
    t0 = time.time()
    texts = [c["text"] for c in chunks]
    embeddings = embedder.embed(texts)
    embed_time = time.time() - t0
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


def query(question: str, components: Dict, config: dict = None) -> Dict:
    """Run the full ReAct pipeline for a research question.

    Args:
        question: The research question to answer.
        components: Initialised pipeline components from setup_pipeline().
        config: Pipeline config (for MLflow logging).

    Returns:
        Result dict with report, trace, and steps_taken.
    """
    orchestrator: ReActOrchestrator = components["orchestrator"]
    tracker: MLflowTracker = components["tracker"]

    if config is None:
        config = {}

    print(f"\n{'#'*60}")
    print(f"  Research Question: {question}")
    print(f"{'#'*60}\n")

    with tracker:
        tracker.start_run(query=question, config=config)

        t0 = time.time()
        result = orchestrator.run(query=question)
        total_time = time.time() - t0

        tracker.log_agent_trace(
            steps_taken=result["steps_taken"],
            total_time=total_time,
        )
        tracker.log_report(result["report"])

    # Print final report
    print(f"\n{'='*60}")
    print("  FINAL REPORT")
    print(f"{'='*60}")
    print(result["report"])
    print(f"\n[Stats] Steps: {result['steps_taken']} | "
          f"Time: {total_time:.2f}s")

    return result


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


if __name__ == "__main__":
    main()
