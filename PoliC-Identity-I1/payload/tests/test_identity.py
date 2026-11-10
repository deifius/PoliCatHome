"""Identity is optional and separate from Catnap/workshop/admin authorization."""
import base64
import hashlib
import json
import time

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from fastapi.testclient import TestClient
from polyc.api import create_app
from polyc.identity import _b64, _verify_google_id_token

ADMIN = 'operator-secret-which-is-very-long-12345'
ORIGIN = {'Origin':'http://testserver'}
JSON_HEADERS = {**ORIGIN,'Content-Type':'application/json'}


def make_key():
    key=ed25519.Ed25519PrivateKey.generate()
    public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
    return key,public


def challenge(c,key,pub,purpose):
    r=c.post('/api/identity/challenge',json={'purpose':purpose,'public_key':pub},headers=ORIGIN)
    assert r.status_code==200,r.text
    p=r.json()
    assert p['message'].startswith('PoliC identity proof v1\ntestserver\n'+purpose+'\n')
    sig=key.sign(p['message'].encode('utf-8')).hex()
    return p,sig


def prove(c,p,sig):
    return c.post('/api/identity/prove',json={'challenge_id':p['challenge_id'],'signature':sig},headers=ORIGIN)


@pytest.fixture
def identity(tmp_path):
    app=create_app(str(tmp_path/'identity.db'),ADMIN)
    with TestClient(app) as c: yield c,app
    app.state.store.db.close()


def test_register_session_prefs_export_logout_and_relogin(identity):
    c,app=identity
    assert c.get('/api/identity/me').json()['authenticated'] is False
    assert c.get('/api/identity/config').json()['google_enabled'] is False
    key,pub=make_key()
    p,sig=challenge(c,key,pub,'register')
    r=prove(c,p,sig)
    assert r.status_code==200,r.text
    assert r.json()['compute_authorized'] is False
    assert 'httponly' in r.headers['set-cookie'].lower()
    assert 'samesite=lax' in r.headers['set-cookie'].lower()
    token=c.cookies.get('polyc_identity_session_dev')
    assert token and token not in json.dumps([dict(x) for x in app.state.store.db.execute('SELECT * FROM identity_sessions')])
    assert c.get('/api/identity/me').json()['login_methods']=={'independent_keys':1,'google_linked':False}
    owner=c.get('/api/identity/me').json()['identity']
    assert owner['id'].startswith('plc_') and owner['default_landing']=='workspace'
    assert c.patch('/api/identity/preferences',json={'default_landing':'bloom'},headers=ORIGIN).status_code==200
    assert c.patch('/api/identity/alias',json={'alias':'The Tolerable Cat'},headers=ORIGIN).status_code==200
    exported=c.get('/api/identity/export').json()
    assert exported['account']['alias']=='The Tolerable Cat'
    assert exported['public_keys']==[pub]
    assert 'private_key' not in exported and not exported.get('private_keys')
    # Identity cannot act as an operator or an enrolled worker.
    assert c.post('/api/nodes',json={},headers=ORIGIN).status_code==401
    assert c.get('/api/catnap/snapshot').status_code==401
    assert c.post('/api/identity/logout',json={},headers=ORIGIN).status_code==200
    assert c.get('/api/identity/me').json()['authenticated'] is False
    assert not list(app.state.store.db.execute('SELECT * FROM identity_sessions'))
    p,sig=challenge(c,key,pub,'login')
    assert prove(c,p,sig).status_code==200
    assert c.get('/api/identity/me').json()['identity']['id']==owner['id']
    assert c.get('/api/identity/me').json()['identity']['default_landing']=='bloom'


def test_invalid_proof_replay_wrong_purpose_and_duplicate_key(identity):
    c,_=identity
    key,pub=make_key()
    p,sig=challenge(c,key,pub,'register')
    bad=prove(c,p,'0'*128)
    assert bad.status_code==401
    assert prove(c,p,sig).status_code==401 # consumed even when signature was wrong
    p,sig=challenge(c,key,pub,'login')
    assert prove(c,p,sig).status_code==401
    p,sig=challenge(c,key,pub,'register')
    assert prove(c,p,sig).status_code==200
    p,sig=challenge(c,key,pub,'register')
    assert prove(c,p,sig).status_code==409


