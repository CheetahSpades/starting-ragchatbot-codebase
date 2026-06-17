import pytest
from unittest.mock import MagicMock, call
from helpers import make_text_block

from vector_store import SearchResults
from search_tools import CourseSearchTool


@pytest.fixture
def tool(mock_vector_store):
    return CourseSearchTool(mock_vector_store)


class TestCourseSearchToolExecute:

    def test_formatted_output_with_lesson_header(self, tool, mock_vector_store):
        """execute() returns [Course - Lesson N] header followed by content."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Supervised learning is a type of ML."],
            metadata=[{"course_title": "ML Course", "lesson_number": 2}],
            distances=[0.1],
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"

        result = tool.execute(query="what is supervised learning")

        assert "[ML Course - Lesson 2]" in result
        assert "Supervised learning is a type of ML." in result

    def test_empty_results_no_filter(self, tool, mock_vector_store):
        """execute() returns the base no-content message when results are empty."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        result = tool.execute(query="something obscure")

        assert result == "No relevant content found."

    def test_empty_results_with_course_filter(self, tool, mock_vector_store):
        """execute() includes course name in the no-content message."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        result = tool.execute(query="test", course_name="Python 101")

        assert "Python 101" in result
        assert "No relevant content found" in result

    def test_error_string_returned_on_search_error(self, tool, mock_vector_store):
        """execute() returns error verbatim when results.error is set."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[],
            error="Search error: Collection is empty",
        )

        result = tool.execute(query="test")

        assert result == "Search error: Collection is empty"
        mock_vector_store.get_lesson_link.assert_not_called()

    def test_course_name_and_lesson_number_forwarded(self, tool, mock_vector_store):
        """execute() passes course_name and lesson_number through to store.search()."""
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        tool.execute(query="ML basics", course_name="Data Science", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="ML basics", course_name="Data Science", lesson_number=3
        )

    def test_last_sources_populated_with_text_and_url(self, tool, mock_vector_store):
        """execute() populates last_sources with {text, url} for each result."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content A", "Content B"],
            metadata=[
                {"course_title": "ML Course", "lesson_number": 1},
                {"course_title": "ML Course", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )
        mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/lesson1",
            "https://example.com/lesson2",
        ]

        tool.execute(query="anything")

        assert len(tool.last_sources) == 2
        assert tool.last_sources[0] == {
            "text": "ML Course - Lesson 1",
            "url": "https://example.com/lesson1",
        }
        assert tool.last_sources[1] == {
            "text": "ML Course - Lesson 2",
            "url": "https://example.com/lesson2",
        }
        mock_vector_store.get_lesson_link.assert_any_call("ML Course", 1)
        mock_vector_store.get_lesson_link.assert_any_call("ML Course", 2)

    def test_chunk_without_lesson_number_no_lesson_in_header(self, tool, mock_vector_store):
        """execute() shows just [Course Title] header when lesson_number is absent."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Intro overview content"],
            metadata=[{"course_title": "General Course"}],
            distances=[0.5],
        )

        result = tool.execute(query="overview")

        first_line = result.split("\n")[0]
        assert "[General Course]" in first_line
        assert "Lesson" not in first_line
        assert tool.last_sources[0] == {"text": "General Course", "url": None}
        mock_vector_store.get_lesson_link.assert_not_called()
