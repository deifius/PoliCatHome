# Repository layout and safe cleanup

**There is one authoritative Python package, one documentation tree, and one test suite.**
Older PoliC@home ZIPs were sometimes extracted on top of earlier checkouts. Extraction
adds or overwrites files but does **not** remove old files, so the root may show
copies of every Python module, an old `web/`, repeated guides, and an entire
nested `polyc-at-home/` repository. Those copies are not the application entry points.

## Where things belong

```text
PoliCatHome/
├── README.md                     Start here; overview and local quickstart
├── Philosophy.md                 Why the Commons exists
├── LICENSE / LICENSING.md        BSD code and separate content rights
├── AGENTS.md                     Developer and coding-agent instructions
├── Dockerfile                    Shared image for coordinator/worker pilot
├── compose.yaml                  Loopback-only Commons
├── compose.catbox.yaml           Optional, separate local Catbox
├── pyproject.toml                Python package, dependencies, tests
├── constitution.example.yaml    Example owner constitution
├── polyc/                        ONLY authoritative Python implementation
│   └── web/                      ONLY authoritative HTML/JS/WebGL frontend
│       └── downloads/            Credential-free generated source ZIP
├── docs/                         Guides, safety notes, architecture, licenses
├── projects/                     Example Cat submissions, not runtime jobs
├── scripts/                      Launch, stop, revoke, cleanup, build, test
├── tests/                        ONLY authoritative Python test suite
└── runtime/                      Local identity/secrets/data: DO NOT DELETE
```

`runtime/` is created locally, is Git-ignored, and may contain Catbox owner
credentials, administrator tokens or a SQLite database. The Commons Docker
Compose setup also stores its coordinator database in a **Docker volume**;
this cleanup does not touch that volume.

## Remove clutter from a previously layered checkout

From the **existing repository root** (preferably under `~/projects` on WSL):

```bash
python3 scripts/tidy-repository.py             # Preview, no changes
python3 scripts/tidy-repository.py --apply     # Move known legacy copies to backup
```

This is a **move-only** operation, not `rm -rf` or `git clean`.

- It preserves the canonical `polyc/`, `docs/`, `tests/`, `scripts/`, and
  `projects/` directories; root launch files and licenses; `.git/`; and `runtime/`.
- It moves obsolete root-level `.py` modules when their canonical copy exists,
  duplicated `.md` guides, old root-level launch scripts, duplicated sample
  manifests, legacy root `web/`, nested `polyc-at-home/`, duplicated example
  project folders, and top-level generated Python caches/metadata.
- **Differences are not discarded.** Even if an old root copy differs from its
  canonical counterpart, it is moved to a backup for inspection. A
  `MANIFEST.json` records which copies were different or unique.
- Any unrecognized files are left untouched. No changes are made to your
  enrolled Catbox, its local identity, or the live coordinator database.

The backup is created **beside** the repository, e.g.:

```text
~/projects/PoliCatHome-cleanup-backup-20261109-173000/
    MANIFEST.json
    api.py
    CATNAP-BROWSER.md
    web/
    polyc-at-home/
    ...
```

**If these legacy paths were Git-tracked**, their removal from the checkout will
appear as deletions in `git status --short`; the script does not modify Git
history, stage changes, or create a commit. Review that diff before committing.

**Before deleting that backup:** inspect the manifest for `DIFFERENT` and
`unique_legacy_files` entries, then run tests and start the service. To
restore a particular file, copy it from the backup to an appropriate location
in a scratch branch; don't blindly overwrite the canonical implementation.

If a Docker container is running, the cleanup does not stop or rebuild it.
To pick up source changes, use `bash scripts/start-local.sh` as usual. No
`docker compose down --volumes` command is needed.

## Verify the resulting project

```bash
# See the meaningful source tree without generated caches/secrets:
tree -a -L 3 -I '.git|.venv|__pycache__|.pytest_cache|*.egg-info|runtime'

python -m pip install -e '.[test]'
pytest -q
node scripts/test-browser-protocol.mjs
node scripts/test-browser-worker.mjs
python3 scripts/build-source-snapshot.py
bash scripts/start-local.sh
```

If you need to stop and remove **workloads**, that is a different operation:
read [Consent and lifecycle](CONSENT-AND-LIFECYCLE.md). Cleaning up source files
must never be confused with revoking consent or removing a Catbox.

## Adding or editing files

Change `polyc/api.py`, never a root `api.py`. Change `polyc/web/app.js`, never
root `web/app.js`. Tests belong in `tests/`, guides in `docs/`, maintenance tools
in `scripts/`, sample Cat manifests in `projects/`. Keep the existing
root-level Docker files and Python project metadata: external tools expect
them there. After any UI/docs changes that affect the public source snapshot,
run `python3 scripts/build-source-snapshot.py` and commit or publish the refreshed
source ZIP with the release.
