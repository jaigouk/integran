"""Tests for build knowledge base CLI command."""

import sys
from unittest.mock import Mock, patch

import pytest

from src.cli.build_knowledge_base import main


class TestBuildKnowledgeBaseCLI:
    """Test the build knowledge base CLI command."""

    def test_cli_help_display(self, capsys):
        """Test CLI help display."""
        with (
            patch.object(sys, "argv", ["build-knowledge-base", "--help"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "German Integration Exam Knowledge Base Management" in captured.out

    @patch("src.cli.build_knowledge_base.has_rag_config")
    def test_build_missing_dependencies(self, mock_has_rag_config, capsys):
        """Test build command when RAG dependencies are missing."""
        mock_has_rag_config.return_value = False

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "build"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Missing RAG dependencies" in captured.out
        assert "pip install chromadb sentence-transformers" in captured.out

    @patch("src.cli.build_knowledge_base.has_rag_config")
    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_build_success(self, mock_rag_engine_class, mock_has_rag_config, capsys):
        """Test successful build command."""
        mock_has_rag_config.return_value = True

        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.build_knowledge_base.return_value = True
        mock_rag_engine.get_knowledge_base_stats.return_value = {
            "total_documents": 100,
            "collection_name": "test_collection",
            "persist_directory": "/tmp/test",
            "sources": {"bamf_main": 50, "bpb": 30},
            "types": {"web_page": 80, "pdf": 20},
        }
        mock_rag_engine_class.return_value = mock_rag_engine

        with (
            patch.object(
                sys, "argv", ["build-knowledge-base", "build", "--force-refresh"]
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Knowledge base built successfully!" in captured.out
        assert "Total documents: 100" in captured.out
        assert "bamf_main: 50 documents" in captured.out

        # Verify RAG engine was called correctly
        mock_rag_engine_class.assert_called_once_with(
            vector_store_dir=None,
            collection_name=None,
            chunk_size=None,
            chunk_overlap=None,
        )
        mock_rag_engine.build_knowledge_base.assert_called_once_with(force_refresh=True)

    @patch("src.cli.build_knowledge_base.has_rag_config")
    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_build_failure(self, mock_rag_engine_class, mock_has_rag_config, capsys):
        """Test build command failure."""
        mock_has_rag_config.return_value = True

        # Mock RAG engine to fail
        mock_rag_engine = Mock()
        mock_rag_engine.build_knowledge_base.return_value = False
        mock_rag_engine_class.return_value = mock_rag_engine

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "build"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to build knowledge base" in captured.out

    @patch("src.cli.build_knowledge_base.has_rag_config")
    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_build_with_custom_options(
        self, mock_rag_engine_class, mock_has_rag_config
    ):
        """Test build command with custom options."""
        mock_has_rag_config.return_value = True

        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.build_knowledge_base.return_value = True
        mock_rag_engine.get_knowledge_base_stats.return_value = {
            "total_documents": 50,
            "collection_name": "custom_collection",
            "persist_directory": "/custom/path",
            "sources": {},
            "types": {},
        }
        mock_rag_engine_class.return_value = mock_rag_engine

        with (
            patch.object(
                sys,
                "argv",
                [
                    "build-knowledge-base",
                    "build",
                    "--vector-store-dir",
                    "/custom/path",
                    "--collection-name",
                    "custom_collection",
                    "--chunk-size",
                    "500",
                    "--chunk-overlap",
                    "100",
                ],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0

        # Verify RAG engine was called with custom options
        mock_rag_engine_class.assert_called_once_with(
            vector_store_dir="/custom/path",
            collection_name="custom_collection",
            chunk_size=500,
            chunk_overlap=100,
        )

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_stats_command(self, mock_rag_engine_class, capsys):
        """Test stats command."""
        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.get_knowledge_base_stats.return_value = {
            "total_documents": 150,
            "collection_name": "test_collection",
            "persist_directory": "/tmp/kb",
            "sources": {"bamf_main": 75, "bpb": 50, "gesetze": 25},
            "types": {"web_page": 100, "pdf": 40, "structured_data": 10},
        }
        mock_rag_engine_class.return_value = mock_rag_engine

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "stats"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Knowledge Base Statistics" in captured.out
        assert "Total documents: 150" in captured.out
        assert "Collection: test_collection" in captured.out
        assert "bamf_main: 75 documents" in captured.out
        assert "web_page: 100 documents" in captured.out

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_search_command(self, mock_rag_engine_class, capsys):
        """Test search command."""
        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.search_knowledge_base.return_value = [
            {
                "content": "Berlin ist die Hauptstadt von Deutschland seit 1990.",
                "metadata": {"source": "bamf_main", "title": "Deutsche Hauptstadt"},
                "score": 0.95,
            },
            {
                "content": "Das Grundgesetz wurde am 23. Mai 1949 verkündet.",
                "metadata": {"source": "gesetze", "title": "Grundgesetz"},
                "score": 0.87,
            },
        ]
        mock_rag_engine_class.return_value = mock_rag_engine

        with (
            patch.object(
                sys,
                "argv",
                ["build-knowledge-base", "search", "Hauptstadt", "--k", "5"],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Search results for: 'Hauptstadt'" in captured.out
        assert "Found 2 documents" in captured.out
        assert "bamf_main" in captured.out
        assert "Score: 0.950" in captured.out
        assert "Berlin ist die Hauptstadt" in captured.out

        # Verify search was called correctly
        mock_rag_engine.search_knowledge_base.assert_called_once_with(
            query="Hauptstadt", k=5
        )

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_test_command(self, mock_rag_engine_class, capsys):
        """Test the test RAG command."""
        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.test_rag_query.return_value = {
            "query": "Was ist die Hauptstadt?",
            "context_used": True,
            "results": [
                {
                    "source": "bamf_main",
                    "score": 0.9,
                    "content": "Berlin ist die Hauptstadt von Deutschland.",
                }
            ],
            "answer": "Berlin ist die Hauptstadt von Deutschland seit der Wiedervereinigung 1990.",
        }
        mock_rag_engine_class.return_value = mock_rag_engine

        with (
            patch.object(
                sys, "argv", ["build-knowledge-base", "test", "Was ist die Hauptstadt?"]
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "RAG Test: 'Was ist die Hauptstadt?'" in captured.out
        assert "Context used: True" in captured.out
        assert "Retrieved 1 documents:" in captured.out
        assert "bamf_main (Score: 0.900)" in captured.out
        assert (
            "Berlin ist die Hauptstadt von Deutschland seit der Wiedervereinigung"
            in captured.out
        )

        # Verify test was called correctly
        mock_rag_engine.test_rag_query.assert_called_once_with(
            query="Was ist die Hauptstadt?"
        )

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_clear_command(self, mock_rag_engine_class, capsys, monkeypatch):
        """Test clear command."""
        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.clear_knowledge_base.return_value = True
        mock_rag_engine_class.return_value = mock_rag_engine

        # Mock stdin to automatically confirm
        from io import StringIO

        monkeypatch.setattr("sys.stdin", StringIO("y\n"))

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "clear"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "Knowledge base cleared" in captured.out

        # Verify clear was called
        mock_rag_engine.clear_knowledge_base.assert_called_once()

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_clear_command_failure(self, mock_rag_engine_class, capsys, monkeypatch):
        """Test clear command failure."""
        # Mock RAG engine to fail
        mock_rag_engine = Mock()
        mock_rag_engine.clear_knowledge_base.return_value = False
        mock_rag_engine_class.return_value = mock_rag_engine

        # Mock stdin to automatically confirm
        from io import StringIO

        monkeypatch.setattr("sys.stdin", StringIO("y\n"))

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "clear"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Failed to clear knowledge base" in captured.out

    @patch("src.cli.build_knowledge_base.has_rag_config")
    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_build_exception_handling(self, mock_rag_engine_class, mock_has_rag_config):
        """Test build command exception handling."""
        mock_has_rag_config.return_value = True

        # Mock RAG engine to raise exception
        mock_rag_engine_class.side_effect = Exception("Test error")

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "build"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_stats_exception_handling(self, mock_rag_engine_class):
        """Test stats command exception handling."""
        # Mock RAG engine to raise exception
        mock_rag_engine_class.side_effect = Exception("Test error")

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "stats"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_search_exception_handling(self, mock_rag_engine_class):
        """Test search command exception handling."""
        # Mock RAG engine to raise exception
        mock_rag_engine_class.side_effect = Exception("Test error")

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "search", "test query"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_test_exception_handling(self, mock_rag_engine_class):
        """Test test command exception handling."""
        # Mock RAG engine to raise exception
        mock_rag_engine_class.side_effect = Exception("Test error")

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "test", "test query"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1

    @patch("src.cli.build_knowledge_base.RAGEngine")
    def test_clear_exception_handling(self, mock_rag_engine_class, monkeypatch):
        """Test clear command exception handling."""
        # Mock RAG engine to raise exception
        mock_rag_engine_class.side_effect = Exception("Test error")

        # Mock stdin to automatically confirm
        from io import StringIO

        monkeypatch.setattr("sys.stdin", StringIO("y\n"))

        with (
            patch.object(sys, "argv", ["build-knowledge-base", "clear"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()

        assert exc_info.value.code == 1
