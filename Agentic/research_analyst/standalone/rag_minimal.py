"""Standalone, self-contained RAG demo -- the retrieval core with NO API/auth/agents.

This file exists so the RAG pipeline can be understood and run on its own:
PDF -> sentence-aware chunks -> dense (MiniLM) + sparse (BM25) -> RRF -> cross-encoder
rerank -> stuff top-N into an Ollama prompt -> grounded answer with citations.

Run it:

    # 1. ingest some PDFs into a dedicated standalone collection
    python -m standalone.rag_minimal ingest --dir sample_pdfs/financial
    python -m standalone.rag_minimal ingest --pdfs a.pdf b.pdf

    # 2. ask a question (one-shot)
    python -m standalone.rag_minimal ask --question "What is the minimum CRAR?"

    # 3. or an interactive Q&A loop
    python -m standalone.rag_minimal chat

Requires Ollama running locally (``ollama serve``) with the configured model
pulled (``ollama pull mistral``). Everything else is CPU-friendly.
"""

import argparse
import glob
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ollama

from main import load_config
from ingestion.chunker import chunk_documents
from ingestion.embedder import Embedder
from ingestion.vector_store import VectorStore
from retrieval.dense import DenseRetriever
from retrieval.sparse import SparseRetriever
from retrieval.reranker import HybridReranker

COLLECTION = "standalone_rag"

ANSWER_PROMPT = """You are a financial document assistant. Answer the question \
using ONLY the context below. Cite every claim inline as [Source: filename, Page: N]. \
If the context does not contain the answer, say so plainly.

# Context
{context}

# Question
{question}

# Answer (grounded, with citations):"""


def _build(config: dict):
    """Construct the minimal RAG stack (shared by all sub-commands)."""
    embedder = Embedder(model_name=config["embedding_model"])
    store = VectorStore(
        persist_dir=config["chroma_persist_dir"], collection_name=COLLECTION
    )
    dense = DenseRetriever(vector_store=store, embedder=embedder)
    sparse = SparseRetriever(vector_store=store)
    if store.count() > 0:
        sparse.build_index()
    reranker = HybridReranker(
        dense=dense, sparse=sparse, reranker_model_name=config["reranker_model"]
    )
    return embedder, store, sparse, reranker


def cmd_ingest(args, config) -> None:
    pdfs = list(args.pdfs or [])
    if args.dir:
        pdfs += glob.glob(os.path.join(args.dir, "*.pdf"))
    if not pdfs:
        print("No PDFs given. Use --pdfs or --dir.")
        return

    embedder, store, sparse, _ = _build(config)
    print(f"[Standalone RAG] Chunking {len(pdfs)} PDF(s)...")
    chunks = chunk_documents(
        pdf_paths=pdfs,
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
    )
    if not chunks:
        print("No chunks produced.")
        return
    print(f"[Standalone RAG] Embedding {len(chunks)} chunks...")
    embeddings = embedder.embed([c["text"] for c in chunks])
    store.add_chunks(chunks, embeddings)
    sparse.build_index()
    print(f"[Standalone RAG] Done. Collection now holds {store.count()} chunks.")


def _answer(question: str, config, reranker) -> str:
    hits = reranker.retrieve_and_rerank(
        query=question,
        top_k=config["retrieval_top_k"],
        top_n=config["reranker_top_n"],
    )
    if not hits:
        return "No relevant context found. Ingest some PDFs first."
    context = "\n---\n".join(
        f"[Source: {h.get('source','?')}, Page: {h.get('page','?')}]\n{h['text']}"
        for h in hits
    )
    client = ollama.Client(host=config["llm_base_url"])
    resp = client.chat(
        model=config["llm_model"],
        messages=[{"role": "user",
                   "content": ANSWER_PROMPT.format(context=context, question=question)}],
    )
    return resp["message"]["content"]


def cmd_ask(args, config) -> None:
    _, store, _, reranker = _build(config)
    if store.count() == 0:
        print("Collection is empty. Run the 'ingest' command first.")
        return
    print("\n" + "=" * 60)
    print(f"Q: {args.question}")
    print("=" * 60)
    print(textwrap.fill(_answer(args.question, config, reranker), width=90))


def cmd_chat(args, config) -> None:
    _, store, _, reranker = _build(config)
    if store.count() == 0:
        print("Collection is empty. Run the 'ingest' command first.")
        return
    print("Standalone RAG chat. Type 'exit' to quit.\n")
    while True:
        try:
            q = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        print("\nbot > " + textwrap.fill(_answer(q, config, reranker), width=90) + "\n")


def main() -> None:
    config = load_config()
    parser = argparse.ArgumentParser(description="Standalone RAG demo.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ing = sub.add_parser("ingest", help="Ingest PDFs into the standalone collection.")
    p_ing.add_argument("--pdfs", nargs="*", help="PDF file paths.")
    p_ing.add_argument("--dir", help="Directory of PDFs to ingest.")
    p_ing.set_defaults(func=cmd_ingest)

    p_ask = sub.add_parser("ask", help="Ask a single question.")
    p_ask.add_argument("--question", required=True)
    p_ask.set_defaults(func=cmd_ask)

    p_chat = sub.add_parser("chat", help="Interactive Q&A loop.")
    p_chat.set_defaults(func=cmd_chat)

    args = parser.parse_args()
    args.func(args, config)


if __name__ == "__main__":
    main()
