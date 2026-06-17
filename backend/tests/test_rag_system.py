import pytest
from unittest.mock import MagicMock, patch
from helpers import make_text_block, make_tool_use_block, make_response


# ---------------------------------------------------------------------------
# Unit tests — VectorStore and AIGenerator fully mocked
# ---------------------------------------------------------------------------

class TestRAGSystemQueryUnit:

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    def test_query_returns_str_list_tuple(self, mock_gen_cls, mock_vs_cls, mock_config):
        """query() returns a (str, list) tuple."""
        mock_vs_cls.return_value = MagicMock()
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate_response.return_value = "Test answer"

        from rag_system import RAGSystem
        rag = RAGSystem(mock_config)

        response, sources = rag.query("What is Python?")

        assert isinstance(response, str)
        assert isinstance(sources, list)
        assert response == "Test answer"

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    def test_query_stores_exchange_in_session(self, mock_gen_cls, mock_vs_cls, mock_config):
        """query() stores user message and assistant answer in session history."""
        mock_vs_cls.return_value = MagicMock()
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate_response.return_value = "Session answer"

        from rag_system import RAGSystem
        rag = RAGSystem(mock_config)
        session_id = rag.session_manager.create_session()

        rag.query("First question?", session_id=session_id)

        history = rag.session_manager.get_conversation_history(session_id)
        assert "First question?" in history
        assert "Session answer" in history

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    def test_query_sources_reset_after_retrieval(self, mock_gen_cls, mock_vs_cls, mock_config):
        """query() resets tool sources after returning them; returned sources match pre-reset value."""
        mock_vs_cls.return_value = MagicMock()
        mock_gen = MagicMock()
        mock_gen_cls.return_value = mock_gen
        mock_gen.generate_response.return_value = "Answer"

        from rag_system import RAGSystem
        rag = RAGSystem(mock_config)

        pre_populated = [{"text": "ML Course - Lesson 1", "url": None}]
        rag.search_tool.last_sources = pre_populated.copy()

        _, sources = rag.query("question?")

        assert sources == pre_populated
        assert rag.search_tool.last_sources == []


# ---------------------------------------------------------------------------
# Integration tests — real ChromaDB in a temporary directory
# ---------------------------------------------------------------------------

class TestVectorStoreIntegration:

    def test_none_lesson_number_stored_without_error(self, chroma_tempdir):
        """Chunks with lesson_number=None are indexed successfully after fix (omit key from metadata)."""
        from vector_store import VectorStore
        from models import CourseChunk

        vs = VectorStore(chroma_tempdir, "all-MiniLM-L6-v2", max_results=5)
        chunks = [
            CourseChunk(
                content="Intro text without a lesson assignment.",
                course_title="Test Course",
                lesson_number=None,
                chunk_index=0,
            )
        ]

        vs.add_course_content(chunks)  # should not raise

        results = vs.search("intro text")
        assert not results.is_empty()
        assert results.error is None
        assert "lesson_number" not in results.metadata[0]

    def test_search_empty_collection_returns_empty_not_raises(self, chroma_tempdir):
        """search() on an empty collection returns graceful empty results, not an exception."""
        from vector_store import VectorStore

        vs = VectorStore(chroma_tempdir, "all-MiniLM-L6-v2", max_results=5)

        results = vs.search("anything at all")

        assert results.documents == []
        assert results.is_empty()

    def test_add_chunk_and_search_roundtrip(self, chroma_tempdir):
        """Add one chunk with a valid lesson_number then retrieve it by semantic search."""
        from vector_store import VectorStore
        from models import CourseChunk

        vs = VectorStore(chroma_tempdir, "all-MiniLM-L6-v2", max_results=5)
        chunks = [
            CourseChunk(
                content="Neural networks are machine learning models inspired by the brain.",
                course_title="Deep Learning 101",
                lesson_number=1,
                chunk_index=0,
            )
        ]
        vs.add_course_content(chunks)

        results = vs.search("machine learning model")

        assert results.error is None
        assert not results.is_empty()
        assert len(results.documents) == 1
        assert "Neural networks" in results.documents[0]
        assert results.metadata[0]["course_title"] == "Deep Learning 101"
        assert results.metadata[0]["lesson_number"] == 1
