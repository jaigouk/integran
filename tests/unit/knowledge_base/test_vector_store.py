"""Tests for vector store functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.knowledge_base.vector_store import VectorStore


class TestVectorStore:
    """Test vector store functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_init_success(self, mock_sentence_transformer, mock_chromadb):
        """Test successful initialization."""
        # Mock ChromaDB
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_chromadb.Settings.return_value = Mock()

        # Mock SentenceTransformer
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        store = VectorStore(
            collection_name="test_collection",
            persist_directory=str(self.test_dir),
            embedding_model="test-model",
        )

        assert store.collection_name == "test_collection"
        assert store.persist_directory == self.test_dir
        mock_chromadb.PersistentClient.assert_called_once()

    def test_init_chromadb_not_available(self):
        """Test initialization when ChromaDB is not available."""
        with (
            patch("src.knowledge_base.vector_store.CHROMADB_AVAILABLE", False),
            pytest.raises(ImportError, match="chromadb is required"),
        ):
            VectorStore()

    def test_init_sentence_transformers_not_available(self):
        """Test initialization when sentence-transformers is not available."""
        with (
            patch(
                "src.knowledge_base.vector_store.SENTENCE_TRANSFORMERS_AVAILABLE", False
            ),
            pytest.raises(ImportError, match="sentence-transformers is required"),
        ):
            VectorStore()

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_embed_text(self, mock_sentence_transformer, mock_chromadb):
        """Test text embedding functionality."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = Mock()
        mock_model.encode.return_value.tolist.return_value = [0.1, 0.2, 0.3]
        mock_sentence_transformer.return_value = mock_model

        self._setup_chromadb_mocks(mock_chromadb)

        store = VectorStore(persist_directory=str(self.test_dir))
        embedding = store.embed_text("test text")

        assert embedding == [0.1, 0.2, 0.3]
        mock_model.encode.assert_called_once_with(
            "test text", normalize_embeddings=True
        )

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_add_documents(self, mock_sentence_transformer, mock_chromadb):
        """Test adding documents to the vector store."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.side_effect = [
            Mock(tolist=lambda: [0.1, 0.2]),
            Mock(tolist=lambda: [0.3, 0.4]),
        ]
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)

        store = VectorStore(persist_directory=str(self.test_dir))

        texts = ["First document", "Second document"]
        metadatas = [{"source": "test1"}, {"source": "test2"}]

        ids = store.add_documents(texts, metadatas)

        assert len(ids) == 2
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[1]
        assert len(call_args["embeddings"]) == 2
        assert call_args["documents"] == texts
        assert call_args["metadatas"] == metadatas

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_add_documents_with_auto_ids(
        self, mock_sentence_transformer, mock_chromadb
    ):
        """Test adding documents with automatically generated IDs."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = Mock(tolist=lambda: [0.1, 0.2])
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)

        store = VectorStore(persist_directory=str(self.test_dir))

        texts = ["Single document"]
        ids = store.add_documents(texts)

        assert len(ids) == 1
        # Should generate UUID
        assert len(ids[0]) > 10  # UUID is longer
        mock_collection.add.assert_called_once()

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_similarity_search(self, mock_sentence_transformer, mock_chromadb):
        """Test similarity search functionality."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = Mock(tolist=lambda: [0.1, 0.2])
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)

        # Mock search results
        mock_collection.query.return_value = {
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
            "distances": [[0.1, 0.3]],
        }

        store = VectorStore(persist_directory=str(self.test_dir))

        results = store.similarity_search("test query", k=2)

        assert len(results) == 2
        assert results[0]["content"] == "Document 1"
        assert results[0]["metadata"]["source"] == "test1"
        assert results[0]["score"] == 0.9  # 1.0 - 0.1
        assert results[1]["score"] == 0.7  # 1.0 - 0.3

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_similarity_search_with_filter(
        self, mock_sentence_transformer, mock_chromadb
    ):
        """Test similarity search with metadata filter."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = Mock(tolist=lambda: [0.1, 0.2])
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)
        mock_collection.query.return_value = {
            "documents": [["Filtered document"]],
            "metadatas": [[{"source": "test"}]],
            "distances": [[0.2]],
        }

        store = VectorStore(persist_directory=str(self.test_dir))

        results = store.similarity_search("test query", k=1, where={"source": "test"})

        assert len(results) == 1
        mock_collection.query.assert_called_once()
        call_args = mock_collection.query.call_args[1]
        assert call_args["where"] == {"source": "test"}

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_similarity_search_empty_results(
        self, mock_sentence_transformer, mock_chromadb
    ):
        """Test similarity search with no results."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = Mock(tolist=lambda: [0.1, 0.2])
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        store = VectorStore(persist_directory=str(self.test_dir))

        results = store.similarity_search("test query")

        assert len(results) == 0

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_get_collection_info(self, mock_sentence_transformer, mock_chromadb):
        """Test getting collection information."""
        # Setup mocks
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)
        mock_collection.count.return_value = 100

        store = VectorStore(
            collection_name="test_collection", persist_directory=str(self.test_dir)
        )

        info = store.get_collection_info()

        assert info["name"] == "test_collection"
        assert info["count"] == 100
        assert str(self.test_dir) in info["persist_directory"]

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_delete_collection(self, mock_sentence_transformer, mock_chromadb):
        """Test deleting the collection."""
        # Setup mocks
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client
        mock_chromadb.Settings.return_value = Mock()

        store = VectorStore(persist_directory=str(self.test_dir))
        store.delete_collection()

        mock_client.delete_collection.assert_called_once()

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_update_document(self, mock_sentence_transformer, mock_chromadb):
        """Test updating a document."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = Mock(tolist=lambda: [0.5, 0.6])
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)

        store = VectorStore(persist_directory=str(self.test_dir))

        result = store.update_document("doc1", "Updated text", {"updated": True})

        assert result is True
        mock_collection.update.assert_called_once()

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_delete_documents(self, mock_sentence_transformer, mock_chromadb):
        """Test deleting documents."""
        # Setup mocks
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)

        store = VectorStore(persist_directory=str(self.test_dir))

        result = store.delete_documents(["doc1", "doc2"])

        assert result is True
        mock_collection.delete.assert_called_once_with(ids=["doc1", "doc2"])

    @patch("src.knowledge_base.vector_store.chromadb")
    @patch("src.knowledge_base.vector_store.SentenceTransformer")
    def test_search_by_metadata(self, mock_sentence_transformer, mock_chromadb):
        """Test searching by metadata."""
        # Setup mocks
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        mock_collection = self._setup_chromadb_mocks(mock_chromadb)
        mock_collection.get.return_value = {
            "documents": ["Doc1", "Doc2"],
            "metadatas": [{"type": "test"}, {"type": "test"}],
            "ids": ["id1", "id2"],
        }

        store = VectorStore(persist_directory=str(self.test_dir))

        results = store.search_by_metadata({"type": "test"}, limit=10)

        assert len(results) == 2
        assert results[0]["content"] == "Doc1"
        assert results[0]["metadata"]["type"] == "test"
        assert results[0]["id"] == "id1"

    def _setup_chromadb_mocks(self, mock_chromadb):
        """Helper to setup ChromaDB mocks."""
        mock_client = Mock()
        mock_collection = Mock()

        # Mock collection creation (not found first, then created)
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection

        mock_chromadb.PersistentClient.return_value = mock_client
        mock_chromadb.Settings.return_value = Mock()

        return mock_collection
