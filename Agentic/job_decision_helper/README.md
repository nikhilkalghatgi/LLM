# Agentic Job Decision Helper

An intelligent, LangGraph-powered conversational agent designed to help you make informed career choices, navigate the AI hype, and analyze industry trends. The agent organically grounds its reasoning in both your localized, internal knowledge base and live web trends.

## Features

- **Agentic ReAct Architecture**: Utilizes a `LangGraph` prebuilt ReAct agent paired with `gemini-2.5-flash` for high-speed, intelligent tool orchestration.
- **RAG Backend**: A powerful local vector store powered by `ChromaDB` and Google Gemini Embeddings (`gemini-embedding-001`) that indexes local docs, job descriptions, and markdown files.
- **Tool-Calling Ecosystem**:
    -  **RAG Retriever:** Injects embedded internal knowledge about specifics formatting/rules/roles directly into the agent.
    -  **Web Search:** Leverages the `Tavily` API for live, up-to-date queries on internet trends.
    -  **Role Analyzer:** A custom post-processing heuristic tool that dynamically extracts skills frequency distributions and salary signals from raw blobs of markdown.

##  Project Structure

```text
job_decision_helper/
├── agent.py            # Main entrypoint and LangGraph conversational CLI orchestrator
├── tools.py            # Definitions for the 3 core tools (@tool wrappers)
├── rag_pipeline.py     # ChromaDB ingestion pipeline and query backend
└── data/               # Source data directories (blogs, github, jobs)
```

##  Setup & Usage

### 1. Requirements

Make sure you have the dependencies from the main project root `pyproject.toml` installed. 

Ensure you have your root `.env` configured with the necessary keys securely:
```env
# Required for Langchain LLM & Embedding processing
GOOGLE_API_KEY="your-gemini-api-key"

# Required for the Web Search tool
TAVILY_API_KEY="your-tavily-api-key"
```

### 2. Index the Knowledge Base

Before relying on the RAG capabilities, build your initial ChromaDB vector store. This processes all `.md` files in your `data/` directories.
```bash
python rag_pipeline.py
```
*(You can force a rebuild if your data changes by running `python rag_pipeline.py --rebuild`)*

### 3. Start Chatting

Initialize the local CLI and interact natively with the agent! It holds contextual memory and will automatically decide which internal or external tools it needs to address your query.
```bash
python agent.py
```

---
*Created strictly with pure standard Python, LangChain Core, and LangGraph.*
