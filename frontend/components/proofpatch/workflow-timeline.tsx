import type { Run, RunEvent } from "@/lib/proofpatch/types";
import {
  phases,
  phaseIndex,
  humanWait,
  terminal,
} from "@/lib/proofpatch/status";
import { date, text } from "@/lib/proofpatch/formatting";
import { Panel, Details } from "./evidence-panel";
export function WorkflowTimeline({
  run,
  events,
}: {
  run: Run;
  events: RunEvent[];
}) {
  const latestPhase = [...events]
    .reverse()
    .map((event) => phaseIndex(event.event_type))
    .find((value) => value != null);
  const current = phaseIndex(run.status) ?? latestPhase ?? 0;
  return (
    <>
      <Panel title="Workflow">
        <ol className="workflow">
          {phases.map((phase, index) => {
            const blocked =
              terminal.has(run.status) || run.status === "CANCELLING";
            const state =
              index < current
                ? "completed"
                : index === current
                  ? blocked
                    ? run.status === "FAILED" || run.status === "UNVERIFIED"
                      ? "failed"
                      : "stopped"
                    : humanWait.has(run.status)
                      ? "waiting"
                      : "current"
                  : "pending";
            return (
              <li key={phase} className={state}>
                <span className="step-symbol">
                  {state === "completed"
                    ? "✓"
                    : String(index + 1).padStart(2, "0")}
                </span>
                <span>
                  {phase}
                  <small>{state}</small>
                </span>
              </li>
            );
          })}
        </ol>
      </Panel>
      <Panel title="Run metadata">
        <dl className="metadata">
          <dt>Run ID</dt>
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
                {run.state_json.budget.llm_calls ?? 0} LLM calls ·{" "}
                {(run.state_json.budget.elapsed_sec ?? 0).toFixed(1)} s
              </dd>
            </>
          )}
        </dl>
      </Panel>
      <Panel title="Event log" label={String(events.length)}>
        <div className="event-log">
          {[...events]
            .sort(
              (a, b) =>
                new Date(a.timestamp).getTime() -
                  new Date(b.timestamp).getTime() || a.id - b.id,
            )
            .map((event) => (
              <article className="event" key={event.id}>
                <time className="mono muted" dateTime={event.timestamp}>
                  {date(event.timestamp, true)}
                </time>
                <b className="mono">{event.event_type}</b>
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
