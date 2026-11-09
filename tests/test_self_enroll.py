"""Self-service registration is separate from explicit consent to work."""
from fastapi.testclient import TestClient
from polyc.api import create_app
from polyc.demo import constitution
from polyc.policy import policy_digest
from tests.conftest import ADMIN

ROOT = {'Authorization': 'Bearer ' + ADMIN}


def test_invitation_fallback_when_self_enroll_disabled(setup):
    client, _, _, _, pub = setup
    assert client.get('/api/catnap/enrollment-options').json()['self_enroll'] is False
    node = {'node_id': 'browser-nopass', 'token': 'k'*32, 'constitution': constitution(pub)}
    result = client.post('/api/catnap/enroll', json={'node': node})
    assert result.status_code == 403
    assert 'self-enrollment is disabled' in result.json()['detail']


def test_self_enroll_no_invitation_catalog_explicit_trust_and_revoke(tmp_path, monkeypatch, setup):
    monkeypatch.setenv('POLYC_SELF_ENROLL', '1')
    _, _, _, signed, pub = setup
    app = create_app(str(tmp_path/'public.sqlite'), ADMIN)
    with TestClient(app) as client:
        options = client.get('/api/catnap/enrollment-options').json()
        assert options['self_enroll'] and options['pilot']
        assert client.get('/api/catnap/catalog').json()['cats'] == []
        # The operator alone approves Cats; catalog never leaks staged proposals.
        cat = signed(project_id='approved-pilot')
        proposal = client.post('/api/workshop/cats', headers=ROOT, json={'invitation': 'x'*40,
                 'signed_project': cat.model_dump(mode='json')})
        assert proposal.status_code == 403
        assert client.get('/api/catnap/catalog').json()['cats'] == []
        assert client.post('/api/jobs', headers=ROOT, json=cat.model_dump(mode='json')).status_code == 200
        approved = client.get('/api/catnap/catalog').json()['cats']
        assert len(approved) == 1
        assert approved[0]['creator_key'] == pub
        assert approved[0]['category'] == 'open_science'
        assert 'signature' not in str(approved)
        # Joining with zero trust registers a consenting *idle* node, never authorizes any Cat.
        idle_c = constitution(pub)
        idle_c['spec']['trust']['trusted_signers'] = []
        idle = {'node_id': 'browser-idle', 'token': 't'*32, 'constitution': idle_c}
        missing_ack = client.post('/api/catnap/enroll', json={'node': idle})
        assert missing_ack.status_code == 422
        response = client.post('/api/catnap/enroll', json={'node': idle, 'accepted_browser_limitations': True})
        assert response.status_code == 200, response.text
        assert response.json()['enrolled']
        idle_auth = {'Authorization': 'Bearer ' + idle['token']}
        lease = client.post('/api/lease', headers=idle_auth,
            json={'node_id': idle['node_id'], 'constitution_digest': policy_digest(idle_c)})
        assert lease.status_code == 200 and lease.json()['assignment'] is None
        # A visitor who explicitly adds a catalog key can lease compatible signed work.
        opted_c = constitution(pub)
        opted = {'node_id': 'browser-opt-in', 'token': 'u'*32, 'constitution': opted_c}
        assert client.post('/api/catnap/enroll', json={'node': opted, 'accepted_browser_limitations': True}).status_code == 200
        lease = client.post('/api/lease', headers={'Authorization': 'Bearer ' + opted['token']},
            json={'node_id': opted['node_id'], 'constitution_digest': policy_digest(opted_c)})
        assert lease.status_code == 200 and lease.json()['assignment'] is not None
        assert client.post('/api/nodes/browser-opt-in/revoke',
            headers={'Authorization': 'Bearer ' + opted['token']}, json={}).status_code == 200
        forbidden = client.post('/api/lease', headers={'Authorization': 'Bearer ' + opted['token']},
            json={'node_id': opted['node_id'], 'constitution_digest': policy_digest(opted_c)})
        assert forbidden.status_code == 403
    app.state.store.db.close()


def test_server_wont_lease_untrusted_signer_even_if_category_matches(setup):
    client, app, c, signed, pub = setup
    malicious = signed(project_id='untrusted-but-approved')
    assert client.post('/api/jobs', headers=ROOT, json=malicious.model_dump(mode='json')).status_code == 200
    # This node approves the category but trusts NO signer; coordinator must not lease.
    idle_c = constitution(pub)
    idle_c['spec']['trust']['trusted_signers'] = []
    assert client.post('/api/nodes', headers=ROOT, json={'node_id': 'server-trust-check',
        'token': 'v'*32, 'constitution': idle_c}).status_code == 200
    lease = client.post('/api/lease', headers={'Authorization': 'Bearer ' + 'v'*32},
        json={'node_id': 'server-trust-check', 'constitution_digest': policy_digest(idle_c)})
    assert lease.status_code == 200 and lease.json()['assignment'] is None


def test_self_enroll_is_transactionally_limited_per_connection(tmp_path, monkeypatch, setup):
    monkeypatch.setenv('POLYC_SELF_ENROLL', 'yes')
    pub = setup[-1]
    app = create_app(str(tmp_path/'limits.sqlite'), ADMIN)
    with TestClient(app) as client:
        for i in range(5):
            response = client.post('/api/catnap/enroll', json={'node': {
                'node_id': f'visitor-{i}', 'token': 'x'*30+str(i).zfill(2),
                'constitution': constitution(pub)}, 'accepted_browser_limitations': True})
            assert response.status_code == 200, response.text
        denied = client.post('/api/catnap/enroll', json={'node': {
            'node_id': 'visitor-six', 'token': 'z'*32, 'constitution': constitution(pub)}, 'accepted_browser_limitations': True})
        assert denied.status_code == 429
        assert 'limit reached' in denied.json()['detail']
        # Rate limits survive a coordinator restart when the same database is reused.
    app.state.store.db.close()
    second = create_app(str(tmp_path/'limits.sqlite'), ADMIN)
    with TestClient(second) as client:
        denied = client.post('/api/catnap/enroll', json={'node': {
            'node_id': 'visitor-seven', 'token': 'w'*32, 'constitution': constitution(pub)}, 'accepted_browser_limitations': True})
        assert denied.status_code == 429
    second.state.store.db.close()


def test_ui_visitor_enrollment_avoids_admin_credential(setup):
    client, *_ = setup
    html = client.get('/').text
    js = client.get('/web/app.js').text
    assert 'id="approvedCatList"' in html
    assert 'id="refreshCatalog"' in html
    assert 'id="inviteFallback"' in html
    assert 'Choose Cats you trust' in html
    assert "'/api/catnap/catalog'" in js
    assert "'/api/catnap/enrollment-options'" in js
    assert 'if(invitation)payload.invitation=invitation' in js
    assert 'Nothing computes until you press Start' in js
    assert 'accepted_browser_limitations:true' in js
