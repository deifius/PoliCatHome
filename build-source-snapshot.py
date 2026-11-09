"""Build the public, credential-free source snapshot linked from the web interface."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
target = root / 'polyc/web/downloads/PoliCatHome-source.zip'
target.parent.mkdir(parents=True, exist_ok=True)
exclude_dirs = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache', '.mypy_cache', 'node_modules', 'runtime', '.tox', 'dist', 'build'}
allowed = {'.py', '.js', '.html', '.css', '.md', '.toml', '.yaml', '.yml', '.json', '.sh', '.txt', '.gitignore'}
with ZipFile(target, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
    for f in sorted(root.rglob('*')):
        rel = f.relative_to(root)
        if not f.is_file() or f == target or any(part in exclude_dirs for part in rel.parts):
            continue
        if rel.parts[0] not in {'polyc', 'scripts', 'tests', 'docs', 'projects'} and rel.as_posix() not in {'pyproject.toml', 'README.md', 'AGENTS.md', 'constitution.example.yaml', '.gitignore'}:
            continue
        if f.suffix not in allowed and f.name != '.gitignore':
            continue
        if f.is_symlink() or f.stat().st_size > 1024 * 1024:
            continue
        archive.write(f, 'PoliCatHome-source/' + rel.as_posix())
print(target)
