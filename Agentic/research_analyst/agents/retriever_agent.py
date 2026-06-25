"""Retriever sub-agent — fetches and formats relevant document chunks."""

from typing import Dict, List

from retrieval.reranker import HybridReranker


class RetrieverAgent:
    """Retrieves top relevant chunks via hybrid reranking and formats them as context."""

    def __init__(self, reranker: HybridReranker, config: dict) -> None:
        self.reranker = reranker
        self.top_k = config.get("retrieval_top_k", 20)
        self.top_n = config.get("reranker_top_n", 5)

    def run(self, query: str) -> Dict:
        """Retrieve and format the most relevant chunks for a query.

        Returns:
            Dict with keys:
                chunks — list of ranked chunk dicts
                formatted_context — human-readable context string with citations
        """
        chunks = self.reranker.retrieve_and_rerank(
            query=query,
            top_k=self.top_k,
            top_n=self.top_n,
        )

        formatted_parts: List[str] = []
        for chunk in chunks:
            formatted_parts.append(
                f"[Source: {chunk['source']}, Page: {chunk['page']}]\n"
                f"{chunk['text']}\n---"
            )

        formatted_context = "\n".join(formatted_parts)

        return {
            "chunks": chunks,
            "formatted_context": formatted_context,
        }
