import pytest


class TestQueryEndpoint:

    def test_happy_path_returns_answer_sources_session(self, api_client, mock_rag_system):
        """POST /api/query returns answer, sources, and a session_id."""
        mock_rag_system.query.return_value = (
            "Python is a programming language.",
            [{"text": "Python 101 - Lesson 1", "url": "https://example.com/lesson1"}],
        )
        mock_rag_system.session_manager.create_session.return_value = "new-session-abc"

        resp = api_client.post("/api/query", json={"query": "What is Python?"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["answer"] == "Python is a programming language."
        assert data["session_id"] == "new-session-abc"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["text"] == "Python 101 - Lesson 1"
        assert data["sources"][0]["url"] == "https://example.com/lesson1"

    def test_no_session_id_auto_creates_session(self, api_client, mock_rag_system):
        """When session_id is omitted, a new session is created via session_manager."""
        mock_rag_system.session_manager.create_session.return_value = "generated-session"

        resp = api_client.post("/api/query", json={"query": "Hello"})

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "generated-session"
        mock_rag_system.session_manager.create_session.assert_called_once()

    def test_existing_session_id_is_reused(self, api_client, mock_rag_system):
        """When session_id is provided, it is passed through and no new session is created."""
        resp = api_client.post(
            "/api/query", json={"query": "Follow-up", "session_id": "existing-sess-99"}
        )

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "existing-sess-99"
        mock_rag_system.session_manager.create_session.assert_not_called()

    def test_rag_error_returns_500_with_detail(self, api_client, mock_rag_system):
        """An exception from RAGSystem.query() surfaces as HTTP 500 with a detail message."""
        mock_rag_system.query.side_effect = RuntimeError("vector store unavailable")

        resp = api_client.post("/api/query", json={"query": "anything"})

        assert resp.status_code == 500
        assert "vector store unavailable" in resp.json()["detail"]

    def test_query_forwarded_to_rag_system(self, api_client, mock_rag_system):
        """The query string from the request body is passed to RAGSystem.query()."""
        resp = api_client.post("/api/query", json={"query": "What is machine learning?"})

        assert resp.status_code == 200
        call_args = mock_rag_system.query.call_args
        assert "machine learning" in call_args[0][0]

    def test_empty_sources_list_is_valid_response(self, api_client, mock_rag_system):
        """A response with no sources is serialised correctly."""
        mock_rag_system.query.return_value = ("No sources found.", [])

        resp = api_client.post("/api/query", json={"query": "obscure topic"})

        assert resp.status_code == 200
        assert resp.json()["sources"] == []


class TestCoursesEndpoint:

    def test_returns_total_and_titles(self, api_client, mock_rag_system):
        """GET /api/courses returns total_courses and the list of course_titles."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["Intro to Python", "Machine Learning", "Deep Learning"],
        }

        resp = api_client.get("/api/courses")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 3
        assert data["course_titles"] == ["Intro to Python", "Machine Learning", "Deep Learning"]

    def test_empty_catalog_returns_zeros(self, api_client, mock_rag_system):
        """An empty catalog is a valid state — returns zero courses."""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        resp = api_client.get("/api/courses")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_analytics_error_returns_500(self, api_client, mock_rag_system):
        """An exception from get_course_analytics() surfaces as HTTP 500."""
        mock_rag_system.get_course_analytics.side_effect = RuntimeError("store unavailable")

        resp = api_client.get("/api/courses")

        assert resp.status_code == 500
        assert "store unavailable" in resp.json()["detail"]


class TestDeleteSessionEndpoint:

    def test_clears_session_and_returns_ok(self, api_client, mock_rag_system):
        """DELETE /api/sessions/{id} clears the session and returns {status: ok}."""
        resp = api_client.delete("/api/sessions/session-xyz-123")

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        mock_rag_system.session_manager.clear_session.assert_called_once_with("session-xyz-123")

    def test_session_id_from_path_is_forwarded(self, api_client, mock_rag_system):
        """The session_id captured from the URL path is passed verbatim to clear_session."""
        api_client.delete("/api/sessions/my-unique-session-id")

        mock_rag_system.session_manager.clear_session.assert_called_once_with(
            "my-unique-session-id"
        )
