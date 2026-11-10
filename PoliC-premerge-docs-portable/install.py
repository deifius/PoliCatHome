#!/usr/bin/env python3
"""Portable pre-merge documentation and release-assets installer.

Checks hashes before overwriting files, stores rollback copies under .git/, and
regenerates only the public source snapshot. Does not touch runtime/ or run compute.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

PACK = Path(__file__).resolve().parent
CONFIG = json.loads((PACK / 'manifest.json').read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_mutually_exclusive_group(required=True)
    cmd.add_argument('--check', action='store_true')
    cmd.add_argument('--apply', action='store_true')
    parser.add_argument('--allow-drift', action='store_true',
                        help='Back up and replace locally changed files; inspect diffs first')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    if not (root / '.git').is_dir():
        print('Run from the PoliCatHome Git checkout root (not a source-only ZIP).',file=sys.stderr)
        return 2
    for name in CONFIG['required']:
        if not (root / name).is_file():
            print(f'Required I1/Bloom feature missing: {name}',file=sys.stderr)
            return 2
    statuses=[]
    for name, expected in CONFIG['files'].items():
        destination=root/name
        desired=digest(PACK/'payload'/name)
        actual=digest(destination)
        if actual == desired:
            state='current'
        elif actual == expected:
            state='baseline'
        else:
            state='drift'
        statuses.append((name,state))
        print(f'{state:>8}  {name}')
    drift=[n for n,s in statuses if s=='drift']
    if drift and not args.allow_drift:
        print('\nSTOP: Some files differ from the reference version. No changes made.\n'
              'Inspect your local modifications before replacing them. --allow-drift '
              'is available for deliberate overwrite with a backup.',file=sys.stderr)
        return 1
    if args.check:
        print('\nCompatible: ready to apply.' if not drift else '\nDrift detected: review before applying.')
        return 0
    if all(s=='current' for _,s in statuses):
        print('Already current. No changes made.')
        return 0
    backup=root/'.git'/'premerge-doc-backups'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    archive=root/'polyc/web/downloads/PoliCatHome-source.zip'
    existed={}
    try:
        for name,state in statuses:
            if state=='current': continue
            destination=root/name
            existed[name]=destination.exists()
            if destination.exists():
                copy_to=backup/name
                copy_to.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(destination,copy_to)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(PACK/'payload'/name,destination)
        if archive.exists():
            copy_to=backup/'polyc/web/downloads/PoliCatHome-source.zip'
            copy_to.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(archive,copy_to)
        subprocess.run([sys.executable,'scripts/build-source-snapshot.py'],cwd=root,check=True)
        subprocess.run([sys.executable,'scripts/verify-release-assets.py','--source-only'],cwd=root,check=True)
        print(f'Installed. Backups stored in {backup.relative_to(root)}')
        print('Next: activate your .venv, run all tests and the wheel packaging gate in docs/RELEASE-CHECKLIST.md')
        return 0
    except Exception as e:
        for name,was_present in existed.items():
            destination=root/name
            if was_present:
                shutil.copy2(backup/name,destination)
            elif destination.exists():
                destination.unlink()
        saved=backup/'polyc/web/downloads/PoliCatHome-source.zip'
        if saved.exists():
            shutil.copy2(saved,archive)
        print('Failed; changed files and the prior snapshot restored: '+str(e),file=sys.stderr)
        return 1

if __name__=='__main__':
    sys.exit(main())
