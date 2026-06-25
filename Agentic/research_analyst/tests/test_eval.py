"""Tests for RAGAS evaluation module.

Mocks the ragas.evaluate call to test score extraction, batch mean computation,
and threshold-based pass/fail logic without requiring a running LLM.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
import pandas as pd


# ---------------------------------------------------------------------------
# Shared test configuration
# ---------------------------------------------------------------------------

def _make_test_config():
    """Build a minimal config dict for eval testing."""
    return {
        "llm_model": "mistral",
        "llm_base_url": "http://localhost:11434",
        "eval": {
            "golden_set_path": "./eval/golden_set.json",
            "faithfulness_threshold": 0.70,
            "answer_relevance_threshold": 0.65,
            "context_precision_threshold": 0.60,
            "ragas_llm_model": "mistral",
            "ragas_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        },
    }


def _make_mock_ragas_result(scores_dict):
    """Create a mock RAGAS evaluate() result object.

    Args:
        scores_dict: Dict with faithfulness, answer_relevancy, context_precision.
    """
    mock_result = MagicMock()
    df = pd.DataFrame([scores_dict])
    mock_result.to_pandas.return_value = df
    return mock_result


# ===========================================================================
# RAGAS EVALUATOR TESTS
# ===========================================================================

class TestRAGASEvaluator:
    """Tests for the RAGASEvaluator class."""

    @patch("eval.ragas_eval.LangchainLLMWrapper", None)
    @patch("eval.ragas_eval.LangchainOllama", None)
    @patch("eval.ragas_eval.LangchainEmbeddingsWrapper", None)
    @patch("eval.ragas_eval.HuggingFaceEmbeddings", None)
    @patch("eval.ragas_eval.ragas_evaluate")
    @patch("eval.ragas_eval.faithfulness")
    @patch("eval.ragas_eval.answer_relevancy")
    @patch("eval.ragas_eval.context_precision")
    def test_evaluate_single_returns_scores(
        self, mock_ctx_prec, mock_ans_rel, mock_faith, mock_ragas_eval
    ):
        """evaluate_single should return dict with expected metric keys."""
        from eval.ragas_eval import RAGASEvaluator

        # Mock ragas evaluate to return known scores
        mock_ragas_eval.return_value = _make_mock_ragas_result({
            "faithfulness": 0.85,
            "answer_relevancy": 0.78,
            "context_precision": 0.72,
        })

        config = _make_test_config()
        evaluator = RAGASEvaluator(config)

        result = evaluator.evaluate_single(
            question="What are the main findings?",
            answer="The main findings include improved accuracy.",
            contexts=["The study reports improved accuracy in classification tasks."],
            ground_truth="The document should contain relevant information.",
        )

        assert "faithfulness" in result
        assert "answer_relevance" in result
        assert "context_precision" in result
        assert isinstance(result["faithfulness"], float)
        assert isinstance(result["answer_relevance"], float)
        assert isinstance(result["context_precision"], float)
        assert result["faithfulness"] == pytest.approx(0.85)
        assert result["answer_relevance"] == pytest.approx(0.78)
        assert result["context_precision"] == pytest.approx(0.72)

    @patch("eval.ragas_eval.LangchainLLMWrapper", None)
    @patch("eval.ragas_eval.LangchainOllama", None)
    @patch("eval.ragas_eval.LangchainEmbeddingsWrapper", None)
    @patch("eval.ragas_eval.HuggingFaceEmbeddings", None)
    @patch("eval.ragas_eval.ragas_evaluate")
    @patch("eval.ragas_eval.faithfulness")
    @patch("eval.ragas_eval.answer_relevancy")
    @patch("eval.ragas_eval.context_precision")
    def test_evaluate_batch_computes_means(
        self, mock_ctx_prec, mock_ans_rel, mock_faith, mock_ragas_eval
    ):
        """evaluate_batch should correctly compute mean scores across questions."""
        from eval.ragas_eval import RAGASEvaluator

        # Different scores for each question
        scores_list = [
            {"faithfulness": 0.80, "answer_relevancy": 0.70, "context_precision": 0.60},
            {"faithfulness": 0.90, "answer_relevancy": 0.80, "context_precision": 0.70},
            {"faithfulness": 0.70, "answer_relevancy": 0.60, "context_precision": 0.80},
        ]

        call_count = {"n": 0}

        def mock_evaluate_side_effect(dataset, metrics=None):
            idx = call_count["n"]
            call_count["n"] += 1
            return _make_mock_ragas_result(scores_list[idx])

        mock_ragas_eval.side_effect = mock_evaluate_side_effect

        config = _make_test_config()
        evaluator = RAGASEvaluator(config)

        golden_set = [
            {"question": f"Question {i+1}?", "ground_truth": "Reference answer."}
            for i in range(3)
        ]
        answers = [f"Answer {i+1}" for i in range(3)]
        contexts = [["Context chunk"] for _ in range(3)]

        result = evaluator.evaluate_batch(golden_set, answers, contexts)

        assert len(result["per_question"]) == 3
        assert result["mean_faithfulness"] == pytest.approx(0.80, abs=0.01)
        assert result["mean_answer_relevance"] == pytest.approx(0.70, abs=0.01)
        assert result["mean_context_precision"] == pytest.approx(0.70, abs=0.01)

    @patch("eval.ragas_eval.LangchainLLMWrapper", None)
    @patch("eval.ragas_eval.LangchainOllama", None)
    @patch("eval.ragas_eval.LangchainEmbeddingsWrapper", None)
    @patch("eval.ragas_eval.HuggingFaceEmbeddings", None)
    @patch("eval.ragas_eval.ragas_evaluate")
    @patch("eval.ragas_eval.faithfulness")
    @patch("eval.ragas_eval.answer_relevancy")
    @patch("eval.ragas_eval.context_precision")
    def test_passed_flag_respects_thresholds(
        self, mock_ctx_prec, mock_ans_rel, mock_faith, mock_ragas_eval
    ):
        """passed should be True when all means exceed thresholds, False otherwise."""
        from eval.ragas_eval import RAGASEvaluator

        config = _make_test_config()

        # Test 1: All above threshold → passed=True
        mock_ragas_eval.return_value = _make_mock_ragas_result({
            "faithfulness": 0.90,
            "answer_relevancy": 0.85,
            "context_precision": 0.80,
        })

        evaluator = RAGASEvaluator(config)
        golden_set = [{"question": "Q?", "ground_truth": "A."}]
        result = evaluator.evaluate_batch(golden_set, ["Answer"], [["Ctx"]])
        assert result["passed"] is True

        # Test 2: One metric below threshold → passed=False
        mock_ragas_eval.return_value = _make_mock_ragas_result({
            "faithfulness": 0.50,  # Below 0.70 threshold
            "answer_relevancy": 0.85,
            "context_precision": 0.80,
        })

        evaluator2 = RAGASEvaluator(config)
        result2 = evaluator2.evaluate_batch(golden_set, ["Answer"], [["Ctx"]])
        assert result2["passed"] is False
