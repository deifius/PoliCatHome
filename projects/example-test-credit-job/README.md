# Signed test-credit job example

This `project.yaml` is for `polyc sign` (the built-in, deterministic CPU job format), **not** the OCI submission `project.yaml` with an associated project-owned `polic.yaml`. The two formats are intentionally separate until HIRD/Linux securely accepts third-party code.

The sender signs the project with `polyc sign --project ... --private ... --out ...`, the operator submits it to `/api/jobs`, and the project owner must reserve `5 × 1 = 5` test credits via `polyc credit-reserve` before the coordinator leases any tasks. Task completion is independently recomputed; credit settlement follows when the results are verified. There is no real payment or guaranteed compute entitlement.

Every contributing node needs `spec.financial` opted in to this asset and a matching registered wallet. The project owner needs its own signed enrolled project wallet whose public key equals the project-signing public key.

See [`docs/economics.md`](../../docs/economics.md) for CLI commands and the complete transaction lifecycle.
