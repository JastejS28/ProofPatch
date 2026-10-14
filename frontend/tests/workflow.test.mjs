import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
const packageRequire = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Compile the actual TS/TSX modules in memory; no test endpoints or app fixtures
// are included in the production application.
const cache = new Map();
function loadSource(relative) {
  const file = path.resolve(__dirname, "..", relative);
  if (cache.has(file)) return cache.get(file);
  const sourceModule = { exports: {} };
  cache.set(file, sourceModule.exports);
  const code = ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.ReactJSX,
      target: ts.ScriptTarget.ES2020,
    },
    fileName: file,
  }).outputText;
  const sourceRequire = (name) => {
    if (!name.startsWith("@/") && !name.startsWith("."))
      return packageRequire(name);
    const base = name.startsWith("@/")
      ? path.resolve(__dirname, "..", name.slice(2))
      : path.resolve(path.dirname(file), name);
    const source = [base, `${base}.ts`, `${base}.tsx`].find(
      (candidate) =>
        fs.existsSync(candidate) && fs.statSync(candidate).isFile(),
    );
    assert.ok(source, `Cannot resolve ${name}`);
    return loadSource(path.relative(path.resolve(__dirname, ".."), source));
  };
  new Function("require", "module", "exports", code)(
    sourceRequire,
    sourceModule,
    sourceModule.exports,
  );
  cache.set(file, sourceModule.exports);
  return sourceModule.exports;
}
const { workflowStages } = loadSource("lib/proofpatch/status.ts");
const { AttemptHistory, BenchmarkPanel } = loadSource(
  "components/proofpatch/evidence-panel.tsx",
);
const { githubURL } = loadSource("lib/proofpatch/formatting.ts");
const { GitHubPublication } = loadSource(
  "components/proofpatch/github-publication.tsx",
);
const { TerminalOutcome, TerminalStatusStrip } = loadSource(
  "components/proofpatch/terminal-outcome.tsx",
);
const { WorkflowProgress } = loadSource(
  "components/proofpatch/workflow-progress.tsx",
);
const { changeExplanation } = loadSource("lib/proofpatch/outcome.ts");
const run = (status, extra = {}) => ({
  status,
  current_step: status,
  ...extra,
});
const event = (id, event_type, payload_json = {}) => ({
  id,
  event_type,
  timestamp: `2026-10-14T10:00:${String(id).padStart(2, "0")}Z`,
  payload_json,
});
const render = (component, props) =>
  renderToStaticMarkup(React.createElement(component, props));

test("successful archived attempts are verified, rather than rejected", () => {
  const html = render(AttemptHistory, {
    state: {
      iteration_count: 1,
      attempt_history: [
        { iteration: 1, outcome: "VERIFIED", verification: { passed: true } },
      ],
    },
    stopped: true,
  });
  assert.match(html, /result pass[^>]*>✓ Verified/);
  assert.doesNotMatch(html, /result fail[^>]*>.*Rejected/);
  assert.doesNotMatch(html, />Current</);
});
test("rejected and interrupted attempts retain distinct labels", () => {
  const html = render(AttemptHistory, {
    state: {
      iteration_count: 2,
      attempt_history: [
        { iteration: 1, outcome: "REJECTED", reason: "Threshold not met" },
      ],
    },
    stopped: true,
  });
  assert.match(html, /× Rejected/);
  assert.match(html, /Stopped/);
  assert.match(html, /Threshold not met/);
});
test("completed runs complete every stage", () =>
  assert.deepEqual(
    workflowStages(run("COMPLETED"), []),
    Array(9).fill("completed"),
  ));
