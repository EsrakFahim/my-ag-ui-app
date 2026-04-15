import { NextRequest, NextResponse } from "next/server";

const UPLOAD_URL =
      process.env.UPLOAD_SERVER_URL || "http://localhost:2024";

export async function POST(req: NextRequest) {
      try {
            const inbound = await req.formData();
            const file = inbound.get("file");
            const threadId = inbound.get("thread_id");

            if (!(file instanceof File)) {
                  return NextResponse.json({ error: "A file is required." }, { status: 400 });
            }
            if (typeof threadId !== "string" || !threadId) {
                  return NextResponse.json({ error: "thread_id is required." }, { status: 400 });
            }

            const outbound = new FormData();
            outbound.append("file", file);
            outbound.append("thread_id", threadId);

            const res = await fetch(`${UPLOAD_URL}/documents/upload`, {
                  method: "POST",
                  body: outbound,
                  cache: "no-store",
            });

            const payload = await res.json().catch(() => ({}));
            if (!res.ok) {
                  return NextResponse.json(
                        { error: payload?.detail || "Upload failed." },
                        { status: res.status },
                  );
            }
            return NextResponse.json(payload, { status: 200 });
      } catch (err) {
            return NextResponse.json(
                  { error: err instanceof Error ? err.message : "Unexpected error" },
                  { status: 500 },
            );
      }
}