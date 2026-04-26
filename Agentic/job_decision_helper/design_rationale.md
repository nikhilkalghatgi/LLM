# RAG Pipeline – Design & Rationale

## Overview

This document explains the design decisions behind the RAG (Retrieval-Augmented Generation)
pipeline for the **Job Decision Helper** project. It also discusses what alternatives would
be appropriate for different use cases.

---

## Architecture

```
data/               rag_pipeline.py            Agent (next step)
┌──────────┐      ┌──────────────────┐      ┌──────────────────┐
│ blogs/   │      │ 1. Load .md files│      │                  │
│ jobs/    │─────>│ 2. Chunk (700t)  │      │  retrieve_docs() │
│ github/  │      │ 3. Embed (OpenAI)│─────>│  → top-k chunks  │
└──────────┘      │ 4. FAISS index   │      │                  │
                  │ 5. Persist       │      └──────────────────┘
                  └──────────────────┘
```

---

## Component Decisions

### 1. Embedding Model — `text-embedding-3-small`

**Why we chose it:**
- Cost-effective: ~$0.02 per 1M tokens (our dataset is tiny — ~200K tokens total)
- 1536-dimension vectors — good balance of quality and index size
- From the same OpenAI ecosystem, so one API key covers embeddings + LLM later

**What we'd use for other cases:**
| Scenario | Better Choice | Why |
|----------|--------------|-----|
| Large-scale production (millions of docs) | `text-embedding-3-large` | Higher recall at scale, worth the 6x cost |
| Fully offline / privacy-critical | `sentence-transformers/all-MiniLM-L6-v2` | Runs locally, no API calls, fast |
| Multilingual corpus | `intfloat/multilingual-e5-large` | Trained on 100+ languages |
| Code-heavy retrieval | `voyage-code-3` or `nomic-embed-text` | Optimized for code semantics |
| Budget = $0 | `nomic-embed-text` via Ollama | Free, local, decent quality |

---

### 2. Vector Store — `FAISS` (Facebook AI Similarity Search)

**Why we chose it:**
- Zero infrastructure — it's a library, not a service. `pip install faiss-cpu` and done
- Extremely fast for datasets under 100K vectors (we have ~300-500 chunks)
- Supports persistence to disk — save/load the index without re-embedding
- Well-documented, battle-tested in production at Meta

**What we'd use for other cases:**
| Scenario | Better Choice | Why |
|----------|--------------|-----|
| Multi-user web app | **Pinecone** or **Weaviate** | Managed service, concurrent access, filtering |
| Need metadata filtering (e.g., "only jobs posted in 2025") | **ChromaDB** or **Qdrant** | Native metadata filters, FAISS doesn't have this |
| Millions of vectors + real-time updates | **Milvus** or **Pinecone** | Built for scale, handles CRUD operations |
| Fully local + metadata filters | **ChromaDB** | Local SQLite backend + vector search |
| Already using PostgreSQL | **pgvector** | No new infra, queries alongside relational data |

---

### 3. Chunking — Recursive Character Splitting (700 tokens, 100 overlap)

**Why we chose it:**
- 700 tokens sits in the 500-800 sweet spot from our plan — large enough for context,
  small enough for precise retrieval
- 100-token overlap ensures we don't lose context at chunk boundaries (e.g., a job
  requirement split across two chunks)
- We use `tiktoken` with `cl100k_base` encoding — this is the exact tokenizer
  used by `text-embedding-3-small`, so "700 tokens" means exactly 700 tokens to the model

**What we'd use for other cases:**
| Scenario | Better Choice | Why |
|----------|--------------|-----|
| Structured docs (code, markdown with headers) | **Markdown/Code-aware splitter** | Splits at heading/function boundaries, preserves structure |
| Long legal/research docs | **Semantic chunking** (sentence-transformers) | Groups semantically similar paragraphs, avoids arbitrary cuts |
| Conversational data | **Smaller chunks (200-300 tokens)** | Conversations are short — big chunks dilute signal |
| Tables, PDFs with layout | **Unstructured.io** or **LlamaParse** | Handles complex document layouts |

---

### 4. Retrieval — Cosine Similarity (Top-K)

**Why we chose it:**
- FAISS `IndexFlatIP` with normalized vectors = exact cosine similarity
- For ~500 chunks, brute-force search is instant (<1ms) — no need for approximate methods
- Simple, deterministic, easy to debug

**What we'd use for other cases:**
| Scenario | Better Choice | Why |
|----------|--------------|-----|
| Millions of vectors | **HNSW index** (FAISS or Qdrant) | Approximate NN — trades tiny accuracy for 100x speed |
| Keyword-heavy queries ("YOLO v8 PyTorch") | **Hybrid search** (BM25 + vector) | BM25 catches exact matches that embeddings may miss |
| Multi-step reasoning | **Re-ranking** (Cohere Rerank, cross-encoder) | Retrieve 20, re-rank to top 5 — much higher precision |
| Diverse results needed | **MMR** (Maximal Marginal Relevance) | Reduces redundancy in retrieved chunks |

---

### 5. Metadata Strategy

Each chunk carries:
- `source_type`: "blog", "job", or "github" — allows the agent to weigh sources differently
- `filename`: trace back to the original file
- `title`: extracted from the first line of each document
- `chunk_index`: position within the document

This metadata enables the agent to say things like "According to the JPMorgan job listing..."
rather than giving unattributed answers.

---

## What This Pipeline Does NOT Do (and Why)

| Feature | Why Not (for now) | When to Add |
|---------|-------------------|-------------|
| Re-ranking | Overkill for ~500 chunks, adds latency + cost | If retrieval quality drops at scale |
| Hybrid search (BM25) | Pure semantic search is sufficient for our natural-language queries | If users search with exact skill names often |
| Document summaries | Our chunks are small enough that summaries add little value | If documents exceed 10K tokens each |
| Query expansion | Simple queries work well with good embeddings | If recall is low on complex queries |
| Caching | Few users, no repeated queries | If deployed as a web app |

---

## File Structure After Implementation

```
job_decision_helper/
├── Plan.docx                    # Original project plan
├── design_rationale.md          # This file
├── rag_pipeline.py              # RAG pipeline implementation
├── requirements.txt             # Python dependencies
├── vectorstore/                 # Persisted FAISS index (auto-generated)
│   ├── index.faiss
│   └── metadata.json
└── data/
    ├── blogs/    (11 files)
    ├── jobs/     (8 files)
    └── github/   (5 files)
```
