"use client";

import { ExampleLayout } from "@/components/example-layout";
import { ExampleCanvas } from "@/components/example-canvas";
import { useGenerativeUIExamples, useExampleSuggestions } from "@/hooks";
import { CopilotChat, useAgent } from "@copilotkit/react-core/v2";
import { useEffect, useState } from "react";

const uploadedDocumentAccept =
  ".txt,.md,.mdx,.csv,.json,.yaml,.yml,.log,.xml,.html,.css,.js,.jsx,.ts,.tsx,.py,.pdf";


const THREAD_STORAGE_KEY = "copilotkit:thread-id";
const UUID_V4_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function createThreadId() {
  return crypto.randomUUID();
}

function isValidThreadId(value: string | null | undefined): value is string {
  return typeof value === "string" && UUID_V4_REGEX.test(value);
}

export default function HomePage() {
  useGenerativeUIExamples();
  useExampleSuggestions();
  // const { agent } = useAgent();
  const [threadId, setThreadId] = useState<string>(() => createThreadId());

  useEffect(() => {
    const savedThreadId = window.localStorage.getItem(THREAD_STORAGE_KEY);
    if (isValidThreadId(savedThreadId)) {
      setThreadId(savedThreadId);
      return;
    }
    const freshThreadId = createThreadId();
    setThreadId(freshThreadId);
    window.localStorage.setItem(THREAD_STORAGE_KEY, freshThreadId);
  }, []);

  useEffect(() => {
    if (!isValidThreadId(threadId)) {
      return;
    }
    window.localStorage.setItem(THREAD_STORAGE_KEY, threadId);
  }, [threadId]);

  const { agent } = useAgent({ threadId });

  const uploadDocumentAsText = async (file: File) => {
    // console.log("=== UPLOAD START ===");
    // console.log("agent:", agent);
    // console.log("agent keys:", agent ? Object.keys(agent) : "no agent");
    // console.log("agent.threadId:", (agent as any)?.threadId);
    // console.log("agent.id:", (agent as any)?.id);
    // console.log("agent.state:", (agent as any)?.state);

    // const threadId =
    //   (agent as any)?.threadId ??
    //   (agent as any)?.id ??
    //   (agent?.state as any)?.thread_id ??
    //   "default";
    // console.log("Using threadId:", threadId);

    const agentThreadId = (agent as { threadId?: string } | undefined)?.threadId;
    const resolvedThreadId = isValidThreadId(agentThreadId)
      ? agentThreadId
      : threadId;

    const fd = new FormData();
    fd.append("file", file);
    fd.append("thread_id", resolvedThreadId);

    const res = await fetch("/api/upload", { method: "POST", body: fd });
    const json = await res.json().catch(() => ({}));
    // console.log("Upload response status:", res.status);
    // console.log("Upload response body:", json);
    // console.log("=== UPLOAD END ===");

    if (!res.ok) {
      throw new Error(
        (json as { error?: string })?.error ||
        "Upload failed. Please try uploading again.",
      );
    }

    return {
      type: "data" as const,
      value: `[Uploaded ${file.name} — available to the assistant for this conversation]`,
      mimeType: "text/plain",
      metadata: { filename: file.name },
    };
  };

  return (
    <ExampleLayout
      chatContent={
        <CopilotChat
          threadId={threadId}
          input={{ disclaimer: () => null, className: "pb-6" }}
          attachments={{
            enabled: true,
            accept: uploadedDocumentAccept,
            maxSize: 5 * 1024 * 1024,
            onUpload: uploadDocumentAsText,
          }}
        />
      }
      appContent={<ExampleCanvas />}
    />
  );
}