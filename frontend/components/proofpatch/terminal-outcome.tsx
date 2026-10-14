import type { Run } from "@/lib/proofpatch/types";
import {
  terminalStrip,
  completionEvidence,
  completedIntroduction,
  changeExplanation,
} from "@/lib/proofpatch/outcome";
import { githubURL, percent, text } from "@/lib/proofpatch/formatting";
import { Details, Result } from "./evidence-panel";

export function TerminalOutcome({
  run,
  animate = false,
}: {
  run: Run;
  animate?: boolean;
}) {
  const strip = terminalStrip(run);
  if (!strip) return null;
  const state = run.state_json ?? {};
  const complete = run.status === "COMPLETED";
  const selected = state.hypotheses?.find(
    (h) => h.id === state.selected_hypothesis_id || h.selected,
  );
  const evidence = completionEvidence(state);
  const prURL = githubURL(state.pr?.url);
  const lastRejected = [...(state.attempt_history ?? [])]
    .reverse()
    .find((attempt) => attempt.outcome === "REJECTED");
  const rejectedValidation = lastRejected?.validation ?? state.validation;
  const rejectedBenchmark = lastRejected?.benchmark ?? state.benchmark;
  const allPassed = evidence.every((check) => check.passed === true);
  return (
    <section
      className={`terminal-outcome outcome-${run.status.toLowerCase()} ${animate ? "outcome-enter" : ""}`}
      aria-labelledby="outcome-title"
    >
      <header className="outcome-heading">
        <div className="outcome-symbol" aria-hidden="true">
          {complete
            ? "✓"
            : run.status === "UNVERIFIED"
              ? "○"
              : run.status === "FAILED"
                ? "✕"
                : "—"}
        </div>
        <div>
          <div className="eyebrow">RUN OUTCOME / {run.status}</div>
          <h2 id="outcome-title">
            {complete ? "Optimization completed" : strip.title.slice(2)}
          </h2>
        </div>
      </header>
      <p className="outcome-intro">
        {complete ? completedIntroduction(run) : strip.description}
      </p>
      {complete && (
        <>
          <dl className="outcome-summary">
            <div className="summary-wide">
              <dt>Selected hypothesis</dt>
              <dd>
                {selected?.summary ||
                  state.selected_hypothesis_id ||
                  "Not recorded"}
              </dd>
            </div>
            <div>
              <dt>Coder attempts</dt>
              <dd className="mono">
                {state.iteration_count != null
                  ? `${state.iteration_count} / 2`
                  : "Not recorded"}
              </dd>
            </div>
            <div>
              <dt>Correctness</dt>
              <dd>
                <OutcomeResult passed={evidence[1].passed} />
              </dd>
            </div>
            <div>
              <dt>Performance threshold</dt>
              <dd>
                <OutcomeResult passed={evidence[2].passed} />
                {state.benchmark?.threshold_percent != null && (
                  <span className="summary-detail">
                    Required: {percent(state.benchmark.threshold_percent)}
                  </span>
                )}
              </dd>
            </div>
            <div>
              <dt>Measured improvement · this run</dt>
              <dd className="outcome-metric mono">
                {state.benchmark?.improvement_percent != null
                  ? percent(state.benchmark.improvement_percent)
                  : "Not recorded"}
              </dd>
            </div>
            <div>
              <dt>Deterministic verification</dt>
              <dd>
                <OutcomeResult passed={evidence[3].passed} />
              </dd>
            </div>
            <div>
              <dt>Pull request</dt>
              <dd className="mono">
                {state.pr?.number != null
                  ? `#${state.pr.number}`
                  : "Not recorded"}
              </dd>
            </div>
            <div className="summary-wide">
              <dt>Reviewer recommendation</dt>
              <dd>{state.review?.recommendation || "Not recorded"}</dd>
            </div>
            <div className="summary-wide">
              <dt>Publication branch</dt>
              <dd className="mono wrap">
                {state.pr?.branch && state.pr.base_branch
                  ? `${state.pr.branch} → ${state.pr.base_branch}`
                  : "Not recorded"}
              </dd>
            </div>
          </dl>
          <div className="outcome-explanation">
            <h3>What changed</h3>
            <p>{changeExplanation(state)}</p>
          </div>
          <div className="outcome-explanation">
            <h3>Why it is safe</h3>
            <p>
              {allPassed
                ? "Static policy, correctness validation, benchmark threshold, deterministic verification, and explicit human PR approval passed."
                : "Recorded checks are listed below. A missing result is not treated as a passing result."}
            </p>
            <ul className="safety-checks">
              {evidence.map((check) => (
                <li key={check.name}>
                  <span>{check.name}</span>
                  <OutcomeResult passed={check.passed} />
                </li>
              ))}
            </ul>
          </div>
          <div className="outcome-footer">
            <span className="muted">
              Review the patch and its evidence on GitHub.
            </span>
            {prURL ? (
              <a
                className="button"
                href={prURL}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open pull request ↗
              </a>
            ) : (
              <span className="muted">Pull request link not recorded.</span>
            )}
          </div>
        </>
      )}
      {run.status === "UNVERIFIED" && (
        <div className="outcome-explanation">
          <h3>Last rejected candidate</h3>
          {lastRejected ? (
            <>
              <div className="rejection-heading">
                <span className="mono">
                  Attempt {lastRejected.iteration ?? "—"} / 2
                </span>
                <span className="result fail">× Rejected</span>
              </div>
              <p>
                {lastRejected.reason || "No rejection reason was recorded."}
              </p>
              {lastRejected.failure_stage && (
                <p className="mono muted">
                  Failure stage: {lastRejected.failure_stage}
                </p>
              )}
            </>
          ) : (
            <p>No rejected-attempt record was provided.</p>
          )}
          <dl className="outcome-summary">
            <div>
              <dt>Correctness</dt>
              <dd>
                <OutcomeResult
                  passed={rejectedValidation?.correctness_passed}
                />
              </dd>
            </div>
            <div>
              <dt>Benchmark threshold</dt>
              <dd>
                <OutcomeResult passed={rejectedBenchmark?.passed} />
              </dd>
            </div>
            {rejectedBenchmark?.improvement_percent != null && (
              <div>
                <dt>Measured improvement</dt>
                <dd className="mono">
                  {percent(rejectedBenchmark.improvement_percent)}
                </dd>
              </div>
            )}
            {rejectedBenchmark?.threshold_percent != null && (
              <div>
                <dt>Required threshold</dt>
                <dd className="mono">
                  {percent(rejectedBenchmark.threshold_percent)}
                </dd>
              </div>
            )}
          </dl>
          <Details
            value={{
              policy: lastRejected?.changes?.policy ?? state.changes?.policy,
              validation: rejectedValidation,
              benchmark: rejectedBenchmark,
              verification: lastRejected?.verification ?? state.verification,
            }}
            label="Final candidate evidence"
          />
        </div>
      )}
      {run.status === "FAILED" && (
        <>
          <div className="outcome-error">
            <h3>Latest backend error</h3>
            <p>
              {text(state.errors?.at(-1)) ||
                "No further error detail was recorded."}
            </p>
          </div>
          <Details value={state.errors} label="Error history" />
        </>
      )}
      {run.status === "CANCELLED" && (
        <p className="outcome-preserved">
          Any hypotheses, candidate changes, and test or benchmark evidence
          produced before cancellation remain in the report below.
        </p>
      )}
    </section>
  );
}

function OutcomeResult({ passed }: { passed?: boolean }) {
  return passed == null ? (
    <span className="result neutral">Not recorded</span>
  ) : (
    <Result passed={passed} />
  );
}
export function TerminalStatusStrip({ run }: { run: Run }) {
  const copy = terminalStrip(run);
  if (!copy) return null;
  return (
    <section
      className={`status-strip terminal-status ${run.status === "COMPLETED" ? "pass" : run.status === "FAILED" ? "fail" : run.status === "UNVERIFIED" ? "waiting" : "neutral"}`}
      aria-live="polite"
    >
      <div>
        <b>{copy.title}</b>
        <p>{copy.description}</p>
      </div>
      <span className="mono status-final">FINAL</span>
    </section>
  );
}
