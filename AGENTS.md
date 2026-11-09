# Instructions for contributors and coding agents

**PolyC@home / PoliC@home** — Candid Constitutional Consent; Coordinated Computational Care.

**No PolyC without PoliC. Culpability with Clarity.**

Read `README.md`, `docs/threat-model.md`, `docs/hird-architecture.md`, `docs/project-submissions.md`, `docs/contribution-ledger.md`, `docs/economics.md`, and `docs/ROADMAP.md` before expanding the execution boundary.

## What is working

- `polyc/api.py`: authenticated FastAPI coordinator, SQLite task leases, cancellation, metrics.
- `polyc/policy.py`: strict fail-closed constitution validation and bidirectional declared-compatibility checks.
- `polyc/crypto.py`: Ed25519-signed project declarations; worker checks against *its own* signer allowlist.
- `polyc/worker.py`: local pause/kill, host activity check, optional CPU package sensor, network-loss abort, Nice Plus duty-cycle controller.
- `polyc/hird.py`: Linux **process runner for trusted built-in CPU work only**. NOT a VM or robust security sandbox.
- `polyc/compute.py`: `sha256_chain_v1`, the single permitted workload in v0.1.
- `polyc/chronicle.py`: grounded, human-readable summaries; no unmeasured energy/heat/GPU claims.
- `polyc/demo.py`: five independently configured agents on one host, 25 CPU tasks.
- `polyc/submission.py`: strict project OCI manifest + project `polic.yaml` schemas, immutable digest, Ed25519 signature, declared mutual compatibility preview.
- `polyc/api.py` `/api/submissions`: **staging only** of signed third-party OCI paperwork. Never enqueue images through the current process worker.
- `polyc/store.py` contribution receipts: one **provisional point** per independently verified built-in CPU task, hash-linked by project; this is NOT a financial balance.
- `polyc/credits.py`: TEST-ONLY, noncash, unbacked credit asset registry, Ed25519 wallet enrollment/transfer consent, issuance tied to verified volunteer receipts, atomic double-entry ledger, reserved paid-job budgets, verified settlement/refunds. No cash conversion or guaranteed compute.
- `polyc/economy_demo.py`: five-node credit experiment (25 volunteer tasks, five bilateral transfers, five paid test tasks, one settled escrow) on one machine.
- `polyc/payment_adapters.py`: declaration-only catalogue and future protocols. No connected PayPal, Zelle, Patreon, Stripe or financial custodian.

## Mandatory invariants

1. **Consent before compute.** Job/project signatures, node constitution digest, matching policies, and revocation are checked before work, and again at the node. Never let the coordinator overrule the host's rejection.
2. **Local always wins.** Owner pause must work with the coordinator offline. CPU resource usage must yield promptly; unsupported checkpointing or GPU preemption must never be promised.
3. **No untrusted code in `HIRD/process`.** Do not implement `exec`, `eval`, arbitrary shell commands, uploaded Python, downloadable models, or arbitrary OCI images as an extension of the subprocess backend. First build and verify real isolation in HIRD/Linux.
4. **Least privilege.** No secrets from host into guest, no administrative token on owner nodes, explicit trust key provisioning, no plaintext remote API in actual deployments.
5. **Culpability with clarity.** Never report task accomplishment, joules, carbon reductions, GPU time, or economic payouts without a trustworthy measurement or explicitly scoped verification. No automated personal ideological profiling.
6. **Thermals fail closed when enabled.** Mandatory stale/unavailable telemetry must deny work. The example config includes future GPU properties that the pilot does *not* enforce; reject unsupported mandatory limits.
7. **Cooperative choice is bilateral.** Enforce contributor allowlists and denylists as well as node content/ethos declarations. Avoid interpreting label matches as proof of real-world morality.
8. **A receipt is not magic.** Signed project manifests and SQLite log records are not proof of tamper-proof accounting or generalized computational correctness. Treat receipts as provisional until independently anchored and verified. Distinguish project "points against gross" from enforceable royalty obligations.
9. **No OCI execution in process mode.** Third-party submissions may only reach a staged state until HIRD/Linux VM isolation, genuine artifact attestation, and runtime network restrictions pass independent tests.
10. **Both documents must be signed as one bundle.** Changing `polic.yaml` or `project.yaml` requires new signature/revision and new project/node consent; preserve already earned credits across cancellation.
11. **No unverifiable geography or character judgments.** Geographic limits require verified location; contributor restrictions use explicitly agreed identifiers and allow appeals.
12. **A ledger hash chain without externally anchored roots can be rewritten.** Never describe local SQLite receipts as immutable, blockchain, or proof of payments.
13. **No third-party copyrighted art in repository** without source-specific provenance and rights review; use original, sparse, Thurber-informed humor. Do not copy specific Thurber drawings or captions.
14. **No money disguised as credits.** Only test-only, nonconvertible, unbacked assets are accepted. Do not add real payment rails, exchange rates, cash redemption, physical-value claims or custody without separate architecture, legal/compliance review and explicit constitutional authorization.
15. **Economic consent is bilateral.** Sender and recipient MUST sign the exact transfer; bind every signed object to one ledger ID, wallet policy digests, amount, expiry and a monotonic sender nonce. Owner key remains local. Do not ask users to hand private keys to the coordinator.
16. **Credits cannot be minted from mere assertions.** Require a verified, not-yet-credited, volunteer CPU receipt under an authorized capped test issuer. Do not silently treat provisional contribution points, reported wall time or claimed GPU-hours as transferable assets.
17. **Never schedule an unfunded promised-credit job.** Funds are reserved in an atomic clearing transaction. Completed verified task claims are honored before an early cancellation returns the remainder; payments are integer units, never floating-point money.
18. **No journal myths.** A local hash-linked double-entry ledger checks consistency, not operator honesty. A provider listed in a catalogue is not integrated, and a provider-declared payment is not a verified bank settlement.

