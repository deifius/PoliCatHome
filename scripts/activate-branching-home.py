#!/usr/bin/env python3
"""Install a minimal, single-screen, choice-based landing without touching Catnap logic.

Run after the Featured Cats patch and its activation. The normal app remains the
non-JavaScript fallback and the place where consent is actually collected.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "polyc" / "web" / "index.html"
HEAD_CSS = '<link rel="stylesheet" href="/web/branching-home.css">'
HEAD_JS = '<script type="module" src="/web/branching-home.js"></script>'

HOME = '''<!-- The minimal invitation is presentation only; consent and computation remain in the existing app. -->
<section id="branchingHome" class="branching-home" hidden aria-label="Explore PoliC@home">
  <header class="branching-top">
    <a class="branching-brand" href="/" aria-label="PoliC at Home, beginning">Poli<span>C</span><small>@home</small></a>
    <span class="branching-topnote">a computing commons</span>
  </header>
  <main id="branchingStage" class="branching-stage" aria-labelledby="branchingTitle">
    <div class="branching-cat" aria-hidden="true">
      <svg viewBox="0 0 220 144" role="presentation" focusable="false">
        <g class="branching-cat-drawing" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M64 72 Q43 63 52 42 L47 22 Q63 29 75 43 Q102 28 135 42 L157 24 L154 56 Q171 81 151 101 Q134 120 105 116 Q74 117 61 99"/>
          <path d="M62 92 Q44 115 35 101 Q22 85 10 99 Q-1 115 24 126 Q48 134 67 111"/>
          <path d="M82 72 Q87 66 91 74 M122 74 Q127 67 132 73"/>
          <path d="M107 87 l-5 4 7 2 M109 93 Q104 102 99 97 M109 93 Q114 102 118 97"/>
          <path d="M85 90 L59 85 M84 97 L57 101 M130 90 L157 85 M129 97 L158 103"/>
          <path d="M77 115 L72 129 M126 115 L133 129"/>
        </g>
        <circle class="branching-orbit" cx="177" cy="34" r="3" fill="currentColor"/>
      </svg>
    </div>
    <div class="branching-content" id="branchingContent">
      <p class="branching-kicker" id="branchingKicker"></p>
      <h1 id="branchingTitle" tabindex="-1"></h1>
      <p id="branchingDescription" class="branching-description"></p>
      <p id="branchingStatus" class="branching-status" hidden></p>
      <div id="branchingChoices" class="branching-choices" aria-label="Your choices"></div>
      <div id="branchingExtra" class="branching-extra"></div>
    </div>
  </main>
  <footer class="branching-foot">
    <button id="branchingHomeButton" class="branching-home-link" type="button" hidden>← Start over</button>
    <span>Looking never starts Catnap.</span>
    <a href="/web/participate.html">How it works</a>
  </footer>
</section>
<!-- End minimal invitation. -->
'''


def activate(html: str) -> str:
    """Idempotent transform; errors do not write partial files."""
    if not re.search(r'<body\b[^>]*>', html, flags=re.I) or '</head>' not in html:
        raise ValueError('Expected HTML head and body in polyc/web/index.html')
    if '/web/featured-cats.js' not in html:
        raise ValueError('Featured Cats must be activated first (run activate-featured-cats.py --apply)')
    if 'id="branchingHome"' not in html:
        match = re.search(r'<body\b[^>]*>', html, flags=re.I)
        html = html[:match.end()] + '\n' + HOME + html[match.end():]
    if HEAD_CSS not in html:
        html = html.replace('</head>', f'  {HEAD_CSS}\n</head>', 1)
    if HEAD_JS not in html:
        html = html.replace('</head>', f'  {HEAD_JS}\n</head>', 1)
    return html


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check', action='store_true', help='Check whether integration is possible')
    action.add_argument('--apply', action='store_true', help='Write the modified homepage')
    args = parser.parse_args()
    try:
        before = INDEX.read_text(encoding='utf8')
        after = activate(before)
    except (OSError, ValueError) as exc:
        print(f'Bloom landing activation stopped: {exc}', file=sys.stderr)
        return 1
    if args.check:
        print('Bloom landing: '+ ('already active' if before == after else 'ready to activate'))
    elif before == after:
        print('Bloom landing: already active, no changes')
    else:
        INDEX.write_text(after, encoding='utf8')
        print('Bloom landing: installed without replacing the Catnap and creator workflows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
