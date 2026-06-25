"""Sparse retrieval using BM25 (Okapi) over the full document corpus."""

from typing import List, Dict

import numpy as np
from rank_bm25 import BM25Okapi

from ingestion.vector_store import VectorStore


class SparseRetriever:
    """BM25-based sparse retrieval over all chunks stored in the vector store."""

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialise with a reference to the vector store (used to fetch corpus).

        Args:
            vector_store: The ChromaDB-backed VectorStore instance.
        """
        self.vector_store = vector_store
        self.bm25: BM25Okapi | None = None
        self.all_chunks: List[Dict] = []
        self.tokenized_corpus: List[List[str]] = []

    def build_index(self) -> None:
        """Fetch all chunks from the vector store and build the BM25 index.

        Tokenisation is simple lowercase whitespace splitting.
        """
        self.all_chunks = self.vector_store.get_all_chunks()
        self.tokenized_corpus = [
            chunk["text"].lower().split() for chunk in self.all_chunks
        ]

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        else:
            self.bm25 = None

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict]:
        """Score all chunks against the query with BM25 and return top-k.

        Args:
            query: The search query string.
            top_k: Number of results to return.

        Returns:
            List of chunk dicts with an added bm25_score field, sorted descending.
        """
        if self.bm25 is None or not self.all_chunks:
            return []

        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)

        # Get indices of top-k scores
        top_indices = np.argsort(scores)[::-1][:top_k]

        results: List[Dict] = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include chunks with nonzero relevance
                chunk = self.all_chunks[idx].copy()
                chunk["bm25_score"] = float(scores[idx])
                results.append(chunk)

        return results
