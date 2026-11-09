"""A ZIP-updated checkout must be easy to understand and safe to tidy."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_source_tree_and_snapshot():
    for required in ('polyc/api.py', 'polyc/web/app.js', 'docs/INDEX.md',
                     'docs/REPOSITORY-LAYOUT.md', 'scripts/tidy-repository.py'):
        assert (ROOT / required).exists(), required
    for stale in ('api.py', 'web', 'polyc-at-home', 'test_api.py',
                  'CATNAP-BROWSER.md', 'example-render'):
        assert not (ROOT / stale).exists(), stale
    with ZipFile(ROOT / 'polyc/web/downloads/PoliCatHome-source.zip') as archive:
        names = set(archive.namelist())
    for rel in ('docs/INDEX.md', 'docs/REPOSITORY-LAYOUT.md',
                'scripts/tidy-repository.py'):
        assert 'PoliCatHome-source/' + rel in names
    assert all('/runtime/' not in name for name in names)
    assert all('/polyc-at-home/' not in name for name in names)


def test_tidy_repository_dry_run_and_move_only(tmp_path):
    root = tmp_path / 'PoliCatHome'
    root.mkdir()
    for folder in ('polyc', 'polyc/web', 'docs', 'tests', 'scripts', 'projects/example-render',
                   'runtime', '.git'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    (root / 'pyproject.toml').write_text('canonical')
    (root / 'README.md').write_text('keep top level')
    (root / 'LICENSE').write_text('keep BSD')
    (root / '.git/config').write_text('git should remain')
    (root / 'runtime/owner-token.txt').write_text('do not touch token')
    (root / 'polyc/api.py').write_text('new canonical module')
    (root / 'api.py').write_text('older changed module; KEEP A BACKUP')
    (root / 'docs/CATNAP-BROWSER.md').write_text('canonical documentation')
    (root / 'CATNAP-BROWSER.md').write_text('old documentation')
    (root / 'polyc/web/app.js').write_text('new frontend')
    (root / 'web').mkdir()
    (root / 'web/app.js').write_text('old frontend')
    (root / 'polyc-at-home').mkdir()
    (root / 'polyc-at-home/unique.md').write_text('only inside legacy repo')
    (root / 'projects/example-render/polic.yaml').write_text('new sample')
    (root / 'polic.yaml').write_text('old sample')
    (root / 'not-a-duplicate.xyz').write_text('should remain unrecognized')
    script = root / 'scripts/tidy-repository.py'
    shutil.copy2(ROOT / 'scripts/tidy-repository.py', script)
    cmd = [sys.executable, str(script), '--root', str(root)]

    preview = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert 'DRY RUN ONLY' in preview.stdout
    assert 'DIFFERENT' in preview.stdout
    assert (root / 'api.py').exists()
    assert (root / 'web/app.js').exists()

    apply = subprocess.run(cmd + ['--apply'], capture_output=True, text=True, check=True)
    assert 'Moved 5 entries' in apply.stdout
    backup_candidates = list(tmp_path.glob('PoliCatHome-cleanup-backup-*'))
    assert len(backup_candidates) == 1
    backup = backup_candidates[0]
    assert (backup / 'api.py').read_text() == 'older changed module; KEEP A BACKUP'
    assert (backup / 'web/app.js').read_text() == 'old frontend'
    assert (backup / 'polyc-at-home/unique.md').read_text() == 'only inside legacy repo'
    assert (backup / 'CATNAP-BROWSER.md').read_text() == 'old documentation'
    assert (backup / 'polic.yaml').read_text() == 'old sample'
    records = json.loads((backup / 'MANIFEST.json').read_text())['entries']
    assert {item['path'] for item in records} == {
        'api.py', 'web', 'polyc-at-home', 'CATNAP-BROWSER.md', 'polic.yaml'
    }
    assert (root / 'README.md').read_text() == 'keep top level'
    assert (root / 'runtime/owner-token.txt').read_text() == 'do not touch token'
    assert (root / '.git/config').read_text() == 'git should remain'
    assert (root / 'not-a-duplicate.xyz').exists()
    assert (root / 'polyc/api.py').read_text() == 'new canonical module'
    again = subprocess.run(cmd + ['--apply'], capture_output=True, text=True, check=True)
    assert 'Already tidy' in again.stdout
    assert len(list(tmp_path.glob('PoliCatHome-cleanup-backup-*'))) == 1