def test_same_origin_rate_and_https_safety(identity):
    c,app=identity
    key,pub=make_key()
    assert c.post('/api/identity/challenge',json={'purpose':'register','public_key':pub}).status_code==403
    assert c.post('/api/identity/challenge',json={'purpose':'register','public_key':pub},headers={'Origin':'https://evil.example'}).status_code==403
    with TestClient(app,base_url='http://unsecured.example') as remote:
        assert remote.post('/api/identity/challenge',json={'purpose':'register','public_key':pub}, headers={'Origin':'http://unsecured.example'}).status_code==503
    for _ in range(40):
        assert c.post('/api/identity/challenge',json={'purpose':'register','public_key':pub},headers=ORIGIN).status_code ==200
    assert c.post('/api/identity/challenge',json={'purpose':'register','public_key':pub},headers=ORIGIN).status_code==429


def test_key_link_requires_live_authenticated_session(identity):
    c,app=identity
    key,pub=make_key()
    p,sig=challenge(c,key,pub,'register'); assert prove(c,p,sig).status_code==200
    second,secondpub=make_key()
    p,sig=challenge(c,second,secondpub,'link-key')
    # A session revoked after the challenge cannot finish linking the key.
    assert c.post('/api/identity/logout',json={},headers=ORIGIN).status_code==200
    assert prove(c,p,sig).status_code==403
    p,sig=challenge(c,key,pub,'login');assert prove(c,p,sig).status_code==200
    p,sig=challenge(c,second,secondpub,'link-key');assert prove(c,p,sig).status_code==200
    assert c.post('/api/identity/logout',json={},headers=ORIGIN).status_code==200
    p,sig=challenge(c,second,secondpub,'login');assert prove(c,p,sig).status_code==200
    assert c.get('/api/identity/me').json()['authenticated'] is True


def test_cannot_unlink_only_authenticator(identity):
    c,app=identity
    key,pub=make_key()
    p,sig=challenge(c,key,pub,'register');assert prove(c,p,sig).status_code==200
    account=c.get('/api/identity/me').json()['identity']['id']
    app.state.identities.provider_connect('google','test-sub',account)
    assert c.delete('/api/identity/providers/google',headers=ORIGIN).status_code==200
    assert app.state.identities.provider_owner('google','test-sub') is None
    app.state.identities.provider_connect('google','test-sub',account)
    with app.state.store.lock:
        app.state.store.db.execute('DELETE FROM identity_keys WHERE identity_id=?',(account,))
    assert c.delete('/api/identity/providers/google',headers=ORIGIN).status_code==409


def sign_jwt(claims, private, kid='test'):
    header={'alg':'RS256','typ':'JWT','kid':kid}
    a=_b64(json.dumps(header).encode());b=_b64(json.dumps(claims).encode())
    sig=private.sign((a+'.'+b).encode(),padding.PKCS1v15(),hashes.SHA256())
    return a+'.'+b+'.'+_b64(sig)


