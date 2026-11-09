"""The browser is a second worker type, NOT a bypass of the signed pilot protocol."""
import secrets
from tests.conftest import ADMIN
from polyc.compute import compute_chain
from polyc.demo import constitution
from polyc.policy import policy_digest

ROOT={'Authorization':f'Bearer {ADMIN}'}


def invite(client,kind,count=1):
    r=client.post('/api/catnap/invitations',headers=ROOT,json={'kind':kind,'count':count,'ttl_seconds':3600})
    assert r.status_code==200,r.text
    return r.json()['invitations']


def test_web_assets_and_preview_is_not_a_public_data_leak(setup):
    client,app,*_=setup
    r=client.get('/')
    assert r.status_code==200 and 'Create a Cat' in r.text
    assert "default-src 'none'" in r.headers['content-security-policy']
    assert client.get('/web/app.js').status_code==200
    assert client.get('/web/scenes/gibson.js').status_code==200
    assert client.get('/api/catnap/snapshot').status_code==401
    assert client.get('/api/catnap/snapshot?node_id=cat-one').status_code==401
    data=client.get('/api/catnap/snapshot',headers=ROOT).json()
    assert data['mode']=='live' and data['scope']=='operator'
    assert len(data['nodes'])==1
    assert 'token_digest' not in str(data)
    assert 'trusted_signers' not in str(data)


def test_one_use_owner_enrollment_and_policy_constraints(setup):
    client,app,c,sign,pub=setup
    ticket=invite(client,'catnap')[0]
    c=constitution(pub)
    payload={'invitation':ticket,'node':{'node_id':'browser-one','token':'b'*32,'constitution':c}}
    r=client.post('/api/catnap/enroll',json=payload)
    assert r.status_code==200,r.text
    assert client.post('/api/catnap/enroll',json={**payload,'node':{**payload['node'],'node_id':'browser-two'}}).status_code==403
    assert client.get('/api/catnap/snapshot?node_id=browser-one',headers={'Authorization':'Bearer '+'b'*32}).status_code==200
    assert client.get('/api/catnap/snapshot?node_id=cat-one',headers={'Authorization':'Bearer '+'b'*32}).status_code==403
    temp=constitution(pub,cpu_sensor_required=True)
    bad=client.post('/api/catnap/enroll',json={'invitation':invite(client,'catnap')[0],
        'node':{'node_id':'browser-hot','token':'h'*32,'constitution':temp}})
    assert bad.status_code==422 and 'temperature' in bad.text
    # Empty trust is a safe, idle constitution: visitor can enroll before any Cat is approved.
    no_trust=constitution(pub)
    no_trust['spec']['trust']['trusted_signers']=[]
    assert client.post('/api/catnap/enroll',json={'invitation':invite(client,'catnap')[0],
        'node':{'node_id':'no-trust','token':'s'*32,'constitution':no_trust}}).status_code==200


def test_create_cat_operator_review_and_contributor_consent(setup):
    client,app,c,sign,pub=setup
    signed=sign(project_id='community-cat',category='open_science')
    key=invite(client,'create_cat')[0]
    r=client.post('/api/workshop/cats',json={'invitation':key,'signed_project':signed.model_dump(mode='json')})
    assert r.status_code==200,r.text
    assert r.json()['executable'] is False
    assert app.state.store.job_summary('community-cat') is None
    assert client.get('/api/workshop/cats').status_code==401
    assert len(client.get('/api/workshop/cats',headers=ROOT).json()['cats'])==1
    assert client.post('/api/workshop/cats',json={'invitation':key,'signed_project':signed.model_dump(mode='json')}).status_code==403
    changed=signed.model_dump(mode='json');changed['project']['commercial']=True
    other=invite(client,'create_cat')[0]
    assert client.post('/api/workshop/cats',json={'invitation':other,'signed_project':changed}).status_code==422
    # Invalid signature must not redeem an invitation.
    assert client.post('/api/workshop/cats',json={'invitation':other,'signed_project':signed.model_dump(mode='json')}).status_code==409
    assert client.post('/api/workshop/cats/community-cat/review',json={'approve':True}).status_code==401
    review=client.post('/api/workshop/cats/community-cat/review',headers=ROOT,json={'approve':True,'note':'Reviewed pilot'})
    assert review.status_code==200,review.text
    assert app.state.store.job_summary('community-cat')['status']=='open'
    assert client.post('/api/workshop/cats/community-cat/review',headers=ROOT,json={'approve':True}).status_code==409
    # Node that previously opted in to the creator is eligible.
    lease=client.post('/api/lease',headers={'Authorization':'Bearer '+'n'*32},json={'node_id':'cat-one','constitution_digest':policy_digest(c)})
    assert lease.status_code==200 and lease.json()['assignment']['task_id'].startswith('community-cat-')


