"""Hybrid retrieval with Reciprocal Rank Fusion and cross-encoder reranking."""

from typing import List, Dict, Tuple
from collections import defaultdict

from sentence_transformers import CrossEncoder

from retrieval.dense import DenseRetriever
from retrieval.sparse import SparseRetriever


class HybridReranker:
    """Combines dense and sparse retrieval via RRF, then reranks with a cross-encoder."""

    def __init__(
        self,
        dense: DenseRetriever,
        sparse: SparseRetriever,
        reranker_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ) -> None:
        """Initialise with dense/sparse retrievers and load the cross-encoder.

        Args:
            dense: DenseRetriever instance.
            sparse: SparseRetriever instance.
            reranker_model_name: HuggingFace model ID for the cross-encoder reranker.
        """
        self.dense = dense
        self.sparse = sparse
        self.cross_encoder = CrossEncoder(reranker_model_name)

    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        k: int = 60,
    ) -> List[Dict]:
        """Merge dense and sparse result lists using Reciprocal Rank Fusion.

        RRF score for each result = sum over lists of 1 / (k + rank),
        where rank is 1-indexed position in each list.

        Args:
            dense_results: Ranked results from dense retrieval.
            sparse_results: Ranked results from sparse retrieval.
            k: RRF smoothing constant (default 60, per the original RRF paper).

        Returns:
            Deduplicated list of chunk dicts with rrf_score, sorted descending.
        """
        # Use chunk text as the deduplication key
        score_map: Dict[str, float] = defaultdict(float)
        chunk_map: Dict[str, Dict] = {}

        for rank, chunk in enumerate(dense_results, start=1):
            key = chunk["text"]
            score_map[key] += 1.0 / (k + rank)
            if key not in chunk_map:
                chunk_map[key] = {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                }

        for rank, chunk in enumerate(sparse_results, start=1):
            key = chunk["text"]
            score_map[key] += 1.0 / (k + rank)
            if key not in chunk_map:
                chunk_map[key] = {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "page": chunk["page"],
                    "chunk_index": chunk["chunk_index"],
                }

        # Attach RRF scores and sort descending
        fused: List[Dict] = []
        for text_key, rrf_score in score_map.items():
            chunk = chunk_map[text_key].copy()
            chunk["rrf_score"] = rrf_score
            fused.append(chunk)

        fused.sort(key=lambda x: x["rrf_score"], reverse=True)
        return fused

    def retrieve_and_rerank(
        self,
        query: str,
        top_k: int = 20,
        top_n: int = 5,
    ) -> List[Dict]:
        """Full hybrid retrieval pipeline: dense + sparse → RRF → cross-encoder rerank.

        Args:
            query: The search query string.
            top_k: Number of results to fetch from each retriever before fusion.
            top_n: Number of final results after cross-encoder reranking.

        Returns:
            List of top_n chunk dicts with cross_encoder_score, sorted descending.
        """
        # Step 1: Retrieve from both sources
        dense_results = self.dense.retrieve(query, top_k=top_k)
        sparse_results = self.sparse.retrieve(query, top_k=top_k)

        # Step 2: Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(dense_results, sparse_results)

        if not fused_results:
            return []

        # Step 3: Cross-encoder reranking on all fused candidates
        pairs: List[Tuple[str, str]] = [
            (query, chunk["text"]) for chunk in fused_results
        ]
        ce_scores = self.cross_encoder.predict(pairs)

        for i, chunk in enumerate(fused_results):
            chunk["cross_encoder_score"] = float(ce_scores[i])

        # Step 4: Sort by cross-encoder score descending, return top_n
        fused_results.sort(key=lambda x: x["cross_encoder_score"], reverse=True)
        return fused_results[:top_n]
