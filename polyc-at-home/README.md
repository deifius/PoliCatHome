# PolyC@home / PoliC@home

**Constitutional computing for the cooperative commons.**

> **No PolyC without PoliC. Culpability with Clarity.**

- **PoliC** — **Candid Constitutional Consent**: *whether* a node and a project have consented to cooperate.
- **PolyC** — **Coordinated Computational Care**: *how* consenting computation is scheduled, supervised, and reported.

PolyC@home is an open-source experiment in household-owned cooperative computation, drawing inspiration from SETI@home, Folding@home, GNU Hurd, and the cheerful impossibility of organizing cats. Owners retain the right to run their own work first, choose which projects their spare cycles support, and withdraw at any time. Project authors can also specify which contributors they consent to work with. Each side has a constitution.

**Status: v0.2 — runnable Linux CPU pilot plus staging-only project-submission protocol.** A coordinator plus **five independently configured worker agents** have successfully completed 25 deterministic tasks in a star network on one Linux machine. The pilot uses a constrained **process runner**, not a VM. **It can validate and stage signed OCI project paperwork; it cannot execute those images, accept arbitrary third-party code, execute ML models, manage GPUs, provide secure multi-tenant isolation, meter household electricity, enforce verified ideological judgments, or pay contributors.** Five separate physical households have not yet been tested.

## Meet the household

> The household has adopted a constitution. The cats have requested individual amendments.

**HIRD — HIRD Isolated Resource Domain** is the name of the future disposable execution sandbox. For now, `HIRD/process` runs only one trusted bundled task with subprocess resource limits and Linux `nice +19`. `HIRD/Linux` (QEMU/KVM) is the next proposed backend; `HIRD/Hurd` is a capability-oriented research track, *not* a runtime dependency.

**Nice Plus** refers to application-level priorities beyond Linux's `nice` range of -20 to +19. A worker process actually uses `nice +19`, plus a best-effort CPU duty cycle, host-side safety checks, and an immediate owner pause flag. None of those is a general solution to GPU preemption. The names are jokes; revocation isn't.

## Submitting a project: OCI image + PoliC constitution + ledger

Proposed projects have **two separate, signed YAML declarations**:

- `project.yaml`: a public source repository pinned to a Git commit, an OCI/Docker-built image **pinned by SHA-256 digest**, a bounded work-sharding protocol, and declared resource needs.
- `polic.yaml`: the project's own constitution: purpose, prohibited uses, commercial terms, contributor eligibility, mutual revocation, output licensing and contribution/revenue distribution.

A third artifact is generated as computation occurs: a **contribution ledger** consisting of per-project hash-linked receipts. The built-in CPU pilot now issues *provisional, non-monetary* credits for independently verified tasks, not payments or proof of GPU-hours. An actual revenue-sharing agreement would need additional contractual, metering and settlement controls.

**v0.2 stage-only path:**

```bash
# project.yaml and polic.yaml are illustrated in projects/example-render/.
polyc validate-submission --dir projects/example-render
# Create a new Ed25519 key pair and put the public key in polic.yaml before signing.
polyc keygen --private runtime/owner.pem --public runtime/owner.pub
polyc sign-submission --dir projects/example-render --private runtime/owner.pem \
  --out runtime/signed-submission.json
# With an already-running, authenticated local coordinator:
polyc submit-submission --signed runtime/signed-submission.json \
  --server http://127.0.0.1:8765 --admin-token-file runtime/admin-token.txt
```

The supplied example has **fake artifact/source hashes and a fake signer key**—replace them before signing. The submission endpoint returns `staged`, explicitly **not executable**. No code is fetched, reviewed, attested, scanned, or launched yet. Do not introduce `docker run` on the host as a shortcut: HIRD/Linux VM isolation must come first.

See [project submission specification](docs/project-submissions.md), [contribution ledger and royalties](docs/contribution-ledger.md), and [example petition](projects/example-render/). Project-side sovereignty and owner-side sovereignty must be mutually compatible. *The author can petition for a cat; no cat is obliged to take the part.*

## Run the five-cat pilot

