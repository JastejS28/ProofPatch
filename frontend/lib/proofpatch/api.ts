import type { Run, RunEvent, RunInput, RunStatus } from "./types";
import { text } from "./formatting";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/proofpatch${path}`, {
    ...options,
    cache: "no-store",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok)
    throw new ApiError(
      response.status,
      text((data as { detail?: unknown } | null)?.detail) ||
        `Request failed (${response.status}).`,
    );
  return data as T;
}
const path = (id: string) => `/runs/${encodeURIComponent(id)}`;
export const createRun = (input: RunInput) =>
  request<{ run_id: string; status: RunStatus }>("/runs", {
    method: "POST",
    body: JSON.stringify(input),
  });
export const getRun = (id: string, signal?: AbortSignal) =>
  request<Run>(path(id), { signal });
export const getRunEvents = (id: string, signal?: AbortSignal) =>
  request<RunEvent[]>(`${path(id)}/events`, { signal });
const decision = (id: string, type: string, value?: string) =>
  request(`${path(id)}/decision`, {
    method: "POST",
    body: JSON.stringify({ type, ...(value ? { value } : {}) }),
  });
export const selectHypothesis = (id: string, value: string) =>
  decision(id, "candidate", value);
export const approvePR = (id: string) => decision(id, "pr_approval");
export const rejectPR = (id: string) => decision(id, "reject");
export const retryPR = (id: string) =>
  request(`${path(id)}/retry-pr`, { method: "POST" });
export const cancelRun = (id: string) =>
  request(`${path(id)}/cancel`, { method: "POST" });
