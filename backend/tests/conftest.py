import sys
from pathlib import Path

# backend/ — for source modules
sys.path.insert(0, str(Path(__file__).parent.parent))
# backend/tests/ — for helpers.py
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import tempfile
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_vector_store():
    return MagicMock()


@pytest.fixture
def chroma_tempdir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def mock_config():
    class C:
        ANTHROPIC_API_KEY = "test-key"
        ANTHROPIC_MODEL = "claude-sonnet-4-6"
        CHROMA_PATH = "/tmp/nonexistent_test_chroma"
        EMBEDDING_MODEL = "all-MiniLM-L6-v2"
        MAX_RESULTS = 5
        CHUNK_SIZE = 800
        CHUNK_OVERLAP = 100
        MAX_HISTORY = 2
    return C()


@pytest.fixture
def mock_rag_system():
    mock = MagicMock()
    mock.query.return_value = ("Test answer", [])
    mock.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }
    mock.session_manager.create_session.return_value = "test-session-id"
    return mock


@pytest.fixture
def api_client(mock_rag_system):
    """TestClient for the FastAPI app with RAGSystem and StaticFiles mocked out."""
    sys.modules.pop("app", None)

    with patch("rag_system.RAGSystem", return_value=mock_rag_system), \
         patch("fastapi.staticfiles.StaticFiles", MagicMock()):
        import app as _app_module
        from starlette.testclient import TestClient
        return TestClient(_app_module.app)
