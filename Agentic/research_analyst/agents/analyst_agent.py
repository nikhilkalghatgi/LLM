"""Analyst sub-agent — generates structured analysis with inline citations."""

import re
from typing import Dict, List

import ollama


class AnalystAgent:
    """Produces a structured analysis of a query grounded in retrieved context."""

    def __init__(self, config: dict) -> None:
        self.model = config.get("llm_model", "mistral")
        self.base_url = config.get("llm_base_url", "http://localhost:11434")
        self.client = ollama.Client(host=self.base_url)

    def run(self, query: str, context: str) -> Dict:
        """Analyse the query using ONLY the provided context.

        Args:
            query: The research question.
            context: Formatted context string with source citations.

        Returns:
            Dict with keys:
                analysis — the structured analysis text
                citations — list of extracted [Source: ...] citation strings
        """
        prompt = (
            "You are a research analyst. Analyse the following query based ONLY on "
            "the provided context. Provide a detailed, structured analysis. "
            "Use inline citations in the format [Source: filename.pdf, Page: N] "
            "whenever you reference information from the context.\n\n"
            f"Query: {query}\n\n"
            f"Context:\n{context}\n\n"
            "Provide your structured analysis below. Include:\n"
            "1. Key Findings\n"
            "2. Supporting Evidence (with citations)\n"
            "3. Summary\n"
        )

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        analysis = response["message"]["content"]

        # Extract all inline citations
        citations = re.findall(r"\[Source:\s*[^\]]+\]", analysis)
        citations = list(set(citations))

        return {
            "analysis": analysis,
            "citations": citations,
        }
