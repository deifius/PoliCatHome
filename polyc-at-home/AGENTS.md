# Instructions for contributors and coding agents

**PolyC@home / PoliC@home** — Candid Constitutional Consent; Coordinated Computational Care.

**No PolyC without PoliC. Culpability with Clarity.**

Read `README.md`, `docs/threat-model.md`, `docs/hird-architecture.md`, `docs/project-submissions.md`, `docs/contribution-ledger.md`, and `docs/ROADMAP.md` before expanding the execution boundary.

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
- `polyc/store.py` contribution receipts: one provisional credit per independently verified built-in CPU task, hash-linked by project. Ledger is unsigned and not externally anchored.

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

## Developer workflow

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
python -m polyc.demo --timeout 35
```

For scheduler, policy, auth, or sandbox modifications, add failure-path tests first. Do not claim milestone success unless all tests and the end-to-end five-node proof pass. Prefer deterministic workload and bounded CPU use. Do not require Docker, Kubernetes, QEMU, GNU Hurd, blockchain, wallets, or proprietary APIs to run the CPU pilot.

If adding a new HIRD backend, implement `create`, `start`, `pause`, `stop`, `destroy`, `status`, with explicit unsupported capability returns. `checkpoint` is optional. A guest cannot authorize itself or declare host temperatures safe. Keep host-side revocation independent of guest cooperation or coordinator connectivity.

## Near-term milestones

1. **M0: Documentation, consent model, threat boundary** — implemented and documented.
2. **M1: Deterministic signed CPU jobs and node constitutions** — implemented and tested.
3. **M2: Durable star coordinator, lease recovery, owner pause, Chronicle and metrics** — implemented and tested on one host.
4. **M3: Five agents completing one joint job** — implemented, run, verified on one host; physical five-host deployment remains untested.
5. **M3c: Signed OCI declaration intake, project PoliC contract, hash-linked CPU credits** — implemented as non-executable staging and provisional records; monetization and attestation remain future work.
6. **M4: True sandbox VM and host-enforced cgroup v2 CPU/memory quotas, TLS remote pilot** — not yet implemented.
7. **M5: GPU worker with host thermals, preemption strategy, power metering** — research only.
8. **M6: Federation, economic agreements, audits, Catnap graphics** — research only.

## Naming / editorial voice

PoliC = Candid Constitutional Consent; PolyC = Coordinated Computational Care. HIRD = HIRD Isolated Resource Domain. HIRDing C@s = decentralized coordination. PolyC Daemon = worker/host agent. Chronicle = measured activity. Catnap = a *future* truthful visualization. Nice Plus = application-level deference, **not** Linux nice greater than +19.

Use original, occasional dry domestic quips; never make emergency messages, policy authorization, security outcomes or audit records depend on understanding a joke. The cats may be fanciful. The enforcement must not be.
