"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createRun } from "@/lib/proofpatch/api";
export function RunForm() {
  const router = useRouter();
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <form
      className="panel run-form"
      onSubmit={async (e) => {
        e.preventDefault();
        if (lock.current) return;
        const data = new FormData(e.currentTarget);
        const input = {
          repo_url: String(data.get("repo_url")).trim(),
          target_file: String(data.get("target_file")).trim(),
          target_function: String(data.get("target_function")).trim(),
          problem_description: String(data.get("problem_description")).trim(),
        };
        if (
          !/^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/?$/.test(input.repo_url)
        ) {
          setError(
            "Enter a public GitHub repository URL: https://github.com/owner/repository",
          );
          return;
        }
        if (
          input.problem_description.length < 5 ||
          !input.target_file ||
          !input.target_function
        ) {
          setError(
            "Complete all fields; the performance concern needs at least 5 characters.",
          );
          return;
        }
        lock.current = true;
        setBusy(true);
        setError("");
        try {
          const result = await createRun(input);
          router.push(`/runs/${encodeURIComponent(result.run_id)}`);
        } catch (err) {
          setError(
            err instanceof Error ? err.message : "Could not create run.",
          );
          lock.current = false;
          setBusy(false);
        }
      }}
    >
      <div className="panel-heading">
        <h2>Configure the target</h2>
        <span className="mono muted">01 / INPUT</span>
      </div>
      <label htmlFor="repo">Repository URL</label>
      <input
        id="repo"
        name="repo_url"
        type="url"
        placeholder="https://github.com/owner/repository"
        required
        disabled={busy}
      />
      <p className="field-help">Public GitHub repositories only.</p>
      <div className="form-row">
        <div>
          <label htmlFor="file">Target file</label>
          <input
            id="file"
            name="target_file"
            placeholder="src/utils/search.py"
            required
            maxLength={1024}
            disabled={busy}
          />
        </div>
        <div>
          <label htmlFor="function">Target function</label>
          <input
            id="function"
            name="target_function"
            placeholder="count_members"
            required
            maxLength={255}
            disabled={busy}
          />
        </div>
      </div>
      <label htmlFor="concern">Performance concern</label>
      <textarea
        id="concern"
        name="problem_description"
        placeholder="Membership checks become slow for large inputs."
        required
        minLength={5}
        maxLength={4000}
        rows={5}
        disabled={busy}
      />
      <p className="field-help">
        Describe the bottleneck and the inputs that make it noticeable.
      </p>
      {error && (
        <p role="alert" className="error-message">
          {error}
        </p>
      )}
      <div className="form-bottom">
        <span className="muted">You’ll choose a hypothesis next.</span>
        <button disabled={busy} type="submit">
          {busy ? "Starting analysis…" : "Analyze repository →"}
        </button>
      </div>
    </form>
  );
}
