import pytest
from unittest.mock import MagicMock, patch
from helpers import make_text_block, make_tool_use_block, make_response


class TestAIGeneratorConfig:

    def test_model_is_not_deprecated_claude_sonnet_4_20250514(self):
        """Regression: the original model name claude-sonnet-4-20250514 no longer exists (404)."""
        from config import config
        assert config.ANTHROPIC_MODEL != "claude-sonnet-4-20250514", (
            "Model claude-sonnet-4-20250514 was removed from the Anthropic API; "
            "use claude-sonnet-4-6 instead"
        )


class TestAIGeneratorGenerateResponse:

    @patch("ai_generator.anthropic.Anthropic")
    def test_direct_response_returns_text(self, mock_anthropic_cls):
        """stop_reason=end_turn → returns content[0].text directly."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_response(
            "end_turn", [make_text_block("Paris is the capital of France.")]
        )

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        result = gen.generate_response(query="What is the capital of France?")

        assert result == "Paris is the capital of France."
        mock_client.messages.create.assert_called_once()

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_use_calls_execute_tool(self, mock_anthropic_cls):
        """stop_reason=tool_use → tool_manager.execute_tool called with correct kwargs."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_block(
            "search_course_content", "toolu_01", {"query": "machine learning"}
        )
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tool_block]),
            make_response("end_turn", [make_text_block("ML answer")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Relevant ML content"

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        gen.generate_response(
            query="What is machine learning?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="machine learning"
        )

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_result_message_structure(self, mock_anthropic_cls):
        """Follow-up API call contains tool_result message with correct structure."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_block(
            "search_course_content", "toolu_01", {"query": "MCP tools"}
        )
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tool_block]),
            make_response("end_turn", [make_text_block("Final answer")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "Relevant ML content"

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        gen.generate_response(
            query="Tell me about MCP",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs
        messages = second_call_kwargs["messages"]

        # messages: [original_user, assistant_tool_use, user_tool_results]
        user_tool_msg = messages[2]
        assert user_tool_msg["role"] == "user"

        tool_result = user_tool_msg["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "toolu_01"
        assert tool_result["content"] == "Relevant ML content"

    @patch("ai_generator.anthropic.Anthropic")
    def test_intermediate_call_includes_tools(self, mock_anthropic_cls):
        """After round 1, the next API call includes tools so Claude can chain if needed."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_block("search_course_content", "t1", {"query": "q"})
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tool_block]),
            make_response("end_turn", [make_text_block("answer")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "result"

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        gen.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        first_call_kwargs = mock_client.messages.create.call_args_list[0].kwargs
        second_call_kwargs = mock_client.messages.create.call_args_list[1].kwargs

        assert "tools" in first_call_kwargs
        assert first_call_kwargs["tool_choice"] == {"type": "auto"}

        # Intermediate call retains tools so Claude can optionally chain
        assert "tools" in second_call_kwargs
        assert second_call_kwargs["tool_choice"] == {"type": "auto"}

    @patch("ai_generator.anthropic.Anthropic")
    def test_api_error_propagates_to_caller(self, mock_anthropic_cls):
        """API errors (e.g. 404 for deprecated model) propagate so app.py can return HTTP 500."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("model: claude-sonnet-4-20250514 not found")

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-sonnet-4-20250514")

        with pytest.raises(Exception, match="not found"):
            gen.generate_response(query="What is Python?")

    @patch("ai_generator.anthropic.Anthropic")
    def test_final_text_from_second_response(self, mock_anthropic_cls):
        """generate_response() returns text from the second (follow-up) call."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_block("search_course_content", "t1", {"query": "q"})
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tool_block]),
            make_response("end_turn", [make_text_block("The final definitive answer")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "tool content"

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        result = gen.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert result == "The final definitive answer"
        assert mock_client.messages.create.call_count == 2


class TestAIGeneratorMultiRound:
    """Tests for the sequential (up to 2-round) tool-calling loop."""

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_path_makes_three_api_calls(self, mock_anthropic_cls):
        """Two tool rounds → 3 API calls total; execute_tool called once per round."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        outline_block = make_tool_use_block("get_course_outline", "t1", {"course_name": "MCP"})
        search_block = make_tool_use_block("search_course_content", "t2", {"query": "MCP servers"})

        mock_client.messages.create.side_effect = [
            make_response("tool_use", [outline_block]),
            make_response("tool_use", [search_block]),
            make_response("end_turn", [make_text_block("Here is what I found.")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course: MCP\nLesson 1: Servers",
            "[MCP - Lesson 1]\nMCP servers handle requests...",
        ]

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        result = gen.generate_response(
            query="What topic does lesson 1 of MCP cover?",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="MCP")
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="MCP servers")
        assert result == "Here is what I found."

    @patch("ai_generator.anthropic.Anthropic")
    def test_two_round_final_synthesis_call_has_no_tools(self, mock_anthropic_cls):
        """After 2 tool rounds, the synthesis call omits tools to force a text answer."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        b1 = make_tool_use_block("get_course_outline", "t1", {"course_name": "MCP"})
        b2 = make_tool_use_block("search_course_content", "t2", {"query": "servers"})

        mock_client.messages.create.side_effect = [
            make_response("tool_use", [b1]),
            make_response("tool_use", [b2]),
            make_response("end_turn", [make_text_block("Final synthesis.")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "tool content"

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        gen.generate_response(
            query="question",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        calls = mock_client.messages.create.call_args_list
        # First two calls keep tools available for chaining
        assert "tools" in calls[0].kwargs
        assert "tools" in calls[1].kwargs
        # Third call (final synthesis) strips tools
        assert "tools" not in calls[2].kwargs
        assert "tool_choice" not in calls[2].kwargs

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_error_delivers_result_then_synthesises(self, mock_anthropic_cls):
        """A tool execution error is wrapped in a tool_result so Claude can respond gracefully."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_block("search_course_content", "t1", {"query": "q"})
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tool_block]),
            make_response("end_turn", [make_text_block("I encountered an error, sorry.")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.side_effect = RuntimeError("DB connection lost")

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        result = gen.generate_response(
            query="question",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Error is sent to Claude as a tool_result so it can write a graceful reply
        assert mock_client.messages.create.call_count == 2
        final_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result_content = final_call_messages[2]["content"][0]
        assert tool_result_content["type"] == "tool_result"
        assert "DB connection lost" in tool_result_content["content"]

        # Claude's graceful reply is returned to the caller
        assert result == "I encountered an error, sorry."

    @patch("ai_generator.anthropic.Anthropic")
    def test_messages_accumulate_across_two_rounds(self, mock_anthropic_cls):
        """Full conversation context (5 messages) is present on the final synthesis call."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        b1 = make_tool_use_block("get_course_outline", "t1", {"course_name": "MCP"})
        b2 = make_tool_use_block("search_course_content", "t2", {"query": "servers"})
        r1 = make_response("tool_use", [b1])
        r2 = make_response("tool_use", [b2])

        mock_client.messages.create.side_effect = [
            r1, r2,
            make_response("end_turn", [make_text_block("done")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "some result"

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        gen.generate_response(
            query="original question",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        final_messages = mock_client.messages.create.call_args_list[2].kwargs["messages"]
        roles = [m["role"] for m in final_messages]

        # user → assistant (R1 tool_use) → user (R1 results) → assistant (R2 tool_use) → user (R2 results)
        assert roles == ["user", "assistant", "user", "assistant", "user"]
        assert len(final_messages) == 5
        assert final_messages[0]["content"] == "original question"

    @patch("ai_generator.anthropic.Anthropic")
    def test_claude_stops_after_one_round_without_second_tool_call(self, mock_anthropic_cls):
        """If Claude returns end_turn after round 1, no synthesis call is made (2 calls total)."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        tool_block = make_tool_use_block("search_course_content", "t1", {"query": "Python"})
        mock_client.messages.create.side_effect = [
            make_response("tool_use", [tool_block]),
            make_response("end_turn", [make_text_block("Python is a programming language.")]),
        ]

        mock_tool_manager = MagicMock()
        mock_tool_manager.execute_tool.return_value = "[Python - Lesson 1]\nPython intro..."

        from ai_generator import AIGenerator
        gen = AIGenerator(api_key="test-key", model="claude-test")

        result = gen.generate_response(
            query="What is Python?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        assert mock_client.messages.create.call_count == 2
        assert result == "Python is a programming language."
