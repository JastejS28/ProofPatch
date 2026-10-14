import type { Run } from "@/lib/proofpatch/types";
import { githubURL } from "@/lib/proofpatch/formatting";
import { Details, Panel } from "./evidence-panel";
export function GitHubPublication({
  run,
  disabled,
  onRetry,
}: {
  run: Run;
  disabled: boolean;
  onRetry: () => void;
}) {
  const pr = run.state_json?.pr;
  if (run.status !== "CREATING_PR" && run.status !== "COMPLETED" && !pr?.status)
    return null;
  const retryable =
    run.status === "CREATING_PR" && pr?.status === "FAILED_RETRYABLE";
  const complete = run.status === "COMPLETED";
  const steps = [
    "Start publication",
    "Create branch",
    "Commit patch",
    "Create pull request",
  ];
  const progress = complete
    ? 4
    : (
        {
          IN_PROGRESS: 0,
          RETRYING: 0,
          BRANCH_CREATED: 1,
          COMMITTED: 2,
          CREATED: 4,
        } as Record<string, number>
      )[pr?.status ?? ""];
  const url = githubURL(pr?.url);
  return (
    <div className={complete ? "publication-success" : "publication"}>
      <Panel
        title={complete ? "Pull request created" : "GitHub publication"}
        label={pr?.status ?? "PENDING"}
      >
        {complete && (
          <div className="success-heading">
            <span className="success-check" aria-hidden="true">
              ✓
            </span>
            <div>
              <h3>Evidence verified. Patch published.</h3>
              <p>The approved candidate is ready for code review.</p>
            </div>
          </div>
        )}
        {!complete && !retryable && (
          <ol className="publication-steps">
            {steps.map((step, index) => (
              <li
                key={step}
                className={
                  progress != null && index < progress
                    ? "done"
                    : index === progress
                      ? "active"
                      : ""
                }
              >
                <span>
                  {progress != null && index < progress ? "✓" : index + 1}
                </span>
                {step}
              </li>
            ))}
          </ol>
        )}
        {pr?.number != null && (
          <h3 className="pr-number">Pull request #{pr.number}</h3>
        )}
        {pr?.branch && (
          <p className="mono wrap">
            {pr.branch} → {pr.base_branch ?? "—"}
          </p>
        )}
        {pr?.attempt_count != null && (
          <p className="field-help">Publication attempt {pr.attempt_count}</p>
        )}
        {retryable && (
          <div className="publication-retry">
            <b>Verified candidate preserved</b>
            <p>
              GitHub operation failed. Retry publication to continue with the
              same verified patch.
            </p>
            <Details value={pr?.last_error} />
            <button disabled={disabled} onClick={onRetry}>
              Retry PR creation
            </button>
          </div>
        )}
        {url && (
          <a
            className="button"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open pull request ↗
          </a>
        )}
      </Panel>
    </div>
  );
}
