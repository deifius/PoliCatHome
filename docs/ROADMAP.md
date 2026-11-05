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
| M4: HIRD/Linux VM isolation, cgroups v2, network deny and proof of kill | Planned | Host security and isolation test suite |
| M5: GPU-aware worker with thermal/power enforcement | Planned | Real device tests, prioritization and preemption evidence |
| M6: federation with cross-location latency, energy, jurisdiction, consent | Research | Signed contracts, load tests, measured fairness |
| M7: real financial transfers, public exchange, audited revenue, Catnap graphical UI | **Not implemented** | Legal/security review, provider integration, calibrated metering, user tests |

## Immediate engineering queue

- Replace host-wide CPU duty approximation with cgroups v2 on supported hosts; detect absent controllers and reject unsupported mandatory quotas.
- Add expiration and revocation of project signer trust (beyond removing keys from constitution and re-enrolling).
- Add authenticated TLS reference deployment and real five-machine network acceptance run.
- Anchor and sign contribution and test-credit ledger roots independently; add contributor disputes, owner wallet key rotation/recovery, authenticated financial event evidence, and corrections, clearly distinguished from proof of honest computation.
- Make HIRD/Linux a *real* VM backend and reject all untrusted tasks until tests prove its isolation and shutdown boundaries.
- Build Catnap text-first truthful screensaver, then graphical visualization.
- Explore federated ML, constrained distributed training/inference, location-awareness, renewable electricity and reusable heat with measured—not assumed—advantages.

> The cats are prepared to expand operations. The fire marshal has requested a diagram.
