# Catnap in a browser — v0.4

> **Catnap** contributes compute. **Create a Cat** creates a project. A **Catbox** is the isolated execution environment for a Cat. No PolyC without PoliC.

## What is runnable now

The existing FastAPI process serves a static, dependency-free web app at `/`:

- **Catnap:** self-service browser enrollment on explicitly opted-in pilot Commons, explicit trust of approved Cat creators, a best-effort CPU budget, a local pause action and coordinator revocation. A dedicated Web Worker performs the **bundled** `sha256_chain_v1` task using Web Crypto. A separate SHA-256 digest of the owner's constitution is verified by the coordinator. The worker verifies each Ed25519 Cat signature against the owner's allowlist and checks basic compatibility again locally before doing work.
- **Create a Cat:** a structured authoring form for the existing signed deterministic CPU protocol. It generates and stores a non-exportable Ed25519 private key in the browser's origin-bound IndexedDB (where supported), exports signed JSON and submits a proposal with a one-use invitation. An operator can review/approve/reject the Cat in the Commons dashboard. **Proposals do not queue jobs automatically.** Once approved, independently consenting workers can lease the built-in work. No arbitrary code is uploaded, executed or fetched.
- **Scenes:** default WebGL 2 Gibson monolith skyline, Flying Cats, Flying Toasters, 3D Pipes (Canvas), Chronicle Terminal, theme presets, import/export of declarative skins, scene SDK. Every built-in scene consumes the *same* privacy-scoped telemetry endpoint. UI updates approximately every 2.5 seconds; local worker progress is updated more often. The `DEMO` badge and central watermark indicate synthetic examples; `LIVE` only appears with authenticated data.
- **Telemetry:** actual coordinator nodes, signed project titles and categories, counts by task state, recent events. Only the operator can see the global picture; owner tokens are restricted to their own nodes. No credentials, constitutions, physical locations or detailed host telemetry leave in scene payloads.

