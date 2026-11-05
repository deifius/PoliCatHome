import time
from tests.conftest import ADMIN
from polyc.policy import policy_digest
from polyc.compute import compute_chain

ROOT={'Authorization':'Bearer '+ADMIN}
NODE={'Authorization':'Bearer '+'n'*32}


def submit(client, sign, **kwargs):
    return client.post('/api/jobs',headers=ROOT,json=sign(**kwargs).model_dump(mode='json'))


def lease(client, c):
    return client.post('/api/lease',headers=NODE,json={'node_id':'cat-one','constitution_digest':policy_digest(c)})


def test_auth_and_consent_gate(setup):
    client, _, c, sign, _ = setup
    assert client.post('/api/jobs',json=sign().model_dump(mode='json')).status_code == 401
    assert submit(client,sign).status_code == 200
    assert lease(client,c).json()['assignment']['task_index'] == 0
    assert client.post('/api/lease',headers=NODE,json={'node_id':'cat-one','constitution_digest':'bad'}).status_code == 409
    assert client.post('/api/lease',headers={'Authorization':'Bearer wrong'},json={'node_id':'cat-one','constitution_digest':policy_digest(c)}).status_code == 403


def test_no_incompatible_work_ever_leased(setup):
    client, _, c, sign, _ = setup
    assert submit(client,sign,category='not_approved').status_code == 200
    assert lease(client,c).json()['assignment'] is None


def test_signed_manifest_rejected_if_modified(setup):
    client, _, _, sign, _ = setup
    sp=sign().model_dump(mode='json')
    sp['project']['commercial']=True
    r=client.post('/api/jobs',headers=ROOT,json=sp)
    assert r.status_code == 422


def test_result_provenance_and_chronicle(setup):
    client, _, c, sign, _ = setup
    assert submit(client,sign).status_code == 200
    assignment=lease(client,c).json()['assignment']
    task=assignment['task_id']
    digest=compute_chain('cat',assignment['task_index'],100)
    result={'node_id':'cat-one','lease_id':assignment['lease_id'],'digest':digest,'duration_seconds':.1}
    bad=client.post(f'/api/tasks/{task}/complete',headers=NODE,json={**result,'lease_id':'wrong'})
    assert bad.status_code==409
    forged=client.post(f'/api/tasks/{task}/complete',headers=NODE,json={**result,'digest':'0'*64})
    assert forged.status_code==409
    assert client.post(f'/api/tasks/{task}/complete',headers=NODE,json=result).status_code==200
    assert client.post(f'/api/tasks/{task}/complete',headers=NODE,json=result).status_code==409
    report=client.get('/api/chronicle/cat-one',headers=NODE)
    assert report.status_code==200
    assert report.json()['projects'][0]['tasks']==1
    assert client.get('/api/chronicle/cat-one',headers={'Authorization':'Bearer none'}).status_code==403
    metrics=client.get('/metrics',headers=ROOT).text
    assert 'polyc_tasks{state="done"} 1' in metrics


def test_owner_revoke_and_project_cancel(setup):
    client, _, c, sign, _ = setup
    assert submit(client,sign).status_code==200
    a=lease(client,c).json()['assignment']
    assert client.post('/api/nodes/cat-one/revoke',headers=NODE).status_code==200
    assert client.post('/api/lease',headers=NODE,json={'node_id':'cat-one','constitution_digest':policy_digest(c)}).status_code==403
    assert client.post(f'/api/tasks/{a["task_id"]}/complete',headers=NODE,json={
        'node_id':'cat-one','lease_id':a['lease_id'],'digest':'a'*64,'duration_seconds':1}).status_code==403
    assert client.post('/api/jobs/cat-math/cancel',headers=ROOT).status_code==200
    assert client.get('/api/jobs/cat-math',headers=ROOT).json()['status']=='cancelled'


def test_lease_expiry_requeues(setup):
    client, app, c, sign, _ = setup
    assert submit(client,sign).status_code==200
    a=lease(client,c).json()['assignment']
    with app.state.store.lock:
        app.state.store.db.execute('UPDATE tasks SET lease_until=? WHERE id=?',(time.time()-1,a['task_id']))
    other=lease(client,c).json()['assignment']
    assert other['task_id']==a['task_id']
    assert other['lease_id']!=a['lease_id']
