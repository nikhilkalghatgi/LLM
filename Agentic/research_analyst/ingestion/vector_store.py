"""ChromaDB-backed persistent vector store for research document chunks."""

from typing import List, Dict, Optional

import numpy as np
import chromadb
from chromadb.config import Settings


class VectorStore:
    """Persistent vector store using ChromaDB with cosine similarity."""

    def __init__(
        self,
        persist_dir: str = "./chroma_db",
        collection_name: str = "research_docs",
    ) -> None:
        """Initialise a persistent ChromaDB client and get-or-create the collection.

        Args:
            persist_dir: Directory path for ChromaDB persistent storage.
            collection_name: Name of the ChromaDB collection.
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name

        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: List[Dict], embeddings: np.ndarray) -> None:
        """Add document chunks and their embeddings to the collection.

        Args:
            chunks: List of chunk dicts with keys: text, source, page, chunk_index.
            embeddings: np.ndarray of shape (N, dim) matching len(chunks).
        """
        ids: List[str] = []
        documents: List[str] = []
        metadatas: List[Dict] = []
        embedding_list: List[List[float]] = []

        for i, chunk in enumerate(chunks):
            doc_id = f"{chunk['source']}_chunk_{chunk['chunk_index']}"
            ids.append(doc_id)
            documents.append(chunk["text"])
            metadatas.append({
                "source": chunk["source"],
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"],
            })
            embedding_list.append(embeddings[i].tolist())

        # ChromaDB supports batch upsert — use upsert to handle re-ingestion gracefully
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embedding_list,
        )

    def query(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
    ) -> List[Dict]:
        """Query the collection with a dense embedding vector.

        Args:
            query_embedding: np.ndarray of shape (dim,).
            top_k: Number of nearest results to return.

        Returns:
            List of dicts with keys: text, source, page, chunk_index, score.
            Score is the cosine distance (lower = more similar).
        """
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output: List[Dict] = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                output.append({
                    "text": results["documents"][0][i],
                    "source": results["metadatas"][0][i]["source"],
                    "page": results["metadatas"][0][i]["page"],
                    "chunk_index": results["metadatas"][0][i]["chunk_index"],
                    "score": results["distances"][0][i],
                })

        return output

    def get_all_texts(self) -> List[str]:
        """Return all stored chunk texts for building a BM25 corpus.

        Returns:
            List of text strings from every chunk in the collection.
        """
        all_data = self.collection.get(include=["documents"])
        return all_data["documents"] if all_data["documents"] else []

    def get_all_chunks(self) -> List[Dict]:
        """Return all stored chunks with their metadata.

        Returns:
            List of dicts with keys: text, source, page, chunk_index.
        """
        all_data = self.collection.get(include=["documents", "metadatas"])
        chunks: List[Dict] = []

        if all_data["documents"]:
            for i in range(len(all_data["documents"])):
                chunks.append({
                    "text": all_data["documents"][i],
                    "source": all_data["metadatas"][i]["source"],
                    "page": all_data["metadatas"][i]["page"],
                    "chunk_index": all_data["metadatas"][i]["chunk_index"],
                })

        return chunks

    def count(self) -> int:
        """Return the total number of chunks in the collection."""
        return self.collection.count()
