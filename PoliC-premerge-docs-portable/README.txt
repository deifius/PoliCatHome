PoliC@home PRE-MERGE DOCUMENTATION + RELEASE-ASSET REPAIR

From your existing Bloom v4 + Identity I1 checkout:

    cd ~/projects/PoliCatHome
    python3 PoliC-premerge-docs-portable/install.py --check
    python3 PoliC-premerge-docs-portable/install.py --apply
    source .venv/bin/activate
    python -m pytest -q
    node scripts/test-identity-ui.mjs
    node scripts/test-branching-home.mjs
    node scripts/test-featured-cats.mjs

Then use docs/RELEASE-CHECKLIST.md, which builds the wheel and
checks that the public source ZIP and wheel contain all assets.
The installer does not modify runtime/ or operator/worker privileges.
Any file differences stop the installer; use --allow-drift only after
reviewing your existing edits. Backups are stored under .git/.
