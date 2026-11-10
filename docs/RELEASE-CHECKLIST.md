# Pre-merge / pre-deployment acceptance checklist

This checklist applies to the **Bloom v4 + Featured Cats + Identity I1** branch.
It separates evidence demonstrated by tests from work that requires a real
browser or public deployment. Do not treat passing tests as public security
certification.

## 1. Review what will be merged

```bash
git status --short
git diff --check
git diff --stat
# Review staged changes too:
git diff --cached --check
git diff --cached --stat
```

Check that no `runtime/` database, `admin-token.txt`, `.env`, Google client
secret, Windows `:Zone.Identifier` file, one-off downloaded patch, portable
installer ZIP, or backup enters the commit. If the local source snapshot ZIP is
tracked, rebuild and inspect it deliberately; it is a **published artifact**,
not a safe place for local secrets.

## 2. Reproducible automated checks

From the repository root on Linux/WSL, after activating the project's `.venv`:

```bash
python -m pip install -e '.[test]'
python -m pytest -q
node scripts/test-browser-protocol.mjs
node scripts/test-browser-worker.mjs
node scripts/test-featured-cats.mjs
node scripts/test-branching-home.mjs
node scripts/test-branching-story.mjs
node scripts/test-identity-ui.mjs
python scripts/verify-release-assets.py --source-only
```

Python tests cover identity challenges, replay, origin validation, provider
linking/unlinking, session revocation, and privilege separation. JavaScript
checks verify the Bloom story, editorial registry and expected UI hooks. Those
checks cannot prove that the UI behaves correctly in **every real browser**.

## 3. Verify packaged website and published source

**This is a release gate.** Editable installs can hide packaging mistakes.
The frontend requires `featured-cats.json` **and** `branching-story.mjs`; both
must exist in a built wheel **and** the downloadable source snapshot.

```bash
mkdir -p dist
python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .
python scripts/build-source-snapshot.py
python scripts/verify-release-assets.py --wheel-dir dist
```

The snapshot is `polyc/web/downloads/PoliCatHome-source.zip`. It should contain
the current source, tests and documentation, but **no Git history or secrets**.
Any failed asset or safety check is a merge blocker. If your environment lacks
wheel-building requirements, install them or run this gate in CI; do not report
it as passed by inference.

## 4. Manual UX and constitutional acceptance

- Fresh anonymous browser gets **Bloom**, one question at a time; no scrolling
  at common viewports, without clipping at large text size.
- **Meet the Cats** shows one editorial entry at a time; future concepts are
  clearly unavailable and cannot become executable through the JSON file.
- **Offer my computer** explains heat, CPU, creator trust and policy before
  opening the original controls. No default creator trust or implicit Start.
- **Propose a project** opens the invitation-gated workshop without suggesting
  arbitrary OCI execution.
- Independent identity registration works over HTTPS/localhost; user returns
  to workspace, can log out, and can choose to see Bloom again.
- Existing Catnap enrollment, pause, revoke and receipts remain usable; signing
  in, signing out, or skipping Bloom never enrolls or starts work.
- Test keyboard navigation, mobile, 200% zoom, reduced motion, failed registry
  fetch, absent Google credentials, and browsers without persistent storage.
- If enabling Google, test the **real** OAuth code flow, session cookie origin,
  account linking/unlinking and recovery warning on the actual HTTPS host.

## 5. Safety and release communication

- Tell visitors that browser Catnap executes **only approved, bounded SHA-256
  work**; Docker Catbox is **not** arbitrary untrusted workload isolation.
- Clearly separate editorial feature placement, operator approval, contributor
  PoliC trust, independent start, identity authentication and operator access.
- Document that an identity export does **not** recover its signing key, that
  removing browser site data can strand accounts, and that Catnap credentials
  should be revoked **before** local removal.
- Confirm the SQLite backup, public host deploy method, and rollback owner.
- Do not claim five real households, live GPU jobs, compensated compute,
  federated PURDAH identities, or live Google sign-in tests unless independently
  verified and recorded.

**Release decision:** record test command outputs, reviewed commit hash,
known limitations and deploy owner in the pull request. Approval to merge is
not the same as approval to enable public identity or anonymous enrollment.
