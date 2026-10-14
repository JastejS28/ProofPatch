import { NextRequest, NextResponse } from "next/server";
export const dynamic = "force-dynamic";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  const valid =
    path[0] === "runs" &&
    ((path.length === 1 && request.method === "POST") ||
      (path.length === 2 && request.method === "GET") ||
      (path.length === 3 &&
        ((path[2] === "events" && request.method === "GET") ||
          (["decision", "retry-pr", "cancel"].includes(path[2]) &&
            request.method === "POST"))));
  if (!valid)
    return NextResponse.json(
      { detail: "Unknown ProofPatch operation." },
      { status: 404 },
    );
  try {
    const base = process.env.FASTAPI_BASE_URL || "http://127.0.0.1:8000";
    const response = await fetch(
      `${base.replace(/\/$/, "")}/${path.map(encodeURIComponent).join("/")}`,
      {
        method: request.method,
        ...(request.method === "POST"
          ? {
              body: await request.text(),
              headers: { "Content-Type": "application/json" },
            }
          : {}),
        cache: "no-store",
        signal: AbortSignal.timeout(30000),
      },
    );
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: {
        "Content-Type":
          response.headers.get("content-type") || "application/json",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "ProofPatch backend is unreachable. Check that FastAPI is running and FASTAPI_BASE_URL is configured.",
      },
      { status: 502 },
    );
  }
}
export { proxy as GET, proxy as POST };