Requirements: Linux, Python 3.10+, a local Python environment with network access for installation, and the dependencies in `pyproject.toml`. The coordinator binds to loopback by default.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
python -m polyc.demo --timeout 35
```

Expected outcome: `"done": 25`, five contributors named `cat-1` through `cat-5`, five completed tasks apiece. Real results are recomputed by the coordinator; no fabricated rendering or model inference is claimed. To retain private demo logs and SQLite records, use:

```bash
python -m polyc.demo --workdir runtime/five-cats --timeout 35
```

Each invocation creates its own run directory. **Keep `runtime/` private**: it contains node tokens and a project private signing key. The ephemeral one-command demo is the fastest test; the manual steps below describe separate owner processes.

## Run the components independently

The operator starts a star coordinator, creates Ed25519 project keys, and provisions five individually authorized owners. Each owner receives only their own `cat-N.yaml`, **never** the coordinator's admin token or the project private key.

```bash
polyc init-pilot --out runtime/my-first-household --nodes 5
export POLYC_ADMIN_TOKEN="$(cat runtime/my-first-household/admin-token.txt)"
polyc serve --db runtime/my-first-household/coordinator.sqlite --host 127.0.0.1 --port 8765
```

In another shell (the coordinator must already be running):

```bash
for n in 1 2 3 4 5; do
  polyc register --config "runtime/my-first-household/nodes/cat-$n.yaml" \
    --server http://127.0.0.1:8765 \
    --admin-token-file runtime/my-first-household/admin-token.txt
done
polyc submit --signed runtime/my-first-household/signed-project.json \
  --server http://127.0.0.1:8765 \
  --admin-token-file runtime/my-first-household/admin-token.txt
```

Then run each of the five workers in its **own terminal or Linux machine** (five commands, replacing `N` with `1` through `5`):

```bash
polyc worker --config runtime/my-first-household/nodes/cat-N.yaml \
  --server http://127.0.0.1:8765
```

This direct HTTP URL is valid only for local testing. **For five real homes, use an authenticated TLS proxy, private VPN, or SSH tunnels; never carry bearer tokens across an untrusted network over plaintext HTTP.** The pilot coordinator is not Internet-hardened. A non-loopback listener is refused unless an explicitly unsafe test flag is passed.

### A node owner can always say no

```bash
polyc pause --config runtime/my-first-household/nodes/cat-1.yaml
polyc chronicle --config runtime/my-first-household/nodes/cat-1.yaml
polyc pause --config runtime/my-first-household/nodes/cat-1.yaml --resume
```

Pause is enforced by the **local worker** even if the coordinator is unreachable. Press `Ctrl-C` to stop the worker. The coordinator also supports node revocation and project cancellation over authenticated API endpoints. An owner may edit a constitution, but must explicitly re-register its digest before new leases: silently changing the policy is not consent.

## The constitutional Cs

| C | Obligation |
|---|---|
| **Consent** | Mutual opt-in, ongoing authorization, revocation |
| **Control** | Local processes and the human owner take priority |
| **Constitution** | Declare and version constraints in machine-readable form |
| **Commons** | Open protocols, public-source aspirations, inspectable governance |
| **Cooperation** | Independent participants make agreements, not submissions |
| **Clarity** | Activity records and plain-language explanations |
| **Culpability** | Investigate responsibility using evidence, rather than assuming guilt from participation |
| **Correction** | Revocation, appeals, reproducibility, repair |
| **Conservation** | Explicitly bound energy and heat claims to *measured* facts |
| **Care** | Protect people, hardware, households, and habitats |

**Clarity before culpability.** Contributor identity, project intent, and culpability cannot be reliably inferred from source comments, a pseudonym, or a node's political labels. The pilot enforces *declared categories, purposes, allow/deny lists, and signed project assertions*—not automated moral certainty.

### Mutual constitutional matching

A project declares category, purposes, commercial terms, contributor allow/deny lists, a public source URL and pinned revision, and a **signed** deterministic workload manifest. The node declares approved categories, disallowed purposes, project signer public keys, resource bounds, and revocation rules. The coordinator matches both; the independent node **checks again** before execution. The pilot does not retrieve or verify that the declared source repository truly corresponds to the bundled code—the only executable artifact is the built-in, pinned `sha256_chain_v1` handler.

See [`constitution.example.yaml`](constitution.example.yaml) for the **future-oriented** constitution sketch, and [`polyc/demo.py`](polyc/demo.py) for the schema actually enforced in the CPU pilot. The older example includes unsupported GPU and energy limits and must **not** be submitted verbatim to the running CPU pilot. The pilot rejects `energy.require_meter: true` and nonzero `gpu_utilization_percent_max` rather than pretending they are enforced. CPU temperature constraints are fail-closed when requested and a suitable host sensor is missing; the portable demo sets this threshold to `null` and therefore **does not claim thermal protection**.

## Architecture

```text
                         +-----------------------+
                         | PolyC Coordinator     |
                         | SQLite lease queue    |
                         | signed project intake |
                         | compatibility checks  |
                         +------------+----------+
                                      |
             +------------------------+-----------------------+
             |            |           |           |           |
          [cat-1]      [cat-2]     [cat-3]     [cat-4]     [cat-5]
           PoliC        PoliC       PoliC       PoliC       PoliC
           PolyC        PolyC       PolyC       PolyC       PolyC
         HIRD/process  HIRD/process  ...       ...         ...
