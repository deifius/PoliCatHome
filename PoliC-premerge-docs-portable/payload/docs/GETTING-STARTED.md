# Getting started with PoliC@home

**Choose the path that matches what you want to do.** Visiting the homepage,
exploring Featured Cats, signing in, or viewing a Gibson scene does **not**
contribute compute. PoliC@home is a constrained SHA-256 research pilot, not yet
a general GPU/OCI or paid-compute exchange.

| Goal | First step | What it does *not* do |
| --- | --- | --- |
| Explore the idea | Open `/` and follow Bloom; `Meet the Cats` displays the editorial registry | Approve projects, download workloads or start Catnap |
| Contribute in a browser | Select **Offer my computer** → **Set my PoliC** | Install Docker or start work before explicit enrollment **and** Start |
| Return to the full workspace | Use **Always open workspace here**, or optionally sign in with a PoliC identity | Grant any Catnap, creator, or operator privilege |
| Propose a project | Select **Propose a project**; the invited workshop signs/stages a pilot Cat | Execute arbitrary submitted containers |
| Run a native worker | Follow [native Catbox instructions](CONSENT-AND-LIFECYCLE.md#2-your-own-native-docker-catbox--works-with-the-commons) | Start without local owner action |
| Host a Commons | Follow [local startup](LOCAL-OPERATOR-RUNBOOK.md) | Offer the server's compute automatically |

## Fastest local test (WSL Ubuntu or Linux)

From a **trusted source checkout**:

```bash
cd ~/projects/PoliCatHome
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'

# Keep this value private; reuse a securely stored token when restarting
# an existing deployment rather than rotating it unexpectedly.
export POLYC_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"
polyc serve --db runtime/browser.sqlite --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/` in a local browser. Press **Ctrl+C** in the
terminal to stop the coordinator. The SQLite database remains on disk. This
example is **local development**, not a production deployment. It does not
enable guest enrollment automatically; that setting depends on
`POLYC_SELF_ENROLL` and the Commons' policy.

For a Docker-managed localhost Commons instead, run `bash scripts/start-local.sh`
from the checkout and use `bash scripts/stop-local.sh` to stop without purging
its **separate Docker volume**. Do not point these two modes at each other's
database paths or assume their data is shared.

## Identity is optional

Bloom offers **Have an identity? Sign in**. An independently generated browser
Ed25519 key or optionally configured Google sign-in can identify a returning
user and bypass the welcome screen. **A PoliC identity is not a Catnap token**.
It does not trust a Cat creator, enroll a device, start a worker, approve a
proposal or grant Commons administration rights.

For the first milestone, browser keys are not portable or recoverable from an
exported account record. Before clearing browser storage, understand the
recovery limits in [Identity sovereignty](IDENTITY-SOVEREIGNTY.md). Never clear
a Catnap worker's local credentials before successfully revoking its
registration; see [Consent and lifecycle](CONSENT-AND-LIFECYCLE.md).

## Next reading

- [Bloom exploration](BRANCHING-HOME.md) and [Featured Cats registry](FEATURED-CATS.md)
- [Consent, enrollment, pause, revoke and removal](CONSENT-AND-LIFECYCLE.md)
- [Identity independence and PURDAH roadmap](IDENTITY-SOVEREIGNTY.md)
- [Operator startup, backup and deployment boundaries](LOCAL-OPERATOR-RUNBOOK.md)
- [Release acceptance checklist](RELEASE-CHECKLIST.md)
- [Documentation index](INDEX.md)
