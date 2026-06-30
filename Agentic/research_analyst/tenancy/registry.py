"""Per-tenant pipeline registry: the multi-tenancy core.

Each tenant gets its **own** ChromaDB collection (``{tenant}_documents``) so a
user in ``retail-bank`` can never retrieve a chunk ingested by ``risk-team`` --
isolation is enforced at the vector-store boundary, not just in application code.

Heavy, stateless models are loaded **once** and shared across all tenants to
keep memory sane on a laptop:

* the SentenceTransformer embedder,
* the cross-encoder reranker,
* the LLM-backed report writer / output guard / RAGAS evaluator / MLflow tracker.

Only the cheap, tenant-scoped pieces (vector store, dense/sparse retrievers,
ReAct orchestrator, input guard) are built per tenant and cached.
"""

import re
import threading
from typing import Dict

from sentence_transformers import CrossEncoder

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
from mlflow_tracker import MLflowTracker


def tenant_collection_name(tenant_id: str) -> str:
    """Return a ChromaDB-safe collection name for a tenant.

    ChromaDB requires 3-63 chars of ``[a-zA-Z0-9._-]`` starting/ending
    alphanumeric. We slugify the tenant id and suffix ``_documents``.
    """
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", tenant_id).strip("-_") or "tenant"
    return f"{slug}_documents"


class TenantRegistry:
    """Builds and caches per-tenant pipeline components, sharing heavy models."""

    def __init__(self, config: dict) -> None:
        self.config = config

        # ---- Shared, expensive, stateless models (loaded once) -------------
        print("[Registry] Loading shared embedder...")
        self.embedder = Embedder(model_name=config["embedding_model"])

        print("[Registry] Loading shared cross-encoder reranker...")
        self.cross_encoder = CrossEncoder(config["reranker_model"])

        print("[Registry] Initialising shared LLM-backed components...")
        self.output_guard = OutputGuard(config=config, embedder=self.embedder)
        self.report_writer = ReportWriter(config=config)
        self.ragas_eval = RAGASEvaluator(config=config)
        self.tracker = MLflowTracker(
            experiment_name=config.get("mlflow_experiment_name", "research_analyst")
        )

        self._tenants: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def _build_tenant(self, tenant_id: str) -> Dict:
        """Construct the per-tenant component bundle for ``tenant_id``."""
        collection = tenant_collection_name(tenant_id)
        print(f"[Registry] Building pipeline for tenant '{tenant_id}' "
              f"(collection='{collection}')")

        vector_store = VectorStore(
            persist_dir=self.config["chroma_persist_dir"],
            collection_name=collection,
        )
        dense = DenseRetriever(vector_store=vector_store, embedder=self.embedder)
        sparse = SparseRetriever(vector_store=vector_store)
        if vector_store.count() > 0:
            sparse.build_index()

        reranker = HybridReranker(
            dense=dense,
            sparse=sparse,
            reranker_model_name=self.config["reranker_model"],
            cross_encoder=self.cross_encoder,  # shared model
        )
        orchestrator = ReActOrchestrator(config=self.config, reranker=reranker)
        input_guard = InputGuard(
            config=self.config, embedder=self.embedder, vector_store=vector_store
        )

        # Mirror the shape of the legacy ``components`` dict so existing
        # ingest()/query helpers work unchanged with a tenant bundle.
        return {
            "tenant_id": tenant_id,
            "collection_name": collection,
            "embedder": self.embedder,
            "vector_store": vector_store,
            "dense": dense,
            "sparse": sparse,
            "reranker": reranker,
            "orchestrator": orchestrator,
            "input_guard": input_guard,
            "output_guard": self.output_guard,
            "report_writer": self.report_writer,
            "ragas_eval": self.ragas_eval,
            "tracker": self.tracker,
        }

    def get(self, tenant_id: str) -> Dict:
        """Return cached components for ``tenant_id``, building them on first use."""
        with self._lock:
            if tenant_id not in self._tenants:
                self._tenants[tenant_id] = self._build_tenant(tenant_id)
            return self._tenants[tenant_id]

    def warm(self, tenant_ids) -> None:
        """Eagerly build pipelines for a list of tenants (startup convenience)."""
        for tid in tenant_ids:
            self.get(tid)
