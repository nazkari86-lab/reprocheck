# SealRail

**A proof-gated payment rail for AI agents on Casper. An agent gets paid only after its work is independently verified and the proof is anchored on-chain.**

[![CI](https://github.com/mystiquemide/sealrail/actions/workflows/ci.yml/badge.svg)](https://github.com/mystiquemide/sealrail/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Casper Testnet](https://img.shields.io/badge/Casper-Testnet%20Anchoring%20Live-red)](https://testnet.cspr.live/deploy/9a708f9e84c6d8f2d93d196823312a7f6ce8f903b93c344115f7e8c9c72edd6d)
[![Backend Tests](https://img.shields.io/badge/backend%20tests-770%20passing-brightgreen)](backend/tests)

**Live app:** [sealrail.xyz](https://sealrail.xyz) &nbsp;·&nbsp; **Judge path:** [sealrail.xyz/review](https://sealrail.xyz/review) &nbsp;·&nbsp; **Demo video:** [youtu.be/K8tqyrEmRzM](https://youtu.be/K8tqyrEmRzM) &nbsp;·&nbsp; **API status:** [api.sealrail.xyz/api/status](https://api.sealrail.xyz/api/status)

> A payment cannot unlock on Casper unless a verified proof exists and a Casper deploy has been confirmed on-chain. No proof, no payment. Enforced, not promised.

Qualified for the **Casper Agentic Buildathon 2026 Final Round**. You can verify the core claim in 30 seconds: open [`/run`](https://sealrail.xyz/run), click **Run failing proof**, and watch the rail refuse to pay for output that fails verification.

### Final-round live update after the submitted demo video

The DoraHacks demo video is the original public walkthrough and may be locked on the submission page. It still shows the core SealRail story: proof-gated agent work, verifier checks, Casper testnet anchoring, and payment unlocks only after proof.

Since that recording, the live app and repository have been polished for final-round review:

- [`/review`](https://sealrail.xyz/review) is the current reviewer entrypoint with live proof links, Casper anchor context, and trust boundaries.
- [`/run`](https://sealrail.xyz/run) now separates the wallet-gated fresh paid run from the public **Safe path** so wallet-less reviewers can verify the invariant without signing.
- The failing-proof path is first-class: failed verification creates no Casper anchor and leaves payment blocked.
- [`/status`](https://sealrail.xyz/status) now reports CSPR.cloud API/rates as live while honestly marking x402/node-health checks as partial when provider endpoints rate-limit.
- Public docs now point to `https://api.sealrail.xyz` and describe API keys as private/operator-managed for protected write APIs.
- Hosted TEE remains pending/configuration-gated; the live verification mode is **Schema + hash verification**.
- RWA compliance remains preview-only; the live runnable product path is the invoice-risk agent flow.

Use the video for the product narrative, then use the live links above as the source of truth for the final-round build state.

## The problem

An AI agent reviews a $12,400 invoice (INV-1030) and returns "approve." It gets paid for that call. But nobody checked the agent's output before the money moved. If the output was hallucinated, malformed, or wrong, the payer already lost twice: once on the bad invoice the agent waved through, once on the agent that waved it through.

This is the default for agent-to-agent commerce today: **output is trusted because it looks like output.** There is no independent gate between "the agent produced text" and "the agent gets paid." As soon as agents pay other agents at machine speed, that gap becomes the attack surface.

## The solution

SealRail puts a verification gate between agent output and payment. Work enters the rail, an agent produces structured output with content-addressed hashes, a verifier checks that output against a schema and a WASM artifact hash, the proof is anchored on Casper testnet, and only a **confirmed** on-chain anchor moves the payment state to payable.

**The hard rule, enforced by the backend state machine and covered by tests: a placeholder, simulated, or unverified proof can never advance a task to payable.** Payment fails closed. The negative path is a first-class demo, not a hidden branch.

## Product screens

Real screens from the live app. Every number on them is produced by the running engine, not mocked up.

| Run flow (the rail, live) | Proof detail with x402-compatible receipt |
|---|---|
| ![SealRail verification run flow: task input, live proof rail, verified output, and Casper anchor](public/screenshots/02-run-flow.png) | ![SealRail proof detail showing hashes, Casper anchor, payment state, and x402-compatible receipt](public/screenshots/06-proof-detail.png) |

| Proof explorer / marketplace | Status board (honest live vs pending) |
|---|---|
| ![SealRail agent marketplace listing runnable and preview agents](public/screenshots/03-marketplace.png) | ![SealRail status dashboard showing live components and pending trust-boundary items](public/screenshots/05-status.png) |

| Home | Reviewer quickstart |
|---|---|
| ![SealRail homepage hero](public/screenshots/01-homepage.png) | ![SealRail reviewer quickstart with judge path, live proof links, and trust boundaries](public/screenshots/04-reviewer-quickstart.png) |

## Try it (real UI, real chain)

Open [`/run`](https://sealrail.xyz/run) and:

1. **Run full flow** — funds a task, runs the live invoice-risk agent, verifies the output, anchors the proof on Casper testnet, and unlocks the payment state. The anchor is a real, freshly-minted deploy you can open on cspr.live.
2. **Run failing proof** — the agent output fails schema verification. The rail halts: **Blocky check FAILED → Casper anchor NONE → payment BLOCKED.**

Running a fresh paid flow requires the Casper Wallet extension, so SealRail can bind the holder identity to a wallet-controlled key. Wallet-less reviewers can still verify the whole invariant through [`/review`](https://sealrail.xyz/review), [`/proofs`](https://sealrail.xyz/proofs), the proof detail pages, and the linked on-chain deploys.

## How it works

```
 Buyer ── fund task ──▶ SealRail API ── dispatch ──▶ Agent runtime (LLM)
                                                          │
                                          hash-bound structured output
                                                          ▼
                             Verifier (schema + WASM hash binding)
                            /                                      \
                 verified proof                                failed proof
                        │                                            │
              Casper ProofRegistry                        no anchor, rail halts
              (anchor_proof deploy)                                  │
                        │                                            ▼
              confirmed on-chain?                          payment stays BLOCKED
                        │
                        ▼
              payment becomes payable
```

1. **Fund.** `POST /api/tasks` creates a task and a locked payment intent.
2. **Run.** The agent runtime sends a structured prompt to an LLM and returns output with input/output hashes.
3. **Verify.** The verifier checks the output against the registered schema and the verifier's WASM artifact hash. Failure ends the rail here.
4. **Anchor.** The proof hash is submitted to the Casper ProofRegistry contract via `anchor_proof`.
5. **Confirm.** SealRail polls the deploy through CSPR.cloud and only accepts the anchor once execution is `processed` with no error. A submitted-but-reverted deploy is treated as a failure.
6. **Unlock.** Payment becomes payable only if steps 3 and 5 both succeeded.

## Key features

| Feature | What it does | Why it matters |
|---|---|---|
| Proof-gated payment state machine | Unlocks a payable state only after verified proof + confirmed anchor | The one invariant the whole product defends |
| Live Invoice Risk Agent | LLM-backed agent returns risk score, decision, reasoning, flags, all hash-bound | Real agentic output, not a canned string |
| Failing-proof path | A one-click demo where bad output creates no anchor and blocks payment | Proves the invariant instead of asserting it |
| Casper anchoring with execution confirmation | Anchors proof hashes and confirms the deploy actually executed | "Anchored" means executed on-chain, not just submitted |
| Verifier registry | Schema + WASM-hash-bound templates with a test endpoint | Verification is content-addressed, not vibes |
| Proof explorer | `/proofs` and `/proofs/:id` resolve live proof, hashes, anchor, payment state | A judge can inspect any proof independently |
| x402-compatible receipts | Proof bundles carry a 402-style payment-required receipt shape | Machine-readable settlement story for agents |
| Casper Wallet sign-in | Connect wallet, sign a nonce challenge, receive a wallet-scoped API key | Owner-sensitive actions are bound to a real key |
| MCP server | Real `@modelcontextprotocol/sdk` stdio server, 5 tools | Any MCP client can read proofs and create tasks |

## Why it is different

The naive version of this is an escrow that releases on "done," where "done" is whatever the agent or the operator asserts. That moves the trust, it does not remove it: the party holding the escrow can still release on unverified work.

Two things make SealRail different:

- **Verification sits between output and payment, and it fails closed.** The payment state machine has no path to payable that skips proof. This is enforced in code and asserted by tests, not left to operator discretion.
- **The proof is anchored on a public chain and the anchor is execution-confirmed.** A third party can open the deploy on cspr.live and see the `anchor_proof` call succeeded. "Trust us, it verified" becomes "here is the transaction."

Remove either and you are back to a database row that says "paid" and a promise that someone checked.

## Architecture

- **Frontend** (`app/`, `components/`, `lib/`) — Next.js App Router, 19 routes, a typed API client, and an in-memory session bootstrap. No secret ever reaches the browser.
- **Backend** (`backend/src/`) — Fastify API. `routes/` are thin; `services/` hold the domain logic: the task and payment state machines, the verifier, the agent runtime, the Casper anchoring service, reputation, and API-key management.
- **Contract** (`contracts/verified-agent-payments/`) — an Odra ProofRegistry deployed to Casper testnet: agent registry, proof anchoring, and payment state transitions.
- **Deliberate constraint:** the LLM sits in the work path, never in the authorization path. A model can produce output, but only the deterministic verifier and the confirmed on-chain anchor can move money. The intelligence is replaceable; the invariant is not.

## Sponsor and ecosystem integrations

SealRail is built as an integration surface for the Casper ecosystem. Every integration below is live, and each is load-bearing rather than decorative.

| Integration | What SealRail does with it | Status |
|---|---|---|
| **Casper testnet** | Anchors every proof hash via the Odra ProofRegistry `anchor_proof` entry point before payment can unlock; live status reports `casper_mode: testnet`, contract config, and chain readiness | Live |
| **CSPR.cloud** | Confirms a deploy actually executed (`processed`, no error) before an anchor is accepted; also exposes deploy, rate, x402-facilitator, and node-health endpoints | Live |
| **LLM provider (Groq in production, any OpenAI-compatible)** | Runs the invoice-risk agent that produces the structured output being verified | Live |
| **Odra ProofRegistry** | Contract deployed on Casper testnet, linked from this README and the testnet explorer | Live |
| **MCP server** | `@modelcontextprotocol/sdk` stdio server, 5 tools (status, manifest, proofs, task creation) any MCP client can call | Live |
| **x402-compatible receipts** | Proof bundles carry payment-required receipt metadata: proof requirement, unlock condition, network, payment state | Live |
| **Casper Wallet authentication** | Wallet connection + signed-challenge flow via `/api/auth/wallet/challenge` and `/api/auth/wallet/verify` | Live |
| **Agent integration manifest** | `GET /api/integrations/agent-manifest` exposes capabilities, endpoints, MCP tools, and trust boundaries | Live |

**The delete test.** If you remove **Casper**, SealRail can no longer prove anything to a third party: payment unlock would rest on the app's own database claim, which the operator could forge. Casper is what turns "we verified it" into "verify it yourself." If you remove **CSPR.cloud**, the anchor degrades to submitted-but-unconfirmed, which is exactly the reverted-deploy failure mode SealRail was built to reject. If you remove the **LLM**, agent runs return an honest 503 instead of fabricating output. None of these are decorative.

### Planned

| Integration | What it unlocks |
|---|---|
| Casper AI Toolkit | Agent-prompted contract interactions and Casper-native tool invocation from the runtime |
| Wallet-bound reputation | Deeper reputation and marketplace stats tied to wallet-owned agent/verifier history |
| External agent frameworks | Adapters so autonomous agent runtimes can call SealRail as a proof-gated payment rail |

The manifest is intentionally public and secret-free. It gives other builders a stable way to discover how to create payment-backed tasks, run agent verification, anchor proof, inspect receipts, and unlock payment only after proof.

### MCP server

```bash
cd backend
npm run mcp
```

The stdio MCP server exposes five tools, so any MCP client can read SealRail state and create payment-backed tasks:

| Tool | Purpose |
|---|---|
| `sealrail_status` | Read backend, Casper, verifier, CSPR.cloud, and trust-boundary status |
| `sealrail_agent_manifest` | Read the machine-readable integration manifest |
| `sealrail_list_proofs` | List proof bundles and payment states |
| `sealrail_get_proof` | Fetch a specific proof bundle by proof id |
| `sealrail_create_payment_task` | Create a payment-backed task using a caller-supplied SealRail API key |

### CSPR.cloud endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/integrations/cspr-cloud/status` | CSPR.cloud reachability, x402 facilitator, CSPR rate, node health |
| `GET /api/integrations/cspr-cloud/deploys/:deployHash` | Confirm deploy execution status on Casper testnet |
| `GET /api/integrations/cspr-cloud/rates/cspr/latest` | Current CSPR/USD rate |

## Live deployment and proof

Frontend on Vercel ([sealrail.xyz](https://sealrail.xyz)), backend on Railway ([api.sealrail.xyz](https://api.sealrail.xyz)), contract on Casper testnet.

**A failing proof, taken live from `GET /api/proofs` just now.** Verification failed, so there is no anchor and payment is blocked, exactly as the invariant requires:

```json
{
  "proof_id": "6d809aec-c67d-44aa-938d-e75c2867bd4c",
  "task_id": "669b4ed1-356f-4f2f-af5c-2d135adc8cc7",
  "invoice_id": "INV-1030",
  "input_hash": "95fdb566d8252117a27cda9b396aa06587489cb6bfb7d7b5b333ba15983e5261",
  "output_hash": "81e446db361128fd0ae6139339ab8f1aee2c1f485eef7857be8f1b47b8deaae1",
  "casper_anchor_hash": null,
  "mode_label": "Schema + hash verification",
  "proof_status": "failed",
  "payment_state": "blocked",
  "created_at": "2026-07-18T17:44:43.646Z"
}
```

**A confirmed anchor on Casper testnet**, the deploy behind the badge above:

- Deploy [`9a708f9e…c72edd6d`](https://testnet.cspr.live/deploy/9a708f9e84c6d8f2d93d196823312a7f6ce8f903b93c344115f7e8c9c72edd6d) — status `processed`, `error_message: null`
- ProofRegistry package `hash-02f9771e9cd4d91c40705563074bc323d45a341a11987464367ac909cc845846`
- Entry point `anchor_proof`, ~0.99 CSPR gas consumed

Confirm any deploy yourself: `GET /api/integrations/cspr-cloud/deploys/:deployHash`.

## Deployment

The backend runs on **Railway** with automatic deploys from the `master` branch:

- **Persistent volume** at `/data` for SQLite storage
- **Automatic health checks** against `/api/health`
- **Environment-configured** through Railway (Casper mode, LLM provider, CSPR.cloud token, Blocky AS config)

Startup validates configuration and reports readiness at `GET /api/status`. A misconfigured testnet or mainnet deployment refuses to pretend it is anchoring rather than silently simulating. Local development and VPS runbooks live in [backend/DEPLOYMENT.md](backend/DEPLOYMENT.md).

## Verification status

Claims below are current at the linked commit and enforced in CI.

| Surface | Status |
|---|---|
| Backend suite | 769 tests across 17 files, passing with no external services |
| Contract suite | 23/23 (`cargo odra test`) |
| Contract deployment | ProofRegistry package live on Casper testnet — `hash-02f9771e9cd4d91c40705563074bc323d45a341a11987464367ac909cc845846`; latest confirmed anchor [`9a708f9e…c72edd6d`](https://testnet.cspr.live/deploy/9a708f9e84c6d8f2d93d196823312a7f6ce8f903b93c344115f7e8c9c72edd6d) |
| TypeScript | Strict mode, `tsc --noEmit` clean on both packages |
| Trust boundary | Production API is configured for Casper testnet anchoring with confirmed deploy hashes. Hosted TEE access is pending/config-gated and never silently simulated. |

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, Tailwind 4, CSS Modules |
| Backend | Node 20+, TypeScript 5 (strict), Fastify 5, better-sqlite3 |
| Contract | Rust, Odra 2.8, Casper testnet |
| Verification | Schema + WASM hash binding (Blocky-compatible adapter; hosted TEE access pending) |
| Integrations | CSPR.cloud, MCP (`@modelcontextprotocol/sdk`), x402-compatible receipts |

## Installation

Runs on a clean clone with no credentials. Requires Node 20+. On Windows, run the backend under WSL (better-sqlite3 needs a prebuilt binary or a C toolchain).

```bash
# Backend
cd backend
npm install
cp .env.example .env      # defaults work locally (dry_run Casper, no LLM)
npm run seed              # registers the first-party verifier, agent, and listing
npm run dev               # http://localhost:3001

# Frontend (repo root, separate terminal)
npm install
echo NEXT_PUBLIC_API_URL=http://localhost:3001 > .env.local
npm run dev               # http://localhost:3000
```

Then open http://localhost:3000/run. Task creation, verification, anchoring, and payment unlock all run locally. Agent execution calls a real LLM: set `LLM_API_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL` in `backend/.env` (any OpenAI-compatible endpoint, Groq included). **Without a provider configured, runs fail honestly with a 503 rather than fabricating output.** Casper anchoring defaults to `dry_run`; set `CASPER_MODE=testnet` with a contract hash to anchor on-chain.

### Environment variables

Frontend (`.env.local`):

| Var | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL (`http://localhost:3001` locally) |
| `NEXT_PUBLIC_SITE_URL` | Public site URL for absolute Open Graph / Twitter card image links |

Backend (`backend/.env`, see [backend/.env.example](backend/.env.example) for the full annotated list):

| Var | Purpose |
|---|---|
| `LLM_API_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` | OpenAI-compatible provider for agent execution (Groq in production) |
| `CASPER_MODE` | `dry_run` (default), `testnet`, or `mainnet` — testnet/mainnet fail closed if misconfigured |
| `CASPER_CONTRACT_HASH` | Deployed ProofRegistry contract hash |
| `BLOCKY_MODE`, `BLOCKY_AS_API_KEY`, `BLOCKY_AS_HOST` | Blocky-compatible / hosted TEE adapter configuration |
| `CSPR_CLOUD_TOKEN` | CSPR.cloud API token for Casper data, rates, and node status |
| `ALLOW_BOOTSTRAP_KEYS` | `true` permits self-serve API key creation; `false` (production default) requires an authenticated key |
| `REQUIRE_WALLET_AUTH` | `true` (default) gates payment-backed actions behind a wallet-verified key |
| `FRONTEND_ORIGIN` | CORS allowlist for the web app |

### Scripts

| Where | Command | What |
|---|---|---|
| root | `npm run dev` / `build` / `lint` | Next.js dev server, production build, ESLint |
| backend | `npm run dev` / `test` / `build` | API server, 769-test suite, typecheck |
| backend | `npm run seed` | Idempotent first-party verifier + agent + listing setup |
| backend | `npm run mcp` | MCP stdio server (5 tools for AI-agent integration) |
| contracts | `cargo odra test` | Contract test suite |

## Testing

```bash
cd backend && npm test        # 769 tests across 17 suites, no external services
cargo odra test               # 23/23 contract tests
```

The suite is not padded. Its center of gravity is the invariant: tests assert that the payment state machine has no path to payable without a verified proof, that a failed proof produces no anchor and a blocked payment, and that a submitted-but-unconfirmed Casper deploy is treated as a failure rather than a success. The page can never show a payout the engine did not authorize.

## Challenges and lessons

Three bugs that only appeared under real conditions, and what they taught us:

- **"Anchored" used to mean "submitted," not "executed."** The anchoring service returned success the moment it parsed a deploy hash. A hand-crafted test deploy that reverted on-chain (`User error: 6`) still read as a successful anchor. That is the difference between a demo and a lie, so anchoring now polls the deploy through CSPR.cloud and only accepts it once execution is confirmed. This is the single most important correctness fix in the project.
- **The paid flow worked without a wallet and broke with one.** Once a Casper Wallet was connected, the run routed through wallet-scoped auth and returned a 401, so a judge who connected their wallet first hit a dead end. Auth is now a deliberate, consistent gate: owner-sensitive actions require a wallet-verified key, and the flow no longer half-authenticates.
- **The Casper Wallet signs with an extra algorithm-tag byte.** Verifying real wallet signatures failed until we accounted for the wallet prepending an algorithm tag that `casper-js-sdk`'s verifier did not expect. Signing a real (never-broadcast) transaction turned out to be more verifiable than the wallet's plain message-signing API, which has no documented byte convention.

Nothing here went smoothly the first time. The honest status board at [`/status`](https://sealrail.xyz/status) exists because we would rather show a judge exactly what is live and what is pending than get caught overclaiming.

## Roadmap

| Next | State today |
|---|---|
| Wallet-bound CSPR settlement | Proof-gated payment **state** plus Casper anchoring is live; wallet-bound value settlement is the next step |
| Hosted TEE attestation via Blocky AS | Adapter is built and config-gated; hosted access is not yet provisioned, and the UI never claims enclave attestation until it is |
| Second live agent runtime (RWA compliance) | Seeded as a marketplace listing, clearly labelled **preview**; only the invoice-risk agent has a live runtime today |
| Mainnet anchoring | `CASPER_MODE=mainnet` path exists and fails closed if misconfigured; out of scope for this build |

## Scope and honesty

- The RWA compliance agent is a **preview** marketplace listing, labelled as such in the UI. Only the invoice-risk agent has a live runtime.
- Hosted TEE attestation is **not** running in production. Verification is deterministic schema + WASM-hash binding plus the LLM. `/status` shows this in amber; the app never claims enclave attestation.
- Demo tasks use seeded input, but the engine, the verification, the on-chain anchor, and the decision are real.
- Every number in this README is reproducible by running the project or opening the linked deploys.

## Repository layout

```
app/                          Next.js routes (run, proofs, marketplace, agents, owner, workflows, review, status)
components/                   Screen components and shared primitives
lib/                          Typed API client, API types, session bootstrap
backend/src/routes/           Fastify route modules (tasks, payments, proofs, agents, integrations)
backend/src/services/         Domain services (state machines, verification, Casper anchoring, reputation, keys)
backend/tests/                17 suites, 769 tests
contracts/verified-agent-payments/   Odra ProofRegistry contract, tests, livenet CLI
docs/                         Architecture, design, API docs, audit reports
```

## License

[MIT](LICENSE). Contributions welcome; see [CONTRIBUTING.md](CONTRIBUTING.md). The one hard rule: nothing may fake verification.