def test_five_browser_enrollments_and_real_telemetry(setup):
    client,app,c,sign,pub=setup
    tickets=invite(client,'catnap',5)
    policies=[]
    for i,ticket in enumerate(tickets):
        n=constitution(pub)
        n['metadata']['name']=f'browser-{i}'
        policies.append(n)
        result=client.post('/api/catnap/enroll',json={'invitation':ticket,'node':{
            'node_id':f'browser-{i}', 'token':str(i)*32,'constitution':n}})
        assert result.status_code==200,result.text
    signed=sign(project_id='five-web-cats')
    assert client.post('/api/jobs',headers=ROOT,json=signed.model_dump(mode='json')).status_code==200
    for i in range(5):
        node=f'browser-{i}'
        auth={'Authorization':f'Bearer {str(i)*32}'}
        lease=client.post('/api/lease',headers=auth,json={'node_id':node,
            'constitution_digest':policy_digest(policies[i])}).json()['assignment']
        # Only two demo tasks exist, so later participants legitimately remain idle.
        if lease:
            digest=compute_chain('cat',lease['task_index'],100)
            assert client.post(f"/api/tasks/{lease['task_id']}/complete",headers=auth,json={
                'node_id':node,'lease_id':lease['lease_id'],'digest':digest,'duration_seconds':.01}).status_code==200
    live=client.get('/api/catnap/snapshot',headers=ROOT).json()
    assert live['counts']['nodes']==6
    assert live['counts']['done']==2
    assert len(live['projects'])==1
    assert any(e['kind']=='task_completed' for e in live['events'])
    own=client.get('/api/catnap/snapshot?node_id=browser-0',headers={'Authorization':'Bearer '+'0'*32}).json()
    assert len(own['nodes'])==1 and own['nodes'][0]['id']=='browser-0'
    assert all(e['node_id']=='browser-0' for e in own['events'])
    assert 'n'*32 not in str(own) and '0'*32 not in str(own)


def test_browser_webcrypto_created_cat_is_accepted_by_python_coordinator(setup):
    import json, shutil, subprocess
    from pathlib import Path
    import pytest
    from polyc.models import SignedProject
    from polyc.crypto import verify_project
    if not shutil.which('node'):
        pytest.skip('Node.js is optional; browser Web Crypto interop test skipped')
    r=subprocess.run(['node','scripts/test-browser-protocol.mjs'],capture_output=True,text=True,timeout=20)
    assert r.returncode==0,r.stderr
    signed=SignedProject.model_validate(json.loads(Path('/tmp/polic-js-signed.json').read_text()))
    assert verify_project(signed,[signed.signer_pubkey])
    client,app,c,sign,_=setup
    ticket=invite(client,'create_cat')[0]
    response=client.post('/api/workshop/cats',json={'invitation':ticket,
        'signed_project':signed.model_dump(mode='json')})
    assert response.status_code==200,response.text
    assert client.post('/api/workshop/cats/web-cat-test/review',headers=ROOT,
        json={'approve':True,'note':'Cross-language verified'}).status_code==200
    owner=constitution(signed.signer_pubkey)
    assert client.post('/api/catnap/enroll',json={'invitation':invite(client,'catnap')[0],
        'node':{'node_id':'browser-js','token':'j'*32,'constitution':owner}}).status_code==200
    lease=client.post('/api/lease',headers={'Authorization':'Bearer '+'j'*32},json={
        'node_id':'browser-js','constitution_digest':policy_digest(owner)}).json()['assignment']
    assert lease and lease['signed_project']['signer_pubkey']==signed.signer_pubkey
    digest_result=compute_chain('cat',lease['task_index'],100)
    assert client.post(f"/api/tasks/{lease['task_id']}/complete",
        headers={'Authorization':'Bearer '+'j'*32},json={'node_id':'browser-js',
            'lease_id':lease['lease_id'],'digest':digest_result,'duration_seconds':.1}).status_code==200


def test_guest_constitution_editor_fields_and_eligibility(setup):
    client, app, c, sign, pub = setup
    html = client.get('/').text
    js = client.get('/web/app.js').text
    for name in ('categoryScience', 'categoryClimate', 'categoryMedia',
                 'allowCommercial', 'excludedPurposes', 'taskSeconds',
                 'sessionMinutes', 'browserConsent', 'previewPolicBtn', 'exportPolicBtn'):
        assert f'id="{name}"' in html
    assert 'async function draftPolic()' in js
    assert 'state.sessionDeadline' in js
    # A restrictive constitutional configuration is accepted and applied to leases.
    custom = constitution(pub)
    custom['spec']['content']['allow_categories'] = ['climate_research']
    custom['spec']['ethos']['exclude_projects_with_declared_purposes'].append('targeted_advertising')
    custom['spec']['nice_plus']['cpu_percent_max'] = 10
    custom['spec']['nice_plus']['task_runtime_seconds_max'] = 5
    node = {'node_id': 'restricted-browser', 'token': 'r'*32, 'constitution': custom}
    assert client.post('/api/catnap/enroll', json={
        'invitation': invite(client, 'catnap')[0], 'node': node}).status_code == 200
    cat = sign(project_id='research-not-approved', category='open_science')
    assert client.post('/api/jobs', headers=ROOT, json=cat.model_dump(mode='json')).status_code == 200
    lease = client.post('/api/lease', headers={'Authorization': 'Bearer ' + 'r'*32},
        json={'node_id': node['node_id'], 'constitution_digest': policy_digest(custom)})
    assert lease.status_code == 200
    assert lease.json()['assignment'] is None


def test_polic_editor_buttons_and_visible_validation(setup):
    client, *_ = setup
    html = client.get('/').text
    js_response = client.get('/web/app.js')
    css_response = client.get('/web/style.css')
    js = js_response.text
    assert '>Preview My PoliC</button>' in html
    assert '>Export PoliC JSON</button>' in html
    assert '>Enroll in Catnap</button>' in html
    for widget in ('policActionNotice', 'enrollmentNotice', 'policEditorReady'):
        assert f'id="{widget}"' in html
    assert 'const c=await draftPolic();' in js
    assert "message('policActionNotice'" in js
    assert "message('enrollmentNotice'" in js
    assert 'This Commons requires a one-use invitation' in js
    assert js_response.headers['cache-control'] == 'no-store'
    assert css_response.headers['cache-control'] == 'no-store'
