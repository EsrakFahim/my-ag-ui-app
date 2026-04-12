"""
This is the main entry point for the agent.
It defines the workflow graph, state, tools, nodes and edges.
"""

from copilotkit import CopilotKitMiddleware
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Data & state tools
from src.query import query_data
from src.todos import AgentState, todo_tools

# A2UI tools
from src.a2ui_dynamic_schema import generate_a2ui
from src.a2ui_fixed_schema import search_flights

import warnings
if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    warnings.warn("GEMINI_API_KEY environment variable is not set. Gemini API calls will fail.")

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key)

agent = create_agent(
    model=llm,
    tools=[query_data, *todo_tools, generate_a2ui, search_flights],
    middleware=[CopilotKitMiddleware()],
    state_schema=AgentState,
    # system_prompt="""
    #     You are a polished, professional demo assistant. Keep responses to 1-2 sentences.

    #     Tool guidance:
    #     - Flights: call search_flights to show flight cards with a pre-built schema.
    #     - Dashboards & rich UI: call generate_a2ui to create dashboard UIs with metrics,
    #       charts, tables, and cards. It handles rendering automatically.
    #     - Charts: call query_data first, then render with the chart component.
    #     - Todos: enable app mode first, then manage todos.
    #     - A2UI actions: when you see a log_a2ui_event result (e.g. "view_details"),
    #       respond with a brief confirmation. The UI already updated on the frontend.
    # """,
    system_prompt="""
    You are a polished, professional tech demo assistant. Do not truncate your responses. Provide full, comprehensive, and detailed answers to user queries.
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
