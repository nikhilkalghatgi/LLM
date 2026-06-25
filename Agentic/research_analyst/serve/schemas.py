"""Pydantic v2 request/response schemas for the AI Research Analyst API."""

from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
class IngestRequest(BaseModel):
    """Request body for ingesting PDFs that already exist on the server disk."""

    pdf_paths: List[str] = Field(
        ..., description="Absolute or relative paths to PDF files on the server."
    )
    description: Optional[str] = Field(
        default=None, description="Optional human description of the document set."
    )


class IngestResponse(BaseModel):
    """Result of an ingestion request."""

    success: bool
    chunks_ingested: int
    documents_processed: int
    embedding_dim: int
    message: str


class UploadResponse(BaseModel):
    """Result of a multipart file upload + ingestion."""

    success: bool
    filename: str
    saved_path: str
    message: str


# ---------------------------------------------------------------------------
# Query
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    """Request body for a research question."""

    question: str = Field(..., description="The research question to answer.")
    include_trace: bool = Field(
        default=False, description="Include the full ReAct trace in the response."
    )
    include_eval: bool = Field(
        default=True, description="Run RAGAS evaluation on the final report."
    )


class QueryResponse(BaseModel):
    """Full result of a research query, including guardrails and evaluation."""

    success: bool
    question: str
    report: str
    confidence_score: float
    word_count: int
    steps_taken: int
    guardrail_passed: bool
    guardrail_blocked_reason: Optional[str] = None
    output_guard_passed: bool
    output_guard_warnings: List[str] = Field(default_factory=list)
    ragas_scores: Optional[dict] = None
    trace: Optional[List[dict]] = None
    citations: List[str] = Field(default_factory=list)
    processing_time_seconds: float


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """Service health and basic configuration info."""

    status: str
    vector_store_count: int
    model: str
    version: str = "1.0.0"


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------
class EvalRequest(BaseModel):
    """Request body for a batch RAGAS evaluation run."""

    questions: Optional[List[str]] = Field(
        default=None,
        description="Questions to evaluate. If omitted, the built-in golden set is used.",
    )


class EvalResponse(BaseModel):
    """Aggregated batch evaluation result."""

    success: bool
    questions_evaluated: int
    mean_faithfulness: float
    mean_answer_relevance: float
    mean_context_precision: float
    passed: bool
    report_path: str


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Standardised error payload returned on failures."""

    success: bool = False
    error: str
    detail: Optional[str] = None

