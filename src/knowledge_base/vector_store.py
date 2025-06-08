"""Clean vector store wrapper for ChromaDB without LangChain."""

import logging
import uuid
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    chromadb = None
    Settings = None

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

logger = logging.getLogger(__name__)


class VectorStore:
    """Simple ChromaDB wrapper for vector storage and retrieval."""

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        persist_directory: str = "data/vector_store",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "chromadb is required for vector storage. "
                "Install with: pip install chromadb"
            )

        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for embeddings. "
                "Install with: pip install sentence-transformers"
            )

        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(allow_reset=True, anonymized_telemetry=False),
        )

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)

        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except Exception:
            # Create new collection with metadata filtering
            self.collection = self.client.create_collection(
                name=collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"Created new collection: {collection_name}")

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a text."""
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def add_documents(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        """Add documents to the vector store."""
        if not texts:
            return []

        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]

        # Generate embeddings
        embeddings = [self.embed_text(text) for text in texts]

        # Prepare metadata
        if metadatas is None:
            metadatas = [{} for _ in texts]

        # Add to collection
        self.collection.add(
            embeddings=embeddings, documents=texts, metadatas=metadatas, ids=ids
        )

        logger.info(f"Added {len(texts)} documents to vector store")
        return ids

    def similarity_search(
        self, query: str, k: int = 4, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar documents."""
        # Generate query embedding
        query_embedding = self.embed_text(query)

        # Search in collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                doc_data = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i]
                    if results["metadatas"]
                    else {},
                    "score": 1.0 - results["distances"][0][i]
                    if results["distances"]
                    else 0.0,
                }
                documents.append(doc_data)

        return documents

    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")

    def get_collection_info(self) -> dict[str, Any]:
        """Get information about the collection."""
        try:
            count = self.collection.count()
            return {
                "name": self.collection_name,
                "count": count,
                "persist_directory": str(self.persist_directory),
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {}

    def update_document(
        self, doc_id: str, text: str, metadata: dict[str, Any] | None = None
    ) -> bool:
        """Update a document in the vector store."""
        try:
            embedding = self.embed_text(text)

            update_data = {
                "ids": [doc_id],
                "embeddings": [embedding],
                "documents": [text],
            }

            if metadata is not None:
                update_data["metadatas"] = [metadata]

            self.collection.update(**update_data)
            logger.info(f"Updated document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False

    def delete_documents(self, ids: list[str]) -> bool:
        """Delete documents from the vector store."""
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False

    def search_by_metadata(
        self, where: dict[str, Any], limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search documents by metadata filters."""
        try:
            results = self.collection.get(
                where=where, limit=limit, include=["documents", "metadatas"]
            )

            documents = []
            if results["documents"]:
                for i, doc in enumerate(results["documents"]):
                    doc_data = {
                        "content": doc,
                        "metadata": results["metadatas"][i]
                        if results["metadatas"]
                        else {},
                        "id": results["ids"][i] if results["ids"] else None,
                    }
                    documents.append(doc_data)

            return documents
        except Exception as e:
            logger.error(f"Failed to search by metadata: {e}")
            return []
