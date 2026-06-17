# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

Requires Python 3.13+ and `uv`. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY`.

```bash
uv sync
cp .env.example .env
```

## Running

```bash
./run.sh
# or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

App: `http://localhost:8000` | API docs: `http://localhost:8000/docs`

## Architecture

This is a full-stack RAG chatbot. FastAPI (`backend/app.py`) serves both the REST API and the static frontend from `../frontend/`.

**Chat query flow:**

1. `frontend/script.js` POSTs to `/api/query`
2. `backend/app.py` delegates to `RAGSystem.query()` (`backend/rag_system.py`) — the central orchestrator
3. `RAGSystem` calls `AIGenerator.generate_response()` (`backend/ai_generator.py`) passing registered Anthropic tool definitions
4. Claude (`claude-sonnet-4-20250514`) decides whether to invoke `search_course_content` (one search max per query per the system prompt)
5. If tool use fires, `ToolManager.execute_tool()` dispatches to `CourseSearchTool.execute()` (`backend/search_tools.py`), which calls `VectorStore.search()`
6. `VectorStore` (`backend/vector_store.py`) uses ChromaDB with `all-MiniLM-L6-v2` embeddings across two collections: `course_catalog` (fuzzy course-name resolution) and `course_content` (chunk retrieval, filterable by `course_title` and/or `lesson_number` metadata)
7. Tool results are sent back to Claude in a follow-up API call; the final text and sources are returned to the frontend

**Document ingestion** (auto-runs at startup from `../docs/`):

`DocumentProcessor` (`backend/document_processor.py`) parses `.txt`/`.pdf`/`.docx` files in this format:
```
Course Title: <title>
Course Link: <url>
Course Instructor: <name>

Lesson 1: <lesson title>
Lesson Link: <url>
<content...>
Lesson 2: ...
```
Lesson text is sentence-split into overlapping chunks (800 chars, 100 overlap) stored as `CourseChunk` objects. ChromaDB persists to `backend/chroma_db/`; courses already indexed by title are skipped on subsequent startups.

**Key config** (`backend/config.py`):
- Model: `claude-sonnet-4-20250514`, embeddings: `all-MiniLM-L6-v2`
- `MAX_RESULTS`: 5 chunks per search; `MAX_HISTORY`: 2 exchanges per session (in-memory, lost on restart)
- `CHROMA_PATH`: `./chroma_db` (relative to `backend/`)

**Data models** (`backend/models.py`): `Course` (title = unique ChromaDB ID) → `Lesson[]`; `CourseChunk` (what gets embedded).

**Adding a new tool**: implement the `Tool` ABC in `backend/search_tools.py` — `get_tool_definition()` returns an Anthropic tool schema dict, `execute(**kwargs)` returns a string — then call `ToolManager.register_tool(your_tool)` in `RAGSystem.__init__`.