def test_google_jwt_signature_audience_nonce_and_expiry():
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    nums=private.public_key().public_numbers()
    jwks={'keys':[{'kid':'test','kty':'RSA','use':'sig',
       'n':_b64(nums.n.to_bytes((nums.n.bit_length()+7)//8,'big')),
       'e':_b64(nums.e.to_bytes((nums.e.bit_length()+7)//8,'big'))}]}
    claims={'iss':'https://accounts.google.com','aud':'configured-client','nonce':'challenge',
            'iat':int(time.time()),'exp':int(time.time())+300,'sub':'google-sub','email':'not-a-key@example.com'}
    assert _verify_google_id_token(sign_jwt(claims,private),'configured-client','challenge',jwks)=='google-sub'
    for updates in ({'nonce':'wrong'},{'aud':'another-site'},{'exp':int(time.time())-1000}):
        with pytest.raises(Exception):
            _verify_google_id_token(sign_jwt({**claims,**updates},private),'configured-client','challenge',jwks)
    with pytest.raises(Exception):
        _verify_google_id_token(sign_jwt(claims,rsa.generate_private_key(public_exponent=65537,key_size=2048)),'configured-client','challenge',jwks)


def test_google_oauth_opt_in_state_nonce_and_independent_key(monkeypatch, tmp_path):
    """Mock Google transport; authenticating to external systems is NEVER test work."""
    import polyc.identity as mod
    monkeypatch.setenv('POLYC_GOOGLE_CLIENT_ID','test-client')
    monkeypatch.setenv('POLYC_GOOGLE_CLIENT_SECRET','test-secret')
    monkeypatch.setenv('POLYC_GOOGLE_REDIRECT_URI','http://localhost:8765/api/identity/google/callback')
    app=create_app(str(tmp_path/'google.db'),ADMIN)
    private=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    nums=private.public_key().public_numbers()
    jwks={'keys':[{'kid':'test','kty':'RSA','use':'sig',
       'n':_b64(nums.n.to_bytes((nums.n.bit_length()+7)//8,'big')),
       'e':_b64(nums.e.to_bytes((nums.e.bit_length()+7)//8,'big'))}]}
    calls=[]
    nonce_holder = {}
    class MockResponse:
        def __init__(self,data): self._data=data
        def raise_for_status(self): pass
        def json(self): return self._data
    class MockGoogleClient:
        def __init__(self,*a,**kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*a): pass
        async def post(self,url,data):
            calls.append(url)
            assert url == mod.GOOGLE_TOKEN
            assert data['grant_type']=='authorization_code'
            assert data['code_verifier']
            nonce=nonce_holder['nonce']
            claims={'iss':'https://accounts.google.com','aud':'test-client','nonce':nonce,
                    'iat':int(time.time()),'exp':int(time.time())+300,'sub':'test-google-sub',
                    'email':'private@example.invalid','name':'Do Not Record'}
            return MockResponse({'id_token':sign_jwt(claims,private)})
        async def get(self,url):
            calls.append(url)
            assert url == mod.GOOGLE_KEYS
            return MockResponse(jwks)
    monkeypatch.setattr(mod.httpx,'AsyncClient',MockGoogleClient)
    with TestClient(app,base_url='http://localhost:8765') as c:
        assert c.get('/api/identity/config').json()['google_enabled'] is True
        assert not calls  # merely exploring the site does not contact Google
        first=c.get('/api/identity/google/start',follow_redirects=False)
        assert first.status_code==303
        from urllib.parse import urlparse,parse_qs
        url=urlparse(first.headers['location'])
        query=parse_qs(url.query)
        assert url.hostname=='accounts.google.com'
        assert query['scope']==['openid']
        state=query['state'][0]
        nonce_holder['nonce'] = app.state.store.db.execute('SELECT nonce FROM identity_google_states').fetchone()['nonce']
        assert c.get('/api/identity/google/callback',params={'state':'attacker','code':'x'}).status_code==403
        callback=c.get('/api/identity/google/callback',params={'state':state,'code':'test-code'},follow_redirects=False)
        assert callback.status_code==303,callback.text
        assert len(calls)==2
        assert c.get('/api/identity/me').json()['login_methods']=={'independent_keys':0,'google_linked':True}
        actor=c.get('/api/identity/me').json()['identity']
        assert actor['id'].startswith('plc_')
        exported=c.get('/api/identity/export').json()
        assert exported['linked_providers']==[{'provider':'google','subject':'test-google-sub'}]
        assert 'private@example.invalid' not in json.dumps(exported)
        assert 'Do Not Record' not in json.dumps(exported)
        # Google is not required after the user explicitly attaches an independent key.
        key,pub=make_key()
        r=c.post('/api/identity/challenge',json={'purpose':'link-key','public_key':pub},headers={'Origin':'http://localhost:8765'})
        assert r.status_code==200,r.text
        proof=r.json();signature=key.sign(proof['message'].encode()).hex()
        assert c.post('/api/identity/prove',json={'challenge_id':proof['challenge_id'],'signature':signature},headers={'Origin':'http://localhost:8765'}).status_code==200
        assert c.delete('/api/identity/providers/google',headers={'Origin':'http://localhost:8765'}).status_code==200
        assert c.post('/api/identity/logout',json={},headers={'Origin':'http://localhost:8765'}).status_code==200
        r=c.post('/api/identity/challenge',json={'purpose':'login','public_key':pub},headers={'Origin':'http://localhost:8765'})
        proof=r.json();signature=key.sign(proof['message'].encode()).hex()
        assert c.post('/api/identity/prove',json={'challenge_id':proof['challenge_id'],'signature':signature},headers={'Origin':'http://localhost:8765'}).status_code==200
        assert c.get('/api/identity/me').json()['identity']['id']==actor['id']
    app.state.store.db.close()


def test_credential_changes_require_recent_login(identity):
    c,app=identity
    key,pub=make_key()
    p,sig=challenge(c,key,pub,'register');assert prove(c,p,sig).status_code==200
    with app.state.store.lock:
        app.state.store.db.execute('UPDATE identity_sessions SET created_at=?',(time.time()-700,))
    other,other_pub=make_key()
    assert c.post('/api/identity/challenge',json={'purpose':'link-key','public_key':other_pub},headers=ORIGIN).status_code==403
    account=c.get('/api/identity/me').json()['identity']['id']
    app.state.identities.provider_connect('google','another-google',account)
    assert c.delete('/api/identity/providers/google',headers=ORIGIN).status_code==403
    assert app.state.identities.provider_owner('google','another-google')==account
    # Ordinary account access remains possible; the credential change requires reauthentication.
    assert c.get('/api/identity/me').status_code==200
