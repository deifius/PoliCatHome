# PoliC@home — Informed consent, installation, execution and removal

> **The three participation paths are independent.** Browser Catnap does not
> install software. A native Catbox is an owner-installed Docker worker. A
> Commons is a Docker-hosted coordinator. Running the Commons does not donate
> compute. The web page cannot start Docker containers on a remote visitor's
> machine; that requires a deliberate local installation by the owner.
>
> No PolyC without PoliC. Culpability with clarity.

Start with **`/web/participate.html`** in the web interface. Every path shows its
limits, commands, stop/revoke procedures, and data-retention consequences.

## Quick choices

| | Browser Catnap | Native Catbox | Own Commons |
|---|---|---|---|
| What runs | Web Worker on visitor CPU | Signed built-in worker inside visitor's Docker | Coordinator in visitor's Docker |
| Installation | None | Docker Engine/Compose and source checkout | Docker Engine/Compose and source checkout |
| CPU allocation | Best-effort 5–75% slider | 0.5 CPU **hard container quota**, 25% best-effort duty-cycle | No volunteer work |
| RAM / processes | Browser managed; no guaranteed cap | 768 MiB container, 64 PIDs, 512 MiB task | Host-defined deployment; not a worker |
| Workload | Approved SHA-256 chain | Approved SHA-256 chain | Distributes approved tasks |
| GPU / arbitrary OCI | **No** | **No** | Does not execute tasks |
| Consent gate | Choose Cats, acknowledge, enroll, separately Start | Choose Cats, review risks, type `I CONSENT`, separately Start | Run local startup script; keep admin token secret |
| Stop | Pause | `catbox-local.sh pause` | `stop-local.sh` |
| Revoke | Revoke Consent | `catbox-local.sh revoke` | Revoke participating nodes first |
| Delete local data | Clear site data **after revocation** | `catbox-local.sh remove` | `remove-local.sh --purge-data` |

## 1. Browser Catnap — two explicit actions

1. Open the Commons site with JavaScript and a secure browser context (HTTPS
   or localhost). Merely opening the site or watching animations **does not
   contribute CPU**.
2. Select only approved Cat creators you trust. A creator key trusts that
   creator's **future approved Cats** subject to your category, ethos and
   commercial filters. An empty trust list is safely idle.
3. Configure CPU pacing, allowed categories, declared purposes, maximum task
   time and session duration. Preview/export your PoliC without enrolling.
4. Read the limitations: electricity, heat, and best-effort (not enforceable)
   CPU pacing. Check the explicit acknowledgement and **Enroll in Catnap**.
5. Only after enrollment, press **Start Catnap**. Pause stops local work. Revoke
   Consent stops local work and asks the coordinator to invalidate your token.
6. To remove settings and creator keys locally, clear browser site data **only
   after successful revocation**. If you clear site data before revoking, you
   may lose the token you need for remote revocation. The server's Chronicle
   and task receipts are not erased by deleting browser data.

Browser mode cannot perform arbitrary Docker tasks, survive tab closure, ensure
any GPU or CPU temperature/power ceiling, or guarantee OS niceness/CPU quotas.

## 2. Your own native Docker Catbox — works with the Commons

**Not a Docker sandbox for arbitrary submitted containers.** The pilot native
Catbox uses PoliC@home's already-auditable built-in SHA-256 worker. It fetches
approved, signed assignments, verifies signers/policy locally, computes tasks,
and posts verified receipts. Nothing runs until its owner runs `start`. Once started, **it keeps running even when the browser closes**, until stopped or paused locally or Docker stops it.

### Requirements

- Docker Engine with Compose v2 on a Linux host, or Ubuntu in WSL2 with a
  working Docker daemon; Python 3 (standard library) is required for setup.
- Source ZIP from `/web/downloads/PoliCatHome-source.zip` or your own Git
  checkout. Extract it into the **native Linux/WSL filesystem**, such as `~/projects`. The Catbox enrollment script refuses Windows-mounted `/mnt/c/...` locations because their permissions may not protect the private contributor token.
