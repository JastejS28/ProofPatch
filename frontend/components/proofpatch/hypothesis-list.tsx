import type { Run } from "@/lib/proofpatch/types";
import { Panel } from "./evidence-panel";

export function HypothesisList({
  run,
  disabled,
  onSelect,
}: {
  run: Run;
  disabled: boolean;
  onSelect: (id: string) => void;
}) {
  const hypotheses = run.state_json?.hypotheses ?? [];
  const waiting = run.status === "WAITING_FOR_CANDIDATE";
  const selected = hypotheses.find(
    (h) => h.id === run.state_json?.selected_hypothesis_id || h.selected,
  );
  if (!hypotheses.length && !waiting) return null;
  const cards = hypotheses.map((hypothesis, index) => {
    const isSelected = hypothesis.id === selected?.id;
    return (
      <article
        className={`hypothesis ${isSelected ? "selected" : ""}`}
        key={hypothesis.id}
      >
        <div className="eyebrow">
          HYPOTHESIS {String(index + 1).padStart(2, "0")}
          {isSelected ? " / SELECTED" : ""}
        </div>
        <h3>{hypothesis.summary}</h3>
        <dl>
          <dt>Mechanism</dt>
          <dd>{hypothesis.mechanism || "Not provided"}</dd>
          <dt>Expected effect</dt>
          <dd>{hypothesis.expected_effect || "Not provided"}</dd>
          <dt>Trade-offs</dt>
          <dd>{hypothesis.trade_offs || "Not provided"}</dd>
        </dl>
        {waiting && (
          <button
            disabled={disabled || !!run.state_json?.selected_hypothesis_id}
            onClick={() => onSelect(hypothesis.id)}
          >
            Use this hypothesis
          </button>
        )}
      </article>
    );
  });
  return (
    <Panel
      title={
        waiting
          ? "Choose an optimization hypothesis"
          : selected
            ? "Selected approach"
            : "Optimization hypotheses"
      }
      label="HUMAN GATE 01"
    >
      {waiting ? (
        <>
          <p className="section-copy">
            Choose the mechanism you want to test. The proposed effect still
            needs to be measured.
          </p>
          {cards}
        </>
      ) : (
        <>
          <h3>{selected?.summary ?? "Optimization hypotheses"}</h3>
          <details>
            <summary>Inspect hypotheses and trade-offs</summary>
            {cards}
          </details>
        </>
      )}
      {!hypotheses.length && (
        <p className="muted">Waiting for the backend to provide hypotheses.</p>
      )}
    </Panel>
  );
}
