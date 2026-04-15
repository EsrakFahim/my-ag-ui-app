"use client";

import { useAgent } from "@copilotkit/react-core/v2";
import { TodoList } from "./todo-list";

export function ExampleCanvas() {
  const { agent } = useAgent();
  const uploadedFilesCount = Array.isArray(agent.state?.uploaded_files)
    ? agent.state.uploaded_files.length
    : 0;

  return (
    <div className="h-full overflow-y-auto bg-[--background]">
      <div className="max-w-4xl mx-auto px-8 py-10 h-full">
        {uploadedFilesCount > 0 ? (
          <div className="mb-4 rounded-md border border-[--border] bg-[--card] px-4 py-2 text-sm text-[--muted-foreground]">
            Agent file context: {uploadedFilesCount} uploaded file
            {uploadedFilesCount === 1 ? "" : "s"}
          </div>
        ) : null}
        <TodoList
          todos={agent.state?.todos || []}
          onUpdate={(updatedTodos) => agent.setState({ todos: updatedTodos })}
          isAgentRunning={agent.isRunning}
        />
      </div>
    </div>
  );
}
