"""MLflow experiment tracker for the research analyst pipeline."""

import time
from typing import Dict, Optional

import mlflow


class MLflowTracker:
    """Tracks ingestion, retrieval, and agent metrics via MLflow."""

    def __init__(self, experiment_name: str = "research_analyst") -> None:
        """Set up the MLflow experiment.

        Args:
            experiment_name: Name of the MLflow experiment to log to.
        """
        self.experiment_name = experiment_name
        mlflow.set_experiment(experiment_name)
        self._run: Optional[mlflow.ActiveRun] = None

    def start_run(self, query: str, config: dict) -> None:
        """Start a new MLflow run and log the pipeline configuration.

        Args:
            query: The research question being processed.
            config: The full pipeline configuration dict.
        """
        self._run = mlflow.start_run()
        mlflow.log_param("query", query[:250])  # MLflow param limit
        for key, value in config.items():
            mlflow.log_param(key, value)

    def log_retrieval(self, chunks_retrieved: int, retrieval_time: float) -> None:
        """Log retrieval metrics.

        Args:
            chunks_retrieved: Number of chunks returned after reranking.
            retrieval_time: Wall-clock seconds for retrieval.
        """
        mlflow.log_metric("chunks_retrieved", chunks_retrieved)
        mlflow.log_metric("retrieval_time_seconds", retrieval_time)

    def log_agent_trace(self, steps_taken: int, total_time: float) -> None:
        """Log agent orchestration metrics.

        Args:
            steps_taken: Number of ReAct steps executed.
            total_time: Total wall-clock seconds for the full agent run.
        """
        mlflow.log_metric("react_steps_taken", steps_taken)
        mlflow.log_metric("total_time_seconds", total_time)

    def log_report(self, report: str) -> None:
        """Log the final report as an MLflow artifact.

        Args:
            report: The final analysis report text.
        """
        # Write to a temp file then log as artifact
        import tempfile, os
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, prefix="report_"
        ) as f:
            f.write(report)
            temp_path = f.name
        mlflow.log_artifact(temp_path, "reports")
        os.remove(temp_path)

    # ------------------------------------------------------------------
    # Day 2 — Guardrail logging
    # ------------------------------------------------------------------

    def log_guardrail_input(self, result: dict) -> None:
        """Log input-guardrail outcomes.

        Args:
            result: Result dict from ``InputGuard.run()``.
        """
        mlflow.log_param("input_guard_passed", bool(result.get("passed", False)))
        mlflow.log_param(
            "input_guard_blocked_reason",
            str(result.get("blocked_reason") or "none")[:250],
        )

        # Topic similarity is nested in the topic_relevance check, if it ran
        checks = result.get("checks", {})
        topic = checks.get("topic_relevance", {})
        if "similarity" in topic:
            mlflow.log_metric("topic_similarity", float(topic["similarity"]))

    def log_guardrail_output(self, result: dict) -> None:
        """Log output-guardrail outcomes.

        Args:
            result: Result dict from ``OutputGuard.run()``.
        """
        mlflow.log_param("output_guard_passed", bool(result.get("passed", False)))
        mlflow.log_metric(
            "output_guard_warnings", len(result.get("warnings", []))
        )

        # Ungrounded claim count is nested in the grounding check, if it ran
        checks = result.get("checks", {})
        grounding = checks.get("grounding", {})
        if "ungrounded_claims" in grounding:
            mlflow.log_metric(
                "ungrounded_claims_count", len(grounding["ungrounded_claims"])
            )

    # ------------------------------------------------------------------
    # Day 2 — RAGAS + report logging
    # ------------------------------------------------------------------

    def log_ragas_scores(self, scores: dict) -> None:
        """Log RAGAS metric scores as MLflow metrics.

        Args:
            scores: Dict with faithfulness, answer_relevance, context_precision.
        """
        mlflow.log_metric("ragas_faithfulness", float(scores.get("faithfulness", 0.0)))
        mlflow.log_metric(
            "ragas_answer_relevance", float(scores.get("answer_relevance", 0.0))
        )
        mlflow.log_metric(
            "ragas_context_precision", float(scores.get("context_precision", 0.0))
        )

    def log_report_metadata(
        self, word_count: int, confidence_score: float, citation_count: int
    ) -> None:
        """Log metadata about the generated report.

        Args:
            word_count: Total words in the report.
            confidence_score: Report confidence as a 0.0–1.0 float.
            citation_count: Number of inline citations in the report.
        """
        mlflow.log_metric("report_word_count", int(word_count))
        mlflow.log_metric("report_confidence_score", float(confidence_score))
        mlflow.log_metric("report_citation_count", int(citation_count))

    def log_eval_batch(self, batch_results: dict) -> None:
        """Log batch RAGAS evaluation results.

        Args:
            batch_results: Result dict from ``RAGASEvaluator.evaluate_batch()``.
        """
        mlflow.log_metric(
            "eval_mean_faithfulness",
            float(batch_results.get("mean_faithfulness", 0.0)),
        )
        mlflow.log_metric(
            "eval_mean_answer_relevance",
            float(batch_results.get("mean_answer_relevance", 0.0)),
        )
        mlflow.log_metric(
            "eval_mean_context_precision",
            float(batch_results.get("mean_context_precision", 0.0)),
        )
        mlflow.log_metric(
            "eval_num_questions", len(batch_results.get("per_question", []))
        )
        mlflow.log_param("eval_passed", bool(batch_results.get("passed", False)))

    def end_run(self) -> None:
        """End the current MLflow run."""
        if self._run:
            mlflow.end_run()
            self._run = None

    # Context manager support
    def __enter__(self) -> "MLflowTracker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_run()
        return None
