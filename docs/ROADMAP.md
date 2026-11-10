# Roadmap and actual evidence

The project works in small, falsifiable milestones. This file distinguishes tests from aspiration.

| Milestone | State | Acceptance evidence |
|---|---|---|
| M0: mission, threat boundary, constitutional vocabulary | Complete | README, AGENTS, threat model |
| M1: signed bounded CPU project, node constitutions, mutual compatibility | Complete | Ed25519 and policy tests |
| M2: durable coordinator, expiring leases, worker local pause and reporting | Complete | SQLite, auth, cancellation and recovery tests |
| M3a: five independent users/agents on one Linux host | **Complete** | `python -m polyc.demo` returns 25 verified tasks, 5 contributors |
| M3b: five distinct household Linux hosts over secure transport | **Not tested** | Needs real volunteers, TLS/VPN, varying kernels/sensors |
| M3c: signed OCI project petitions + project-side PoliC + provisional receipt ledger | **Staging and CPU receipts complete** | Signed manifests and contribution receipts; OCI is never executed |
| M3d: noncash transferable test credits | **Implemented and locally tested** | Wallet consent, bounded issuance, bilateral transfers, escrow, verified settlement, refunds, 5-owner economic demo |
| M3e: invited browser Catnap + Create a Cat workshop | **Implemented MVP; UI hardware test outstanding** | WebGL 2 Gibson + 4 other scenes; read-only real telemetry; browser SHA-256/Ed25519; browser and API tests; see the validation record |
| M3f: real five-browser end-to-end / persistent household browser contribution | **Not yet tested on unrestricted browsers** | Physical/browsers and differing policies; TLS, CPU load, browser suspension |
| M3g: Bloom v4 + Featured Cats editorial discovery | **Implemented, pilot UI review required** | Story module, static registry, no-compute UX tests; check real browser states and accessibility |
| I1: First-party identity with optional Google OIDC | **Implemented MVP, public rollout pending security review** | Independent Ed25519 key, one-time challenges, sessions, provider linking tests; no portable recovery or verified live Google callback |
| I2–I6: recoverable and federated PURDAH-inspired identity | Planned/research | Passkeys, key rotation, portability, unlinkable claims, recovery without original coordinator; see [identity plan](IDENTITY-SOVEREIGNTY.md) |
| M4: HIRD/Linux VM isolation, cgroups v2, network deny and proof of kill | Planned | Host security and isolation test suite |
| M5: GPU-aware worker with thermal/power enforcement | Planned | Real device tests, prioritization and preemption evidence |
| M6: federation with cross-location latency, energy, jurisdiction, consent | Research | Signed contracts, load tests, measured fairness |
| M7: real financial transfers, public exchange, audited revenue, production-grade Catnap UI | **Not implemented** | Legal/security review, provider integration, calibrated metering, user tests |

## Immediate engineering queue

- Replace host-wide CPU duty approximation with cgroups v2 on supported hosts; detect absent controllers and reject unsupported mandatory quotas.
- Add expiration and revocation of project signer trust (beyond removing keys from constitution and re-enrolling).
- Add authenticated TLS reference deployment and real five-machine network acceptance run.
- Anchor and sign contribution and test-credit ledger roots independently; add contributor disputes, owner wallet key rotation/recovery, authenticated financial event evidence, and corrections, clearly distinguished from proof of honest computation.
- Make HIRD/Linux a *real* VM backend and reject all untrusted tasks until tests prove its isolation and shutdown boundaries.
- Test and harden browser Catnap and its scenes on actual Chromium/Firefox/Safari devices, and audit the UI against the security model; add real opt-in public aggregated visualizations.
- Explore federated ML, constrained distributed training/inference, location-awareness, renewable electricity and reusable heat with measured—not assumed—advantages.

> The cats are prepared to expand operations. The fire marshal has requested a diagram.

## Release artifacts and public-host blockers

Before merging Identity I1, verify that the wheel bundles `polyc/web/featured-cats.json`
and `polyc/web/branching-story.mjs`, and that the published source ZIP is rebuilt
from the updated checkout. Run [release acceptance](RELEASE-CHECKLIST.md).
Local WSL tests are not proof of the Linode HTTPS deployment, Google OAuth
with real accounts, or permission to enable unreviewed public self-enrollment.
