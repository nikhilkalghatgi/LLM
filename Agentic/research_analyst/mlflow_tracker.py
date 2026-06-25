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
