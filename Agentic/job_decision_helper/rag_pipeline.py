"""
RAG Pipeline for Job Decision Helper
=====================================
Indexes documents from data/blogs, data/jobs, data/github using
Google Gemini embeddings and ChromaDB for fast similarity search.

Usage:
    # Build index (first time — auto-detects if missing)
    python rag_pipeline.py

    # Force rebuild index
    python rag_pipeline.py --rebuild

    # Query the index
    python rag_pipeline.py --query "What skills are needed for an ML Engineer?"
"""

import os
import json
import argparse
import time
from pathlib import Path

import chromadb
import numpy as np
import tiktoken
from google import genai
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

# Load .env from the LLM project root (two levels up from job_decision_helper)
load_dotenv(BASE_DIR.parent.parent / ".env")

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 3072   # gemini-embedding-001 output dimension
CHUNK_SIZE = 700        # tokens
CHUNK_OVERLAP = 100     # tokens
TOP_K = 5               # default number of results

# Tiktoken encoder for consistent token counting
ENCODER = tiktoken.get_encoding("cl100k_base")

# Google GenAI client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


# ---------------------------------------------------------------------------
# 1. Document Loading
# ---------------------------------------------------------------------------

def load_documents() -> list[dict]:
    """
    Walk data/blogs, data/jobs, data/github and read every .md file.
    Returns a list of dicts: {text, source_type, filename, title}
    """
    documents = []
    source_folders = {
        "blog": DATA_DIR / "blogs",
        "job": DATA_DIR / "jobs",
        "github": DATA_DIR / "github",
    }

    for source_type, folder in source_folders.items():
        if not folder.exists():
            print(f"  ⚠  Folder not found, skipping: {folder}")
            continue

        for filepath in sorted(folder.glob("*.md")):
            text = filepath.read_text(encoding="utf-8")

            # Extract title from the first non-empty line
            title = ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped:
                    title = stripped.lstrip("#").strip()
                    if title.lower().startswith("title:"):
                        title = title[6:].strip()
                    break

            documents.append({
                "text": text,
                "source_type": source_type,
                "filename": filepath.name,
                "title": title,
            })

    print(f"  📄 Loaded {len(documents)} documents "
          f"({sum(1 for d in documents if d['source_type'] == 'blog')} blogs, "
          f"{sum(1 for d in documents if d['source_type'] == 'job')} jobs, "
          f"{sum(1 for d in documents if d['source_type'] == 'github')} github)")
    return documents


