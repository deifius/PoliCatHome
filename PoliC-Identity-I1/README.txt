PoliC@home — Sovereign Identity I1 — portable installer
======================================================

Designed to install on TOP of the Bloom v4 portable setup.
No older Featured Cats or Bloom patches are required again.

From ~/projects/PoliCatHome:

  unzip -q PoliC-Identity-I1.zip
  python3 PoliC-Identity-I1/install.py --check
  python3 PoliC-Identity-I1/install.py --apply

Activate your existing Python virtual environment for the Python tests:

  source .venv/bin/activate
  node scripts/test-identity-ui.mjs
  node scripts/test-branching-home.mjs
  node scripts/test-featured-cats.mjs
  python -m pytest -q

RESTART the 'polyc serve' coordinator. This version adds API routes at startup.
Open http://127.0.0.1:8765/ and choose 'Have an identity? Sign in'.

Optional Google OpenID Connect requires your own Google OAuth client and
three environment variables. No Google account is needed for a pseudonym.
See docs/IDENTITY-SOVEREIGNTY.md for constitutional goals, security
boundaries, what I1 does and DOES NOT implement, and the full roadmap.

The installer is idempotent, checks file anchors, declines to overwrite
conflicting new files, makes backups in .git/identity-backups, and rolls
back changes on a failed self-check. It does not commit, deploy, or
change Catnap permissions.
