"""
Main entry point for the agent.
Defines the workflow graph, state, tools, nodes and edges.
"""

from typing import Callable, Awaitable

from copilotkit import CopilotKitMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
import os
import warnings

# Data & state tools
from src.query import query_data
from src.todos import AgentState, todo_tools

# A2UI tools
from src.a2ui_dynamic_schema import generate_a2ui
from src.a2ui_fixed_schema import search_flights

# Shared file store (populated by /documents/upload route)
from src.file_store import UPLOADED_DOCS

if not os.getenv("ANTHROPIC_API_KEY"):
    warnings.warn(
        "ANTHROPIC_API_KEY environment variable is not set. "
        "Anthropic API calls will fail."
    )


class SystemMessageMergerMiddleware(AgentMiddleware):
    """Merge all system messages into a single one at the front before the model call."""

    @property
    def name(self) -> str:
        return "SystemMessageMergerMiddleware"

    def _merge(self, request: ModelRequest) -> ModelRequest:
        system_parts: list[str] = []
        other_messages = []

        if request.system_message:
            content = request.system_message.content
            if isinstance(content, list):
                content = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            system_parts.append(content)

        for msg in request.messages:
            if isinstance(msg, SystemMessage):
                content = msg.content
                if isinstance(content, list):
                    content = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in content
                    )
                system_parts.append(content)
            else:
                other_messages.append(msg)

        if not system_parts:
            return request

        merged_system = SystemMessage(content="\n\n".join(system_parts))
        return request.override(
            messages=[merged_system, *other_messages],
            system_message=None,
        )

    def wrap_model_call(self, request, handler):
        return handler(self._merge(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._merge(request))


class UploadedFileContextMiddleware(AgentMiddleware):
    """Inject uploaded document text from the thread-keyed store every turn.

    Mirrors the ADK pattern: files live server-side keyed by thread_id, and we
    re-attach them to the system prompt on EVERY model call. This way the file
    survives across turns and is never dependent on message-part serialization.
    """

    _max_file_chars = 8000
    _max_total_chars = 20000

    @property
    def name(self) -> str:
        return "UploadedFileContextMiddleware"

    def _get_thread_id(self, request: ModelRequest) -> str | None:
        # LangGraph exposes the current run's config via a contextvar.
        # This is the same source the logger uses (thread_id appears in log lines).
        try:
            from langgraph.config import get_config

            cfg = get_config()
            if isinstance(cfg, dict):
                configurable = cfg.get("configurable") or {}
                tid = configurable.get("thread_id")
                if tid:
                    print(
                        f"[file-middleware] thread_id={tid} "
                        f"store_keys={list(UPLOADED_DOCS.keys())}",
                        flush=True,
                    )
                    return str(tid)
        except Exception as exc:
            print(f"[file-middleware] get_config failed: {exc}", flush=True)
        return None

    def _build_context(self, thread_id: str) -> str | None:
        docs = UPLOADED_DOCS.get(thread_id, [])
        if not docs:
            return None

        sections: list[str] = []
        total = 0
        for doc in docs:
            snippet = doc.content
            if len(snippet) > self._max_file_chars:
                snippet = snippet[: self._max_file_chars] + "\n...[truncated]"
            section = f"=== FILE: {doc.filename} ({doc.mime_type}) ===\n{snippet}\n=== END FILE ==="
            if total + len(section) > self._max_total_chars:
                break
            sections.append(section)
            total += len(section)

        if not sections:
            return None

        filenames = ", ".join(f'"{d.filename}"' for d in docs[: len(sections)])
        return (
            f"=== ABSOLUTE OVERRIDE INSTRUCTION ===\n"
            f"The user uploaded {len(sections)} file(s): {filenames}\n"
            f"The complete file contents are already included below.\n"
            f"You are FORBIDDEN from calling any tool to fetch uploaded files.\n"
            f"You are FORBIDDEN from saying the file is empty, missing, or not uploaded.\n"
            f"You MUST answer directly using the file contents below.\n"
            f"If asked to summarize, summarize the uploaded file content and cite the filename.\n\n"
            + "\n\n".join(sections)
        )

    def _merge(self, request: ModelRequest) -> ModelRequest:
        thread_id = self._get_thread_id(request)
        if not thread_id:
            return request
        ctx = self._build_context(thread_id)
        if not ctx:
            return request
        print(
            f"[file-middleware] injecting {len(ctx)} chars for thread {thread_id}",
            flush=True,
        )
        # APPEND the file context at the END (after other system messages)
        # so it's the most recent instruction the model sees.
        return request.override(
            messages=[*request.messages, SystemMessage(content=ctx)],
        )

    def wrap_model_call(self, request, handler):
        return handler(self._merge(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._merge(request))


llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    max_output_tokens=8192,
)

agent = create_agent(
    model=llm,
    tools=[query_data, *todo_tools, generate_a2ui, search_flights],
    middleware=[
        UploadedFileContextMiddleware(),
        SystemMessageMergerMiddleware(),
        CopilotKitMiddleware(),
    ],
    state_schema=AgentState,
    system_prompt="""
You are a polished, professional tech demo assistant.

RESPONSE RULES (follow strictly):
- ALWAYS give complete, thorough answers. Never truncate or summarize prematurely.
- NEVER give one-liner responses unless the user explicitly says "short answer" or "briefly".
- For technical questions: include explanation, steps, and a concrete example.
- For analytical questions: cover all relevant angles before concluding.
- After any tool call, ALWAYS produce a final assistant message to the user. Never end the run with tool output only.

UPLOADED FILES:
- If "Uploaded file context" appears anywhere in the system prompt, the user HAS uploaded files and their full content is provided to you directly in that context block.
- DO NOT call any tool to fetch uploaded files — there is no such tool. The file content is already in your context.
- Any vague request like "summarize this", "what is this", "explain the file", or "summarize the file" refers to the uploaded files. Read the "Uploaded file context" block and answer immediately.
- ALWAYS cite the filename when answering from uploaded file context.
- NEVER say "please upload a file" if "Uploaded file context" is present in your system prompt — the file is already there.

TOOL GUIDANCE:
- Flights: call `search_flights` to show flight cards.
- Dashboards & rich UI: call `generate_a2ui` to create dashboards.
- Charts: call `query_data` before rendering charts.
- Todos: use `manage_todos` / `get_todos`.
""",
)

graph = agent
