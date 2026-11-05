# Contributions, credits, and distribution: the ledger of household affairs

> The cat responsible for the broken vase should be identifiable. This is not evidence that the cat agreed to buy the vase.

**Goal:** transparent auditable *contributions*, not a speculative token. A ledger is about **clarity** and **fair terms** before revenue, not about compelling owners to reveal their identities.

## Receipt contract

For each verified task, the coordinator records a receipt with project ID, pseudonymous node ID, task ID, result digest, the verification actually performed, the reported duration (identified as self-reported), a provisional credit quantity, project declaration hash, timestamp, and preceding receipt hash. The SHA-256 digest of `{previous,entry}` forms a per-project hash chain. Duplicate task completion cannot create a second receipt because existing task leases cannot be completed twice.

The `polyc ledger --project-id PROJECT --admin-token-file ...` CLI and authenticated `GET /api/ledger/{project_id}` return receipts, current root, locally verified chain consistency, and provisional credits. Results currently represent only the **built-in independently re-computed SHA-256 task**; the coordinator awards one provisional unit per completed verified task. This is not a claim about quality, hours, energy, greenhouse emissions, GPU service, or money. The ledger does **not** execute the project's declared credit/revenue terms yet.

## Why not blockchain first?

A hash chain plus periodic publication of signed ledger roots to an **independent append-only archive** would be a useful next milestone. Blockchain anchoring may be added later, but does not by itself prove which code ran, whether a node contributed real compute, whether an ethical constraint was respected, or who deserves intellectual-property rights. A coordinator able to rewrite every historical record and root can rewrite a chain unless independently anchored. This prototype's root is **not anchored or signed**.

For a real cooperative exchange, design receipts *signed by worker and project verifier*, reconcile independent observations, disclose disputes, and give participants a way to export and challenge their records.

## Distribution agreements (specified, not yet executed)

The project constitution chooses one of three modes:

- `volunteer`: no credit claims and no monetary distribution.
- `credits`: issue project-specific, **non-transferable provisional credits** for independently accepted work; no guaranteed value.
- `revenue_share`: designate an explicit percentage of applicable revenue to contributors, define eligible revenue, expenses, settlement frequency, jurisdiction, taxes, dispute process, and the fraction attributable to each verified contribution. The schema records `revenue_pool_percent` plus a mandatory choice between **gross receipts** or **net receipts** (`revenue_basis`) for revenue-sharing projects, **not** a legally sufficient contract. For the envisioned "points against gross," set `revenue_basis: gross_receipts` and negotiate an explicit definition of gross receipts.

A potential future formula for one revenue-sharing period, **only under an accepted written agreement**, is:

`contributor_allocation = distributable_revenue × pool_percent / 100 × contributor_accepted_units / total_accepted_units`

But credits can only become distributable units after an agreed measurement/verification scheme; project revisions cannot dilute existing claims without fresh consent. Cancellation or local withdrawal stops future work; valid past credits are preserved for review. No payouts, revenue metering, royalties, legal title transfers or tax processing are implemented.

## Access, retention, and ethics

By default receipts should be participant-visible; pseudonymous public ledgers require opt-in. No public household addresses, device serial numbers, hidden ideology scores, or geolocation. Corrections should be **new compensating events** rather than erasure (except legally required redactions, with an accompanying notice and restricted audit). Contributor exclusions are contractual identity decisions, not automated accusations.

The prototype API is **administrator-only** and does not yet implement per-participant ledger authorization, signed receipts, external anchors, appeals, revenue distribution or automated settlement. Do not deploy it as an actual exchange.
