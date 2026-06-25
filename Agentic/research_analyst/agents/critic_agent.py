"""Critic sub-agent — validates analysis accuracy against source context."""

import re
from typing import Dict, Optional

import ollama


class CriticAgent:
    """Reviews an analysis for factual accuracy and source support."""

    def __init__(self, config: dict) -> None:
        self.model = config.get("llm_model", "mistral")
        self.base_url = config.get("llm_base_url", "http://localhost:11434")
        self.client = ollama.Client(host=self.base_url)

    def run(self, query: str, analysis: str, context: str) -> Dict:
        """Critique an analysis against the original context.

        Args:
            query: The original research question.
            analysis: The analyst's draft analysis.
            context: The retrieved context used for the analysis.

        Returns:
            Dict with keys:
                passed — True if the analysis is accurate
                feedback — specific issues or "looks good"
                revised_analysis — corrected analysis if FAIL, else None
        """
        prompt = (
            "You are a research critic. Your job is to verify whether the "
            "analysis below accurately reflects the provided context.\n\n"
            "Check that:\n"
            "1. All claims are supported by the context.\n"
            "2. Citations are correct and present.\n"
            "3. No information is fabricated.\n\n"
            f"Original Query: {query}\n\n"
            f"Context:\n{context}\n\n"
            f"Analysis to Review:\n{analysis}\n\n"
            "Respond in EXACTLY this format:\n"
            "Verdict: PASS or FAIL\n"
            "Feedback: <specific issues or 'looks good'>\n"
            "Revised: <if FAIL, provide the corrected analysis here; if PASS, write None>\n"
        )

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response["message"]["content"]

        # Parse verdict
        verdict_match = re.search(r"Verdict:\s*(PASS|FAIL)", raw, re.IGNORECASE)
        passed = True
        if verdict_match:
            passed = verdict_match.group(1).strip().upper() == "PASS"

        # Parse feedback
        feedback_match = re.search(
            r"Feedback:\s*(.+?)(?=\nRevised:|\Z)", raw, re.DOTALL
        )
        feedback = feedback_match.group(1).strip() if feedback_match else raw

        # Parse revised analysis
        revised_analysis: Optional[str] = None
        if not passed:
            revised_match = re.search(r"Revised:\s*(.+)", raw, re.DOTALL)
            if revised_match:
                revised_text = revised_match.group(1).strip()
                if revised_text.lower() != "none":
                    revised_analysis = revised_text

        return {
            "passed": passed,
            "feedback": feedback,
            "revised_analysis": revised_analysis,
        }
