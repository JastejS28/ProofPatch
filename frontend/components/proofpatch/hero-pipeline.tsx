export function HeroPipeline() {
  return (
    <div className="hero-visual">
      <div className="visual-heading">
        <span className="mono">PATCH → PROOF → PULL REQUEST</span>
        <span className="visual-label">Architecture</span>
      </div>
      <svg
        viewBox="0 0 600 280"
        role="img"
        aria-labelledby="pipeline-title pipeline-desc"
      >
        <title id="pipeline-title">
          A patch through the verification pipeline
        </title>
        <desc id="pipeline-desc">
          A Python code diff passes static policy, Docker tests, a runtime
          benchmark, and a deterministic verifier before human approval and a
          GitHub pull request. This is an architectural illustration, not live
          run data.
        </desc>
        <defs>
          <pattern
            id="pipeline-grid"
            width="24"
            height="24"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".7" fill="#29343e" />
          </pattern>
        </defs>
        <rect width="600" height="280" fill="url(#pipeline-grid)" />
        <g className="diagram-code">
          <rect x="20" y="45" width="226" height="171" rx="8" />
          <path d="M20 76H246" />
          <circle cx="36" cy="60" r="3" />
          <circle cx="48" cy="60" r="3" />
          <circle cx="60" cy="60" r="3" />
          <text x="82" y="64">
            target.py · diff
          </text>
          <text x="36" y="99">
            def optimize(values):
          </text>
          <rect
            className="diff-removed"
            x="31"
            y="109"
            width="204"
            height="25"
            rx="3"
          />
          <text x="36" y="126">
            − repeated work
          </text>
          <rect
            className="diff-added"
            x="31"
            y="143"
            width="204"
            height="25"
            rx="3"
          />
          <text className="accent-text" x="36" y="160">
            + constrained patch
          </text>
          <path className="code-line" d="M44 188H153 M44 198H121" />
        </g>
        <path
          className="pipeline-path"
          d="M246 131H285V85H328 M328 85H451V160H328V230H533"
        />
        <path
          className="pipeline-signal"
          d="M246 131H285V85H328 M328 85H451V160H328V230H533"
        />
        <g className="diagram-gate">
          <rect x="298" y="63" width="97" height="44" rx="6" />
          <text x="311" y="81">
            01 POLICY
          </text>
          <path d="M313 94L317 98L325 90" />
          <path className="code-line" d="M337 94H380" />
        </g>
        <g className="diagram-gate">
          <rect x="424" y="63" width="143" height="44" rx="6" />
          <text x="437" y="81">
            02 DOCKER TESTS
          </text>
          <path d="M440 94L444 98L452 90" />
          <path className="code-line" d="M464 94H550" />
        </g>
        <g className="diagram-gate">
          <rect x="424" y="137" width="143" height="45" rx="6" />
          <text x="437" y="154">
            03 BENCHMARK
          </text>
          <path className="code-line" d="M439 166H545" />
          <path className="accent-stroke" d="M439 174H490" />
        </g>
        <g className="diagram-gate">
          <rect x="298" y="137" width="103" height="45" rx="6" />
          <text x="309" y="154">
            04 VERIFY
          </text>
          <path d="M313 168L317 172L325 164" />
          <text className="accent-text" x="336" y="173">
            NON-LLM
          </text>
        </g>
        <text className="diagram-caption" x="348" y="216">
          HUMAN APPROVAL
        </text>
        <g className="branch-end">
          <path d="M482 230H539 M502 230V212H532" />
          <circle cx="482" cy="230" r="4" />
          <circle cx="532" cy="212" r="4" />
          <circle cx="539" cy="230" r="5" />
          <text x="550" y="234">
            PR
          </text>
        </g>
      </svg>
      <div className="visual-footer">
        <span>Constrained patch</span>
        <span>Deterministic evidence</span>
        <span>Human control</span>
      </div>
    </div>
  );
}