## Developer workflow

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
python -m polyc.demo --timeout 35
python -m polyc.economy_demo
```

For scheduler, policy, auth, or sandbox modifications, add failure-path tests first. Do not claim milestone success unless all tests and the end-to-end five-node proof pass. Prefer deterministic workload and bounded CPU use. Do not require Docker, Kubernetes, QEMU, GNU Hurd, blockchain, wallets, or proprietary APIs to run the CPU pilot.

If adding a new HIRD backend, implement `create`, `start`, `pause`, `stop`, `destroy`, `status`, with explicit unsupported capability returns. `checkpoint` is optional. A guest cannot authorize itself or declare host temperatures safe. Keep host-side revocation independent of guest cooperation or coordinator connectivity.

## Near-term milestones

1. **M0: Documentation, consent model, threat boundary** — implemented and documented.
2. **M1: Deterministic signed CPU jobs and node constitutions** — implemented and tested.
3. **M2: Durable star coordinator, lease recovery, owner pause, Chronicle and metrics** — implemented and tested on one host.
4. **M3: Five agents completing one joint job** — implemented, run, verified on one host; physical five-host deployment remains untested.
5. **M3c: Signed OCI declaration intake, project PoliC contract, hash-linked CPU receipts** — implemented as non-executable staging and provisional points.
6. **M3d: Test-credit clearing** — implemented on a single coordinator: wallet consent, issuance, transfer, escrow, verified settlement, refunds. No monetary meaning, exchange or payment-provider connection.
7. **M4: True sandbox VM and host-enforced cgroup v2 CPU/memory quotas, TLS remote pilot** — not yet implemented.
8. **M5: GPU worker with host thermals, preemption strategy, power metering** — research only.
9. **M6: Federation, actual financial agreements, external audits, Catnap graphics** — research only.

## Naming / editorial voice

PoliC = Candid Constitutional Consent; PolyC = Coordinated Computational Care. HIRD = HIRD Isolated Resource Domain. HIRDing C@s = decentralized coordination. PolyC Daemon = worker/host agent. Chronicle = measured activity. Catnap = an explicitly opted-in contribution workflow (with an optional truthful visualization). Nice Plus = application-level deference, **not** Linux nice greater than +19.

Use original, occasional dry domestic quips; never make emergency messages, policy authorization, security outcomes or audit records depend on understanding a joke. The cats may be fanciful. The enforcement must not be.


## v0.4 binding terminology and browser contribution

- **Catnap** = contributing computation, **Create a Cat** = project authoring/submission, **Cat** = computational project/workload, **Catbox** = its sandboxed execution environment. Do not invert the roles.
- Default Catnap scene is **Gibson** (blue-monolith homage to *Hackers*); all scenery must be attributable to authenticated data or explicitly labeled synthetic demonstration data. Other built-ins: Flying Cats, Flying Toasters, 3D Pipes and Chronicle Terminal.
- Browser UI code is in `polyc/web/`, renderer SDK in `polyc/web/scenes/`, HTTP/invite/review routes in `polyc/browser.py`, and private SQLite extensions in `polyc/store.py`. See `docs/CATNAP-BROWSER.md` and `docs/SCENE-SDK.md`.
- Never let unauthenticated visitors query live private Chronicle data. Never publish tokens or node constitutions inside scene snapshots. No imported executable skin/plugin code. Do not approve arbitrary image execution as if it were the known built-in SHA-256 operation.
- Test `pytest -q`, `node scripts/test-browser-worker.mjs`, `node scripts/test-browser-protocol.mjs` for protocol compatibility. UI visual/browser reliability testing and five real physical browser participants remain explicitly outstanding.

## Publishing and licensing (2026)

- The project-created implementation, scripts, tests, configs and protocol code are BSD 3-Clause (`LICENSE`). Forks may remain private and proprietary; do not add compulsory contribution or disclosure terms.
- Original project documentation is CC BY 4.0 (`docs/LICENSE-CC-BY-4.0.md`); code examples are also BSD-licensed for reuse.
- Independent artwork is **not** automatically licensed; follow `docs/ART-ASSET-MANIFEST.md` and source-specific rights review. Third-party Cat submissions and output rights follow each creator's declarations, not repository defaults.
- Read `Philosophy.md` for principles, `LICENSING.md` for actual scope. A PoliC is a compute-consent declaration, not a copyright license.
- Rebuild `polyc/web/downloads/PoliCatHome-source.zip` after editing licensing files and check that it includes the notices, never `runtime/` secrets.

## Repository hygiene

- `polyc/` is the only implementation; `polyc/web/` is the only shipped browser frontend.
- Do not create root-level aliases of modules, docs, scripts, tests, or a nested repository.
- Read `docs/REPOSITORY-LAYOUT.md` before moving anything. A legacy checkout may
  have distinct edits in duplicate files; use `scripts/tidy-repository.py` to
  back them up, never delete them silently.
- Never move, wipe, package, or publish `runtime/` or Docker persistent volumes.
