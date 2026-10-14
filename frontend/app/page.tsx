import { RunForm } from "@/components/proofpatch/run-form";
import { HeroPipeline } from "@/components/proofpatch/hero-pipeline";
export default function Home() {
  return (
    <main className="home">
      <div className="hero-composition">
        <div className="hero-copy">
          <div className="eyebrow">PYTHON OPTIMIZATION / EVIDENCE FIRST</div>
          <h1>
            Performance patches.
            <br />
            <span>With proof behind them.</span>
          </h1>
          <p className="intro">
            Generate, validate, benchmark, and review Python performance patches
            before they reach GitHub.
          </p>
          <p className="proof-statement">
            <span>LLM proposes</span>
            <i>·</i>
            <span>Harness verifies</span>
            <i>·</i>
            <span>You approve</span>
          </p>
        </div>
        <HeroPipeline />
      </div>
      <div className="configuration-intro">
        <div>
          <div className="eyebrow">START A REAL RUN</div>
          <h2>Point us at the bottleneck.</h2>
        </div>
        <p>
          One function. Two human gates.
          <br />
          At most two Coder attempts.
        </p>
      </div>
      <div className="home-grid">
        <RunForm />
        <aside className="home-aside">
          <div className="eyebrow">HOW PROOFPATCH WORKS</div>
          <h2>Every patch earns its way in.</h2>
          <ol className="explain-steps">
            <li>
              <b>Inspect & propose</b>
              <p>
                Analyze a public repository and identify focused optimization
                hypotheses.
              </p>
            </li>
            <li>
              <b>You choose the approach</b>
              <p>
                Select a hypothesis before any candidate patch is generated.
              </p>
            </li>
            <li>
              <b>Measure & verify</b>
              <p>
                Static policy, correctness tests, and runtime benchmarks decide
                whether the patch passes.
              </p>
            </li>
            <li>
              <b>You approve publication</b>
              <p>
                Review the evidence before a branch, commit, and pull request
                are created.
              </p>
            </li>
          </ol>
          <div className="aside-note">
            <b>Constrained by design</b>
            <p>
              One target function. At most two Coder attempts. No pull request
              without your approval.
            </p>
          </div>
        </aside>
      </div>
    </main>
  );
}
