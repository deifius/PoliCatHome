# PoliC@home: local browser acceptance test (WSL2 + Docker)

This quickstart launches only the *coordinator*. The browser contributes its own CPU through a Web Worker only after explicit enrollment and Start Catnap. The Docker host does not donate resources automatically.

## Start

Use a Windows 11 WSL Ubuntu shell with Docker Desktop running and WSL integration enabled. From the extracted repository root:

```bash
bash scripts/start-local.sh
```

The startup script generates a fresh operator credential at `runtime/admin-token.txt` (unless a previous one exists), builds the container, starts the service on **host loopback only**, and preserves the coordinator's SQLite database in a named Docker volume. From Windows, open **http://localhost:8765/**. To read the private operator credential from WSL:

```bash
cat runtime/admin-token.txt
```

The server binds to `0.0.0.0` *inside the Docker network*, because a bridged container needs that address; the Compose port is published **only on 127.0.0.1 of the host**. The CLI's `--insecure-http-on-lan` override is necessary for this containerized development-only configuration. **Do not republish port 8765 publicly**. Use a TLS proxy/VPN and security review first.

## Walkthrough — no operator invitation needed for a guest Catnap

The local Compose file explicitly enables `POLYC_SELF_ENROLL=1` for **loopback-only testing**. It does not authorize general public hosting. A visitor should not need to see the Commons operator screen or enter an administrator token.

1. **Prepare a safe approved Cat (operator, once):** Use **Commons** and `runtime/admin-token.txt` to connect as operator. Generate a **Create a Cat** invitation, then use **Create a Cat** to sign and submit a public-source SHA-256 pilot project. Choose ≤10,000 iterations/task (the browser safety bound). In Commons, inspect and **Approve Built-In Cat**. This role is distinct from being a contributor. No arbitrary code is run. Source/commit declarations are not independently audited by this prototype.
2. **Try as a guest (no operator account):** Open a new private browser profile at `http://localhost:8765/` → **Catnap**. The page should say **Self-enrollment is enabled: no invitation or operator account is needed.** The approved Cat appears in **Choose Cats you trust to work for**. Its creator is unchecked by default. Select it deliberately. A creator trust choice covers **future operator-approved Cats from the same signer**, subject to the rest of the owner's PoliC. It is not blanket trust in uploaded code.
3. **Choose your constitutional consent:** Review categories, commercial-use preferences, excluded purposes, CPU pacing and session limits. **Preview My PoliC** and **Export PoliC JSON** never consume resources. Read and check the heat/electricity/limitations acknowledgement. Click **Enroll in Catnap**. No CPU work starts yet.
4. **Start, pause and revoke:** Click **Start Catnap**. Leave the page visible while it processes an approved matching Cat. Watch verified tasks and the Chronicle; click **Pause** and then **Revoke Consent**. You may enroll again with a newly generated visitor identity and new consent without a new invitation.
5. **Test zero trust:** Enroll a second visitor with no creators selected. Enrollment is allowed and recorded, but no lease is issued. That visitor is idle until they revoke and re-enroll selecting a trusted creator. Approval by the operator never bypasses individual selection.

Run additional browser instances/devices with distinct browser profiles. This pilot rate-limits invitation-free enrollments to **five successful enrollments per connected peer per hour**, persisted in SQLite, and limits the total number of active enrolled nodes to 250. Behind a reverse proxy, several visitors may share a single peer address. These limits are *not* adequate public Internet anti-abuse protection; they exist to prevent accidental local test flooding.

## Inspection and shutdown

```bash
bash scripts/commons-local.sh status
bash scripts/commons-local.sh logs
bash scripts/stop-local.sh
```

To restart, `bash scripts/start-local.sh`. `bash scripts/stop-local.sh` retains the SQLite volume; to erase all local test data, use `bash scripts/remove-local.sh --purge-data` (interactive, and only after revoking/removing native Catboxes). Keep `runtime/admin-token.txt` private; never commit the token or SQLite database.

## Testing without Docker

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest -q
export POLYC_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(36))')"
polyc serve --db runtime/browser.sqlite --host 127.0.0.1 --port 8765
```

Visit `http://localhost:8765/`. The admin token will be the value just exported in that shell. Node.js 22+ can additionally run `node scripts/test-browser-worker.mjs` and `node scripts/test-browser-protocol.mjs`.

## Known limits

Browser Catnap only runs bounded SHA-256 workloads, not submitted Docker images or GPUs. CPU pacing and session time are cooperative browser controls, not hardware temperature or OS-level quotas. The Git commit/source declaration is not cryptographically checked against the remote repository by the pilot. Real money settlement and unattended persistent browser contribution are not implemented.

## Troubleshooting the PoliC editor buttons

The preview and export buttons work without an invitation or a trusted creator key. A zero-trust PoliC is safe to enroll: it receives no work. The enrollment acknowledgement is mandatory in the self-service flow, and enrollment **does not** start CPU execution. If `POLYC_SELF_ENROLL=0`, the UI will show an invitation field; the administrator can still issue legacy one-use contributor invitations. Error messages appear adjacent to the relevant buttons.

After replacing the repository, run `bash scripts/start-local.sh` to rebuild the Docker image. Reload `http://localhost:8765/` with Ctrl+Shift+R. Browser JS/CSS assets use `Cache-Control: no-store` during local testing to avoid stale code.

## Native Catbox integration acceptance (consent-first)

With the coordinator running and self-enrollment enabled, go to
`/web/participate.html#catbox`, read disclosures, then run
`bash scripts/catbox-local.sh enroll` from a WSL terminal. Enroll with zero
trusted Cats to confirm idle-by-default, or first approve a signed built-in
Cat and select its creator key to receive work. No admin credential is needed.
Check that enrollment never starts the container; `start` does. Verify logs,
`pause`, `resume`, `revoke` and `remove`, then confirm the local token file is
gone and the coordinator rejects leases for the revoked node. Finally test
`stop-local.sh` retains DB and `remove-local.sh --purge-data` requires its
destructive typed confirmation. Native Docker runtime acceptance must be
performed on a host with working Docker Engine; Python unit tests do not
prove the Compose service ran.
