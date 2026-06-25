"""Golden set — generic research questions for evaluation.

Provides a set of 12 domain-agnostic research questions suitable for evaluating
the pipeline against ANY ingested document set. Ground truths are generic
placeholders since RAGAS evaluates faithfulness against retrieved context rather
than gold-standard answers.
"""

import json
import os
from typing import Dict, List


GOLDEN_SET: List[Dict] = [
    {
        "question": "What are the main contributions of this work?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What methodology was used in the research?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What were the key results and findings?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What are the limitations acknowledged by the authors?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "How does this work compare to prior approaches?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What datasets or benchmarks were used for evaluation?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What future work do the authors suggest?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What problem does this research address?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What evaluation metrics were used?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What are the practical applications of this research?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What assumptions does the research rely on?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
    {
        "question": "What is the significance of the results?",
        "ground_truth": "The document should contain relevant information about this topic.",
    },
]


def save_golden_set(path: str) -> None:
    """Save the golden set to a JSON file.

    Args:
        path: File path to write the JSON golden set to.
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(GOLDEN_SET, f, indent=2, ensure_ascii=False)
    print(f"[GoldenSet] Saved {len(GOLDEN_SET)} questions to {path}")


def load_golden_set(path: str) -> List[Dict]:
    """Load a golden set from a JSON file.

    Args:
        path: File path to read the JSON golden set from.

    Returns:
        List of dicts with ``question`` and ``ground_truth`` keys.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"[GoldenSet] Loaded {len(data)} questions from {path}")
    return data