## Quick start — operator and one or more browsers

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
node scripts/test-browser-worker.mjs      # optional: requires Node.js 22+
node scripts/test-browser-protocol.mjs    # optional: requires Node.js 22+
export POLYC_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"
polyc serve --db runtime/browser.sqlite --host 127.0.0.1 --port 8765
```

Open **http://127.0.0.1:8765/** in a compatible secure-context browser. It displays a **synthetic** Gibson demonstration until you connect. You can switch scenes and skins without credentials. A browser with WebGL 2 is required for Gibson; other scenes fall back to Canvas 2D. Modern Web Crypto Ed25519 support is required to create or verify Cats in the browser.

For a complete local workflow:

1. In **Commons**, enter the `POLYC_ADMIN_TOKEN` value (held in page memory, not saved to local storage), choose **Create a Cat**, generate a one-use invitation, and privately give it to the creator.
2. In **Create a Cat**, choose the workload template, enter a *real* public source URL and a *real* 40-hex Git commit, declare contributor eligibility and any optional **noncash test-credit** terms, describe the Cat, and submit with the invitation. The app generates a non-exportable browser signing key and downloads the signed manifest. The public signer key is displayed and can be copied.
3. In **Commons**, review and **approve** the signed Cat. This only queues its built-in deterministic SHA-256 tasks. The operator must independently inspect source/license/purpose claims; this pilot **does not** verify the claimed source commit or remote repository.
4. With `POLYC_SELF_ENROLL=1`, each willing visitor opens a browser, chooses the approved Cat creator they trust, reviews their personal PoliC and browser limitations, acknowledges the resource impact, enrolls without an invitation and **separately** clicks **Start Catnap**. No administrator token or pasted public key is required for guests.
5. Switch to the default **Gibson** scene and use the authenticated operator overview to see all nodes and projects, or use each owner's restricted local view. The confirmed `done` count and Chronicle events originate from verified coordinator records. The monolith animation is artistic; it is not a precision power/thermal meter.

For five contributors, let each visitor opt into a Cat creator and enroll from their own device. The coordinator applies a five-successes-per-direct-peer-per-hour pilot limit. Use five distinct browsers/devices/contexts and keep the app open and visible. When there are no consent-compatible approved Cats, the worker honestly reports `IDLE — NO MATCHING CATS`. You can also use the existing `polyc init-pilot` and native agent commands alongside browser nodes.

### HTTPS and network boundary

Binding to `127.0.0.1` is an intentional safety default. Do **not** open the development server directly to the public Internet or use `--insecure-http-on-lan` for real volunteers. Use a properly configured HTTPS reverse proxy or VPN, separate identities, careful secret distribution, request limits and auditing before enrolling actual households. Secure contexts are also required for Web Crypto and many browser capabilities. No OS screensaver registration is implemented; **FULLSCREEN** is a browser-scene view, and it doesn't make browser work persist with the tab closed.

### Important enforcement limitations

Browser workers do not enforce host CPU niceness, cgroups, GPU/CPU package temperatures, GPU power, whole-system electricity, thermal kill switches, strict CPU quotas, or persistent idle-only scheduling. They deliberately refuse registration with an explicit required CPU temperature threshold, GPU utilization cap or financial settlement policy, and the source code only executes a known built-in algorithm. A browser contributor explicitly accepts the remaining *cooperative* CPU pacing limitation. For constitutional safeguards that must be enforced at OS level, choose the **native** worker or a future audited Catbox/HIRD virtual machine.

Tasks are capped at **10,000** SHA-256 iterations in the browser, with a **20-second local timeout** against the coordinator's **25-second lease**. Larger jobs may be served to native workers instead. A suspended browser tab can abandon a leased task; the coordinator reclaims it after expiry. A Cat creator can declare a test-credit contract, but credit-priced work remains unschedulable until an operator provisions valid assets/wallets and places funded escrow using the existing economic protocol. Volunteering creates provisional receipts, **not** automatically paid credits; no real money is involved. Provisional receipts are created only on independently verified success, as before.

Browser identity secrets and node configuration are temporarily stored in *sessionStorage*, which is readable to same-origin scripts; a compromised origin or browser extension can steal them. Page CSP disallows external scripts, but that is not a complete defense. The creator's private key is non-exportable via the Web Crypto API; clearing IndexedDB destroys that creator identity. There is no account recovery/transfer mechanism yet.

## API additions

| Path | Authorization | Behavior |
|---|---|---|
| `GET /` and `/web/*` | Public | Static app; visible synthetic demo |
| `GET /api/catnap/constitution-template` | Public | Minimal browser policy scaffold; empty signer trust remains safely idle |
| `POST /api/catnap/invitations` | Operator | One-use, hashed invitation credentials for `catnap` or `create_cat` |
| `POST /api/catnap/enroll` | Either one-use invitation or explicit self-enrollment opt-in | Register node under declared browser-safe PoliC; self-enrollment requires acknowledged limitations |
| `GET /api/catnap/catalog` | Public | Browser-compatible, operator-approved Cat metadata and creator keys, never pending proposals |
| `GET /api/catnap/enrollment-options` | Public | Shows whether self-enrollment is enabled for this coordinator |
| `GET /api/catnap/snapshot` | Operator | Live global visualization data |
| `GET /api/catnap/snapshot?node_id=...` | Own node token or operator | Node-scoped live visualization data |
| `POST /api/workshop/cats` | One-use Create a Cat invitation | Verify signature; stage Cat proposal (not executable) |
| `GET /api/workshop/cats` | Operator | Review queue |
| `GET /api/workshop/cats/{id}` | Operator | Signed Cat proposal and metadata |
| `POST /api/workshop/cats/{id}/review` | Operator | Approve the built-in job or reject |

Other endpoints (`/api/jobs`, `/api/lease`, `/api/tasks/*`, `/api/credits/*`, `/api/chronicle/*`) retain their existing semantics and authorization.

## Verification

Run `pytest -q` for coordinator/regression/authorization tests. `node scripts/test-browser-worker.mjs` runs the **actual browser worker** SHA-256 loop against a known reference, and `node scripts/test-browser-protocol.mjs` signs/verifies a Cat using Web Crypto; Python `polyc.crypto.verify_project` can independently verify the resulting manifest. Browser-side WebGL visual and multi-tab tests are still needed on an unrestricted browser and hardware; this initial revision does not claim those have passed.

## Public source snapshot and contributor capability disclosure

The Catnap landing page shows a capability summary **before** the scene: browser CPU-only SHA-256 chain, user-controlled pause and consent, no native GPU or arbitrary Catbox, and no guaranteed thermal or CPU cap. It explains invitation-free opt-in on the local pilot, explicit creator selection, the visible tab requirement, and that no contribution occurs just by visiting.

The homepage includes a **Get the source** link to `/web/downloads/PoliCatHome-source.zip` and a standalone `/web/self-host.html` guide. Operators can regenerate the published source snapshot after source changes with `python scripts/build-source-snapshot.py`. The snapshot is a **ZIP copy of source**, not a Git clone/history or a remote repository URL, and deliberately excludes runtime data and secrets; review its contents before a public release. Running your own coordinator does not automatically register your compute as a contributor.

## Owner-authored browser PoliC (v0.5)

The Catnap enrollment panel offers a visitor-editable constitution before any registration is submitted. A guest explicitly chooses allowed project categories (open science, climate research, open media), whether commercial projects are eligible (default **no**), additional excluded purpose tags, explicitly trusted creator Ed25519 public keys, cooperative CPU pacing (5–75%), and a per-task local runtime timeout (5–20 seconds). Baseline hard-coded exclusions, public-source/pinned-commit requirements, signature checks, and the owner's ability to stop work remain in place. A zero-category constitution is rejected. The creator declares a project's category and purposes; those labels are not independently verified facts about project content.

**Preview My PoliC** displays the exact constitution that would be submitted, and **Export PoliC JSON** downloads it without enrolling or starting Catnap. Explicit acknowledgement of the browser's energy/heat and unenforceable resource limitations is required before enrollment. The checkbox is sent as a boolean acknowledgement that the server validates for invitation-free enrollment; it does not prove understanding or enforce hardware safety. Registered restrictions, including trusted creator keys, are enforced by the coordinator before lease matching and checked again on the client; changing them after enrollment currently requires revoking and re-enrolling (no new invitation if self-enrollment is enabled). The interface displays the registered policy after enrollment to avoid suggesting a draft is already active.

The visitor also chooses a browser-local session limit of 15, 30, 60 minutes or until manually paused. This session limit does **not** become part of the server-side constitution; it stops further leasing once its deadline is noticed by the running page, and existing Web Worker tasks still obey their separate task timeout. It is not an OS-level scheduler or a guarantee against CPU usage after browser suspension. On page close, local worker execution is terminated. The per-session duration selection is not a persistent consent preference and reverts to the default on page reload.

## Self-service Catnap (v0.6 local pilot)

Set `POLYC_SELF_ENROLL=1` only on a coordinator you intentionally allow to accept anonymous guest registrations. The supplied **local-only** `compose.yaml` opts in. Self-enrollment requires a browser form acknowledgement (`accepted_browser_limitations: true`, independently checked by the API), but **not** operator credentials, a contributor invitation, or a creator key. An empty signer allowlist means **zero tasks can be leased**; it does not imply trust in the Commons. The UI lists only approved, executable, browser-bounded built-in Cats and lets the contributor explicitly select their signing keys. Key trust extends to future approved Cats signed by the same creator, subject to category, purpose, commercial and other PoliC restrictions. The server checks signer trust before leasing; the worker also verifies signatures locally. Revocation blocks future API access and new leases.

For the local pilot, self-enrollment is constrained to five successes per directly connected peer per hour (the peer identity is stored only as a keyed hash), and at most 250 active nodes. These lightweight quotas are not a public-grade identity, DDoS defense, or anti-bot solution. Behind proxies, multiple visitors may share a peer IP; do **not** accept untrusted forwarded headers. Public service would need TLS, ingress limits, bot defenses, structured abuse review, and a lifecycle for dormant identities. The administrator still reviews Cat submissions and the existing one-use Create a Cat invitation remains required.
