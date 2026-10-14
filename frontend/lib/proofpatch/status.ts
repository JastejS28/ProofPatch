import type { Run, RunStatus } from "./types";
export const terminal = new Set<RunStatus>([
  "COMPLETED",
  "UNVERIFIED",
  "FAILED",
  "CANCELLED",
]);
export const humanWait = new Set<RunStatus>([
  "WAITING_FOR_CANDIDATE",
  "WAITING_FOR_PR_APPROVAL",
]);
export const statusCopy: Record<RunStatus, string> = {
  QUEUED: "Run queued for repository inspection.",
  INITIALIZING: "Preparing the repository and inspecting the target.",
  ANALYZING:
    "Analyzing the target function and proposing optimization hypotheses.",
  WAITING_FOR_CANDIDATE: "Choose a hypothesis to begin patch generation.",
  MODIFYING: "Generating a constrained patch for the selected hypothesis.",
  VALIDATING: "Checking baseline and candidate correctness in Docker.",
  BENCHMARKING: "Measuring baseline and candidate runtime with Pyperf.",
  VERIFYING: "Evaluating policy, correctness, and performance evidence.",
  REVIEWING: "Preparing an evidence-based review of the candidate.",
  WAITING_FOR_PR_APPROVAL:
    "Review the evidence and decide whether to publish a pull request.",
  CREATING_PR: "Publishing the approved patch to GitHub.",
  COMPLETED: "Pull request created. The evidence trail is preserved below.",
  UNVERIFIED:
    "ProofPatch exhausted the allowed optimization attempts without producing a candidate that satisfied all verification requirements.",
  FAILED:
    "The run stopped because ProofPatch encountered a system, repository, or unsupported-operation failure.",
  CANCELLING: "Cancelling the run and cleaning up its workspace.",
  CANCELLED: "Run cancelled.",
};
export function tone(status: RunStatus) {
  return status === "COMPLETED"
    ? "pass"
    : status === "FAILED"
      ? "fail"
      : humanWait.has(status) || status === "UNVERIFIED"
        ? "waiting"
        : "neutral";
}
export const phases = [
  "Repository analysis",
  "Hypothesis selection",
  "Patch generation",
  "Correctness validation",
  "Performance benchmark",
  "Deterministic verification",
  "Review",
  "PR approval",
  "GitHub publication",
];
export function phaseIndex(status: string) {
  return (
    {
      QUEUED: 0,
      INITIALIZING: 0,
      ANALYZING: 0,
      WAITING_FOR_CANDIDATE: 1,
      MODIFYING: 2,
      VALIDATING: 3,
      BENCHMARKING: 4,
      VERIFYING: 5,
      REVIEWING: 6,
      WAITING_FOR_PR_APPROVAL: 7,
      CREATING_PR: 8,
      COMPLETED: 9,
    } as Record<string, number>
  )[status];
}
export function canCancel(run: Run) {
  return (
    humanWait.has(run.status) ||
    (run.status === "CREATING_PR" &&
      run.state_json?.pr?.status === "FAILED_RETRYABLE")
  );
}
