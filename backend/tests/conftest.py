import sys
from pathlib import Path

# backend/ — for source modules
sys.path.insert(0, str(Path(__file__).parent.parent))
# backend/tests/ — for helpers.py
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import tempfile


@pytest.fixture
def mock_vector_store():
    from unittest.mock import MagicMock
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