- A compatible Commons: `http://127.0.0.1:8765` locally, or an external **HTTPS**
  coordinator with `POLYC_SELF_ENROLL=1`. No Commons admin token is required.
- Read the source before executing local shell commands. Docker access grants
  powerful control over the local host.

### Full lifecycle

```bash
# Run from the extracted PoliCatHome-source root.
docker compose version

# Option A: an existing local Commons at localhost:8765:
bash scripts/catbox-local.sh enroll

# Option B: an external HTTPS Commons (from YOUR OWN local computer):
bash scripts/catbox-local.sh enroll https://your-commons.example

# Enrollment prints the approved Cat catalog, creator signing keys,
# commercial consent, Docker limits, network risks, retention notes.
# Type I CONSENT to register; otherwise absolutely nothing is registered.
# The local secret config is runtime/catbox-owner/owner.yaml (0600).

bash scripts/catbox-local.sh start    # first command which actually starts work
# Catbox uses standalone compose.catbox.yaml; no admin token is needed.
bash scripts/catbox-local.sh status
bash scripts/catbox-local.sh logs     # Ctrl+C detaches from logs, not Catnap
bash scripts/catbox-local.sh pause    # immediate local Docker stop, no new leases
bash scripts/catbox-local.sh resume   # explicit restart
bash scripts/catbox-local.sh revoke   # stop; server confirms revocation
bash scripts/catbox-local.sh remove   # stop, revoke, rm ONLY Catbox + local secret
```

`remove` refuses to erase the local token if the remote coordinator is
unreachable; it leaves the Catbox stopped and asks you to retry. This avoids
claiming authorization was revoked when the coordinator cannot confirm it.
For a permanently lost server, the local compute is already stopped and local
cleanup can be done manually **only with the understanding that remote
revocation could not be confirmed**. Never claim remote records were deleted.

If startup says `POLYC_ADMIN_TOKEN is missing`, you have an older
`catbox-local.sh` that loads the coordinator Compose file. Update the script;
its `compose=(...)` line must use **only** `docker compose -f compose.catbox.yaml`.
Your enrollment remains valid; you do **not** need to consent again.
Alternatively, run this local-only, explicit one-time command from the checkout
hosting your Commons (after `bash scripts/start-local.sh`):

```bash
CATBOX_UID="$(id -u)" CATBOX_GID="$(id -g)" CATBOX_SERVER=http://commons:8765 \
  docker compose -f compose.catbox.yaml up --build --no-deps -d catbox
```

The local Commons and Catbox share the same default Compose project network
because both configuration files live in the same checkout. For a **remote**
HTTPS Commons, use the `catbox-local.sh enroll https://...` path; the script
will configure the remote HTTPS endpoint instead of the local service name.

To change the trusted creators or other registered PoliC fields: pause/revoke,
remove, then enroll again. The current pilot does not offer live constitutional
amendment or recovery of forgotten node credentials.

### Enforced vs. declared controls

- `compose.catbox.yaml` applies a Docker **CPU cgroup quota** of 0.5 of one logical CPU (not 50% of the whole computer),
  768 MiB total memory, 64 process/PID maximum, dropped Linux capabilities,
  `no-new-privileges`, a read-only root filesystem and non-root identity.
- The signed-task worker also applies a 512 MiB task memory ceiling,
  15-second runtime, process isolation and 25% **cooperative** duty cycle.
  The 25% is *not* another hard host CPU percentage.
- There is **no mount of `/var/run/docker.sock`** or personal directories.
  Only the private owner config directory is mounted read-only.
- Container networking is **enabled** so the worker can talk to the chosen
  coordinator. The network is **not** an outbound firewall or a guarantee of
  no Internet access. A container is **not** a VM-grade isolation boundary.
- There is **no** real temperature sensor or thermal kill switch in this
  container, no GPU/power management, no financial settlement or guaranteed
  monetary reward. Do not rely on it for thermal safety or run untrusted code.
- Contributors trust explicit creator Ed25519 signing keys and the server
  independently checks them before leasing. Creator-declared category and
  purpose tags are *not* independently audited.