test("a late cleanup event does not hide the failed correctness stage", () => {
  const stages = workflowStages(run("FAILED"), [
    event(4, "WORKSPACE_CLEANED"),
    event(2, "VALIDATING"),
    event(3, "FAILED"),
  ]);
  assert.equal(stages[3], "failed");
  assert.equal(stages[4], "pending");
});
test("exhausted attempts identify their actual policy rejection stage", () => {
  const stages = workflowStages(run("UNVERIFIED"), [
    event(1, "MODIFYING"),
    event(2, "CODER_ATTEMPT_REJECTED", { failure_stage: "policy" }),
    event(3, "UNVERIFIED"),
  ]);
  assert.equal(stages[2], "failed");
  assert.equal(stages[3], "pending");
});
test("retries return to patch generation rather than showing future evidence as complete", () => {
  const stages = workflowStages(run("MODIFYING"), [
    event(1, "BENCHMARKING"),
    event(2, "MODIFYING"),
  ]);
  assert.equal(stages[2], "current");
  assert.equal(stages[3], "pending");
});
test("human gates and cancellation use explicit waiting and stopped states", () => {
  assert.equal(
    workflowStages(run("WAITING_FOR_PR_APPROVAL"), [])[7],
    "waiting",
  );
  assert.equal(
    workflowStages(run("CANCELLED"), [
      event(1, "WAITING_FOR_CANDIDATE"),
      event(2, "CANCELLED"),
    ])[1],
    "stopped",
  );
});
test("GitHub failure preserves earlier verified stages", () => {
  const stages = workflowStages(
    run("CREATING_PR", { state_json: { pr: { status: "FAILED_RETRYABLE" } } }),
    [],
  );
  assert.equal(stages[5], "completed");
  assert.equal(stages[8], "failed");
  const html = render(GitHubPublication, {
    run: run("CREATING_PR", {
      state_json: { pr: { status: "FAILED_RETRYABLE" } },
    }),
    disabled: false,
    onRetry() {},
  });
  assert.match(html, /Verified candidate preserved/);
  assert.match(html, /Retry PR creation/);
});
test("benchmark bars use actual relative medians and preserve measured percentage", () => {
  const html = render(BenchmarkPanel, {
    data: {
      baseline: { median_seconds: 0.004 },
      candidate: { median_seconds: 0.001 },
      improvement_percent: 75,
      threshold_percent: 10,
      passed: true,
    },
  });
  assert.match(html, /width:100%/);
  assert.match(html, /width:25%/);
  assert.match(html, /75.00%/);
  assert.match(html, /10.00%/);
});
test("PR links cannot send users to script or lookalike hosts", () => {
  assert.equal(githubURL("javascript:alert(1)"), undefined);
  assert.equal(
    githubURL("https://github.com.attacker.example/pull/1"),
    undefined,
  );
  assert.equal(
    githubURL("https://github.com/owner/repo/pull/1"),
    "https://github.com/owner/repo/pull/1",
  );
});
const completedState = {
  hypotheses: [
    { id: "hypothesis-a", summary: "Replace repeated scans with a set." },
  ],
  selected_hypothesis_id: "hypothesis-a",
  iteration_count: 1,
  changes: {
    policy: { passed: true },
    change_summary: "Fallback change description.",
  },
  validation: { correctness_passed: true },
  benchmark: {
    passed: true,
    threshold_percent: 10,
    improvement_percent: 42.125,
  },
  verification: {
    passed: true,
    policy_passed: true,
    correctness_passed: true,
    performance_passed: true,
  },
  approvals: { pr: { status: "APPROVED" } },
  review: {
    change_explanation:
      "Used a set for membership checks. Removed repeated list slicing. Preserved the return contract.",
    recommendation: "Approve for review.",
  },
  pr: {
    status: "CREATED",
    number: 17,
    branch: "proofpatch/test",
    base_branch: "main",
    url: "https://github.com/owner/repo/pull/17",
  },
};
test("completed outcomes summarize real evidence and offer the recorded PR", () => {
  const html = render(TerminalOutcome, {
    run: run("COMPLETED", { state_json: completedState }),
  });
  for (const expected of [
    "Optimization completed",
    "Replace repeated scans with a set.",
    "1 / 2",
    "42.13%",
    "Approve for review.",
    "#17",
    "proofpatch/test → main",
    "What changed",
    "Why it is safe",
    "Used a set for membership checks.",
  ])
    assert.ok(html.includes(expected), expected);
  assert.match(html, /href="https:\/\/github.com\/owner\/repo\/pull\/17"/);
  assert.match(html, /explicit human PR approval passed/);
  const strip = render(TerminalStatusStrip, {
    run: run("COMPLETED", { state_json: completedState }),
  });
  assert.match(strip, /✓ Run completed successfully/);
  assert.match(strip, /Verified candidate published as PR #17/);
});
test("missing evidence never becomes an invented success metric or safety claim", () => {
  const html = render(TerminalOutcome, { run: run("COMPLETED") });
  assert.match(html, /Not recorded/);
  assert.doesNotMatch(html, /explicit human PR approval passed/);
  assert.doesNotMatch(html, /validated correctness/);
  assert.doesNotMatch(html, /href=/);
  assert.doesNotMatch(html, /\d+\.\d+%/);
  const strip = render(TerminalStatusStrip, {
    run: run("COMPLETED", { state_json: { pr: { number: 17 } } }),
  });
  assert.doesNotMatch(strip, /Verified candidate/);
  assert.match(strip, /verification was not recorded/);
});
test("a contradictory result is visible even if the run status is completed", () => {
  const html = render(TerminalOutcome, {
    run: run("COMPLETED", {
      state_json: {
        ...completedState,
        validation: { correctness_passed: false },
      },
    }),
  });
  assert.match(html, /× Not passed/);
  assert.doesNotMatch(html, /explicit human PR approval passed/);
});
test("unverified outcome shows the last rejected attempt and its evidence", () => {
  const html = render(TerminalOutcome, {
    run: run("UNVERIFIED", {
      state_json: {
        attempt_history: [
          { iteration: 1, outcome: "REJECTED", reason: "First attempt" },
          {
            iteration: 2,
            outcome: "REJECTED",
            reason: "Threshold not met",
            failure_stage: "benchmark",
            validation: { correctness_passed: true },
            benchmark: {
              passed: false,
              improvement_percent: 3,
              threshold_percent: 10,
            },
          },
        ],
      },
    }),
  });
  assert.match(html, /No verified candidate/);
  assert.match(html, /Attempt 2 \/ 2/);
  assert.match(html, /Threshold not met/);
  assert.match(html, /Failure stage: benchmark/);
  assert.match(html, /3.00%/);
  assert.doesNotMatch(html, /infrastructure/);
  assert.doesNotMatch(html, /First attempt/);
});
test("failure shows the latest backend error with history and no candidate retry", () => {
  const html = render(TerminalOutcome, {
    run: run("FAILED", {
      state_json: {
        errors: [
          { message: "First error" },
          { message: "Repository unreachable" },
        ],
      },
    }),
  });
  assert.match(html, /Run stopped/);
  assert.match(html, /Latest backend error/);
  assert.match(html, /Repository unreachable/);
  assert.match(html, /Error history/);
  assert.doesNotMatch(html, /<button/);
  assert.doesNotMatch(html, /Retry optimization/);
});
test("cancellation closes the report without claiming failure or publication", () => {
  const html = render(TerminalOutcome, { run: run("CANCELLED") });
  assert.match(html, /Run cancelled/);
  assert.match(html, /intentionally stopped before publication/);
  assert.match(html, /remain in the report below/);
  assert.doesNotMatch(html, /Run stopped/);
  assert.doesNotMatch(html, /href=/);
});
test("completion resolves final node and connectors, with transition only when requested", () => {
  const html = render(WorkflowProgress, {
    run: run("COMPLETED"),
    events: [],
    completionTransition: true,
  });
  assert.match(html, /completion-transition/);
  assert.equal((html.match(/workflow-stage completed/g) || []).length, 9);
  assert.match(html, />Complete</);
  const staticHtml = render(TerminalOutcome, { run: run("COMPLETED") });
  assert.doesNotMatch(staticHtml, /outcome-enter/);
  const animatedHtml = render(TerminalOutcome, {
    run: run("COMPLETED"),
    animate: true,
  });
  assert.match(animatedHtml, /outcome-enter/);
});
test("change explanation uses backend fallbacks and stays within three sentences", () => {
  assert.equal(
    changeExplanation({
      changes: { change_summary: "Actual candidate description." },
    }),
    "Actual candidate description.",
  );
  assert.equal(
    changeExplanation({
      review: { change_explanation: "One. Two. Three. Four." },
    }),
    "One. Two. Three.",
  );
});
