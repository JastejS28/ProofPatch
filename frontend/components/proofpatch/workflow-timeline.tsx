"use client";
import { useState } from "react";
import type { Run, RunEvent } from "@/lib/proofpatch/types";
import { date, text } from "@/lib/proofpatch/formatting";
import { Panel, Details } from "./evidence-panel";
export function WorkflowTimeline({
  run,
  events,
}: {
  run: Run;
  events: RunEvent[];
}) {
  const [copyState, setCopyState] = useState("");
  return (
    <>
      <Panel title="Run metadata" label="CONTEXT">
        <dl className="metadata">
          <dt>
            Run ID{" "}
            <button
              className="copy-button"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(run.id);
                  setCopyState("Copied");
                } catch {
                  setCopyState("Copy unavailable");
                }
              }}
              aria-label="Copy run ID"
            >
              {copyState || "Copy"}
            </button>
          </dt>
          <dd className="mono">{run.id}</dd>
          <dt>Created</dt>
          <dd>{date(run.created_at)}</dd>
          <dt>Last updated</dt>
          <dd>{date(run.updated_at)}</dd>
          <dt>Performance concern</dt>
          <dd>{run.problem_description}</dd>
          {run.state_json?.budget && (
            <>
              <dt>Resource usage</dt>
              <dd className="mono">
                {run.state_json.budget.llm_calls ?? "—"} LLM calls ·{" "}
                {run.state_json.budget.elapsed_sec != null
                  ? run.state_json.budget.elapsed_sec.toFixed(1)
                  : "—"}{" "}
                s
              </dd>
            </>
          )}
          {run.state_json?.workspace?.cleaned != null && (
            <>
              <dt>Workspace cleanup</dt>
              <dd>
                {run.state_json.workspace.cleaned
                  ? "✓ Cleaned"
                  : "Not yet cleaned"}
              </dd>
            </>
          )}
        </dl>
        <span className="sr-only" role="status">
          {copyState}
        </span>
      </Panel>
      <Panel title="Event activity" label={String(events.length)}>
        <div className="event-log">
          {[...events]
            .sort(
              (a, b) =>
                new Date(a.timestamp).getTime() -
                  new Date(b.timestamp).getTime() || a.id - b.id,
            )
            .map((event) => (
              <article className="event" key={event.id}>
                <div className="event-heading">
                  <time className="mono muted" dateTime={event.timestamp}>
                    {date(event.timestamp, true)}
                  </time>
                  <span
                    className={`event-indicator ${event.event_type.includes("FAILED") || event.event_type.includes("REJECTED") ? "error" : event.event_type.startsWith("WAITING") ? "wait" : ""}`}
                    aria-hidden="true"
                  />
                  <b className="mono">{event.event_type}</b>
                </div>
                {event.payload_json?.message != null && (
                  <p>{text(event.payload_json.message)}</p>
                )}
                <Details value={event.payload_json} label="Event payload" />
              </article>
            ))}
          {!events.length && (
            <p className="muted">Waiting for backend events.</p>
          )}
        </div>
      </Panel>
    </>
  );
}
