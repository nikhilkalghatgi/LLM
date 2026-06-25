"""Report writer agent — produces structured research reports with citations.

Generates a professional research report by synthesising the analyst's analysis,
critic feedback, and source context into a standardised format with executive
summary, key findings, detailed analysis, and confidence scoring.
"""

import re
from typing import Dict, List

import ollama


REPORT_SYSTEM_PROMPT = """You are a professional research analyst. Write a structured research report based on the provided analysis and source context. 
The report must follow this exact format:

## Executive Summary
<2-3 sentence summary of key findings>

## Key Findings
<bullet points, each ending with an inline citation like [Source: filename.pdf, Page: N]>

## Detailed Analysis
<paragraphs expanding on findings, all claims cited>

## Limitations & Confidence
<what the documents do not cover, gaps in evidence>

## Confidence Score: X/10
<brief justification>

Rules: Only use information from the provided context. Every factual claim needs a citation. Do not invent sources."""


class ReportWriter:
    """Produces structured, citation-rich research reports.

    Args:
        config: Pipeline configuration dict.
    """

    def __init__(self, config: dict) -> None:
        self.model = config.get("llm_model", "mistral")
        self.base_url = config.get("llm_base_url", "http://localhost:11434")
        self.client = ollama.Client(host=self.base_url)

    def run(
        self,
        query: str,
        analysis: str,
        critic_feedback: str,
        retrieved_chunks: List[Dict],
    ) -> Dict:
        """Generate a structured research report.

        Args:
            query: The original research question.
            analysis: The analyst agent's analysis text.
            critic_feedback: The critic agent's feedback (may be empty).
            retrieved_chunks: List of chunk dicts with ``text``, ``source``, ``page`` keys.

        Returns:
            Dict with keys:
                report (str) — the formatted research report.
                confidence_score (float) — extracted confidence as 0.0–1.0.
                word_count (int) — total word count of the report.
        """
        # Format retrieved chunks for the prompt
        formatted_chunks = []
        for chunk in retrieved_chunks:
            source = chunk.get("source", "unknown")
            page = chunk.get("page", "?")
            formatted_chunks.append(
                f"[Source: {source}, Page: {page}]\n{chunk['text']}"
            )
        chunks_text = "\n---\n".join(formatted_chunks)

        # Build user message
        user_message = (
            f"## Research Question\n{query}\n\n"
            f"## Analyst's Analysis\n{analysis}\n\n"
        )
        if critic_feedback:
            user_message += f"## Critic Feedback\n{critic_feedback}\n\n"
        user_message += f"## Source Context\n{chunks_text}"

        # Call LLM
        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            report = response["message"]["content"]
        except Exception as e:
            report = (
                f"## Report Generation Error\n\n"
                f"Failed to generate report: {e}\n\n"
                f"## Fallback: Raw Analysis\n\n{analysis}"
            )

        # Parse confidence score from "Confidence Score: X/10"
        confidence_score = 0.5  # default if parsing fails
        confidence_match = re.search(
            r"Confidence\s+Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", report
        )
        if confidence_match:
            try:
                raw_score = float(confidence_match.group(1))
                confidence_score = raw_score / 10.0
            except (ValueError, ZeroDivisionError):
                pass

        word_count = len(report.split())

        return {
            "report": report,
            "confidence_score": confidence_score,
            "word_count": word_count,
        }
