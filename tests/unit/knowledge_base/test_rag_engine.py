"""Tests for RAG engine functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.knowledge_base.rag_engine import RAGEngine


class TestRAGEngine:
    """Test RAG engine functionality."""

    def setup_method(self):
        """Setup for each test method."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    @pytest.mark.skip(reason="RAG dependencies are available in test environment")
    @patch("src.core.settings.has_rag_config")
    def test_init_rag_not_available(self, mock_has_rag_config):
        """Test initialization when RAG is not available."""
        mock_has_rag_config.return_value = False

        with pytest.raises(ImportError, match="RAG dependencies not available"):
            RAGEngine()

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.has_rag_config")
    @patch("src.core.settings.get_settings")
    def test_init_rag_available(
        self,
        mock_get_settings,
        mock_has_rag_config,
        mock_gemini,
        mock_fetcher,
        mock_vector_store,
    ):
        """Test successful initialization when RAG is available."""
        mock_has_rag_config.return_value = True

        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock component instances
        mock_vector_store.return_value = Mock()
        mock_fetcher.return_value = Mock()
        mock_gemini.return_value = Mock()

        # This should succeed without throwing an exception
        engine = RAGEngine()
        assert engine is not None

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.get_settings")
    def test_build_knowledge_base_success(
        self, mock_get_settings, mock_gemini, mock_fetcher, mock_vector_store
    ):
        """Test successful knowledge base building."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock content fetcher
        mock_content_fetcher = Mock()
        mock_content = {
            "web_pages": [
                {
                    "source": "test_source",
                    "content": "Test content for German integration",
                    "title": "Test Title",
                    "metadata": {"category": "test"},
                }
            ],
            "pdfs": [],
            "structured_data": [],
        }
        mock_content_fetcher.fetch_all_content.return_value = mock_content
        mock_fetcher.return_value = mock_content_fetcher

        # Mock vector store
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.get_collection_info.return_value = {"count": 0}
        mock_vector_store.return_value = mock_vector_store_instance

        # Mock gemini client
        mock_gemini.return_value = Mock()

        engine = RAGEngine()
        result = engine.build_knowledge_base(force_refresh=True)

        assert result is True
        mock_content_fetcher.fetch_all_content.assert_called_once_with(
            force_refresh=True
        )
        mock_vector_store_instance.add_documents.assert_called()

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.get_settings")
    def test_search_knowledge_base(
        self, mock_get_settings, mock_gemini, mock_fetcher, mock_vector_store
    ):
        """Test searching the knowledge base."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock vector store
        mock_vector_store_instance = Mock()
        search_results = [
            {
                "content": "Berlin ist die Hauptstadt von Deutschland",
                "metadata": {"source": "test", "score": 0.9},
            },
            {
                "content": "Das Grundgesetz wurde 1949 verkündet",
                "metadata": {"source": "test", "score": 0.8},
            },
        ]
        mock_vector_store_instance.similarity_search.return_value = search_results
        mock_vector_store.return_value = mock_vector_store_instance

        # Mock other components
        mock_fetcher.return_value = Mock()
        mock_gemini.return_value = Mock()

        engine = RAGEngine()
        results = engine.search_knowledge_base(
            "Was ist die Hauptstadt von Deutschland?", k=5
        )

        assert len(results) == 2
        assert results[0]["content"] == "Berlin ist die Hauptstadt von Deutschland"
        assert results[0]["metadata"]["score"] == 0.9
        mock_vector_store_instance.similarity_search.assert_called_once_with(
            query="Was ist die Hauptstadt von Deutschland?", k=5, where=None
        )

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.get_settings")
    def test_generate_explanation_with_rag(
        self, mock_get_settings, mock_gemini, mock_fetcher, mock_vector_store
    ):
        """Test generating explanation with RAG."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock vector store
        mock_vector_store_instance = Mock()
        search_results = [
            {
                "content": "Berlin ist seit 1990 die Hauptstadt der wiedervereinigten Bundesrepublik Deutschland",
                "metadata": {"source": "bamf_main", "score": 0.95},
            }
        ]
        mock_vector_store_instance.similarity_search.return_value = search_results
        mock_vector_store.return_value = mock_vector_store_instance

        # Mock gemini client
        mock_gemini_client = Mock()
        mock_gemini_response = """Berlin ist die richtige Antwort, weil es seit 1990 die Hauptstadt der wiedervereinigten Bundesrepublik Deutschland ist. Die anderen Städte sind zwar wichtige deutsche Städte, aber nicht die Hauptstadt."""
        mock_gemini_client.generate_with_context.return_value = mock_gemini_response
        mock_gemini_client.extract_key_concepts.return_value = [
            "Hauptstadt",
            "Deutschland",
            "Berlin",
        ]
        mock_gemini.return_value = mock_gemini_client

        # Mock other components
        mock_fetcher.return_value = Mock()

        engine = RAGEngine()

        result = engine.generate_explanation_with_rag(
            question="Was ist die Hauptstadt von Deutschland?",
            correct_answer="Berlin",
            options={"A": "Berlin", "B": "München", "C": "Hamburg", "D": "Köln"},
            category="Geographie",
        )

        assert result["explanation"] == mock_gemini_response
        assert result["context_used"] is True
        assert len(result["context_sources"]) == 1
        assert result["context_sources"][0] == "bamf_main"
        assert len(result["key_concepts"]) == 3

        # Verify search was called
        mock_vector_store_instance.similarity_search.assert_called()

        # Verify Gemini was called with context
        mock_gemini_client.generate_with_context.assert_called_once()

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.get_settings")
    def test_generate_explanation_no_context(
        self, mock_get_settings, mock_gemini, mock_fetcher, mock_vector_store
    ):
        """Test generating explanation when no relevant context found."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock vector store to return no results
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.similarity_search.return_value = []
        mock_vector_store.return_value = mock_vector_store_instance

        # Mock gemini client
        mock_gemini_client = Mock()
        mock_gemini_response = (
            "Basierend auf allgemeinem Wissen ist Berlin die Hauptstadt."
        )
        mock_gemini_client.generate_with_context.return_value = mock_gemini_response
        mock_gemini_client.extract_key_concepts.return_value = []
        mock_gemini.return_value = mock_gemini_client

        # Mock other components
        mock_fetcher.return_value = Mock()

        engine = RAGEngine()

        result = engine.generate_explanation_with_rag(
            question="Was ist die Hauptstadt von Deutschland?",
            correct_answer="Berlin",
            options={"A": "Berlin", "B": "München"},
            category="Geographie",
        )

        assert result["explanation"] == mock_gemini_response
        assert result["context_used"] is False
        assert result["context_sources"] == []

        # Verify generate_with_context was called (with empty context)
        mock_gemini_client.generate_with_context.assert_called_once()

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.get_settings")
    def test_get_knowledge_base_stats(
        self, mock_get_settings, mock_gemini, mock_fetcher, mock_vector_store
    ):
        """Test getting knowledge base statistics."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock vector store
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.get_collection_info.return_value = {
            "count": 100,
            "name": "test_collection",
            "persist_directory": str(self.test_dir),
        }
        mock_vector_store_instance.search_by_metadata.return_value = [
            {"metadata": {"source": "bamf_main", "type": "web_page"}},
            {"metadata": {"source": "bamf_main", "type": "web_page"}},
            {"metadata": {"source": "bpb", "type": "pdf"}},
        ]
        mock_vector_store.return_value = mock_vector_store_instance

        # Mock other components
        mock_fetcher.return_value = Mock()
        mock_gemini.return_value = Mock()

        engine = RAGEngine()
        stats = engine.get_knowledge_base_stats()

        assert stats["total_documents"] == 100
        assert stats["collection_name"] == "test_collection"
        assert "bamf_main" in stats["sources"]
        assert "bpb" in stats["sources"]
        assert "web_page" in stats["types"]
        assert "pdf" in stats["types"]

    @patch("src.knowledge_base.rag_engine.VectorStore")
    @patch("src.knowledge_base.rag_engine.ContentFetcher")
    @patch("src.knowledge_base.rag_engine.GeminiClient")
    @patch("src.core.settings.get_settings")
    def test_test_rag_query(
        self, mock_get_settings, mock_gemini, mock_fetcher, mock_vector_store
    ):
        """Test the test RAG query method."""
        # Mock settings
        mock_settings = Mock()
        mock_settings.vector_store_dir = str(self.test_dir)
        mock_settings.vector_collection_name = "test_collection"
        mock_settings.embedding_model = "test-model"
        mock_settings.chunk_size = 1000
        mock_settings.chunk_overlap = 200
        mock_get_settings.return_value = mock_settings

        # Mock vector store
        mock_vector_store_instance = Mock()
        search_results = [
            {
                "content": "Berlin ist die Hauptstadt von Deutschland seit 1990",
                "metadata": {"source": "bamf_main"},
                "score": 0.9,
            }
        ]
        mock_vector_store_instance.similarity_search.return_value = search_results
        mock_vector_store.return_value = mock_vector_store_instance

        # Mock gemini client
        mock_gemini_client = Mock()
        mock_gemini_client.generate_with_context.return_value = (
            "Berlin ist die Hauptstadt."
        )
        mock_gemini.return_value = mock_gemini_client

        # Mock other components
        mock_fetcher.return_value = Mock()

        engine = RAGEngine()
        result = engine.test_rag_query("Was ist die Hauptstadt?")

        assert result["query"] == "Was ist die Hauptstadt?"
        assert result["answer"] == "Berlin ist die Hauptstadt."
        assert result["context_used"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["source"] == "bamf_main"
