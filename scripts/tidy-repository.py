#!/usr/bin/env python3
"""Non-destructive cleanup of legacy files left by layered PoliC@home ZIPs.

Default: dry-run. --apply moves identified redundant root entries into a
sibling backup directory; never deletes source, Git data, or runtime state.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys

KEEP_ROOT = {
    '.git', '.gitignore', '.dockerignore', '.env', '.venv',
    'AGENTS.md', 'Dockerfile', 'LICENSE', 'LICENSING.md', 'Philosophy.md',
    'README.md', 'compose.yaml', 'compose.catbox.yaml',
    'constitution.example.yaml', 'pyproject.toml',
    'docs', 'polyc', 'projects', 'scripts', 'tests', 'runtime',
}
# These directories were complete, stale copies created by earlier releases.
LEGACY_DIRS = {
    'polyc-at-home': None,
    'web': 'polyc/web',
    'example-render': 'projects/example-render',
    'example-test-credit-job': 'projects/example-test-credit-job',
    '__pycache__': None,
    '.pytest_cache': None,
    'polyc_at_home.egg-info': None,
}
# Old example manifests are replaced by projects/example-render/ counterparts.
LEGACY_MANIFESTS = {'polic.yaml': 'projects/example-render/polic.yaml',
                    'project.yaml': 'projects/example-render/project.yaml'}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def compare_entry(old: Path, authoritative: Path | None) -> dict:
    """Describe potential differences without deciding that one is disposable."""
    if authoritative is None or not authoritative.exists():
        return {'comparison': 'legacy / no counterpart'}
    if old.is_symlink() or authoritative.is_symlink():
        return {'comparison': 'symlink; moved as link, never followed'}
    if old.is_file() and authoritative.is_file():
        a, b = sha256(old), sha256(authoritative)
        return {'comparison': 'identical' if a == b else 'DIFFERENT; backed up',
                'original_sha256': a, 'canonical_sha256': b}
    if old.is_dir() and authoritative.is_dir():
        files = [p for p in old.rglob('*') if p.is_file() and not p.is_symlink()]
        identical = changed = unique = 0
        for f in files:
            counterpart = authoritative / f.relative_to(old)
            if not counterpart.is_file():
                unique += 1
            elif sha256(f) == sha256(counterpart):
                identical += 1
            else:
                changed += 1
        return {'comparison': 'directory backup (including any unique files)',
                'identical_files': identical, 'different_files': changed,
                'unique_legacy_files': unique}
    return {'comparison': 'type differs; backed up'}


def candidate_target(root: Path, item: Path) -> Path | None:
    """Return canonical counterpart, legacy dir sentinel, or None for keep."""
    name = item.name
    if name in KEEP_ROOT or name.startswith('.git'):
        return None
    if name in LEGACY_DIRS and (item.is_dir() or item.is_symlink()):
        rel = LEGACY_DIRS[name]
        return root / rel if rel is not None else item  # same path = intentional orphan
    if name in LEGACY_MANIFESTS and item.is_file():
        counterpart = root / LEGACY_MANIFESTS[name]
        if counterpart.is_file():
            return counterpart
    if item.is_file() and item.suffix == '.md' and (root / 'docs' / name).is_file():
        return root / 'docs' / name
    # Legacy root Python and scripts are duplicate import/test/launcher entry points.
    if item.is_file() and item.suffix in {'.py', '.sh', '.mjs'}:
        for folder in ('polyc', 'tests', 'scripts'):
            counterpart = root / folder / name
            if counterpart.is_file():
                return counterpart
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1],
                        help='repository root (defaults to this script\'s parent repo)')
    parser.add_argument('--apply', action='store_true',
                        help='move known legacy entries into a sibling backup')
    args = parser.parse_args()
    root = args.root.resolve()
    required = ('pyproject.toml', 'polyc', 'docs', 'scripts', 'tests')
    if not all((root / name).exists() for name in required):
        print('Refusing: not a recognizable PoliC@home repository root.', file=sys.stderr)
        return 2
    candidates = []
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        target = candidate_target(root, item)
        if target is None:
            continue
        comparison = compare_entry(item, None if item == target else target)
        candidates.append({'path': item.name,
                           'canonical': str(target.relative_to(root)) if target != item else None,
                           **comparison})
    if not candidates:
        print('Already tidy: no known legacy root copies found. Runtime was untouched.')
        return 0
    print(f'PoliC@home legacy cleanup: {len(candidates)} root entries')
    print('Preserved: README, LICENSE, Philosophy, canonical folders, Git and runtime/.')
    for record in candidates:
        canonical = f' -> {record["canonical"]}' if record['canonical'] else ''
        print(f'  {record["path"]}{canonical}: {record["comparison"]}')
    if not args.apply:
        print('\nDRY RUN ONLY. No files moved. Review entries, then run with --apply.')
        return 0

    suffix = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    backup = root.parent / f'{root.name}-cleanup-backup-{suffix}'
    num = 1
    while backup.exists():
        backup = root.parent / f'{root.name}-cleanup-backup-{suffix}-{num}'
        num += 1
    backup.mkdir(mode=0o700)
    # A manifest describes differences and allows individual files to be restored.
    manifest = {'project': str(root), 'created_utc': datetime.now(timezone.utc).isoformat(),
                'note': 'Move-only cleanup. Nothing under runtime/ or .git/ was touched.',
                'entries': candidates}
    (backup / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    moved = 0
    try:
        for entry in candidates:
            name = entry['path']
            shutil.move(str(root / name), str(backup / name))
            moved += 1
    except Exception as exc:
        print(f'ERROR after {moved} moves: {exc}', file=sys.stderr)
        print(f'Recover files manually from {backup}', file=sys.stderr)
        return 1
    print(f'\nMoved {moved} entries to: {backup}')
    print('Your active polyc/, docs/, tests/, scripts/, projects/, .git/ and runtime/ remain.')
    print('Inspect MANIFEST.json and test your application before removing the backup.')
    print('If legacy files were tracked, review git status --short before committing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
