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
npm run build
```

The browser accesses only `/api/proofpatch/*`. A server route handler forwards the supported FastAPI run operations, preserving response status and error bodies. Backend connection failures return 502. No backend credentials belong in this directory.

Run pages poll without overlapping cycles, abort requests on navigation, retain previous evidence during refreshes, and stop polling terminal runs. Human decisions use a synchronous action lock and refetch authoritative state; successful actions remain disabled until backend state advances. Rejection and cancellation require confirmation.

There is no run-list endpoint, authentication, fabricated evidence, or client-side GitHub API access. PR links are restricted to HTTPS GitHub URLs.

## Integration verification

Lint, TypeScript, and production build passed. Desktop and mobile pages were inspected in the browser with no horizontal overflow at the mobile breakpoint. Live FastAPI checks covered run creation, run/event polling, hypothesis selection, duplicate-selection rejection, cancellation, and propagation of 404/409/422 responses.

The optimization smoke run reached Docker validation, then the backend returned `FAILED` with `Baseline relevant tests did not pass.` Benchmarking, reviewer approval/rejection, and PR publication/retry therefore remain unverified end to end against this repository. Their frontend controls are connected to the existing backend operations; no fabricated results are used. No PR was published during verification.
