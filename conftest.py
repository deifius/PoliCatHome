import pytest
from fastapi.testclient import TestClient
from polyc.api import create_app
from polyc.demo import constitution
from polyc.crypto import create_keypair, sign_project
from polyc.models import Project

ADMIN = 'z'*32

@pytest.fixture
def setup(tmp_path):
    private, public = str(tmp_path/'secret.pem'), str(tmp_path/'public.txt')
    create_keypair(private, public)
    pub = (tmp_path/'public.txt').read_text()
    c = constitution(pub)
    app = create_app(str(tmp_path/'coord.sqlite'), ADMIN)
    with TestClient(app) as client:
        r = client.post('/api/nodes', json={'node_id':'cat-one','token':'n'*32,'constitution':c},headers={'Authorization':f'Bearer {ADMIN}'})
        assert r.status_code == 200, r.text
        def signed(project_id='cat-math', category='open_science', purposes=None, commercial=False, **kwargs):
            return sign_project(Project(project_id=project_id, title='Cat arithmetic',
                source_repo='https://example.org/repo',source_commit='a'*40,
                category=category,purposes=purposes or ['open_knowledge'], commercial=commercial,
                work={'kind':'sha256_chain_v1', 'tasks':2, 'iterations':100, 'seed':'cat'},**kwargs),private)
        yield client, app, c, signed, pub
    app.state.store.db.close()
