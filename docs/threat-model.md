# Security boundary and threat model (v0.3)

> The guest was given a room, not the keys to the house. The pilot's room has no secure lock yet.

## Assets and parties

- **Host owner:** owns hardware, node constitution, pause flag, personal data and local OS.
- **Project author:** owns project declaration and signing key; may approve/reject declared contributors.
- **Coordinator operator:** controls job intake, nodes and leases; is *not* the final authority on a host.
- **Potential adversaries:** malicious submitter, malicious coordinator, compromised node, thief of a bearer token, hostile network peer, dishonest claimant about a project's purposes.

## Implemented controls

- Admin bearer token is required to register nodes, submit jobs, cancel jobs or see aggregate project summaries.
- Node bearer tokens are stored in SQLite only as SHA-256 digests; each node's reports are access controlled.
- Ed25519 signs canonical project manifests. Workers verify against their own explicit signer allowlist, not only the coordinator's decision.
- Node constitution digest is checked against the coordinator's registered copy. Node independently evaluates matching rules.
- Node owner pause file and process kill operate locally; coordinator outage stops a running task at next status check and prevents new leases.
- Worker only executes the bundled `sha256_chain_v1` deterministic task with a limited parser. No arbitrary shell, uploaded Python, image, container, model weights or remote code.
- Process runner applies Linux `nice +19`, address-space and CPU-seconds rlimits, and a best-effort run/suspend duty cycle. A separate supervisor enforces runtime and a local stop.
- Results are checked against independent deterministic computation before the coordinator marks them done.
- When a CPU package thermal limit is explicitly set, a missing identifiable sensor denies execution. Demo leaves this optional threshold unset and therefore does **not** claim thermal monitoring.

## Not guaranteed / unacceptable assumptions

- **No hostile-code isolation**: ordinary subprocesses share the host kernel and Python package path. DO NOT run untrusted code via HIRD/process.
- **No transport security**: local HTTP development API is not suitable for remote household networks. Run behind authenticated TLS/SSH tunnel/private VPN before actual five-host pilot. Bind localhost by default.
- **No independent log immutability**: SQLite event records and the new hash-linked credit journal can be modified and rehashed by an administrator with database access. Ed25519 signs jobs, wallets, transfers and project reservations, but not an independently witnessed ledger checkpoint.
- **No source-to-binary attestation**: the `source_repo` and `source_commit` fields are declarations. The running work is bundled with this installed version of PolyC, not fetched from that source repo.
- **No device identity verification**: a node string plus secret bearer token identifies its role, not a person's beliefs or an independently audited identity.
- **No whole-system energy or GPU thermal enforcement**: if requested, unsupported mandatory mechanisms must deny execution. There is no basis to calculate heat recovered or carbon avoided.
- **No system-wide CPU quota guarantee**: the duty-cycle approach and `nice` are advisory under varied kernels/cgroup configurations. A hardened HIRD/Linux must use host-controlled cgroups and measure results.
- **No perfect immediate stop**: the worker checks pause every ~60 ms during an assigned subprocess; scheduler and OS latency are not bounded as a real-time guarantee.
- **No generalized result proof**: the coordinator can verify tiny known hash chains, not arbitrary AI inference or training results.
- **No signed contributor reputation, automatic ethos verification, content moderation ML, global audit blockchain, or real payments**. v0.3 credits are noncash test units with no contractual redemption rights.
- **No public-grade economic identity, recovery or federation**: wallets have no revocation/recovery/rotation process, nor identity proof beyond a key and operator enrollment. Accounts are ledger-local, and the operator is a trusted sequencer.
- **No guarantee of value, liquidity or earning rates**: test credits are not real GPU-hours and do not entitle holders to a particular node; owners can withdraw hardware consent. An asset issuer declaration is not proof of reserves.
- **No live provider evidence**: PayPal/Patreon/Zelle/Stripe labels in a signed `polic.yaml` are assertions about intended money flows, not verified payment events or provider connectivity.

## Mandatory future negative tests before executing third-party code

VM escape, kernel attack surface, no network egress without permission, filesystem secret and mount isolation, swap/core dump handling, syscall and GPU DMA attack paths, cgroup memory/CPU pressure, guest pause/kill during coordinator loss, stale sensors, power meter loss, VMs without nested virtualization, GPU passthrough revocation, socket and artifact injection, and secrets leaked through logs.

A policy declaration is evidence that a participant *said* something, not proof of ethical behavior or legal responsibility. The owner remains sovereign even when the coordinator cannot be reached.