# ---------------------------------------------------------------------------
# 2. Chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into chunks of `chunk_size` tokens with `overlap` token overlap.
    Uses tiktoken for accurate token counting.
    """
    tokens = ENCODER.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text_str = ENCODER.decode(chunk_tokens)
        chunks.append(chunk_text_str)
        start += chunk_size - overlap

    return chunks


def chunk_documents(documents: list[dict]) -> list[dict]:
    """
    Chunk all documents. Each chunk inherits the document's metadata
    and gets a chunk_index.
    """
    all_chunks = []

    for doc in documents:
        text_chunks = chunk_text(doc["text"])
        for i, chunk in enumerate(text_chunks):
            all_chunks.append({
                "text": chunk,
                "source_type": doc["source_type"],
                "filename": doc["filename"],
                "title": doc["title"],
                "chunk_index": i,
            })

    print(f"  🔪 Created {len(all_chunks)} chunks from {len(documents)} documents")
    return all_chunks


# ---------------------------------------------------------------------------
# 3. Embeddings (Google Gemini)
# ---------------------------------------------------------------------------

def get_embeddings(texts: list[str], batch_size: int = 10) -> np.ndarray:
    """
    Get embeddings from Google Gemini in batches.
    Returns numpy array of shape (n_texts, EMBEDDING_DIM).

    Uses small batches + exponential backoff to handle Gemini free-tier
    rate limits (429 errors).
    """
    all_embeddings = []
    total_batches = (len(texts) - 1) // batch_size + 1
    max_retries = 8

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_num = i // batch_size + 1

        # Retry with exponential backoff on rate limit errors
        for attempt in range(max_retries):
            try:
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=batch,
                )
                break  # success
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                    wait = 2 ** (attempt + 2)  # 4, 8, 16, 32, 64, 128, 256, 512
                    print(f"    Rate limited/Quota, waiting {wait}s "
                          f"(attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    raise
        else:
            raise RuntimeError(f"Failed after {max_retries} retries on batch {batch_num}")

        batch_embeddings = [emb.values for emb in response.embeddings]
        all_embeddings.extend(batch_embeddings)

        if total_batches > 1:
            print(f"    Embedded batch {batch_num}/{total_batches} "
                  f"({len(all_embeddings)}/{len(texts)} chunks)")
            # Delay between batches to respect rate limits (Gemini is ~15 RPM)
            if batch_num < total_batches:
                time.sleep(4.5)

    return np.array(all_embeddings, dtype=np.float32)


# ---------------------------------------------------------------------------
# 4. ChromaDB Index
# ---------------------------------------------------------------------------

def build_index(chunks: list[dict]) -> chromadb.Collection:
    """
    Build a ChromaDB index from chunk embeddings.
    """
    texts = [c["text"] for c in chunks]

    embeddings = get_embeddings(texts)

    VECTORSTORE_DIR.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    
    # Delete existing if we're rebuilding
    try:
        client.delete_collection("job_decision_helper")
    except Exception:
        pass

    collection = client.create_collection(
        name="job_decision_helper",
        metadata={"hnsw:space": "cosine"}
    )

    print(f"  📐 Building Chroma index ({len(embeddings)} vectors, {EMBEDDING_DIM}d)...")
    
    ids = [f"chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source_type": c["source_type"],
            "filename": c["filename"],
            "title": c["title"],
            "chunk_index": c["chunk_index"]
        } for c in chunks
    ]
    
    collection.add(
        ids=ids,
        embeddings=embeddings.tolist(),
        documents=texts,
        metadatas=metadatas
    )

    print(f"  💾 Saved index to {VECTORSTORE_DIR}")
    return collection


def load_index() -> chromadb.Collection:
    """Load ChromaDB index from disk."""
    if not VECTORSTORE_DIR.exists() or not (VECTORSTORE_DIR / "chroma.sqlite3").exists():
        raise FileNotFoundError("No saved index found. Run with --rebuild first.")

    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))
    try:
        collection = client.get_collection("job_decision_helper")
        print(f"  📂 Loaded index from {VECTORSTORE_DIR}")
        return collection
    except Exception:
        raise FileNotFoundError("No saved index found. Run with --rebuild first.")


# ---------------------------------------------------------------------------
# 5. Retriever — Tool 1 from Plan.docx
# ---------------------------------------------------------------------------

def retrieve_docs(query: str, k: int = TOP_K,
                  collection: chromadb.Collection = None) -> list[dict]:
    """
    Retrieve the top-k most relevant chunks for a query.

    Returns a list of dicts:
        {text, source_type, filename, title, chunk_index, score}
    """
    if collection is None:
        collection = load_index()

    # Embed the query
    query_embedding = get_embeddings([query])

    # Search
    results_dict = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=k,
        include=["documents", "metadatas", "distances"]
    )

    results = []
    if results_dict["ids"] and results_dict["ids"][0]:
        for i in range(len(results_dict["ids"][0])):
            result = results_dict["metadatas"][0][i].copy()
            result["text"] = results_dict["documents"][0][i]
            # Convert cosine distance to cosine similarity
            result["score"] = 1.0 - float(results_dict["distances"][0][i])
            results.append(result)

    return results


def format_retrieved_docs(results: list[dict]) -> str:
    """
    Format retrieved chunks into a readable string.
    This is also used to inject context into the LLM prompt.
    """
    if not results:
        return "No relevant documents found."

    parts = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[{i}] ({r['source_type'].upper()}) {r['title']}\n"
            f"    Source: {r['filename']} | Chunk: {r['chunk_index']} | "
            f"Score: {r['score']:.3f}\n"
            f"    {r['text'][:500]}{'...' if len(r['text']) > 500 else ''}"
        )
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# 6. Pipeline Orchestration
# ---------------------------------------------------------------------------

def build_pipeline():
    """Full pipeline: load → chunk → embed → index → save."""
  
    documents = load_documents()

    chunks = chunk_documents(documents)

    start = time.time()
    collection = build_index(chunks)
    elapsed = time.time() - start
    print(f" Embedding + indexing took {elapsed:.1f}s")

    return collection


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="RAG Pipeline for Job Decision Helper"
    )
    parser.add_argument("--rebuild", action="store_true",
                        help="Force rebuild the ChromaDB index from scratch")
    parser.add_argument("--query", type=str, default=None,
                        help="Query the index and print results")
    parser.add_argument("-k", type=int, default=TOP_K,
                        help=f"Number of results to return (default: {TOP_K})")
    args = parser.parse_args()

    # Build or load index
    if args.rebuild or not (VECTORSTORE_DIR / "chroma.sqlite3").exists():
        collection = build_pipeline()
    else:
        collection = load_index()

    # Query mode
    if args.query:
        print(f"\n🔍 Query: {args.query}\n" + "-" * 40)
        results = retrieve_docs(args.query, k=args.k,
                                collection=collection)
        print(format_retrieved_docs(results))

    # Interactive mode (if no query and not just rebuilding)
    elif not args.rebuild:
        print("\n💬 Enter queries (type 'quit' to exit):\n")
        while True:
            try:
                query = input("Query> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if query.lower() in ("quit", "exit", "q"):
                break
            if not query:
                continue
            results = retrieve_docs(query, k=args.k,
                                    collection=collection)
            print(f"\n{format_retrieved_docs(results)}\n")


if __name__ == "__main__":
    main()
