# Operator runbook: restart, configuration, backups and deployment

**Audience:** a trusted local pilot operator. This is **not** a turnkey public
production deployment guide. Identity I1 and guest Catnap have not received a
complete public-service security audit. No Google account or PoliC identity
confers operator privileges.

## Local WSL/Linux coordinator (Python)

From your checkout in the Linux filesystem, not `/mnt/c`:

```bash
cd ~/projects/PoliCatHome
. .venv/bin/activate
python -m pip install -e '.[test]'

# Load an existing administrator token from your private secret manager.
# For a disposable, new local instance ONLY, you may generate one:
export POLYC_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"

polyc serve --db runtime/browser.sqlite --host 127.0.0.1 --port 8765
```

Stop the foreground service with **Ctrl+C**. Restart with the same command and
database path. Keep a stable, secret operator token across restarts where
required by the deployment. The shell variable does not persist in new
terminals unless explicitly loaded; never commit it, paste it into browser
screenshots, or store it inside Git.

Inspect without changing any consent:

```bash
curl -fsS http://127.0.0.1:8765/health
curl -fsS http://127.0.0.1:8765/api/identity/config
curl -fsS http://127.0.0.1:8765/web/featured-cats.json >/dev/null
curl -fsS http://127.0.0.1:8765/web/branching-story.mjs >/dev/null
```

Use Ctrl+Shift+R after changing static assets. Test in a new browser profile
when a remembered workspace preference or existing enrollment hides Bloom.

### Local Docker Commons: a **different** persistent database

```bash
bash scripts/start-local.sh
bash scripts/commons-local.sh status
bash scripts/commons-local.sh logs
bash scripts/stop-local.sh       # preserves the Commons' named Docker volume
bash scripts/start-local.sh      # restart the same local Commons
```

The launcher stores the administrator secret at `runtime/admin-token.txt` and
the Commons SQLite database in a Docker volume. The Docker Compose service
binds to `127.0.0.1:8765` and enables anonymous self-enrollment **for local
testing**. Do **not** use `remove-local.sh --purge-data` as a restart command;
it irreversibly removes the local Commons volume after explicit confirmation.

## Identity I1 configuration

Independent pseudonymous browser keys work without Google configuration and
require HTTPS or loopback localhost for Web Crypto. Google sign-in is optional;
if enabled, configure all three privately:

```bash
POLYC_GOOGLE_CLIENT_ID=<Google OAuth web client ID>
POLYC_GOOGLE_CLIENT_SECRET=<Google OAuth client secret>
POLYC_GOOGLE_REDIRECT_URI=https://YOUR-HTTPS-ORIGIN/api/identity/google/callback
```

These are **configuration variable names**, not a shell snippet to paste with
placeholder values. Supply them through your real service's secret store;
never commit an `.env` file or print secrets in logs. Register the exact HTTPS
callback with Google. Google login should be hidden when these settings are
absent. A first-party session probe does not contact Google until the user
chooses that method. See [Identity sovereignty](IDENTITY-SOVEREIGNTY.md).

## Private database backup before updating

Identity I1 creates identity tables inside the same coordinator SQLite
database as the existing pilot. Preserve that database before updating code,
changing schema, or experimenting with account linking. Do **not** simply copy
a live SQLite file while it may be writing. For a local Python coordinator:

1. Stop the foreground process, and confirm no other server writes that file.
2. Copy `runtime/browser.sqlite` to an access-restricted backup outside the
   repository and web root; also protect any associated WAL files if you cannot
   first checkpoint/stop the writer.
3. Preserve the operator secret separately in your secret manager, not inside a
   publicly accessible backup or Git.
4. Restart against the original DB, not a newly created empty file. Verify
   `/health`, read-only identity config and that existing Catnap registrations
   are still present.

For Docker, stop the service before performing a backup of its **named volume**
using your container/volume backup procedure. The Python file and Docker volume
are different stores. Test restoring backups on a disposable instance before
relying on them. Identity account records and Catnap receipts may survive
logout, revocation, and browser deletion; those actions are not server-side
record erasure.

## Public HTTPS / Linode is a separate deployment

The public site at `policathome.dafehughes.com` will not change merely because
a patch was applied to local WSL files. Identify the actual public deployment
checkout, container image, service manager and database **before** updating it.
There is deliberately no guessed `systemctl` service or Docker command here:
use the one your public host actually runs. Verify the TLS reverse proxy and
trusted forwarding so the app observes the correct HTTPS origin. An incorrect
scheme or host can break `__Host-` secure cookies, same-origin protections,
and Google OAuth redirect validation.

Before enabling public accounts or self-enrollment: do a security review,
implement public-grade abuse controls and request limits, protect backups and
session data, define retention/deletion, verify CSRF/origin handling through the
actual reverse proxy, and test OAuth with Google's real endpoints. The current
unit tests mock Google's token exchange; they are not production OAuth proof.
Do not expose a development coordinator directly on an unprotected port.

## Rollback rules

Code rollback and data rollback are **different operations**. Reverting files
may preserve a DB that includes newer identity tables; deleting or restoring an
older DB snapshot can discard identity accounts, sessions and contributor
records. Stop writes, preserve a backup, and verify compatibility before
rolling back a public release. The user-facing Bloom and Featured Cats changes
must never start worker computation as a side effect of navigating or signing
in. Use the [release checklist](RELEASE-CHECKLIST.md) for acceptance.
