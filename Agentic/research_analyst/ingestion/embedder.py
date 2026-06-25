"""Embedding wrapper around SentenceTransformers."""

from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    """Thin wrapper over a SentenceTransformer model for text embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialise the embedding model.

        Args:
            model_name: HuggingFace model identifier for sentence-transformers.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            np.ndarray of shape (N, dim) where dim is the embedding dimension.
        """
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        return embeddings

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text string.

        Args:
            text: The text to embed.

        Returns:
            np.ndarray of shape (dim,).
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
