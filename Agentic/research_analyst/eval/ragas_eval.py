"""RAGAS evaluator — faithfulness, answer relevance, and context precision.

Wraps the RAGAS evaluation library to measure RAG pipeline quality using
locally-hosted Ollama LLM and sentence-transformer embeddings. Supports
single-query and batch evaluation modes.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

try:
    from datasets import Dataset
except ImportError:
    Dataset = None

try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision
except ImportError:
    ragas_evaluate = None
    faithfulness = None
    answer_relevancy = None
    context_precision = None

try:
    from ragas.llms import LangchainLLMWrapper
    from langchain_community.llms import Ollama as LangchainOllama
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from langchain_community.embeddings import HuggingFaceEmbeddings
except ImportError:
    LangchainLLMWrapper = None
    LangchainOllama = None
    LangchainEmbeddingsWrapper = None
    HuggingFaceEmbeddings = None


class RAGASEvaluator:
    """Evaluates RAG pipeline quality using RAGAS metrics.

    Configured to use a local Ollama LLM and HuggingFace sentence-transformer
    embeddings, matching the pipeline's existing inference stack.

    Args:
        config: Full pipeline configuration dict.
    """

    def __init__(self, config: dict) -> None:
        self.config = config
        self.eval_config = config.get("eval", {})

        self.faithfulness_threshold = self.eval_config.get(
            "faithfulness_threshold", 0.70
        )
        self.answer_relevance_threshold = self.eval_config.get(
            "answer_relevance_threshold", 0.65
        )
        self.context_precision_threshold = self.eval_config.get(
            "context_precision_threshold", 0.60
        )

        # Configure RAGAS LLM and embeddings wrappers
        self.ragas_llm = None
        self.ragas_embeddings = None
        self._setup_ragas_wrappers()

    def _setup_ragas_wrappers(self) -> None:
        """Initialise Langchain-compatible LLM and embedding wrappers for RAGAS."""
        if LangchainLLMWrapper is None or LangchainOllama is None:
            print(
                "[RAGASEvaluator] WARNING: langchain/ragas wrappers not available. "
                "Install langchain-community and ragas."
            )
            return

        try:
            llm_model = self.eval_config.get(
                "ragas_llm_model", self.config.get("llm_model", "mistral")
            )
            llm_base_url = self.config.get("llm_base_url", "http://localhost:11434")
            embedding_model = self.eval_config.get(
                "ragas_embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
            )

            self.ragas_llm = LangchainLLMWrapper(
                LangchainOllama(model=llm_model, base_url=llm_base_url)
            )
            self.ragas_embeddings = LangchainEmbeddingsWrapper(
                HuggingFaceEmbeddings(model_name=embedding_model)
            )
        except Exception as e:
            print(f"[RAGASEvaluator] WARNING: Failed to init wrappers: {e}")

    def _build_ragas_dataset(
        self,
        questions: List[str],
        answers: List[str],
        contexts: List[List[str]],
        ground_truths: List[str],
    ) -> Optional[object]:
        """Build a HuggingFace Dataset for RAGAS evaluation.

        Args:
            questions: List of research questions.
            answers: List of generated answers/reports.
            contexts: List of lists of retrieved chunk texts (one list per question).
            ground_truths: List of reference answers.

        Returns:
            HuggingFace Dataset object, or None if datasets library is unavailable.
        """
        if Dataset is None:
            print("[RAGASEvaluator] ERROR: 'datasets' library not installed.")
            return None

        return Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })

    def evaluate_single(
        self,
        question: str,
        answer: str,
        contexts: List[str],
        ground_truth: str,
    ) -> Dict:
        """Evaluate a single question-answer pair using RAGAS metrics.

        Args:
            question: The research question.
            answer: The generated answer/report.
            contexts: List of retrieved chunk texts.
            ground_truth: Reference ground-truth answer.

        Returns:
            Dict with keys: faithfulness (float), answer_relevance (float),
            context_precision (float). Returns 0.0 for all metrics on error.
        """
        fallback = {
            "faithfulness": 0.0,
            "answer_relevance": 0.0,
            "context_precision": 0.0,
        }

        if ragas_evaluate is None or faithfulness is None:
            print("[RAGASEvaluator] RAGAS not available. Returning zero scores.")
            return fallback

        try:
            dataset = self._build_ragas_dataset(
                questions=[question],
                answers=[answer],
                contexts=[contexts],
                ground_truths=[ground_truth],
            )
            if dataset is None:
                return fallback

            # Configure metrics with local LLM and embeddings
            metrics = [faithfulness, answer_relevancy, context_precision]
            if self.ragas_llm:
                faithfulness.llm = self.ragas_llm
                answer_relevancy.llm = self.ragas_llm
                context_precision.llm = self.ragas_llm
            if self.ragas_embeddings:
                answer_relevancy.embeddings = self.ragas_embeddings

            result = ragas_evaluate(dataset, metrics=metrics)

            # Extract scores, handling NaN → 0.0
            scores = result.to_pandas().iloc[0].to_dict() if hasattr(result, 'to_pandas') else {}

            def safe_float(val):
                try:
                    f = float(val)
                    return 0.0 if np.isnan(f) else f
                except (TypeError, ValueError):
                    return 0.0

            return {
                "faithfulness": safe_float(scores.get("faithfulness", 0.0)),
                "answer_relevance": safe_float(scores.get("answer_relevancy", 0.0)),
                "context_precision": safe_float(scores.get("context_precision", 0.0)),
            }

        except Exception as e:
            print(f"[RAGASEvaluator] Evaluation error: {e}")
            return fallback

    def evaluate_batch(
        self,
        golden_set: List[Dict],
        answers: List[str],
        contexts: List[List[str]],
    ) -> Dict:
        """Evaluate a batch of question-answer pairs.

        Args:
            golden_set: List of dicts with ``question`` and ``ground_truth`` keys.
            answers: List of generated answers (one per golden set item).
            contexts: List of retrieved context lists (one per golden set item).

        Returns:
            Dict with keys:
                per_question (list[dict]) — individual scores per question.
                mean_faithfulness (float) — average faithfulness.
                mean_answer_relevance (float) — average answer relevance.
                mean_context_precision (float) — average context precision.
                passed (bool) — True if all mean scores exceed thresholds.
        """
        per_question = []

        for i, item in enumerate(golden_set):
            answer = answers[i] if i < len(answers) else ""
            ctx = contexts[i] if i < len(contexts) else []
            ground_truth = item.get("ground_truth", "")

            scores = self.evaluate_single(
                question=item["question"],
                answer=answer,
                contexts=ctx,
                ground_truth=ground_truth,
            )
            scores["question"] = item["question"]
            per_question.append(scores)

        # Compute means
        if per_question:
            mean_faithfulness = float(
                np.mean([s["faithfulness"] for s in per_question])
            )
            mean_answer_relevance = float(
                np.mean([s["answer_relevance"] for s in per_question])
            )
            mean_context_precision = float(
                np.mean([s["context_precision"] for s in per_question])
            )
        else:
            mean_faithfulness = 0.0
            mean_answer_relevance = 0.0
            mean_context_precision = 0.0

        # Check thresholds
        passed = (
            mean_faithfulness >= self.faithfulness_threshold
            and mean_answer_relevance >= self.answer_relevance_threshold
            and mean_context_precision >= self.context_precision_threshold
        )

        return {
            "per_question": per_question,
            "mean_faithfulness": mean_faithfulness,
            "mean_answer_relevance": mean_answer_relevance,
            "mean_context_precision": mean_context_precision,
            "passed": passed,
        }

    def generate_eval_report(
        self, results: Dict, output_path: str = "./eval_report.json"
    ) -> None:
        """Save evaluation results to a JSON file with a timestamp.

        Args:
            results: The evaluation results dict from evaluate_batch.
            output_path: File path for the output JSON report.
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "thresholds": {
                "faithfulness": self.faithfulness_threshold,
                "answer_relevance": self.answer_relevance_threshold,
                "context_precision": self.context_precision_threshold,
            },
            **results,
        }

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"[RAGASEvaluator] Evaluation report saved to {output_path}")
