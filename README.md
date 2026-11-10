# PoliC@home

**Your compute. Your constitution. Your choice.**

> **No PolyC without PoliC. Culpability with clarity.**

PoliC@home is an experimental, open-source network for voluntarily sharing computing power. It is inspired by distributed projects such as SETI@home and by the idea that each participating machine should remain under its owner's control.

**Release state (November 2026):** Bloom v4 (one-question exploration), the versioned Featured Cats editorial registry, and Identity I1 (optional pseudonym/key login and configured Google OIDC) are implemented in the pilot. Browser and native Catnap still execute only approved, bounded SHA-256 tasks. **No login authorizes compute.** For a new visitor start with the [short getting-started guide](docs/GETTING-STARTED.md); for an existing deployment use the [operator runbook](docs/LOCAL-OPERATOR-RUNBOOK.md).

**PoliC** (*Candid Constitutional Consent*) says *what work may run, for whom, and under what limits*. **PolyC** (*Coordinated Computational Care*) matches consenting participants with approved work and records what happened. You can contribute without administering a server.

## Choose your way to participate

| I want to… | What I need | What actually runs |
| --- | --- | --- |
| **Start Catnap in my browser** | A browser and a participating Commons | An opt-in CPU Web Worker; no installation |
| **Run my own Catbox** | Linux/WSL, Docker Compose, and a source checkout | A locally controlled, resource-limited Docker worker |
| **Host a Commons** | Linux/WSL and Docker Compose | A coordinator and website; **not** a volunteer worker |

**Catnap** means contributing compute. A **Cat** is a submitted project. **Create a Cat** submits a project; it does *not* create a worker. A **Catbox** is the isolated environment used to execute a Cat's work. In today's browser pilot, that environment is a Web Worker rather than a Docker container.

## Universal running rules

1. **Nothing starts just because you visit.** Reading the site, previewing a PoliC, or watching Gibson contributes no compute.
2. **Consent precedes execution.** Review what can run, select trusted Cat creators, accept the resource disclosure, **enroll**, and separately **start** Catnap.
3. **No implicit trust.** An empty creator allowlist is valid and receives *no work*. Trusting a creator also permits their *future operator-approved Cats*, subject to your other PoliC restrictions.
4. **Your PoliC limits participation.** The Commons checks eligible Cats, and the local worker checks task signatures and policy again. Declared project purposes are not independently audited.
5. **Stop is not revoke; revoke is not erase.** Pausing stops local execution. Revocation invalidates future authorization. Neither erases already recorded work or the Commons Chronicle.
6. **Use the safeguards that actually exist.** Browser CPU pacing is best-effort. Docker quotas constrain a Catbox, but neither mode currently guarantees safe temperatures, power consumption, or VM-grade isolation.
7. **Protect local credentials.** Keep `runtime/` private. Don't publish node tokens or Commons administrator credentials. Installing or running Docker requires informed trust in the code and your own host environment.

## Define your PoliC before joining

Your PoliC is your own set of conditions: **which Cat creators you trust**, **which categories and declared purposes are allowed**, **whether commercial work is acceptable**, and **how much time and CPU you want to offer**. Browser contributors configure these in the on-page editor; native Catbox contributors use the interactive enrollment wizard. Both present the disclosure **before** asking for consent.

The starter [`constitution.example.yaml`](constitution.example.yaml) illustrates the broader vision, **not** a copy-and-paste production policy: some GPU, energy, and thermal settings in that example are not supported by today's pilot. Use the live browser editor or Catbox wizard to register the policy this version can actually enforce. To change a registered PoliC, revoke and enroll again.

## 1. Start Catnap in your browser — no installation

Open a participating PoliC@home Commons, select **Catnap**, and follow this sequence:

1. **Choose Cats.** Review the catalog of operator-approved Cats and deliberately select the creators you trust. Choosing none is allowed; you will remain idle.
2. **Make your PoliC.** Select eligible categories, excluded purposes, commercial-use consent, best-effort CPU pacing, task timeout, and session duration. Use **View My PoliC**, **Download PoliC YAML**, or **Download JSON** before joining, and again after enrollment to retrieve the exact registered policy. A separate **Inspect my browser** action locally reports browser-visible capabilities; a tiny GPU proof is optional and never Catnap work.
3. **Understand the limits.** This browser runs only the built-in, bounded **SHA-256 CPU pilot**. It may use electricity and create heat. It cannot run arbitrary Docker images, use native GPUs, continue after the tab closes, or enforce a hardware temperature limit.
4. **Enroll in Catnap.** Acknowledge the resource disclosure and enroll. Enrollment alone does **not** start work. Where self-enrollment is enabled, no invitation or operator account is needed.
5. **Start Catnap.** Press **Start Catnap** to contribute CPU on this device. Inspect task receipts and the Chronicle, **Pause** to stop, and **Revoke Consent** to end authorization.

After confirmed revocation, you may clear this site's browser data to remove local settings and tokens. **Revoke first:** clearing data prematurely can lose the credential needed to revoke at the Commons. Closing the tab stops local browser computation but does *not* revoke registration.

A local Commons started using the instructions below is available at **http://localhost:8765/**; its full guided onboarding page is **http://localhost:8765/web/participate.html**.

## 2. Run your first native Catbox — Docker on your machine

A Catbox is optional for browser Catnap. Choose this mode when you want a separately controlled worker that can keep running after you close the website.

**Before you begin:** You need Docker Engine with `docker compose` v2, Python 3, and the PoliC@home source. On Windows 11, run the commands from **Ubuntu in WSL2** with a working Docker daemon. Store the checkout on the Linux filesystem (for example `~/projects/PoliCatHome`), **not** under `/mnt/c/`, because Catbox enrollment writes a private token.

Get the **source ZIP** from a Commons' **Get the source** page (`/web/downloads/PoliCatHome-source.zip`), then extract it into your Linux/WSL projects directory. This is a source snapshot, not a Git clone with history. From the extracted repository root:

```bash
docker compose version
python3 --version

# Enroll with an existing Commons running on this computer:
bash scripts/catbox-local.sh enroll

# OR enroll with a separately hosted Commons using HTTPS:
# bash scripts/catbox-local.sh enroll https://your-commons.example
```

The enrollment wizard shows the approved Cat catalog, trusted signing keys, commercial-use choice, execution limits, network disclosure, and retention notes. **Choose your Cats and type `I CONSENT`** to register. Any other response cancels. Your new Catbox is **still idle** after enrollment.

```bash
bash scripts/catbox-local.sh start     # explicit first start
bash scripts/catbox-local.sh status    # confirm container state
bash scripts/catbox-local.sh logs      # inspect activity (Ctrl+C exits log view)
```

**The current Catbox only executes approved, signed, built-in SHA-256 tasks.** Docker enforces a maximum of **0.5 of one logical CPU**, **768 MiB** container memory, and **64 PIDs**; the task worker also has runtime and memory limits. There is no Docker socket mount, GPU execution, arbitrary uploaded image execution, thermal kill switch, or guaranteed electricity limit. Outbound container networking is enabled. A container is not a full security boundary for untrusted workloads.

**If you selected no trusted creator, a successfully started Catbox will remain idle.** If your Commons has no approved Cats yet, you can enroll idle, or follow the [local acceptance test](docs/LOCAL-TEST.md) to learn how a test Cat is approved. To change your registered PoliC, revoke and re-enroll; live amendment is not implemented yet.

### Stop, resume, revoke, remove

```bash
bash scripts/catbox-local.sh pause     # stops local container; consent retained
bash scripts/catbox-local.sh resume    # deliberately start again
bash scripts/catbox-local.sh revoke    # stop and revoke at the Commons
bash scripts/catbox-local.sh remove    # revoke, remove Catbox and local credentials
```

`remove` stops the worker and **requires confirmation of remote revocation** before deleting the local token. If the Commons is unreachable, the Catbox stays stopped and retains the credential so you can retry. It does **not** delete the Commons database, receipts, or your source checkout. Catbox operations need **no Commons administrator token**.

## 3. Run your own Commons — optional

If you don't have a Commons to join, you can host one locally. This starts the coordinator and its browser UI, **not** a Catbox or a compute contribution. Use the source ZIP above or a checkout you trust. From its root:

```bash
bash scripts/start-local.sh
# Open http://localhost:8765/ in your browser

bash scripts/commons-local.sh status
bash scripts/commons-local.sh logs
bash scripts/stop-local.sh             # stop; preserve database and credentials
bash scripts/start-local.sh            # restart later
```

The local-only setup binds port **8765 to 127.0.0.1** and enables guest self-enrollment for testing. The operator credential is generated at `runtime/admin-token.txt`; ordinary Catnap contributors never need it. Hosting a Commons does not grant it access to visiting machines' Docker daemons.

To **permanently remove** your local Commons and its database volume, first revoke/remove any Catboxes that use it, then run:

```bash
bash scripts/remove-local.sh --purge-data
# Requires the explicit confirmation: DELETE MY COMMONS
```

This erases **your local Commons database and administrator credential**, not the source tree or records held elsewhere. **Do not expose the sample Compose service directly to the public Internet.** Public hosting requires HTTPS, ingress and abuse controls, secret management, backups, and security review.

## What works today (and what doesn't)

The current pilot has a coordinator, an approved signed **SHA-256** task protocol, independently configured workers, consent checks, task receipts/Chronicle, browser Catnap, a local Docker Catbox, and a WebGL visualization (default **Gibson** scene). A five-worker demonstration runs on one Linux host; **five independent households have not yet been validated**. Create a Cat stages signed proposals for operator approval; its submission path is not unrestricted container execution.

**Not yet available:** arbitrary Cat/OCI execution, native GPU or WebGPU **Catnap workloads** (the separate local WebGPU diagnostic is not donated compute), guaranteed host thermal/power enforcement, unattended public Internet deployment, automatic verification of creators' stated project purposes, and real-money payments. A separate **noncash test-credit** prototype exists; its credits are not money or guaranteed compute. See the [roadmap](docs/ROADMAP.md) for planned work.

## Further reading and development

- **[Browser resources and PoliC YAML](docs/RESOURCE-CONSENT.md)** — what the browser can inspect and precisely control, and how to export a draft or enrolled policy.
- **[Informed consent and full lifecycle](docs/CONSENT-AND-LIFECYCLE.md)** — complete permissions, security limits, pause/revoke/removal, troubleshooting.
- **[Local acceptance walkthrough](docs/LOCAL-TEST.md)** — how to approve a test Cat and verify that a consenting visitor actually receives work.
- **[Documentation index](docs/INDEX.md)** — browser protocol, project submissions, threat model, economics, architecture, scenes, and developer references.
- **[Philosophy](Philosophy.md)** and **[licensing](LICENSING.md)** — developer freedom and contributor sovereignty are separate: freedom to build does not confer authority over another's machine.

To run the project's automated checks (developer workflow, not required for Catnap):

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
node scripts/test-browser-protocol.mjs
node scripts/test-browser-worker.mjs
node scripts/test-featured-cats.mjs
node scripts/test-branching-home.mjs
node scripts/test-branching-story.mjs
node scripts/test-identity-ui.mjs
```

Before merging or publishing a source snapshot, follow the [release checklist](docs/RELEASE-CHECKLIST.md). It checks wheel inclusion of the `.json` and `.mjs` Bloom assets as well as the downloadable source ZIP, secrets, tests, and rollback.

**Software and protocols:** [BSD 3-Clause](LICENSE), including the freedom to keep your improvements private. **Original documentation:** [CC BY 4.0](docs/LICENSE-CC-BY-4.0.md). Independent illustrations, submitted Cats, and their outputs have separately specified rights; see [LICENSING.md](LICENSING.md).

## Identity without captivity (PURDAH direction)

PoliC@home now has an **optional first-party pseudonymous identity** for returning visitors: a browser-held Ed25519 proof-of-control key, server-managed session, and account-level Bloom bypass. A separately configured Google OpenID Connect login can be linked or unlinked; Google email is never the account key. **Signing in cannot enroll, authorize or start Catnap and does not grant creator or operator rights.**

This is an **initial milestone toward**, not an implementation of, the PURDAH identity vision in Stephenson's *Fall; or, Dodge in Hell*. Keys cannot yet be recovered across devices; passkeys, portable author claims and cross-Commons recovery are future milestones. Read [Identity without captivity](docs/IDENTITY-SOVEREIGNTY.md) before enabling public sign-in.
