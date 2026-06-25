# AI Research Analyst

> A local-first, multi-agent RAG system that reads your PDFs and writes cited, evaluated research reports — with guardrails and RAGAS scoring on every query.

---

## Architecture

```
Multi-agent ReAct system: Orchestrator → [RetrieverAgent | AnalystAgent | CriticAgent] → ReportWriter
RAG pipeline: PDF → sentence-aware chunking → dense (all-MiniLM) + sparse (BM25) → RRF merge → cross-encoder reranker
Guardrails: input (injection detection, PII, topic relevance) + output (citation grounding, toxicity)
Eval: RAGAS (faithfulness, answer relevance, context precision) logged to MLflow per run
```

**Request flow for a query:**

```
question
   │
   ▼
InputGuard ──► (injection → PII → topic relevance)  ──► blocked? return reason
   │ clean_query
   ▼
ReActOrchestrator ──► RetrieverAgent ──► AnalystAgent ──► CriticAgent  (Thought/Action/Observation loop)
   │ analysis + retrieved_chunks
   ▼
ReportWriter ──► structured report w/ inline [Source: file, Page: N] citations + confidence score
   │ report
   ▼
OutputGuard ──► (citation grounding cosine check → toxicity → has-citations)  ──► hard-block or soft-warn
   │
   ▼
RAGAS (per-query) ──► faithfulness / answer relevance / context precision ──► MLflow
```

---

## Setup (3 commands)

```bash
git clone <your-repo-url> && cd research_analyst
pip install -r requirements.txt
ollama pull mistral
```

> Requires [Ollama](https://ollama.com) running locally (`ollama serve`) for all LLM calls.

---

## Quick Start

```bash
python demo.py
```

The demo downloads two ArXiv papers (the Transformer and RAG papers), ingests
them, runs five research questions end-to-end with full ReAct traces, guardrail
results, and RAGAS scores, then prints a batch-evaluation summary table.

---

## CLI Usage

```bash
# Ingest one or more PDFs into the vector store
python main.py ingest --pdfs paper1.pdf paper2.pdf

# Ask a research question (full guardrails + RAGAS + MLflow)
python main.py query --question "What is attention?"

# Run a batch RAGAS evaluation (omit --questions to use the golden set)
python main.py eval
python main.py eval --questions "What problem does this address?" "What are the limitations?"
```

---

## API Usage

```bash
uvicorn serve.api:app --reload --port 8000
```

Interactive docs are served at `http://localhost:8000/docs`.

**Health**

```bash
curl http://localhost:8000/health
```

**Ingest server-side PDFs**

```bash
curl -X POST http://localhost:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"pdf_paths": ["sample_pdfs/rag_paper.pdf"]}'
```

**Upload a PDF (multipart) and ingest it**

```bash
curl -X POST http://localhost:8000/ingest/upload \
  -F "file=@/path/to/paper.pdf"
```

**Query**

```bash
curl -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is attention?", "include_trace": true, "include_eval": true}'
```

**Evaluate**

```bash
curl -X POST http://localhost:8000/eval \
  -H 'Content-Type: application/json' \
  -d '{"questions": ["What are the key results?", "What are the limitations?"]}'
```

| Method | Path              | Purpose                                        |
| ------ | ----------------- | ---------------------------------------------- |
| GET    | `/health`         | Liveness + vector store count + model name     |
| POST   | `/ingest`         | Ingest PDFs already present on the server disk  |
| POST   | `/ingest/upload`  | Upload a PDF (multipart) then ingest it        |
| POST   | `/query`          | Full pipeline: guards → ReAct → report → RAGAS |
| POST   | `/eval`           | Batch RAGAS evaluation, saves a JSON report    |
| GET    | `/trace/{run_id}` | Placeholder pointer to the MLflow UI           |

---

## Docker

```bash
docker compose up --build
```

This starts three services:

- **api** — the FastAPI app on `http://localhost:8000`
- **ollama** — the LLM runtime on `http://localhost:11434`
- **mlflow** — the MLflow tracking UI on `http://localhost:5000`

> **First run:** the `ollama` image starts without any models. Pull `mistral`
> once (this may take a few minutes):
>
> ```bash
> docker compose exec ollama ollama pull mistral
> ```

The `OLLAMA_BASE_URL=http://ollama:11434` environment variable in
`docker-compose.yml` overrides the config so the API talks to the Ollama
container instead of `localhost`.

---

## Design Decisions

- **Why custom ReAct over LangGraph** — Full control over the state machine,
  easier to debug and explain in interviews, and no hidden abstractions. Every
  Thought/Action/Observation is plain Python we can inspect and log.

- **Why hybrid retrieval** — Dense retrieval misses exact keyword matches; BM25
  misses semantic similarity. Reciprocal Rank Fusion (RRF) of both gets the best
  of each without tuning a brittle weighted sum.

- **Why a cross-encoder reranker** — Bi-encoder (dense) retrieval is fast but
  approximate. A cross-encoder scores query–chunk pairs jointly, giving much
  higher precision for the top-N selection — worth the latency for research
  quality.

- **Why RAGAS per-query** — Catching faithfulness regressions per-query (not just
  in batch eval) lets us flag bad outputs before they reach the user. MLflow
  tracking makes regressions visible across experiments and over time.

- **Guardrails design** — The input guard fails fast (injection → PII → topic) so
  expensive LLM calls are never made on invalid input. Output citation grounding
  is a lightweight cosine check, not another LLM call — keeping latency down
  while still catching ungrounded claims.

---

## What I Would Add With More Time

- Streaming ReAct trace via SSE (Server-Sent Events) in the API
- Async ingestion worker with a job queue (SQS / Redis)
- Fine-tuned cross-encoder on domain-specific query–chunk pairs
- Pinecone/Weaviate swap for a production vector store
- LLM-as-judge scoring in addition to RAGAS

---

## Project Structure

```
research_analyst/
├── ingestion/
│   ├── chunker.py            # sentence-aware PDF chunking (PyMuPDF)
│   ├── embedder.py           # SentenceTransformer wrapper (all-MiniLM)
│   └── vector_store.py       # ChromaDB persistent store (cosine)
├── retrieval/
│   ├── dense.py              # dense vector retrieval
│   ├── sparse.py             # BM25 sparse retrieval
│   └── reranker.py           # RRF merge + cross-encoder rerank
├── agents/
│   ├── orchestrator.py       # pure-Python ReAct loop
│   ├── retriever_agent.py    # retrieve + format context
│   ├── analyst_agent.py      # analyse context, cite sources
│   ├── critic_agent.py       # verify analysis, give feedback
│   └── report_writer.py      # structured report + confidence score
├── guardrails/
│   ├── input_guard.py        # injection / PII / topic relevance
│   └── output_guard.py       # grounding / toxicity / citations
├── eval/
│   ├── ragas_eval.py         # RAGAS metrics via local Ollama + HF embeddings
│   └── golden_set.py         # 12 generic research questions
├── serve/
│   ├── api.py                # FastAPI app (lifespan, CORS, endpoints)
│   ├── schemas.py            # Pydantic v2 request/response models
│   └── middleware.py         # request timing + upload size limit
├── tests/
│   ├── test_guardrails.py
│   └── test_eval.py
├── configs/config.yaml       # all pipeline + serve + paths settings
├── mlflow_tracker.py         # MLflow logging helpers
├── main.py                   # CLI: ingest / query / eval
├── demo.py                   # one-command live demo
├── Dockerfile                # multi-stage build
├── docker-compose.yml        # api + ollama + mlflow
├── .dockerignore
├── requirements.txt
└── .github/workflows/eval_ci.yml
```

