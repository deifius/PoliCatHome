"""Visitor-facing copy should distinguish current features from future intentions."""
from pathlib import Path

HTML = (Path(__file__).resolve().parents[1] / "polyc/web/index.html").read_text()


def test_stop_and_value_sharing_are_distinct_disclosures():
    assert "Can I stop at any time?" in HTML
    assert "Can I stop, and is it paid?" not in HTML
    assert "Is Catnap paid?" in HTML
    assert "No payment is promised" in HTML
    assert "compensation or income is not guaranteed" in HTML
    assert "accountable mutual prosperity" in HTML
    assert "informed, enthusiastic collaboration" in HTML
    assert "not available in today\'s browser pilot" in HTML
    assert "does <strong>not</strong> revoke enrollment" in HTML
    assert "once revocation is confirmed" in HTML


def test_shorter_navigational_copy():
    assert "Explore @home screensaver options" in HTML
    assert "Bring PoliC@home home." in HTML
    assert "Take PoliC@home home." not in HTML
    assert "Explore the Gibson and other optional visualizations" not in HTML
    assert "The graphics do not donate compute." in HTML
