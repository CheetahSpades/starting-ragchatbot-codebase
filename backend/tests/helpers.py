from unittest.mock import MagicMock


def make_text_block(text):
    b = MagicMock()
    b.type = "text"
    b.text = text
    return b


def make_tool_use_block(name, tool_id, inputs):
    b = MagicMock()
    b.type = "tool_use"
    b.name = name
    b.id = tool_id
    b.input = inputs
    return b


def make_response(stop_reason, content):
    r = MagicMock()
    r.stop_reason = stop_reason
    r.content = content
    return r
