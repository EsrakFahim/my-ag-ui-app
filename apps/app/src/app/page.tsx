// "use client";

// import { ExampleLayout } from "@/components/example-layout";
// import { ExampleCanvas } from "@/components/example-canvas";
// import { useGenerativeUIExamples, useExampleSuggestions } from "@/hooks";

// import { CopilotChat } from "@copilotkit/react-core/v2";

// export default function HomePage() {
//   useGenerativeUIExamples();
//   useExampleSuggestions();

//   return (
//     <ExampleLayout
//       chatContent={
//         <CopilotChat input={{ disclaimer: () => null, className: "pb-6" }} />
//       }
//       appContent={<ExampleCanvas />}
//     />
//   );
// }

"use client";

import { ExampleLayout } from "@/components/example-layout";
import { ExampleCanvas } from "@/components/example-canvas";
import { useGenerativeUIExamples, useExampleSuggestions } from "@/hooks";
import { CopilotChat, useAgent } from "@copilotkit/react-core/v2";

const uploadedDocumentAccept =
  ".txt,.md,.mdx,.csv,.json,.yaml,.yml,.log,.xml,.html,.css,.js,.jsx,.ts,.tsx,.py,.pdf";

export default function HomePage() {
  useGenerativeUIExamples();
  useExampleSuggestions();
  const { agent } = useAgent();

  // const uploadDocumentAsText = async (file: File) => {
  //   // CopilotKit/LangGraph thread id — adjust the path if your agent exposes it differently.
  //   const threadId =
  //     (agent as any)?.threadId ??
  //     (agent?.state as any)?.thread_id ??
  //     "default";

  //   const fd = new FormData();
  //   fd.append("file", file);
  //   fd.append("thread_id", threadId);

  //   const res = await fetch("/api/upload", { method: "POST", body: fd });
  //   if (!res.ok) {
  //     const err = await res.json().catch(() => ({}));
  //     throw new Error(err?.error || "Upload failed");
  //   }

  //   // Return a tiny stub for the chat UI bubble. The model will NOT read this —
  //   // it reads the server-side store via middleware.
  //   return {
  //     type: "data" as const,
  //     value: `[Uploaded ${file.name} — available to the assistant for this conversation]`,
  //     mimeType: "text/plain",
  //     metadata: { filename: file.name },
  //   };
  // };


  const uploadDocumentAsText = async (file: File) => {
    console.log("=== UPLOAD START ===");
    console.log("agent:", agent);
    console.log("agent keys:", agent ? Object.keys(agent) : "no agent");
    console.log("agent.threadId:", (agent as any)?.threadId);
    console.log("agent.id:", (agent as any)?.id);
    console.log("agent.state:", (agent as any)?.state);

    const threadId =
      (agent as any)?.threadId ??
      (agent as any)?.id ??
      (agent?.state as any)?.thread_id ??
      "default";
    console.log("Using threadId:", threadId);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("thread_id", threadId);

    const res = await fetch("/api/upload", { method: "POST", body: fd });
    const json = await res.json().catch(() => ({}));
    console.log("Upload response status:", res.status);
    console.log("Upload response body:", json);
    console.log("=== UPLOAD END ===");

    if (!res.ok) {
      throw new Error(json?.error || "Upload failed");
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