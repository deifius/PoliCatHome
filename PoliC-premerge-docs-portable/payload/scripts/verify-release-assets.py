#!/usr/bin/env python3
"""Fail closed when a release wheel or public source ZIP lacks required UI assets.

Runs offline using Python's standard library. Use --source-only before building
an artifact; the full check must run before a release or source ZIP publish.
"""
import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    'polyc/web/index.html',
    'polyc/web/branching-home.js',
    'polyc/web/branching-home.css',
    'polyc/web/branching-story.mjs',
    'polyc/web/featured-cats.js',
    'polyc/web/featured-cats.json',
    'polyc/web/identity-ui.js',
    'polyc/web/identity-ui.css',
)
DOCS = ('README.md', 'docs/GETTING-STARTED.md',
        'docs/IDENTITY-SOVEREIGNTY.md', 'docs/RELEASE-CHECKLIST.md')


def inspect_archive(path, prefix, entries):
    with zipfile.ZipFile(path) as archive:
        files = set(archive.namelist())
        missing = [name for name in entries if prefix + name not in files]
        unsafe = [name for name in files if
                  '/.git/' in '/' + name or '/runtime/' in '/' + name or
                  name.endswith((':Zone.Identifier', '.env', 'admin-token.txt')) or
                  '/.venv/' in '/' + name or '/identity-backups/' in '/' + name]
        return missing, unsafe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-only', action='store_true',
                        help='Validate source code and packaging rules without built ZIP/wheel')
    parser.add_argument('--wheel-dir', default='dist')
    parser.add_argument('--snapshot', default='polyc/web/downloads/PoliCatHome-source.zip')
    args = parser.parse_args()

    errors = []
    for path in ASSETS + DOCS:
        if not (ROOT / path).is_file():
            errors.append(f'Missing source: {path}')
    config = (ROOT / 'pyproject.toml').read_text()
    snapshot_builder = (ROOT / 'scripts/build-source-snapshot.py').read_text()
    for pattern in ('"web/*.json"', '"web/*.mjs"'):
        if pattern not in config:
            errors.append(f'Missing wheel package-data rule: {pattern}')
    if "'.mjs'" not in snapshot_builder:
        errors.append('Source ZIP builder does not include .mjs files')

    if not args.source_only:
        wheel_files = sorted((ROOT / args.wheel_dir).glob('polyc_at_home-*.whl'))
        if not wheel_files:
            errors.append('No built wheel found; build one before release')
        else:
            wheel = wheel_files[-1]
            missing, unsafe = inspect_archive(wheel, '', ASSETS)
            errors += [f'{wheel.name} missing {x}' for x in missing]
            errors += [f'{wheel.name} unsafe entry {x}' for x in unsafe]
        source_zip = ROOT / args.snapshot
        if not source_zip.is_file():
            errors.append(f'Missing source snapshot: {source_zip}')
        else:
            missing, unsafe = inspect_archive(source_zip, 'PoliCatHome-source/', ASSETS + DOCS)
            errors += [f'Source snapshot missing {x}' for x in missing]
            errors += [f'Source snapshot contains unsafe entry {x}' for x in unsafe]

    if errors:
        for error in errors:
            print('FAIL:', error, file=sys.stderr)
        return 1
    print('OK: required website assets, packaging declarations, and source safety checks passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