```

Each node retains its own constitution, owner pause flag, and trusted project signers. The coordinator stores node token **hashes**, active task leases, result digests, a hash-linked provisional contribution ledger, and an event log in SQLite. Ed25519 signs project declarations. An authenticated worker reports a result; the coordinator independently recomputes the deterministic answer before recording completion. This establishes the correctness of this *toy task*, **not** general-purpose verifiable computation. Tokens are not transferable trust certifications, and coordinator logs are not cryptographically immutable.

- **PoliC negotiator:** `polyc/policy.py` and `polyc/crypto.py`.
- **PolyC coordinator and exchange:** `polyc/api.py`, `polyc/store.py`.
- **PolyC Daemon:** `polyc/worker.py` monitors consent, project cancellation, host activity, and owner pause.
- **HIRD/process:** `polyc/hird.py`, `polyc/task_child.py` limit runtime, address space, and CPU priority for a bundled task only.
- **Chronicle:** `polyc/chronicle.py`, `polyc chronicle`, authenticated `/api/chronicle/{node_id}`.
- **Monitor:** authenticated `/metrics` endpoint for Prometheus; Grafana and Nagios remain integrations to build.
- **Catnap:** proposed screensaver; no graphical UI yet. The cats decline to pretend that hashes are cinema.

More detail: [HIRD architecture](docs/hird-architecture.md), [threat model](docs/threat-model.md), [milestones](docs/ROADMAP.md), [five-node acceptance](docs/pilot-acceptance.md).

## What works, and what does not

| Capability | State |
|---|---|
| Five independently configured agents, one host | **Tested** |
| REST coordinator with durable queue and lease expiry | **Implemented** |
| Ed25519 project signatures and trusted signer allowlist | **Implemented** |
| Mutual declared-constitution matching | **Implemented** |
| Owner local pause, fail-closed on coordinator loss | **Implemented** |
| Best-effort CPU duty and Linux `nice +19` | **Implemented** |
| CPU package threshold if sensor available | **Conditional; fail-closed when requested** |
| Deterministic result verification and Chronicle records | **Implemented** |
| Five separate Linux hosts over encrypted transport | **Instructions; not yet validated** |
| HIRD/Linux QEMU/KVM VM isolation | **Not yet implemented** |
| GNU Hurd HIRD guest research | **Planned** |
| GPU scheduling, thermal VRAM limits, energy metering | **Not yet implemented** |
| OCI/PoliC manifest validation, signatures, staging-only intake | **Implemented; NOT executable** |
| Project contribution receipts and provisional credits | **Implemented for built-in CPU tasks only** |
| Arbitrary OCI execution, distributed ML, monetary payouts, blockchain | **Not yet implemented** |

This is a **research prototype**; do not run it with untrusted workloads or expose the API publicly. Running untrusted code inside an ordinary subprocess would not respect the architecture's security requirements. Physical and network tests on actual contributing households will be a separate milestone.

## The Thurber principle: cats, not cattle

James Thurber's dry domestic absurdity is an influence, just as Monty Python supplied some of Python's cultural vocabulary. The project should honor the humor while writing **original** captions and illustrations. Do not reproduce a specific Thurber picture, caption, or *New Yorker* page without confirming the particular artwork's rights status; material collected in *The Thurber Carnival* may have different original publication dates. See [art and rights](docs/art-and-rights.md).

> A HIRD is not a herd. The distinction is most apparent at feeding time.

> The guest was given a room, not the keys to the house.

The first line is a joke. The second is a security goal. For the current process pilot, the guest has not yet been given a reliably locked room. That is precisely why we don't invite strangers' code inside.

The cats are free to disagree. The logs are expected to be accurate.
