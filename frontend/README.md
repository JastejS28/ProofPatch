# ProofPatch frontend

Next.js App Router, TypeScript, Tailwind CSS, and native fetch. This directory sits alongside `backend`; no backend changes are required.

## Start

1. Start the existing FastAPI backend at `http://127.0.0.1:8000`.
2. In `frontend`, run `npm install`.
3. Copy `.env.example` to `.env.local` if needed. `FASTAPI_BASE_URL` is server-only.
4. Run `npm run dev` and open `http://localhost:3000`.

For production: `npm run build`, then `npm start`.

## Checks

```sh
npm run lint
npm run typecheck
npm test
npm run build
```

The browser accesses only `/api/proofpatch/*`. A server route handler forwards the supported FastAPI run operations, preserving response status and error bodies. Backend connection failures return 502. No backend credentials belong in this directory.

Run pages poll without overlapping cycles, abort requests on navigation, retain previous evidence during refreshes, and stop polling terminal runs. Human decisions use a synchronous action lock and refetch authoritative state; successful actions remain disabled until backend state advances. Rejection and cancellation require confirmation.

There is no run-list endpoint, authentication, fabricated evidence, or client-side GitHub API access. PR links are restricted to HTTPS GitHub URLs.

## Integration verification

The dark interface includes a technical pipeline illustration, a horizontal workflow derived from actual run states/events, and dedicated terminal reports for completed, unverified, failed, and cancelled runs. Success reports use recorded checks and human approval; absent evidence is marked as not recorded. Final connector, check, and report transitions run only when a polled run changes to completed, and all motion is disabled for reduced-motion preferences. Previously produced evidence remains visible below every terminal outcome.

Lint, TypeScript, production build, and 18 regression tests passed. The tests cover archived attempt outcomes, real workflow-stage derivation, terminal reports, missing or contradictory success evidence, measured benchmark ratios, and safe PR links. Browser checks covered the homepage and real failed/cancelled runs at 1440, 1024, 768, and 390px with no horizontal page overflow. The workflow has its own controlled horizontal scroll on narrower screens; the compiled reduced-motion rules were checked.

Live FastAPI checks covered run creation, run/event polling, hypothesis selection, duplicate-selection rejection, cancellation, and propagation of 404/409/422 responses.

The latest optimization smoke run (`c4901d1c-25a5-4f05-91ba-8a56a9e25560`) reached Docker validation, then the backend returned `FAILED` with `Baseline relevant tests did not pass.` The repository's demo tests import `algorithms` as a top-level module while that file lives in `proofpatch-demo-target`, causing test collection to fail in the sandbox. Backend code was not changed. Benchmarking, reviewer approval/rejection, and PR publication/retry therefore remain unverified end to end against this repository. Completed and unverified report rendering is covered by regression tests, not fabricated live runs. No PR was published during verification.
