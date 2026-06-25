"""Dense retrieval via embedding similarity against ChromaDB."""

from typing import List, Dict

from ingestion.embedder import Embedder
from ingestion.vector_store import VectorStore


class DenseRetriever:
    """Retrieve chunks using dense (embedding-based) similarity search."""

    def __init__(self, vector_store: VectorStore, embedder: Embedder) -> None:
        """Initialise with a vector store and an embedder.

        Args:
            vector_store: The ChromaDB-backed VectorStore instance.
            embedder: The Embedder instance for encoding queries.
        """
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 20) -> List[Dict]:
        """Embed the query and retrieve the top-k most similar chunks.

        Args:
            query: The search query string.
            top_k: Number of results to return.

        Returns:
            List of chunk dicts, each containing text, source, page,
            chunk_index, and score (cosine distance).
        """
        query_embedding = self.embedder.embed_single(query)
        results = self.vector_store.query(query_embedding, top_k=top_k)
        return results
