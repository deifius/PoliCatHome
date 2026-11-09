# Catbox starts without the Commons administrator credential

This note applies to the `POLYC_ADMIN_TOKEN is missing` error raised by
`bash scripts/catbox-local.sh start`, `status`, `logs`, `pause`, `revoke`, or `remove`
from early consent-first test builds.

## What happened

The native Catbox script asked Docker Compose to read both `compose.yaml`
(the coordinator) and `compose.catbox.yaml` (the volunteer worker). Compose
interpolates **all** services at configuration-parse time, even when told to
start only `catbox`. The coordinator rightly requires an admin token, but a
volunteer worker should never need or obtain one.

**This is a launcher error, not an enrollment error.** If enrollment printed
`Enrolled (CPU still idle)`, your identity and consent were registered. Do not
enroll again just to fix this message.

## Apply the patch in your existing checkout

From the **root** of the installation you have been using (inside WSL's native
Linux filesystem):

```bash
unzip -o /mnt/c/Users/sunji/Downloads/PoliCatHome-Catbox-compose-fix.zip -d .
# If your downloaded patch has a different name, substitute it above.
bash scripts/catbox-local.sh start
bash scripts/catbox-local.sh status
bash scripts/catbox-local.sh logs
```

`Ctrl+C` exits the log viewer **without** stopping the worker.

No administrative credential, Compose config reset, or re-enrollment is
necessary. Start requires a local `runtime/catbox-owner/owner.yaml`, created
by your previous successful enrollment.

The local Commons must already be running, started from the same source
checkout with `bash scripts/start-local.sh`. Both Compose configurations use
the same default project network, allowing Catbox to contact local Commons at
`http://commons:8765`. For a **remote** Commons, enroll with its HTTPS URL.

### If the Catbox starts but has no work

A previous enrollment message stating `No Cat creators trusted` is a valid
**zero-trust**, idle PoliC: the worker cannot lease jobs without a trusted,
operator-approved Cat creator. Starting the container still consumes some
idle system resources; you may pause or remove it.

To authorize a creator once the Commons has an approved Cat:

```bash
bash scripts/catbox-local.sh remove    # stops, confirms revoke, deletes local secret
bash scripts/catbox-local.sh enroll    # explicitly SELECT an approved Cat number
bash scripts/catbox-local.sh start     # compute is still an independent action
```

`remove` deliberately retains the credential for retry if remote revocation
cannot be confirmed. It does **not** remove the Commons or its audit history.

### Operator diagnostic commands

For the operator who runs the coordinator (not needed by Catbox volunteers):

```bash
bash scripts/commons-local.sh status
bash scripts/commons-local.sh logs
```

The Commons helper reads the existing private operator token without asking
users to copy it to their terminal environment manually. Never share this
file with volunteer Catbox contributors.

### Safety and removal

```bash
bash scripts/catbox-local.sh pause   # stop own worker, keep enrollment
bash scripts/catbox-local.sh revoke  # stop and revoke at coordinator
bash scripts/catbox-local.sh remove  # revoke and delete own container/credentials
```

Only the packaged SHA-256 pilot workload executes. The Catbox has a
0.5-logical-CPU Docker quota, a 768 MiB memory limit, and no hardware thermal
ceiling. It does not accept arbitrary OCI images or use GPUs. There is no
promise that a successfully started container actually has approved work.

## Verification

A regression test invokes `start`, `status`, `logs`, and `pause` in an isolated
checkout with a mocked Docker command and **without** `POLYC_ADMIN_TOKEN`, and
asserts the Catbox-only Compose file is used. Backend and JavaScript tests
also run in CI-style checks. An actual Docker run still needs verification on
your local Docker host.
