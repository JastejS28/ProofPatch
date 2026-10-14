import type { Run, RunState } from "./types";

export function completionEvidence(state: RunState) {
  return [
    {
      name: "Static policy",
      passed:
        state.verification?.policy_passed ?? state.changes?.policy?.passed,
    },
    {
      name: "Correctness validation",
      passed:
        state.validation?.correctness_passed ??
        state.verification?.correctness_passed,
    },
    {
      name: "Benchmark threshold",
      passed: state.benchmark?.passed ?? state.verification?.performance_passed,
    },
    { name: "Deterministic verifier", passed: state.verification?.passed },
    {
      name: "Human PR approval",
      passed:
        state.approvals?.pr?.status == null
          ? undefined
          : state.approvals.pr.status === "APPROVED",
    },
  ];
}

export function completedIntroduction(run: Run) {
  const state = run.state_json ?? {};
  return completionEvidence(state).every((check) => check.passed === true) &&
    state.pr?.status === "CREATED"
    ? "ProofPatch proposed a candidate, validated correctness, benchmarked performance, passed deterministic verification, received human approval, and created a GitHub pull request."
    : "The backend reports this run as completed. The recorded optimization and publication evidence is summarized below.";
}

export function changeExplanation(state: RunState) {
  const source =
    state.review?.change_explanation?.trim() ||
    state.review?.summary?.trim() ||
    state.changes?.change_summary?.trim();
  return source
    ? source
        .split(/(?<=[.!?])\s+(?=[A-Z])/)
        .slice(0, 3)
        .join(" ")
    : "No change explanation was recorded by the backend.";
}

export function terminalStrip(run: Run) {
  switch (run.status) {
    case "COMPLETED":
      return {
        title: "✓ Run completed successfully",
        description:
          run.state_json?.pr?.number != null
            ? run.state_json.verification?.passed === true
              ? `Verified candidate published as PR #${run.state_json.pr.number}`
              : `Candidate published as PR #${run.state_json.pr.number}; verification ${run.state_json.verification?.passed === false ? "did not pass" : "was not recorded"}.`
            : "Backend reports completion. Pull request number was not recorded.",
      };
    case "UNVERIFIED":
      return {
        title: "○ No verified candidate",
        description:
          "No candidate met all verification requirements within the allowed 2 Coder attempts.",
      };
    case "FAILED":
      return {
        title: "✕ Run stopped",
        description:
          "Execution stopped because ProofPatch encountered a repository, infrastructure, unsupported-operation, or internal workflow failure.",
      };
    case "CANCELLED":
      return {
        title: "— Run cancelled",
        description: "The run was intentionally stopped before publication.",
      };
    default:
      return undefined;
  }
}
