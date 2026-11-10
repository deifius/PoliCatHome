"""Documentation and release-artifact contracts (no network required)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_relative_markdown_links_resolve():
    files = [ROOT / 'README.md', *sorted((ROOT / 'docs').glob('*.md'))]
    missing = []
    for page in files:
        text = page.read_text(encoding='utf-8')
        for _, target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text):
            path = target.split('#', 1)[0]
            if path and not path.startswith(('http:', 'https:', 'mailto:', '/')):
                if not (page.parent / path).exists():
                    missing.append((page.relative_to(ROOT).as_posix(), target))
    assert not missing, f'broken documentation links: {missing}'


def test_release_docs_name_separation_of_identity_and_consent():
    doc = (ROOT / 'docs/IDENTITY-SOVEREIGNTY.md').read_text()
    checklist = (ROOT / 'docs/RELEASE-CHECKLIST.md').read_text()
    assert 'Identity is evidence, not authority' in doc
    assert 'not a Catnap token' in (ROOT / 'docs/GETTING-STARTED.md').read_text()
    assert 'Google' in doc and 'recovery' in doc.lower()
    assert 'featured-cats.json' in checklist
    assert 'branching-story.mjs' in checklist
