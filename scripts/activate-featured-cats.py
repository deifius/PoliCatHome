#!/usr/bin/env python3
"""Add the editorial Featured Cats gallery to the visitor homepage.

The catalog assets are delivered as additive files. This installer avoids a brittle
unified-diff hunk in index.html so it works with nearby homepage revisions.
It never touches consent, authorization, workload, or coordinator code.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "polyc" / "web" / "index.html"

GALLERY = '''      <!-- FEATURED CATS GALLERY: discovery only; never authorizes execution -->
      <section id="featured-cats" class="featured-cats" aria-labelledby="featured-cats-title">
        <div class="featured-cats-head">
          <div>
            <div class="eyebrow">DISCOVER FIRST · CONSENT LATER</div>
            <h2 id="featured-cats-title">Meet the Cats</h2>
            <p>Explore potential work before committing your computer. A Cat is a project; a Catbox is the sandbox that might run it. Some examples are ideas, not available workloads.</p>
          </div>
          <div class="featured-cats-filters" role="group" aria-label="Filter featured Cats">
            <button type="button" data-featured-filter="all" aria-pressed="true">All Cats</button>
            <button type="button" data-featured-filter="pilot" aria-pressed="false">Pilot</button>
            <button type="button" data-featured-filter="concept" aria-pressed="false">Concepts</button>
          </div>
        </div>
        <p id="featuredCatsStatus" class="featured-cats-status" role="status" aria-live="polite">Loading the featured collection…</p>
        <div id="featuredCatsGrid" class="featured-cats-grid" aria-label="Featured Cats"></div>
        <p class="featured-cats-disclaimer">Featured means editorially selected, not approved to run or trusted by you. Actual eligible work is determined separately by Commons approval, creator trust, and your PoliC. Today's browser pilot runs only approved, matching SHA-256 tasks.</p>
      </section>
      <!-- END FEATURED CATS GALLERY -->
'''

HEAD_CSS = '<link rel="stylesheet" href="/web/featured-cats.css">'
HEAD_JS = '<script type="module" src="/web/featured-cats.js"></script>'


def activate(html: str) -> str:
    """Return an idempotently enhanced homepage or fail without modifying it."""
    if '</head>' not in html:
        raise ValueError('Cannot find </head> in polyc/web/index.html')

    # Place a section just before the existing learning/consent journey, not by
    # line number or by assuming particular whitespace around the hero closure.
    if not re.search(r'<section\s+id=["\']before-you-decide["\']', html):
        if 'id="featured-cats"' not in html:
            raise ValueError('Cannot find the before-you-decide section to anchor the gallery')

    # Keep the existing hero intact on unknown revisions. Revise copy only when
    # we recognize its exact original wording. Re-running never duplicates it.
    old_heading = '<h1>Contribute your Compute, <em>Cultivate the Commons.</em></h1>'
    new_heading = '<h1>Your computer. Your rules. <em>Our common future.</em></h1>'
    if old_heading in html:
        html = html.replace(old_heading, new_heading, 1)
        old_intro = ('Help with computing projects you choose, under rules you set. '
                     "Your personal <strong>PoliC</strong> is your permission slip—not the Commons' "
                     'permission to take over your computer.')
        new_intro = ('Discover projects that could benefit from shared computing power. '
                     "Choose what you believe in and what you're comfortable offering. "
                     'Your <strong>PoliC</strong> is your permission slip, never a surrender of your machine.')
        html = html.replace(old_intro, new_intro, 1)
        html = html.replace(new_heading,
                            new_heading + '\n          <p class="hero-tagline">Contribute your Compute, Cultivate the Commons.</p>', 1)

    old_cta = '<a class="hero-primary" href="#contribute">Set up browser Catnap <span aria-hidden="true">→</span></a>'
    new_cta = ('<a class="hero-primary" href="#featured-cats">Meet the Cats '
               '<span aria-hidden="true">→</span></a>\n'
               '            <a class="hero-secondary" href="#contribute">Set up browser Catnap</a>')
    if old_cta in html:
        html = html.replace(old_cta, new_cta, 1)

    if 'id="featured-cats"' not in html:
        preflight = re.search(r'(?m)^[ \t]*<section\s+id=["\']before-you-decide["\']', html)
        if not preflight:
            # Pages using a compact one-line layout are supported as well.
            preflight = re.search(r'<section\s+id=["\']before-you-decide["\']', html)
        if not preflight:
            raise ValueError('Could not locate a stable gallery insertion point')
        html = html[:preflight.start()] + GALLERY + html[preflight.start():]

    # Adding both tags is safe even when the current project loads other modules.
    if HEAD_CSS not in html:
        html = html.replace('</head>', f'  {HEAD_CSS}\n</head>', 1)
    if HEAD_JS not in html:
        html = html.replace('</head>', f'  {HEAD_JS}\n</head>', 1)
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true', help='Verify integration can be applied without writing')
    group.add_argument('--apply', action='store_true', help='Apply the homepage integration')
    args = parser.parse_args()
    try:
        original = INDEX.read_text(encoding='utf-8')
        updated = activate(original)
    except (ValueError, OSError) as exc:
        print(f'Featured Cats activation failed safely: {exc}', file=sys.stderr)
        return 1
    if args.check:
        print('Featured Cats activation: homepage anchor found; ' + ('already active' if updated == original else 'ready to apply'))
    elif updated == original:
        print('Featured Cats activation: already applied (no change)')
    else:
        INDEX.write_text(updated, encoding='utf-8')
        print('Featured Cats activation: added homepage gallery and asset imports')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
