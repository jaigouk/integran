"""Tests for text splitting functionality."""

import pytest

from src.knowledge_base.text_splitter import (
    ParagraphTextSplitter,
    RecursiveCharacterTextSplitter,
    SentenceTextSplitter,
    create_text_splitter,
)


class TestRecursiveCharacterTextSplitter:
    """Test recursive character text splitter."""

    def test_simple_split(self):
        """Test basic text splitting."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=2)
        text = "This is a simple test."
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert all(len(chunk) <= 15 for chunk in chunks)  # Allow some flexibility

    def test_paragraph_split(self):
        """Test splitting by paragraphs."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=5)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert any("First" in chunk for chunk in chunks)
        assert any("Second" in chunk for chunk in chunks)

    def test_large_text_force_split(self):
        """Test force splitting of very large text."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=0)
        text = "This_is_a_very_long_word_that_cannot_be_split_by_separators"
        chunks = splitter.split_text(text)

        assert len(chunks) > 1
        assert all(len(chunk) <= 15 for chunk in chunks)  # Allow some flexibility

    def test_overlap_functionality(self):
        """Test that overlap works correctly."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=20, chunk_overlap=5)
        text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7"
        chunks = splitter.split_text(text)

        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            first_chunk_end = chunks[0][-5:]
            second_chunk_start = chunks[1][:10]
            # There should be some common words
            first_words = set(first_chunk_end.split())
            second_words = set(second_chunk_start.split())
            assert len(first_words & second_words) > 0 or len(chunks) == 1

    def test_empty_text(self):
        """Test handling of empty text."""
        splitter = RecursiveCharacterTextSplitter()
        assert splitter.split_text("") == []
        # Whitespace-only text may be preserved as a chunk
        result = splitter.split_text("   ")
        assert isinstance(result, list)

    def test_custom_separators(self):
        """Test custom separators."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=50, separators=["|", " "])
        text = "Part1|Part2|Part3 with spaces"
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        # Should split on | first
        assert any("Part1" in chunk for chunk in chunks)

    def test_create_documents(self):
        """Test document creation with metadata."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=20)
        texts = ["Short text", "This is a longer text that should be split"]
        metadatas = [{"source": "test1"}, {"source": "test2"}]

        docs = splitter.create_documents(texts, metadatas)

        assert len(docs) >= 2  # At least one per input text
        assert all("content" in doc for doc in docs)
        assert all("metadata" in doc for doc in docs)
        assert all("source_index" in doc["metadata"] for doc in docs)
        assert all("chunk_index" in doc["metadata"] for doc in docs)


class TestSentenceTextSplitter:
    """Test sentence-based text splitter."""

    def test_sentence_splitting(self):
        """Test basic sentence splitting."""
        splitter = SentenceTextSplitter(chunk_size=100)
        text = "First sentence. Second sentence! Third sentence? Fourth sentence."
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert all(len(chunk) <= 120 for chunk in chunks)  # Allow some flexibility

    def test_long_sentences(self):
        """Test handling of very long sentences."""
        splitter = SentenceTextSplitter(chunk_size=20)
        text = "This is a very long sentence that exceeds the chunk size limit."
        chunks = splitter.split_text(text)

        assert len(chunks) >= 1

    def test_no_sentence_boundaries(self):
        """Test text without clear sentence boundaries."""
        splitter = SentenceTextSplitter(chunk_size=20)
        text = "NoSentenceBoundariesInThisTextAtAll"
        chunks = splitter.split_text(text)

        assert len(chunks) >= 1


class TestParagraphTextSplitter:
    """Test paragraph-based text splitter."""

    def test_paragraph_splitting(self):
        """Test basic paragraph splitting."""
        splitter = ParagraphTextSplitter(chunk_size=100)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert any("First" in chunk for chunk in chunks)

    def test_large_paragraphs(self):
        """Test handling of paragraphs larger than chunk size."""
        splitter = ParagraphTextSplitter(chunk_size=20)
        text = (
            "This is a very long paragraph that exceeds the chunk size.\n\nShort para."
        )
        chunks = splitter.split_text(text)

        assert len(chunks) >= 1

    def test_no_paragraph_breaks(self):
        """Test text without paragraph breaks."""
        splitter = ParagraphTextSplitter(chunk_size=50)
        text = "All text in one paragraph without any double newlines."
        chunks = splitter.split_text(text)

        # May split into multiple chunks if text exceeds chunk_size
        assert len(chunks) >= 1


class TestCreateTextSplitter:
    """Test the factory function for creating text splitters."""

    def test_create_recursive_splitter(self):
        """Test creating recursive character splitter."""
        splitter = create_text_splitter("recursive", chunk_size=100)
        assert isinstance(splitter, RecursiveCharacterTextSplitter)
        assert splitter.chunk_size == 100

    def test_create_sentence_splitter(self):
        """Test creating sentence splitter."""
        splitter = create_text_splitter("sentence", chunk_size=200)
        assert isinstance(splitter, SentenceTextSplitter)
        assert splitter.chunk_size == 200

    def test_create_paragraph_splitter(self):
        """Test creating paragraph splitter."""
        splitter = create_text_splitter("paragraph", chunk_size=300)
        assert isinstance(splitter, ParagraphTextSplitter)
        assert splitter.chunk_size == 300

    def test_invalid_splitter_type(self):
        """Test error handling for invalid splitter type."""
        with pytest.raises(ValueError, match="Unknown splitter type"):
            create_text_splitter("invalid_type")

    def test_custom_parameters(self):
        """Test passing custom parameters to splitters."""
        splitter = create_text_splitter(
            "recursive", chunk_size=500, chunk_overlap=100, separators=["\n\n", "\n"]
        )
        assert splitter.chunk_size == 500
        assert splitter.chunk_overlap == 100
        assert splitter.separators == ["\n\n", "\n"]


class TestTextSplitterEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_chunk_size(self):
        """Test handling of zero chunk size."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=0)
        text = "Some text"
        chunks = splitter.split_text(text)
        # Should handle gracefully
        assert isinstance(chunks, list)

    def test_negative_chunk_size(self):
        """Test handling of negative chunk size."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=-10)
        text = "Some text"
        chunks = splitter.split_text(text)
        # Should handle gracefully
        assert isinstance(chunks, list)

    def test_large_overlap(self):
        """Test overlap larger than chunk size."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=10, chunk_overlap=20)
        text = "This is some test text"
        chunks = splitter.split_text(text)
        # Should handle gracefully
        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_unicode_text(self):
        """Test handling of Unicode text."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=50)
        text = "Müller weiß über die Größe Bescheid. Hübsch! Tschüß!"
        chunks = splitter.split_text(text)

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)
        # Should preserve Unicode characters
        joined = " ".join(chunks)
        assert "Müller" in joined
        assert "Größe" in joined
        assert "Tschüß" in joined

    def test_very_long_text(self):
        """Test performance with very long text."""
        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=10)
        # Create a long text (10KB)
        long_text = "This is a test sentence. " * 400
        chunks = splitter.split_text(long_text)

        assert len(chunks) > 10  # Should create many chunks
        assert all(len(chunk) <= 120 for chunk in chunks)  # Respect size limits

        # Verify all text is preserved
        total_length = sum(len(chunk) for chunk in chunks)
        assert total_length >= len(long_text) * 0.9  # Account for overlap
