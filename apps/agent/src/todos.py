from langchain.agents import AgentState as BaseAgentState
from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import TypedDict, Literal
import uuid

class Todo(TypedDict):
    id: str
    title: str
    description: str
    emoji: str
    status: Literal["pending", "completed"]


class UploadedFile(TypedDict):
    id: str
    filename: str
    mime_type: str
    content: str
    uploaded_at: str


class AgentState(BaseAgentState):
    todos: list[Todo]
    uploaded_files: list[UploadedFile]

@tool
def manage_todos(todos: list[Todo], runtime: ToolRuntime) -> Command:
    """
    Manage the current todos.
    """
    # Ensure all todos have IDs that are unique
    for todo in todos:
        if "id" not in todo or not todo["id"]:
            todo["id"] = str(uuid.uuid4())

    # Update the state
    return Command(update={
        "todos": todos,
        "messages": [
            ToolMessage(
                content="Successfully updated todos",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })

@tool
def get_todos(runtime: ToolRuntime):
    """
    Get the current todos.
    """
    return runtime.state.get("todos", [])




@tool
def manage_uploaded_files(uploaded_files: list[UploadedFile], runtime: ToolRuntime) -> Command:
    """
    Replace the current uploaded files stored in agent state.
    """
    normalized: list[UploadedFile] = []
    for item in uploaded_files:
        normalized.append({
            "id": item.get("id") or str(uuid.uuid4()),
            "filename": item.get("filename") or "uploaded-file",
            "mime_type": item.get("mime_type") or "text/plain",
            "content": item.get("content") or "",
            "uploaded_at": item.get("uploaded_at") or "",
        })

    return Command(update={
        "uploaded_files": normalized,
        "messages": [
            ToolMessage(
                content="Successfully updated uploaded files",
                tool_call_id=runtime.tool_call_id,
            )
        ],
    })


todo_tools = [
    manage_todos,
    get_todos,
    manage_uploaded_files,
]
