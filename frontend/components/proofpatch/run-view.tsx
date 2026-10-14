"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Run, RunEvent } from "@/lib/proofpatch/types";
import {
  getRun,
  getRunEvents,
  selectHypothesis,
  approvePR,
  rejectPR,
  retryPR,
  cancelRun,
} from "@/lib/proofpatch/api";
import {
  canCancel,
  humanWait,
  statusCopy,
  terminal,
  tone,
} from "@/lib/proofpatch/status";
import { githubURL, text } from "@/lib/proofpatch/formatting";
import {
  AttemptHistory,
  BenchmarkPanel,
  Details,
  Panel,
  ReviewPanel,
  ValidationPanel,
  VerificationPanel,
} from "./evidence-panel";
import { HypothesisList } from "./hypothesis-list";
import { WorkflowTimeline } from "./workflow-timeline";
export function RunView({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connectionError, setConnectionError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState<string | null>(null);
  const actionLock = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshRef = useRef<() => Promise<void>>(async () => {});
  const active = useRef(false);
  const modal = useRef<HTMLDialogElement>(null);
  const [confirm, setConfirm] = useState<"reject" | "cancel">("reject");
  const refresh = useCallback(async () => {
    if (timer.current) clearTimeout(timer.current);
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    let nextDelay: number | null = 2000;
    try {
      const [runResult, eventResult] = await Promise.allSettled([
        getRun(runId, abort.signal),
        getRunEvents(runId, abort.signal),
      ]);
      if (abort.signal.aborted || !active.current) return;
      const failures: string[] = [];
      if (runResult.status === "fulfilled") {
        const next = runResult.value;
        setRun(next);
        setAccepted((previous) =>
          previous &&
          previous !== `${next.status}:${next.state_json?.pr?.status ?? ""}`
            ? null
            : previous,
        );
        nextDelay = terminal.has(next.status)
          ? null
          : humanWait.has(next.status)
            ? 3000
            : 1800;
      } else {
        failures.push(
          runResult.reason instanceof Error
            ? runResult.reason.message
            : "Could not fetch run.",
        );
      }
      if (eventResult.status === "fulfilled") setEvents(eventResult.value);
      else
        failures.push(
          eventResult.reason instanceof Error
            ? eventResult.reason.message
            : "Could not fetch events.",
        );
      setConnectionError(failures.join(" "));
      if (failures.length) nextDelay = 3000;
    } finally {
      if (!abort.signal.aborted && active.current && nextDelay != null)
        timer.current = setTimeout(() => {
          void refreshRef.current();
        }, nextDelay);
    }
  }, [runId]);
  useEffect(() => {
    active.current = true;
    refreshRef.current = refresh;
    void refresh();
    return () => {
      active.current = false;
      controller.current?.abort();
      if (timer.current) clearTimeout(timer.current);
    };
  }, [refresh]);
  async function act(operation: () => Promise<unknown>) {
    if (actionLock.current || !run) return;
    actionLock.current = true;
    setBusy(true);
    setActionError("");
    try {
      await operation();
      if (active.current)
        setAccepted(`${run.status}:${run.state_json?.pr?.status ?? ""}`);
    } catch (error) {
      if (active.current)
        setActionError(
          error instanceof Error
            ? error.message
            : "The action could not be completed.",
        );
    } finally {
      if (active.current) {
        await refresh();
        setBusy(false);
      }
      actionLock.current = false;
    }
  }
  const disabled = busy || accepted != null;
  const state = run?.state_json ?? {};
  const pr = state.pr;
  const retryable =
    run?.status === "CREATING_PR" && pr?.status === "FAILED_RETRYABLE";
  const prURL = githubURL(pr?.url);
  const openConfirm = (kind: "reject" | "cancel") => {
    setConfirm(kind);
    modal.current?.showModal();
  };
  return (
    <main className="run-page">
      <Link className="back-link" href="/">
        ← New run
      </Link>
      {!run ? (
        <section className="panel loading">
          <h1>Loading run</h1>
          <p className="mono muted">{runId}</p>
          {connectionError ? (
            <p className="error-message" role="alert">
              {connectionError}
            </p>
          ) : (
            <p role="status">Fetching backend state…</p>
          )}
          <button className="secondary" onClick={() => void refresh()}>
            Refresh
          </button>
        </section>
      ) : (
        <>
          <div className="run-heading">
            <div>
              <div className="eyebrow">
                OPTIMIZATION RUN / {run.id.slice(0, 8)}
              </div>
              <h1>
                {run.target_function}
                <span className="mono">()</span>
              </h1>
              <p className="run-target">
                {githubURL(run.repo_url) ? (
                  <a
                    href={githubURL(run.repo_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {run.repo_url.replace("https://github.com/", "")}
                  </a>
                ) : (
                  run.repo_url
                )}
                <span>/</span>
                <code>{run.target_file}</code>
              </p>
            </div>
            <span className={`status-badge ${tone(run.status)}`}>
              {run.status.replaceAll("_", " ")}
            </span>
          </div>
          <section
            className={`status-strip ${tone(run.status)}`}
            aria-live="polite"
          >
            <span
              className={
                !terminal.has(run.status) &&
                !humanWait.has(run.status) &&
                !retryable
                  ? "activity-dot"
                  : "status-dot"
              }
            />
            <div>
              <b>
                {retryable
                  ? "GitHub publication needs attention"
                  : humanWait.has(run.status)
                    ? "Your decision is needed"
                    : run.status.replaceAll("_", " ")}
              </b>
              <p>
                {retryable
                  ? "GitHub operation failed. The verified patch is preserved and can be retried."
                  : statusCopy[run.status]}
              </p>
            </div>
            {canCancel(run) && (
              <button
                className="secondary"
                disabled={disabled}
                onClick={() => openConfirm("cancel")}
              >
                Cancel run
              </button>
            )}
          </section>
          {connectionError && (
            <div className="error-message" role="alert">
              {connectionError}{" "}
              <button className="secondary" onClick={() => void refresh()}>
                Refresh
              </button>
            </div>
          )}
          {actionError && (
            <p className="error-message" role="alert">
              {actionError}
            </p>
          )}
          {accepted != null && (
            <p className="field-help" role="status">
              Decision accepted. Waiting for the latest backend state…
            </p>
          )}
          <div className="run-grid">
            <div className="main-column">
              {run.status === "FAILED" && (
                <Panel title="Run stopped">
                  <p>{statusCopy.FAILED}</p>
                  <p className="error-message">
                    {text(state.errors?.at(-1)) ||
                      "No further error detail was provided."}
                  </p>
                  <Details value={state.errors} label="Error history" />
                </Panel>
              )}
              {run.status === "UNVERIFIED" && (
                <Panel title="No verified candidate">
                  <p>{statusCopy.UNVERIFIED}</p>
                </Panel>
              )}
              <HypothesisList
                run={run}
                disabled={disabled}
                onSelect={(id) => void act(() => selectHypothesis(runId, id))}
              />
              <AttemptHistory
                state={state}
                stopped={terminal.has(run.status)}
              />
              {state.iteration_count || state.validation?.strategy ? (
                <>
                  <ValidationPanel data={state.validation} />
                  <BenchmarkPanel data={state.benchmark} />
                  <VerificationPanel
                    data={state.verification}
                    policy={state.changes?.policy?.passed}
                  />
                </>
              ) : null}
              {(state.changes?.diff || state.changes?.unified_diff) && (
                <Panel title="Candidate patch">
                  <Details
                    value={state.changes.diff ?? state.changes.unified_diff}
                    label="Inspect patch diff"
                  />
                </Panel>
              )}
              {(state.review?.summary ||
                run.status === "REVIEWING" ||
                run.status === "WAITING_FOR_PR_APPROVAL") && (
                <ReviewPanel data={state.review} />
              )}{" "}
              {run.status === "WAITING_FOR_PR_APPROVAL" && (
                <Panel title="Publish this patch?" label="HUMAN GATE 02">
                  <p className="section-copy">
                    Approval authorizes ProofPatch to create a GitHub branch,
                    commit, and pull request for this candidate.
                  </p>
                  <div className="actions">
                    <button
                      disabled={disabled}
                      onClick={() => void act(() => approvePR(runId))}
                    >
                      {busy ? "Submitting…" : "Approve PR"}
                    </button>
                    <button
                      className="danger"
                      disabled={disabled}
                      onClick={() => openConfirm("reject")}
                    >
                      Reject
                    </button>
                  </div>
                </Panel>
              )}
              {(run.status === "CREATING_PR" ||
                run.status === "COMPLETED" ||
                pr?.status) && (
                <Panel
                  title={
                    run.status === "COMPLETED"
                      ? "Pull request created"
                      : "GitHub publication"
                  }
                  label={pr?.status ?? "PENDING"}
                >
                  {pr?.number != null && <h3>Pull request #{pr.number}</h3>}
                  {pr?.branch && (
                    <p className="mono wrap">
                      {pr.branch} → {pr.base_branch ?? "—"}
                    </p>
                  )}
                  {pr?.attempt_count != null && (
                    <p className="muted">
                      Publication attempt {pr.attempt_count}
                    </p>
                  )}
                  {retryable && (
                    <>
                      <p>
                        GitHub operation failed. The verified patch is preserved
                        and can be retried.
                      </p>
                      <Details value={pr?.last_error} />
                      <button
                        disabled={disabled}
                        onClick={() => void act(() => retryPR(runId))}
                      >
                        Retry PR creation
                      </button>
                    </>
                  )}
                  {prURL && (
                    <a
                      className="button"
                      href={prURL}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open pull request ↗
                    </a>
                  )}
                </Panel>
              )}
              {!state.iteration_count &&
                !state.hypotheses?.length &&
                !terminal.has(run.status) && (
                  <Panel title="Repository analysis">
                    <p className="section-copy">
                      The target is being inspected. Hypotheses and evidence
                      will appear as the backend produces them.
                    </p>
                    <div className="target-summary">
                      <code>{run.target_file}</code>
                      <code>{run.target_function}()</code>
                    </div>
                  </Panel>
                )}
            </div>
            <aside className="side-column">
              <WorkflowTimeline run={run} events={events} />
            </aside>
          </div>
        </>
      )}
      <dialog
        ref={modal}
        aria-labelledby="confirm-title"
        onCancel={() => modal.current?.close()}
      >
        <h2 id="confirm-title">
          {confirm === "reject" ? "Reject this patch?" : "Cancel this run?"}
        </h2>
        <p>
          This terminates the run and starts workspace cleanup. A pull request
          will not be created.
        </p>
        <div className="actions">
          <button className="secondary" onClick={() => modal.current?.close()}>
            Keep run
          </button>
          <button
            className="danger"
            disabled={disabled}
            onClick={() => {
              modal.current?.close();
              void act(() =>
                confirm === "reject" ? rejectPR(runId) : cancelRun(runId),
              );
            }}
          >
            {confirm === "reject" ? "Reject patch" : "Cancel run"}
          </button>
        </div>
      </dialog>
    </main>
  );
}
