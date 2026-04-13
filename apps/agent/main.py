"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

from typing import Callable, Awaitable

from copilotkit import CopilotKitMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
# from langchain_anthropic import ChatAnthropic
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

if not os.getenv("ANTHROPIC_API_KEY"):
    warnings.warn(
        "ANTHROPIC_API_KEY environment variable is not set. "
        "Anthropic API calls will fail."
    )


class SystemMessageMergerMiddleware(AgentMiddleware):
    """Merge all system messages into a single one at the front before the model call.

    Claude requires all system messages to be consecutive at the start of the
    message list. CopilotKit may inject additional SystemMessages mid-conversation
    (e.g. for app context), which Claude rejects.

    This middleware collects every SystemMessage from both request.system_message
    (the agent's system_prompt) and request.messages (the conversation state),
    merges their content into one SystemMessage, and passes a clean message list
    to the next handler — without touching the persisted state.
    """

    @property
    def name(self) -> str:
        return "SystemMessageMergerMiddleware"

    def _merge(self, request: ModelRequest) -> ModelRequest:
        system_parts: list[str] = []
        other_messages = []

        # Collect the agent-level system message (from system_prompt param)
        if request.system_message:
            content = request.system_message.content
            if isinstance(content, list):
                content = " ".join(
                    block.get("text", "") if isinstance(block, dict) else str(block)
                    for block in content
                )
            system_parts.append(content)

        # Collect any SystemMessages stored in the conversation state
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
        # Place the merged SystemMessage at the front; clear request.system_message
        # so _execute_model does not prepend it a second time.
        return request.override(
            messages=[merged_system, *other_messages],
            system_message=None,
        )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._merge(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(self._merge(request))


# llm = ChatAnthropic(
#     model="claude-opus-4-6",
#     max_tokens=2048,
#     temperature=0.3,  # 0 = deterministic, 1 = creative
# )
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.8,
    max_output_tokens=8192,
)

agent = create_agent(
    model=llm,
    tools=[query_data, *todo_tools, generate_a2ui, search_flights],
    middleware=[CopilotKitMiddleware()],
    state_schema=AgentState,
    system_prompt="""
    You are a polished, professional tech demo assistant.
    Default to complete, detailed responses (not one-liners) unless the user explicitly asks for a short answer.
    If helpful, structure answers with bullets, numbered steps, and concrete examples.
    You fully support analyzing images, PDFs, and other uploaded files. When a user uploads a file, process its content thoroughly and provide detailed insights.

    Tool guidance:
    - Flights: call search_flights to show flight cards with a pre-built schema.
    - Dashboards & rich UI: call generate_a2ui to create dashboard UIs with metrics,
      charts, tables, and cards. It handles rendering automatically.
    - Charts: call query_data first, then render with the chart component.
    - Todos: enable app mode first, then manage todos.
    - A2UI actions: when you see a log_a2ui_event result (e.g. "view_details"),
      respond with a brief confirmation. The UI already updated on the frontend.
    """,
)

graph = agent