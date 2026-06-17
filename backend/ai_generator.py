import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use `search_course_content` **only** for questions about specific course content or detailed educational materials
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Outline Tool Usage:
- Use `get_course_outline` for questions about course structure, lesson list, or "what does X cover"
- Return the course title, course link, and every lesson as "Lesson N: <title>" on its own line
- Do not use `search_course_content` when an outline is all that is needed

Sequential Tool Use:
- You may make up to 2 sequential tool calls when a query requires it (e.g., retrieve an outline first, then search based on what you found)
- Only chain tool calls when the result of the first genuinely informs the input of the second
- After completing tool use, synthesize all results into a single direct answer

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._run_agentic_loop(
                response,
                api_params["messages"].copy(),
                system_content,
                tools,
                tool_manager,
            )

        # Return direct response
        return response.content[0].text

    def _run_agentic_loop(self,
                          first_response,
                          messages: List,
                          system_content: str,
                          tools: Optional[List],
                          tool_manager) -> str:
        """
        Run up to MAX_ROUNDS of sequential tool calling, then issue a final
        no-tools synthesis call.

        Each intermediate call includes tools so Claude can chain calls when
        the result of one informs the next. The final synthesis call omits tools
        to force a text answer once all rounds are consumed.

        Termination conditions (whichever comes first):
          (a) MAX_ROUNDS rounds completed
          (b) Claude returns stop_reason != "tool_use" on an intermediate call
          (c) A tool execution raises an exception
        """
        response = first_response

        for round_num in range(self.MAX_ROUNDS):
            # Append this round's assistant content (tool_use blocks + any text)
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls in this response
            tool_results = []
            had_error = False

            for block in response.content:
                if block.type == "tool_use":
                    try:
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as exc:
                        result = f"Tool execution error: {exc}"
                        had_error = True

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Exit the loop if tool failed or all rounds are consumed
            if had_error or round_num == self.MAX_ROUNDS - 1:
                break

            # Intermediate call WITH tools — Claude may chain to another tool call
            next_response = self.client.messages.create(**{
                **self.base_params,
                "messages": messages,
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"},
            })

            if next_response.stop_reason != "tool_use":
                return next_response.content[0].text

            response = next_response

        # Final synthesis call WITHOUT tools — Claude summarises what it found
        final_response = self.client.messages.create(**{
            **self.base_params,
            "messages": messages,
            "system": system_content,
        })
        return final_response.content[0].text
