#!/usr/bin/env python3
"""Portable, checked, idempotent installation for PoliC identity I1 over Bloom v4.

New files are never overwritten when locally modified. Existing sources are changed
through narrow anchors, not a fragile hunk/line-number patch. A reversible backup is
retained under .git/identity-backups. No Git commits or remote actions are performed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent / 'payload'
NEW = [
 'polyc/identity.py', 'polyc/web/identity-ui.js', 'polyc/web/identity-ui.css',
 'tests/test_identity.py', 'docs/IDENTITY-SOVEREIGNTY.md', 'scripts/test-identity-ui.mjs',
]
EXISTING = ['polyc/api.py','polyc/web/index.html','polyc/web/branching-home.js',
            'README.md','docs/BRANCHING-HOME.md','docs/INDEX.md']


def replace_once(original: str, before: str, after: str, name: str) -> str:
    if after in original:
        return original
    if original.count(before) != 1:
        raise ValueError(f'{name}: expected exactly one anchor; found {original.count(before)}. File left unchanged.')
    return original.replace(before, after, 1)


def revise(name: str, source: str, new_docs: str) -> str:
    if name == 'polyc/api.py':
        before = '    from .browser import mount_browser\n'
        after = '    from .identity import mount_identity\n    mount_identity(app, store, admin_token)\n' + before
        return replace_once(source,before,after,name)
    if name == 'polyc/web/index.html':
        before = '  <script type="module" src="/web/branching-home.js"></script>'
        after = before + '\n  <link rel="stylesheet" href="/web/identity-ui.css">'
        return replace_once(source,before,after,name)
    if name == 'polyc/web/branching-home.js':
        before = "import { BLOOM_STAGES, storyFor } from './branching-story.mjs';"
        after = before + "\nimport { identityMe, installIdentityUI } from './identity-ui.js';"
        source = replace_once(source,before,after,name)
        source = replace_once(source,'function shouldShowHome() {','function shouldShowHome(identity) {',name)
        before = '  return !hasEnrolledSession() && !preferredWorkspace();'
        after = "  if (hasEnrolledSession()) return false;\n  if (identity?.authenticated) return identity.identity?.default_landing === 'bloom';\n  return !preferredWorkspace();"
        source = replace_once(source,before,after,name)
        before = 'function init() {\n  installPreferenceControls();\n  if (!home || !shouldShowHome()) return;'
        after = 'async function init() {\n  const identity = await identityMe();\n  installPreferenceControls();\n  installIdentityUI();\n  if (!home || !shouldShowHome(identity)) return;'
        return replace_once(source,before,after,name)
    if name == 'README.md':
        if '## Identity without captivity (PURDAH direction)' in source:
            return source
        before = '## Meet the household'
        after = '''## Identity without captivity (PURDAH direction)\n\nPoliC@home now has an **optional first-party pseudonymous identity** for returning visitors: a browser-held Ed25519 proof-of-control key, server-managed session, and account-level Bloom bypass. A separately configured Google OpenID Connect login can be linked or unlinked; Google email is never the account key. **Signing in cannot enroll, authorize or start Catnap and does not grant creator or operator rights.**\n\nThis is an **initial milestone toward**, not an implementation of, the PURDAH identity vision in Stephenson's *Fall; or, Dodge in Hell*. Keys cannot yet be recovered across devices; passkeys, portable author claims and cross-Commons recovery are future milestones. Read [Identity without captivity](docs/IDENTITY-SOVEREIGNTY.md) before enabling public sign-in.\n\n''' + before
        if before not in source:
            return source.rstrip()+'\n\n'+after.split(before)[0]
        return replace_once(source,before,after,name)
    if name == 'docs/BRANCHING-HOME.md':
        if '## I1 — Returning with an independent identity' in source:
            return source
        return source.rstrip()+'''\n\n## I1 — Returning with an independent identity\n\nA small Bloom footer action, **Have an identity? Sign in**, opens the opt-in\nfirst-party identity dialog. A valid identity session with the `workspace` preference\nopens the detailed application without Bloom; a user can switch their account preference\nback to `bloom`. Anonymous and local browser-preference entry points still work.\nNo credential or Google SDK is loaded merely because someone sees Bloom. Identity never\ncauses Catnap enrollment, approval, creator trust, or compute start. See\n[Identity sovereignty](IDENTITY-SOVEREIGNTY.md) for implementation, known limitations\nand recovery milestones.\n'''
    if name == 'docs/INDEX.md':
        if 'Identity sovereignty and PURDAH roadmap' in source:
            return source
        return source.rstrip()+'\n\n- [Identity sovereignty and PURDAH roadmap](IDENTITY-SOVEREIGNTY.md) — pseudonymous identity, privacy, provider independence, trust boundaries and recovery roadmap.\n'
    raise ValueError('Unrecognized file: '+name)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',default='.',help='PoliCatHome root directory; defaults to current directory')
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--check',action='store_true',help='Validate preconditions without writing files')
    group.add_argument('--apply',action='store_true',help='Install with rollback and backups')
    args=ap.parse_args()
    root=Path(args.repo).resolve()
    if not (root/'polyc/api.py').is_file() or not (root/'polyc/web/branching-home.js').is_file():
        ap.error('Not a PoliCatHome checkout with Bloom v4; no files changed')
    targets={}
    try:
        for rel in NEW:
            proposed=(PAYLOAD/rel).read_bytes()
            actual=(root/rel)
            if actual.exists() and actual.read_bytes()!=proposed:
                raise ValueError(f'{rel} already exists with different contents; preserving local work')
            targets[rel]=proposed
        for rel in EXISTING:
            actual=root/rel
            if not actual.is_file(): raise ValueError(f'Missing {rel}')
            new=revise(rel,actual.read_text(encoding='utf-8'),'')
            targets[rel]=new.encode('utf-8')
        changed=[rel for rel, content in targets.items() if not (root/rel).exists() or (root/rel).read_bytes()!=content]
        print('Identity I1 preflight: clean; '+str(len(changed))+' file(s) to create/update')
        for rel in changed: print('  '+rel)
        if args.check or not changed: return
        backup_root=root/'.git'/'identity-backups'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        backup_root.mkdir(parents=True,exist_ok=False)
        applied=[]
        try:
            for rel in changed:
                path=root/rel
                was_present=path.exists()
                if was_present:
                    dest=backup_root/rel
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(path,dest)
                else:
                    dest=backup_root/(rel+'.absent')
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_text('Created by installer; delete on rollback.\n')
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(targets[rel]);applied.append((path,dest,was_present))
            subprocess.run([sys.executable,'-m','py_compile',str(root/'polyc/identity.py')],check=True)
            if shutil.which('node'):
                subprocess.run(['node','--check',str(root/'polyc/web/identity-ui.js')],check=True)
                subprocess.run(['node',str(root/'scripts/test-identity-ui.mjs')],cwd=root,check=True)
        except Exception:
            for path,backup,was_present in reversed(applied):
                if was_present: shutil.copy2(backup,path)
                else: path.unlink(missing_ok=True)
            print('Install failed: restored previous files.',file=sys.stderr)
            raise
        print('Installed identity I1. Backups:',backup_root)
        print('Run: node scripts/test-branching-home.mjs && python -m pytest -q')
        print('Restart the PoliC coordinator to activate the new identity API.')
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print('Installation aborted:',exc,file=sys.stderr)
        sys.exit(1)

if __name__=='__main__': main()