`compose.catbox.yaml` uses the host UID/GID so a 0600 token file remains readable
only to the owner's container process. It stores the config under
`runtime/catbox-owner` (not part of the public ZIP). Never commit that directory.

## 3. Your own Docker Commons

```bash
# Extract and enter the downloaded ZIP source directory:
unzip PoliCatHome-source.zip
cd PoliCatHome-source
bash scripts/start-local.sh
# Visit http://localhost:8765
# Admin credential is in runtime/admin-token.txt — NEVER publish it.

bash scripts/commons-local.sh status
bash scripts/commons-local.sh logs  # Ctrl+C stops following logs only
bash scripts/stop-local.sh        # stop only, retains volume and admin secret
bash scripts/start-local.sh       # restart with saved data
```

The `compose.yaml` binds **127.0.0.1:8765** rather than a public port and
keeps the SQLite database in a Docker volume. The host coordinator is not a
Catbox; it does not start volunteer workload execution by itself. Locally
running the coordinator and a native Catbox are **separate** opt-ins.

### Destructive removal

```bash
# If you enrolled a native Catbox with this same Commons:
bash scripts/catbox-local.sh remove
# Only after all applicable nodes have been revoked:
bash scripts/remove-local.sh --purge-data
# Type exactly DELETE MY COMMONS when you genuinely intend to erase local data.
```

`stop-local.sh` leaves data intact. `remove-local.sh --purge-data` removes the
**current Compose project's** coordinator container, its Docker database
volume and `runtime/admin-token.txt`; it does **not** remove your source tree
or unrelated Docker resources. The database loss is irreversible absent a
backup. If another owner's remote node uses your Commons, notify them and
allow revocation/transition first. This script does not contact all remote
contributors. Do **not** `docker system prune -a --volumes`: that might delete
unrelated data from your computer.

For public hosting, local Compose defaults are insufficient: use HTTPS,
reverse proxy / ingress controls, abuse rate limits, authenticating identity
where needed, secret rotation, container security hardening, proper backups,
restore tests, and a security review. The prototype must not be deployed as
an unattended public workload execution service.

## Troubleshooting (WSL / Docker)

| Symptom | Check |
|---|---|
| `docker compose` not found | Ubuntu package `docker-compose-v2` (Ubuntu 26.04) or Docker Desktop WSL integration |
| Socket `permission denied` | Check group access, `docker info`; Docker group is root-equivalent |
| `http://localhost:8765` not loading | `bash scripts/commons-local.sh status` and `bash scripts/commons-local.sh logs`; start with `bash scripts/start-local.sh` |
| `self-enrollment is disabled` | Coordinator must enable `POLYC_SELF_ENROLL=1`; never bypass its policy |
| No approved Cats | Enroll idle, ask operator to approve a Cat, then revoke/re-enroll to authorize its creator |
| `POLYC_ADMIN_TOKEN is missing` from Catbox commands | Update the old combined-Compose launcher; the Catbox uses `compose.catbox.yaml` alone. Enrollment is preserved. |
| Native Catbox has no tasks | Verify approved Cats, signer opt-in, categories and time limits; view `catbox-local.sh logs` |
| `catbox-local.sh remove` fails | Remote revocation unconfirmed: local work is stopped, token is retained for retry |
| Want to change your PoliC | Revoke/remove, then enroll with your new selected creators/categories |
| Browser button seems idle | Read its nearby error notice, enable JavaScript, and verify HTTPS/localhost |
| Concerned about temperature | **Stop Catnap**. The browser and this native pilot cannot enforce a thermal ceiling |

## Source and personal data boundaries

Source ZIP is a versioned **snapshot**, not a live `git clone`. To clone with
history, use a real repository URL you personally verify; the app must not
invent one. The public source ZIP excludes `runtime/`, local `.env`, secrets,
Python caches and the ZIP itself. Inspect sources before public distribution.

Revocation ends *new* leases and invalidates the node token. It does not
retroactively erase signed Chronicle events or data already contributed. The
screensaver is a representation; it is not a wattmeter, thermal sensor or proof
of work by itself.
