"""Publication should preserve code freedom, doc rights, and source notices."""
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient

from polyc.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_license_scopes_and_source_snapshot():
    license_text = (ROOT / 'LICENSE').read_text()
    assert 'BSD 3-Clause License' in license_text
    assert 'Neither the name of the copyright holder' in license_text
    assert (ROOT / 'polyc/web/LICENSE.txt').read_text() == license_text
    assert 'CC BY 4.0' in (ROOT / 'docs/LICENSE-CC-BY-4.0.md').read_text()
    assert 'proprietary' in (ROOT / 'Philosophy.md').read_text()
    with ZipFile(ROOT / 'polyc/web/downloads/PoliCatHome-source.zip') as archive:
        names = set(archive.namelist())
        for path in (
            'LICENSE', 'Philosophy.md', 'LICENSING.md',
            'docs/LICENSE-CC-BY-4.0.md',
            'docs/ART-ASSET-MANIFEST.md',
            'polyc/web/licenses.html', 'polyc/web/LICENSE.txt',
        ):
            assert 'PoliCatHome-source/' + path in names
        assert all('/runtime/' not in p and 'admin-token' not in p for p in names)


def test_license_page_served(tmp_path):
    app = create_app(str(tmp_path / 'license.sqlite'), 'test-admin-token-must-be-long' )
    with TestClient(app) as client:
        response = client.get('/web/licenses.html')
        assert response.status_code == 200
        assert 'BSD 3-Clause' in response.text
        assert 'Catbox' in response.text
        assert client.get('/web/LICENSE.txt').status_code == 200
        assert client.get('/web/downloads/PoliCatHome-source.zip').status_code == 200
