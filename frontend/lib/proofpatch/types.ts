export type RunStatus =
  | "QUEUED"
  | "INITIALIZING"
  | "ANALYZING"
  | "WAITING_FOR_CANDIDATE"
  | "MODIFYING"
  | "VALIDATING"
  | "BENCHMARKING"
  | "REVIEWING"
  | "VERIFYING"
  | "WAITING_FOR_PR_APPROVAL"
  | "CREATING_PR"
  | "COMPLETED"
  | "UNVERIFIED"
  | "FAILED"
  | "CANCELLING"
  | "CANCELLED";
export interface RunInput {
  repo_url: string;
  target_file: string;
  target_function: string;
  problem_description: string;
}
export interface Hypothesis {
  id: string;
  summary?: string;
  mechanism?: string;
  expected_effect?: string;
  trade_offs?: string;
  selected?: boolean;
  status?: string;
}
export interface ExecutionEvidence {
  passed?: boolean;
  duration_ms?: number;
  stdout?: string;
  stderr?: string;
  exit_code?: number;
  timed_out?: boolean;
}
export interface ValidationEvidence {
  iteration?: number;
  strategy?: string;
  correctness_passed?: boolean;
  baseline?: ExecutionEvidence;
  candidate?: ExecutionEvidence;
  differential?: ExecutionEvidence;
}
export interface TimingEvidence {
  median_seconds?: number;
  mean_seconds?: number;
  stdev_seconds?: number;
  values_count?: number;
  duration_ms?: number;
}
export interface BenchmarkEvidence {
  iteration?: number;
  baseline?: TimingEvidence;
  candidate?: TimingEvidence;
  improvement_percent?: number;
  threshold_percent?: number;
  passed?: boolean;
}
export interface VerificationEvidence {
  iteration?: number;
  passed?: boolean;
  policy_passed?: boolean;
  correctness_passed?: boolean;
  performance_passed?: boolean;
  reasons?: string[];
}
export interface ReviewEvidence {
  summary?: string;
  change_explanation?: string;
  correctness_summary?: string;
  performance_summary?: string;
  risks_and_tradeoffs?: string[] | string;
  recommendation?: string;
}
export interface PREvidence {
  status?: string;
  attempt_count?: number;
  branch?: string;
  base_branch?: string;
  number?: number;
  url?: string;
  last_error?: unknown;
}
export interface ChangesEvidence {
  change_summary?: string;
  policy?: { passed?: boolean; reasons?: string[] };
  diff?: string;
  unified_diff?: string;
}
export interface AttemptHistoryEntry {
  iteration?: number;
  outcome?: "REJECTED" | "VERIFIED";
  failure_stage?: string | null;
  reason?: string | null;
  changes?: ChangesEvidence;
  validation?: ValidationEvidence;
  benchmark?: BenchmarkEvidence;
  verification?: VerificationEvidence;
}
export interface RunState {
  workspace?: { cleaned?: boolean };
  approvals?: {
    candidate?: { status?: string; hypothesis_id?: string };
    pr?: { status?: string };
  };
  purity_check?: { passed?: boolean; reasons?: string[] };
  repository_summary?: {
    owner?: string;
    repository?: string;
    target_function?: string;
    signature?: string;
    source?: string;
    line_start?: number;
    line_end?: number;
    imports?: string[];
    related_test_files?: string[];
  };
  hypotheses?: Hypothesis[];
  selected_hypothesis_id?: string | null;
  iteration_count?: number;
  attempt_history?: AttemptHistoryEntry[];
  retry_feedback?: unknown;
  changes?: ChangesEvidence;
  validation?: ValidationEvidence;
  benchmark?: BenchmarkEvidence;
  verification?: VerificationEvidence;
  review?: ReviewEvidence;
  pr?: PREvidence;
  errors?: unknown[];
  budget?: { llm_calls?: number; elapsed_sec?: number; cost_usd?: number };
}
export interface Run extends RunInput {
  id: string;
  status: RunStatus;
  current_step: string;
  state_json?: RunState;
  created_at: string;
  updated_at: string;
}
export interface RunEvent {
  id: number;
  run_id: string;
  timestamp: string;
  event_type: string;
  payload_json?: Record<string, unknown>;
}
