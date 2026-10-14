"use client";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Run, RunEvent, RunStatus } from "@/lib/proofpatch/types";
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
  EvidenceSummary,
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
import { WorkflowProgress } from "./workflow-progress";
import { GitHubPublication } from "./github-publication";
import { TerminalOutcome, TerminalStatusStrip } from "./terminal-outcome";
function decisionKey(run: Run) {
  return `${run.status}:${run.state_json?.selected_hypothesis_id ?? ""}:${run.state_json?.pr?.status ?? ""}:${run.state_json?.pr?.attempt_count ?? 0}`;
}
export function RunView({ runId }: { runId: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [connectionError, setConnectionError] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState<string | null>(null);
  const [completionTransition, setCompletionTransition] = useState(false);
  const previousStatus = useRef<RunStatus | null>(null);
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
        if (
          next.status === "COMPLETED" &&
          previousStatus.current != null &&
          previousStatus.current !== "COMPLETED"
        )
          setCompletionTransition(true);
        previousStatus.current = next.status;
        setRun(next);
        setAccepted((previous) =>
          previous && previous !== decisionKey(next) ? null : previous,
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
    previousStatus.current = null;
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
      if (active.current) setAccepted(decisionKey(run));
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
          <div className="eyebrow">CONNECTING TO RUN</div>
          <h1>Retrieving the evidence trail</h1>
          <div className="loading-skeleton" aria-hidden="true">
            <div />
            <div />
            <div />
          </div>
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
          <WorkflowProgress
            run={run}
            events={events}
            completionTransition={completionTransition}
          />
          {terminal.has(run.status) ? (
            <TerminalStatusStrip run={run} />
          ) : (
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
                      ? "Action required"
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
          )}
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
              <TerminalOutcome run={run} animate={completionTransition} />
              {terminal.has(run.status) && (
                <div className="report-divider">
                  <h2>Evidence trail</h2>
                  <p>Recorded hypotheses, attempts, and evaluation results.</p>
                </div>
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
                  <EvidenceSummary state={state} />
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
                  <EvidenceSummary state={state} />
                  <div className="approval-summary">
                    <h3>Reviewer recommendation</h3>
                    <p>{state.review?.recommendation ?? "Not provided"}</p>
                    <h3>Risks / trade-offs</h3>
                    <p>
                      {text(state.review?.risks_and_tradeoffs) ||
                        "No risks reported by the reviewer."}
                    </p>
                  </div>
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
              {!terminal.has(run.status) && (
                <GitHubPublication
                  run={run}
                  disabled={disabled}
                  onRetry={() => void act(() => retryPR(runId))}
                />
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
