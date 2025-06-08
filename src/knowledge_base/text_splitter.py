"""Simple text splitter implementation without external dependencies."""

import re
from typing import Any


class TextSplitter:
    """Base class for text splitting."""

    def __init__(
        self, chunk_size: int = 1000, chunk_overlap: int = 200, separator: str = "\n\n"
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def split_text(self, text: str) -> list[str]:
        """Split text into chunks."""
        raise NotImplementedError

    def create_documents(
        self, texts: list[str], metadatas: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Create document objects from texts."""
        documents = []
        for i, text in enumerate(texts):
            chunks = self.split_text(text)
            for j, chunk in enumerate(chunks):
                doc = {
                    "content": chunk,
                    "metadata": {
                        "source_index": i,
                        "chunk_index": j,
                        "total_chunks": len(chunks),
                    },
                }

                # Add additional metadata if provided
                if metadatas and i < len(metadatas):
                    doc["metadata"].update(metadatas[i])

                documents.append(doc)

        return documents


class RecursiveCharacterTextSplitter(TextSplitter):
    """Split text recursively by different separators."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        super().__init__(chunk_size, chunk_overlap)

        if separators is None:
            # Default separators in order of preference
            self.separators = [
                "\n\n",  # Double newline (paragraphs)
                "\n",  # Single newline
                " ",  # Space
                "",  # Character level
            ]
        else:
            self.separators = separators

    def split_text(self, text: str) -> list[str]:
        """Split text recursively by separators."""
        return self._split_text_recursive(text, self.separators)

    def _split_text_recursive(self, text: str, separators: list[str]) -> list[str]:
        """Recursively split text using different separators."""
        final_chunks = []

        # Get the first separator
        separator = separators[0] if separators else ""
        new_separators = separators[1:] if len(separators) > 1 else []

        # Split by the current separator
        splits = text.split(separator) if separator else list(text)

        # Process each split
        good_splits = []
        for split in splits:
            if len(split) < self.chunk_size:
                good_splits.append(split)
            else:
                if good_splits:
                    # Merge good splits and add to final chunks
                    merged = self._merge_splits(good_splits, separator)
                    final_chunks.extend(merged)
                    good_splits = []

                # If we have more separators, try splitting recursively
                if new_separators:
                    other_chunks = self._split_text_recursive(split, new_separators)
                    final_chunks.extend(other_chunks)
                else:
                    # No more separators, force split
                    final_chunks.extend(self._force_split(split))

        # Handle remaining good splits
        if good_splits:
            merged = self._merge_splits(good_splits, separator)
            final_chunks.extend(merged)

        return final_chunks

    def _merge_splits(self, splits: list[str], separator: str) -> list[str]:
        """Merge splits into chunks with overlap."""
        chunks = []
        current_chunk = ""

        for split in splits:
            # Test if adding this split would exceed chunk size
            potential_chunk = (
                current_chunk + separator + split if current_chunk else split
            )

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk)

                # Handle overlap
                if self.chunk_overlap > 0 and chunks:
                    # Find overlap content from the end of current chunk
                    overlap_content = self._get_overlap_content(current_chunk)
                    current_chunk = (
                        overlap_content + separator + split
                        if overlap_content
                        else split
                    )
                else:
                    current_chunk = split

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_overlap_content(self, text: str) -> str:
        """Get overlap content from the end of text."""
        if len(text) <= self.chunk_overlap:
            return text

        # Try to find a good breakpoint within overlap range
        overlap_text = text[-self.chunk_overlap :]

        # Look for sentence boundaries
        sentence_end = max(
            overlap_text.rfind("."), overlap_text.rfind("!"), overlap_text.rfind("?")
        )

        if sentence_end > 0:
            return overlap_text[sentence_end + 1 :].strip()

        # Look for word boundaries
        word_boundary = overlap_text.rfind(" ")
        if word_boundary > 0:
            return overlap_text[word_boundary + 1 :].strip()

        # Return the end portion as is
        return overlap_text

    def _force_split(self, text: str) -> list[str]:
        """Force split text when no separators work."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to find a word boundary within chunk
            if end < len(text):
                # Look back for word boundary
                word_boundary = text.rfind(" ", start, end)
                if word_boundary > start:
                    end = word_boundary

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # Handle overlap
            if self.chunk_overlap > 0 and end < len(text):
                start = max(start + 1, end - self.chunk_overlap)
            else:
                start = end

        return chunks


class SentenceTextSplitter(TextSplitter):
    """Split text by sentences."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)

        # Simple sentence splitting pattern
        self.sentence_pattern = re.compile(r"[.!?]+\s+")

    def split_text(self, text: str) -> list[str]:
        """Split text into sentences, then group into chunks."""
        # Split into sentences
        sentences = self._split_into_sentences(text)

        # Group sentences into chunks
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Test if adding this sentence would exceed chunk size
            potential_chunk = (
                current_chunk + " " + sentence if current_chunk else sentence
            )

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Handle overlap by including some sentences from previous chunk
                if self.chunk_overlap > 0 and chunks:
                    overlap_sentences = self._get_overlap_sentences(current_chunk)
                    current_chunk = (
                        overlap_sentences + " " + sentence
                        if overlap_sentences
                        else sentence
                    )
                else:
                    current_chunk = sentence

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = self.sentence_pattern.split(text)

        # Clean up and filter empty sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                cleaned_sentences.append(sentence)

        return cleaned_sentences

    def _get_overlap_sentences(self, text: str) -> str:
        """Get overlap sentences from the end of text."""
        sentences = self._split_into_sentences(text)

        # Include sentences from the end that fit within overlap size
        overlap_text = ""
        for sentence in reversed(sentences):
            potential_overlap = (
                sentence + " " + overlap_text if overlap_text else sentence
            )
            if len(potential_overlap) <= self.chunk_overlap:
                overlap_text = potential_overlap
            else:
                break

        return overlap_text.strip()


class ParagraphTextSplitter(TextSplitter):
    """Split text by paragraphs."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap, separator="\n\n")

    def split_text(self, text: str) -> list[str]:
        """Split text by paragraphs, then group into chunks."""
        # Split into paragraphs
        paragraphs = text.split(self.separator)

        # Clean paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para:
                cleaned_paragraphs.append(para)

        # Group paragraphs into chunks
        chunks = []
        current_chunk = ""

        for para in cleaned_paragraphs:
            # Test if adding this paragraph would exceed chunk size
            potential_chunk = (
                current_chunk + self.separator + para if current_chunk else para
            )

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                # Save current chunk
                if current_chunk:
                    chunks.append(current_chunk.strip())

                # Handle large paragraphs
                if len(para) > self.chunk_size:
                    # Split large paragraph using recursive splitter
                    recursive_splitter = RecursiveCharacterTextSplitter(
                        chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
                    )
                    para_chunks = recursive_splitter.split_text(para)
                    chunks.extend(para_chunks)
                    current_chunk = ""
                else:
                    # Handle overlap
                    if self.chunk_overlap > 0 and chunks:
                        overlap_content = self._get_overlap_content(current_chunk)
                        current_chunk = (
                            overlap_content + self.separator + para
                            if overlap_content
                            else para
                        )
                    else:
                        current_chunk = para

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _get_overlap_content(self, text: str) -> str:
        """Get overlap content from paragraphs."""
        if len(text) <= self.chunk_overlap:
            return text

        # Get paragraphs from the end that fit within overlap
        paragraphs = text.split(self.separator)
        overlap_text = ""

        for para in reversed(paragraphs):
            potential_overlap = (
                para + self.separator + overlap_text if overlap_text else para
            )
            if len(potential_overlap) <= self.chunk_overlap:
                overlap_text = potential_overlap
            else:
                break

        return overlap_text.strip()


def create_text_splitter(
    splitter_type: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    **kwargs,
) -> TextSplitter:
    """Factory function to create text splitters."""
    if splitter_type == "recursive":
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs
        )
    elif splitter_type == "sentence":
        return SentenceTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs
        )
    elif splitter_type == "paragraph":
        return ParagraphTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, **kwargs
        )
    else:
        raise ValueError(f"Unknown splitter type: {splitter_type}")
