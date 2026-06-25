"""Output guardrail — citation grounding, toxicity, and citation-presence checks.

Validates generated reports before returning them to the user. Ensures factual
claims are grounded in retrieved source chunks, content is non-toxic, and
inline citations are present.
"""

import re
from typing import Dict, List

import numpy as np
import ollama


class OutputGuard:
    """Validates generated reports for grounding, safety, and citation quality.

    Args:
        config: Full pipeline configuration dict (guardrails sub-dict accessed internally).
        embedder: An Embedder instance with ``embed_single(text)`` method.
    """

    def __init__(self, config: dict, embedder) -> None:
        self.config = config
        self.guard_config = config.get("guardrails", {})
        self.embedder = embedder

        self.cosine_threshold = self.guard_config.get("cosine_threshold", 0.70)

        # Ollama client for toxicity detection
        self.llm_model = config.get("llm_model", "mistral")
        self.llm_base_url = config.get("llm_base_url", "http://localhost:11434")
        self.client = ollama.Client(host=self.llm_base_url)

    # ------------------------------------------------------------------
    # Private check methods
    # ------------------------------------------------------------------

    def _check_citation_grounding(
        self, report: str, retrieved_chunks: List[Dict]
    ) -> Dict:
        """Verify that factual claims in the report are grounded in source chunks.

        Splits the report into sentences, embeds each, and checks cosine
        similarity against all retrieved chunks. If >30% of substantive
        sentences are ungrounded, the check fails.

        Args:
            report: The generated report text.
            retrieved_chunks: List of chunk dicts with at least a ``text`` key.

        Returns:
            Dict with keys: passed (bool), reason (str),
            ungrounded_claims (list[str]), grounding_scores (list[float]).
        """
        # Split report into sentences
        raw_sentences = re.split(r"\. |\.\n", report)
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        # Filter to substantive sentences (>20 chars)
        substantive = [s for s in sentences if len(s) > 20]

        if not substantive:
            return {
                "passed": True,
                "reason": "No substantive sentences to check",
                "ungrounded_claims": [],
                "grounding_scores": [],
            }

        if not retrieved_chunks:
            return {
                "passed": False,
                "reason": "No retrieved chunks to ground against",
                "ungrounded_claims": substantive,
                "grounding_scores": [0.0] * len(substantive),
            }

        # Pre-embed all retrieved chunks for efficiency
        chunk_embeddings = []
        for chunk in retrieved_chunks:
            emb = self.embedder.embed_single(chunk["text"])
            emb_norm = emb / (np.linalg.norm(emb) + 1e-10)
            chunk_embeddings.append(emb_norm)

        ungrounded_claims = []
        grounding_scores = []

        for sentence in substantive:
            sent_emb = self.embedder.embed_single(sentence)
            sent_norm = sent_emb / (np.linalg.norm(sent_emb) + 1e-10)

            # Max cosine similarity across all chunks
            max_score = max(
                float(np.dot(sent_norm, chunk_emb))
                for chunk_emb in chunk_embeddings
            )

            grounding_scores.append(max_score)
            if max_score < self.cosine_threshold:
                ungrounded_claims.append(sentence)

        # Fail if >30% of checked sentences are ungrounded
        ungrounded_ratio = len(ungrounded_claims) / len(substantive)
        passed = ungrounded_ratio <= 0.30

        reason = (
            f"{len(ungrounded_claims)}/{len(substantive)} sentences ungrounded "
            f"({ungrounded_ratio:.0%})"
        )

        return {
            "passed": passed,
            "reason": reason,
            "ungrounded_claims": ungrounded_claims,
            "grounding_scores": grounding_scores,
        }

    def _check_toxicity(self, report: str) -> Dict:
        """Check report for harmful, offensive, or dangerous content via LLM.

        Args:
            report: The generated report text (first 1000 chars are sent).

        Returns:
            Dict with keys: passed (bool), reason (str).
        """
        try:
            prompt = (
                "Does the following text contain harmful, offensive, "
                "discriminatory, or dangerous content? Answer only YES or NO.\n"
                f"Text: {report[:1000]}"
            )
            response = self.client.chat(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            answer = response["message"]["content"].strip().upper()

            if "YES" in answer:
                return {
                    "passed": False,
                    "reason": "Toxic or harmful content detected in report",
                }
        except Exception:
            # Fail open on LLM errors
            pass

        return {"passed": True, "reason": "No toxic content detected"}

    def _check_has_citations(self, report: str) -> Dict:
        """Verify the report contains inline source citations.

        Looks for the ``[Source: ...]`` citation pattern.

        Args:
            report: The generated report text.

        Returns:
            Dict with keys: passed (bool), reason (str), citation_count (int).
        """
        citations = re.findall(r"\[Source:.*?\]", report)
        citation_count = len(citations)

        if citation_count == 0:
            return {
                "passed": False,
                "reason": "Report contains no citations",
                "citation_count": 0,
            }

        return {
            "passed": True,
            "reason": f"Found {citation_count} citation(s)",
            "citation_count": citation_count,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, report: str, retrieved_chunks: List[Dict]) -> Dict:
        """Run all output guardrail checks.

        Checks run in order: toxicity (hard block) → citation grounding
        (hard block) → citation presence (soft warning only).

        Args:
            report: The generated report text.
            retrieved_chunks: List of chunk dicts used for grounding verification.

        Returns:
            Dict with keys:
                passed (bool) — True if all hard checks pass.
                checks (dict) — per-check result dicts keyed by check name.
                warnings (list[str]) — soft warning messages.
                blocked_reason (str or None) — reason for blocking, or None.
        """
        checks = {}
        warnings = []

        # 1. Toxicity check — HARD block
        toxicity_result = self._check_toxicity(report)
        checks["toxicity"] = toxicity_result
        if not toxicity_result["passed"]:
            return {
                "passed": False,
                "checks": checks,
                "warnings": warnings,
                "blocked_reason": toxicity_result["reason"],
            }

        # 2. Citation grounding check — HARD block
        grounding_result = self._check_citation_grounding(report, retrieved_chunks)
        checks["grounding"] = grounding_result
        if not grounding_result["passed"]:
            return {
                "passed": False,
                "checks": checks,
                "warnings": warnings,
                "blocked_reason": grounding_result["reason"],
            }

        # 3. Citation presence check — SOFT warning only
        citation_result = self._check_has_citations(report)
        checks["citations"] = citation_result
        if not citation_result["passed"]:
            warnings.append(citation_result["reason"])

        return {
            "passed": True,
            "checks": checks,
            "warnings": warnings,
            "blocked_reason": None,
        }
