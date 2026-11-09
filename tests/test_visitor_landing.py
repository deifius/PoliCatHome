"""Consent-first landing page regression; standard-library only."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, name, attrs):
        self.tags.append((name, dict(attrs)))


def test_visitor_landing_order_and_unique_controls():
    html = (ROOT / 'polyc/web/index.html').read_text()
    tags = Tags(); tags.feed(html)
    ids = [attributes['id'] for _name, attributes in tags.tags if 'id' in attributes]
    assert max(Counter(ids).values()) == 1, 'Duplicate IDs break JS handlers and labels'
    assert html.index('id="before-you-decide"') < html.index('id="contribute"') < html.index('id="visualizerDisclosure"')
    assert any(n == 'details' and a.get('id') == 'visualizerDisclosure' and 'open' not in a for n, a in tags.tags)
    assert any(n == 'input' and a.get('id') == 'browserConsent' and a.get('type') == 'checkbox' and 'checked' not in a for n, a in tags.tags)
    assert any(n == 'div' and a.get('id') == 'participationForm' and 'hidden' in a for n, a in tags.tags)
    for name in ('startBtn', 'pauseBtn', 'revokeBtn', 'visitorStatus', 'policPreview', 'enrollBtn'):
        assert name in ids
    assert 'aria-live="polite"' in html
    assert 'Start Catnap</button>' in html and 'Revoke Consent</button>' in html


def test_disclosures_cover_consent_questions():
    html = (ROOT / 'polyc/web/index.html').read_text()
    tags = Tags(); tags.feed(html)
    for text in ('What exactly happens when I start?', 'Who decides which projects I work for?',
                 'What information leaves my computer?', 'Can I stop, and is it paid?'):
        assert text in html
    assert html.count('class="help-tip"') >= 4
    assert html.count('aria-label="More about ') >= 4
    assert '<details class="polic-extra">' in html
    assert 'No payment is promised' in html
    assert 'future approved Cats' in html
    assert 'not a guaranteed hardware limit' in html


def test_browser_scene_is_lazy_and_status_is_explicit():
    js = (ROOT / 'polyc/web/app.js').read_text()
    css = (ROOT / 'polyc/web/style.css').read_text()
    assert "if(!$('visualizerDisclosure').open)return;" in js
    assert "visualizer.addEventListener('toggle'" in js
    assert "state.scene?.destroy();state.scene=null;" in js
    assert 'function updateVisitorStatus()' in js
    assert 'Not enrolled · CPU work is off' in js
    assert 'Enrolled · CPU work is off until you press Start' in js
    assert '.help-tip:hover>.tip-content' in css
    assert '.help-tip:focus-within>.tip-content' in css
    assert '@media(max-width:600px)' in css
