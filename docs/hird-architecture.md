# HIRD — HIRD Isolated Resource Domain

GNU Hurd's recursive HIRD/HURD naming and its user-space server architecture inspire a **separation of authority**, not a requirement to use GNU Hurd or a promise that its microkernel offers stronger modern sandboxing.

## Guest-independent HIRD contract (target)

| Operation | v0.1 HIRD/process | Future HIRD/Linux KVM | HIRD/Hurd research |
|---|---|---|---|
| `start` | Bundled CPU hash-chain only | VM boot and signed workload | Experimental guest |
| `pause` | SIGSTOP process group | Host VM pause/cgroup | TBD |
| `stop` | SIGKILL process group | Kill VM from host | TBD |
| `status` | process `poll()` | VM monitor + host telemetry | TBD |
| `destroy` | child cleanup | VM resources/scratch cleanup | TBD |
| `checkpoint` | Unsupported | Depends on workload/hardware | TBD |
| GPU | Unsupported | Device-specific research | Unsupported for MVP |
| Isolation of strangers' code | **NO** | Requires separate security audit | **NO CLAIM** |

The only actual runner in v0.1 is `polyc/hird.py`. The name HIRD does not magically confer virtualization. The worker supervises its subprocess and kills it on owner pause, timeout, lost consent, expired lease, or coordinator failure. This is fine for **our own trusted demo function**, not for arbitrary third-party code.

## Data flow

1. Project author signs a manifest containing fixed executable *kind*, task count, bounded iterations, declared intents, contributor terms and source-repository metadata.
2. Coordinator checks signature and registers a queue of deterministic tasks.
3. Each participant's node constitution is registered and approved; the node retains its own copy and signer public keys.
4. Coordinator authorizes an eligible lease, checking declared compatibility and contribution fairness.
5. Worker independently verifies signed project, signer allowlist, node consent, task index, local activity and optional CPU package sensor; denies on any mismatch.
6. Worker launches its *bundled* `sha256_chain_v1` function in a low-priority process under resource limits.
7. Worker supervises locally and verifies current lease with coordinator while running. Local revocation works without network.
8. Coordinator verifies deterministic result, stores duration, outcome, and event records. Chronicle reports only actual measurements.

## Next engineering step

Linux/KVM guest images with reproducible builds and hashes, readonly rootfs, isolated ephemeral disk, disabled host mounts, default-denied network, QEMU security profile, cgroups v2 CPU and memory, host-side network and sensors, and testable shutdown under guest compromise. A passed-through consumer GPU may not yield gracefully to host use; treat this as a blocker rather than a promise. Hurd translators and Mach ports could be explored for capability-oriented API designs, while keeping host enforcement entirely outside the guest.

> HIRDing C@s is the art of arranging sufficient cooperation that nobody has to herd anybody.
