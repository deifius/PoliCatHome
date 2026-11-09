"""The landing explainer must be accessible, accurate, and separate from enrollment."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_explainer_has_three_genuine_tabs_and_single_default_panel():
    html = (ROOT / 'polyc/web/index.html').read_text()
    elements = Elements(); elements.feed(html)
    tabs = [attrs for tag, attrs in elements.tags if tag == 'button' and attrs.get('role') == 'tab']
    assert len(tabs) == 3
    assert [tab['aria-controls'] for tab in tabs] == ['explainPanel1', 'explainPanel2', 'explainPanel3']
    assert [tab['aria-selected'] for tab in tabs] == ['true', 'false', 'false']
    panels = [attrs for _tag, attrs in elements.tags if attrs.get('role') == 'tabpanel']
    assert len(panels) == 3
    assert sum('hidden' not in panel for panel in panels) == 1
    assert all(tab['aria-controls'] == panel['id'] for tab, panel in zip(tabs, panels))


def test_explainer_is_clear_about_capabilities_and_consent():
    html = (ROOT / 'polyc/web/index.html').read_text()
    js = (ROOT / 'polyc/web/app.js').read_text()
    for text in ('Contribute your Compute,', 'Cultivate the Commons.',
                 'CPU time, electricity and heat', 'GPU memory (VRAM)',
                 'not a guaranteed hardware limit', 'SHA-256 hashing tasks',
                 'Automatic negotiation of arbitrary Catboxes is a future goal',
                 'Gibson screensaver', 'Nothing starts by visiting'):
        assert text in html
    assert 'function selectExplainer' in js
    assert "event.key==='ArrowRight'" in js
    assert "button.setAttribute('aria-selected',String(selected))" in js
    assert "$('visualizerDisclosure').open=true" in js
    assert 'type="checkbox"' in html and 'id="browserConsent"' in html
