import type { Run, RunEvent } from "@/lib/proofpatch/types";
import { workflowStages } from "@/lib/proofpatch/status";
const labels = [
  "Repository",
  "Hypothesis",
  "Patch",
  "Correctness",
  "Benchmark",
  "Verify",
  "Review",
  "Approval",
  "GitHub",
];
export function WorkflowProgress({
  run,
  events,
  completionTransition = false,
}: {
  run: Run;
  events: RunEvent[];
  completionTransition?: boolean;
}) {
  const stages = workflowStages(run, events);
  return (
    <nav
      className={`workflow-track ${completionTransition ? "completion-transition" : ""}`}
      aria-label="Run workflow"
    >
      <ol>
        {labels.map((label, index) => (
          <li
            key={label}
            className={`workflow-stage ${stages[index]}`}
            aria-current={
              stages[index] === "current" || stages[index] === "waiting"
                ? "step"
                : undefined
            }
          >
            <span className="track-node" aria-hidden="true">
              {stages[index] === "completed"
                ? "✓"
                : stages[index] === "failed"
                  ? "×"
                  : stages[index] === "stopped"
                    ? "−"
                    : String(index + 1).padStart(2, "0")}
            </span>
            <b>{label}</b>
            <span className="stage-state">
              {run.status === "COMPLETED" && index === labels.length - 1
                ? "Complete"
                : stages[index] === "waiting"
                  ? "Action required"
                  : stages[index]}
            </span>
          </li>
        ))}
      </ol>
    </nav>
  );
}
