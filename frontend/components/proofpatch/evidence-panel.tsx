import type {
  RunState,
  ValidationEvidence,
  BenchmarkEvidence,
  VerificationEvidence,
  ReviewEvidence,
} from "@/lib/proofpatch/types";
import { percent, text, timing } from "@/lib/proofpatch/formatting";
export function Panel({
  title,
  label,
  children,
}: {
  title: string;
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="panel evidence">
      <div className="panel-heading">
        <h2>{title}</h2>
        {label && <span className="mono muted">{label}</span>}
      </div>
      {children}
    </section>
  );
}
export function Result({ passed }: { passed?: boolean }) {
  return (
    <span
      className={`result ${passed == null ? "neutral" : passed ? "pass" : "fail"}`}
    >
      {passed == null ? "Pending" : passed ? "Passed" : "Not passed"}
    </span>
  );
}
function Row({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="data-row">
      <span className="muted">{name}</span>
      <span>{children}</span>
    </div>
  );
}
export function Details({
  value,
  label = "Technical details",
}: {
  value: unknown;
  label?: string;
}) {
  if (value == null || text(value) === "") return null;
  return (
    <details>
      <summary>{label}</summary>
      <pre>{text(value)}</pre>
    </details>
  );
}
export function ValidationPanel({ data }: { data?: ValidationEvidence }) {
  return (
    <Panel title="Correctness validation" label="DOCKER">
      <Row name="Correctness">
        <Result passed={data?.correctness_passed} />
      </Row>
      <Row name="Test strategy">
        {data?.strategy === "existing_tests"
          ? "Existing repository tests"
          : data?.strategy === "hypothesis_differential"
            ? "Generated differential tests"
            : "Awaiting validation"}
      </Row>
      {(["baseline", "candidate", "differential"] as const).map(
        (key) =>
          data?.[key] && (
            <div key={key}>
              <Row name={`${key[0].toUpperCase()}${key.slice(1)}`}>
                <Result passed={data[key]?.passed} />
              </Row>
              {data[key]?.duration_ms != null && (
                <Row name="Execution duration">
                  <span className="mono">
                    {timing(data[key]!.duration_ms! / 1000)}
                  </span>
                </Row>
              )}
              <Details
                value={[data[key]?.stdout, data[key]?.stderr]
                  .filter(Boolean)
                  .join("\n")}
                label={`${key} technical details`}
              />
            </div>
          ),
      )}
    </Panel>
  );
}
export function BenchmarkPanel({ data }: { data?: BenchmarkEvidence }) {
  const values = [
    data?.baseline?.median_seconds,
    data?.candidate?.median_seconds,
  ];
  const max = Math.max(
    ...values.filter((v): v is number => v != null && Number.isFinite(v)),
    0,
  );
  return (
    <Panel title="Performance benchmark" label="PYPERF">
      <div className="benchmark-values">
        <div>
          <span className="muted">Baseline median</span>
          <strong>{timing(values[0])}</strong>
        </div>
        <div>
          <span className="muted">Candidate median</span>
          <strong>{timing(values[1])}</strong>
        </div>
      </div>
      {max > 0 && (
        <div className="bars" aria-label="Median runtime comparison">
          {values.map(
            (value, index) =>
              value != null &&
              Number.isFinite(value) && (
                <div className="bar-row" key={index}>
                  <span>{index === 0 ? "Baseline" : "Candidate"}</span>
                  <div className="bar-track">
                    <div
                      className={`bar ${index === 1 ? "candidate" : ""}`}
                      style={{ width: `${Math.max(0, (value / max) * 100)}%` }}
                    />
                  </div>
                </div>
              ),
          )}
        </div>
      )}
      <Row name="Measured improvement">
        <span className="mono">{percent(data?.improvement_percent)}</span>
      </Row>
      <Row name="Required threshold">
        <span className="mono">{percent(data?.threshold_percent)}</span>
      </Row>
      <Row name="Benchmark result">
        <Result passed={data?.passed} />
      </Row>
      <p className="field-help">
        Measurements apply to this candidate and this run.
      </p>
      {data?.baseline && (
        <Details
          value={{ baseline: data.baseline, candidate: data.candidate }}
          label="Sampling details"
        />
      )}
    </Panel>
  );
}
export function VerificationPanel({
  data,
  policy,
}: {
  data?: VerificationEvidence;
  policy?: boolean;
}) {
  return (
    <Panel title="Deterministic verification" label="NON-LLM">
      <p className="section-copy">
        ProofPatch accepts a patch only when policy, correctness, and
        performance evidence all pass.
      </p>
      <Row name="Static policy">
        <Result passed={data?.policy_passed ?? policy} />
      </Row>
      <Row name="Correctness">
        <Result passed={data?.correctness_passed} />
      </Row>
      <Row name="Performance">
        <Result passed={data?.performance_passed} />
      </Row>
      <Row name="Verification">
        <Result passed={data?.passed} />
      </Row>
      {data?.reasons?.map((reason, index) => (
        <p className="error-message" key={index}>
          {reason}
        </p>
      ))}
    </Panel>
  );
}
export function ReviewPanel({ data }: { data?: ReviewEvidence }) {
  const sections: [string, unknown][] = [
    ["Review summary", data?.summary],
    ["Change", data?.change_explanation],
    ["Correctness", data?.correctness_summary],
    ["Performance", data?.performance_summary],
    ["Risks / trade-offs", data?.risks_and_tradeoffs],
    ["Recommendation", data?.recommendation],
  ];
  return (
    <Panel title="Reviewer assessment" label="AI SUMMARY">
      <p className="field-help">
        The reviewer summarizes evidence. Deterministic verification decides
        acceptance.
      </p>
      {sections.map(
        ([label, value]) =>
          value != null && (
            <div className="review-section" key={label}>
              <h3>{label}</h3>
              {Array.isArray(value) ? (
                value.length ? (
                  <ul>
                    {value.map((item, index) => (
                      <li key={index}>{text(item)}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No risks reported by the reviewer.</p>
                )
              ) : (
                <p>{text(value)}</p>
              )}
            </div>
          ),
      )}
      {!data?.summary && (
        <p className="muted">
          The reviewer’s assessment will appear here when available.
        </p>
      )}
    </Panel>
  );
}
export function AttemptHistory({
  state,
  stopped = false,
}: {
  state: RunState;
  stopped?: boolean;
}) {
  const history = state.attempt_history ?? [];
  const iteration = state.iteration_count ?? 0;
  if (!history.length && !iteration) return null;
  const currentArchived = history.some((item) => item.iteration === iteration);
  return (
    <Panel title="Coder attempts" label={`${iteration} / 2`}>
      <p className="field-help">
        Rejected candidates remain in the evidence trail.
      </p>
      {history.map((attempt, index) => (
        <article className="attempt" key={index}>
          <div className="attempt-heading">
            <b>Attempt {attempt.iteration ?? index + 1}</b>
            <span className="result fail">Rejected</span>
          </div>
          <p>
            {attempt.reason ||
              "Candidate did not satisfy verification requirements."}
          </p>
          {attempt.failure_stage && (
            <span className="mono muted">{attempt.failure_stage}</span>
          )}
          <Details
            label="Archived attempt evidence"
            value={{
              policy: attempt.changes?.policy,
              validation: attempt.validation,
              benchmark: attempt.benchmark,
              verification: attempt.verification,
            }}
          />
        </article>
      ))}
      {iteration > 0 && !currentArchived && (
        <article className="attempt">
          <div className="attempt-heading">
            <b>Attempt {iteration}</b>
            <span
              className={`result ${state.verification?.passed ? "pass" : "neutral"}`}
            >
              {state.verification?.passed
                ? "Verified"
                : stopped
                  ? "Stopped"
                  : "Current"}
            </span>
          </div>
        </article>
      )}
      {state.retry_feedback != null && (
        <Details value={state.retry_feedback} label="Coder retry feedback" />
      )}
    </Panel>
  );
}
