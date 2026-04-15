import {
  CopilotRuntime,
  createCopilotEndpoint,
  InMemoryAgentRunner,
} from "@copilotkit/runtime/v2";
import { LangGraphAgent } from "@copilotkit/runtime/langgraph";
import { handle } from "hono/vercel";

const defaultAgent = new LangGraphAgent({
  deploymentUrl:
    process.env.AGENT_URL ||
    process.env.LANGGRAPH_DEPLOYMENT_URL ||
    "http://localhost:2024",
  graphId: "sample_agent",
  langsmithApiKey: process.env.LANGSMITH_API_KEY || "",
});

const runtime = new CopilotRuntime({
  agents: { default: defaultAgent },
  runner: new InMemoryAgentRunner(),
  beforeRequestMiddleware: async ({ request }) => {
    if (request.method !== "POST") return;

    const contentType = request.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return;

    // ✅ CLONE FIRST
    const clonedRequest = request.clone();

    let body: Record<string, unknown>;
    try {
      body = (await clonedRequest.json()) as Record<string, unknown>;
    } catch {
      return;
    }

    const forwardedProps =
      (body.forwardedProps as Record<string, unknown> | undefined) ?? {};

    const streamMode = forwardedProps.streamMode;

    const hasMessagesTuple =
      Array.isArray(streamMode) && streamMode.includes("messages-tuple");

    if (!hasMessagesTuple) return;

    const patchedBody = {
      ...body,
      forwardedProps: {
        ...forwardedProps,
        // streamMode: ["events", "values", "updates"],
        streamMode: Array.from(
          new Set(
            [
              ...(streamMode as string[]),
              "events",
              "values",
              "updates",
            ]
          )
        )
      },
    };

    // ✅ RETURN NEW REQUEST (safe now)
    return new Request(request.url, {
      method: request.method,
      headers: request.headers,
      body: JSON.stringify(patchedBody),
    });
  },
  openGenerativeUI: true,
  a2ui: {
    injectA2UITool: false,
  },
  mcpApps: {
    servers: [
      {
        type: "http",
        url: process.env.MCP_SERVER_URL || "https://mcp.excalidraw.com",
        serverId: "example_mcp_app",
      },
    ],
  },
});

const app = createCopilotEndpoint({
  runtime,
  basePath: "/api/copilotkit",
});

export const GET = handle(app);
export const POST = handle(app);
