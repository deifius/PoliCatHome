"""OCI intake is deliberately staging-only; executable pilot remains unchanged."""
from pathlib import Path
import copy
import json
import pytest
from pydantic import ValidationError
from tests.conftest import ADMIN
from polyc.submission import (load_submission, sign_submission, verify_submission,
                              submission_digest, Submission)
from polyc.compute import compute_chain
from polyc.policy import policy_digest

EXAMPLE = Path(__file__).parents[1] / 'projects' / 'example-render'
ROOT = {'Authorization': 'Bearer '+ADMIN}
NODE = {'Authorization': 'Bearer '+'n'*32}


def project_with_owner_key(tmp_path):
    from polyc.crypto import create_keypair
    private, public = tmp_path/'owner.pem', tmp_path/'owner.pub'
    create_keypair(str(private),str(public))
    p = load_submission(EXAMPLE).model_dump(mode='json')
    p['polic']['spec']['project_owner_pubkey'] = public.read_text()
    return Submission.model_validate(p), private


def test_submit_schema_and_signed_contract(tmp_path):
    submission, private=project_with_owner_key(tmp_path)
    assert submission.manifest.artifact.image.endswith('a'*64)
    signed=sign_submission(submission,str(private))
    assert verify_submission(signed)
    assert submission_digest(submission)==submission_digest(signed.submission)
    changed=signed.model_copy(deep=True)
    changed.submission.polic.spec.distribution.credit_per_verified_task=10
    assert not verify_submission(changed)
    changed=signed.model_copy(deep=True)
    changed.submission.manifest.execution.task_count=99
    assert not verify_submission(changed)


def test_nonimmutable_images_and_revisions_rejected(tmp_path):
    sample,_=project_with_owner_key(tmp_path)
    data=sample.model_dump(mode='json')
    data['manifest']['artifact']['image']='registry.example.org/foo/render:latest'
    with pytest.raises(ValidationError):
        Submission.model_validate(data)
    data=sample.model_dump(mode='json')
    data['polic']['metadata']['revision']=2
    with pytest.raises(ValidationError):
        Submission.model_validate(data)
    data=sample.model_dump(mode='json')
    data['polic']['spec']['distribution']['mode']='revenue_share'
    with pytest.raises(ValidationError):
        Submission.model_validate(data)
    data=sample.model_dump(mode='json')
    data['manifest']['execution']['network']='host'
    with pytest.raises(ValidationError):
        Submission.model_validate(data)


def test_stage_api_not_job_execution(setup,tmp_path):
    client,app,_,_,_=setup
    submission,private=project_with_owner_key(tmp_path)
    signed=sign_submission(submission,str(private)).model_dump(mode='json')
    assert client.post('/api/submissions',json=signed).status_code == 401
    posted=client.post('/api/submissions',headers=ROOT,json=signed)
    assert posted.status_code==200,posted.text
    assert posted.json()['state']=='staged'
    assert posted.json()['executable'] is False
    assert client.post('/api/submissions',headers=ROOT,json=signed).status_code==409
    response=client.get('/api/submissions/community-render-demo/1',headers=ROOT)
    assert response.status_code==200 and response.json()['state']=='staged'
    assert client.get('/api/jobs/community-render-demo',headers=ROOT).status_code==404
    assert app.state.store.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]==0
    tampered=copy.deepcopy(signed)
    tampered['submission']['polic']['spec']['purpose']['summary']='Tampered project statement'
    assert client.post('/api/submissions',headers=ROOT,json=tampered).status_code==422


def test_coordinator_receipt_ledger_and_chain_tamper(setup):
    client,app,c,sign,_=setup
    assert client.post('/api/jobs',headers=ROOT,json=sign().model_dump(mode='json')).status_code==200
    for _ in range(2):
        assignment=client.post('/api/lease',headers=NODE,json={'node_id':'cat-one',
                          'constitution_digest':policy_digest(c)}).json()['assignment']
        assert assignment is not None
        digest=compute_chain('cat',assignment['task_index'],100)
        result={'node_id':'cat-one','lease_id':assignment['lease_id'],'digest':digest,'duration_seconds':.12}
        assert client.post(f'/api/tasks/{assignment["task_id"]}/complete',headers=NODE,json=result).status_code==200
    ledger=client.get('/api/ledger/cat-math',headers=ROOT).json()
    assert ledger['chain_valid_locally'] is True
    assert ledger['credits_provisional']==2
    assert len(ledger['receipts'])==2
    assert ledger['externally_anchored'] is False
    assert ledger['monetary_settlement']=='not_implemented'
    assert client.get('/api/ledger/cat-math').status_code==401
    with app.state.store.lock:
        app.state.store.db.execute('UPDATE contribution_receipts SET receipt_sha256=? WHERE project_id=? AND seq=1',('f'*64,'cat-math'))
    assert client.get('/api/ledger/cat-math',headers=ROOT).json()['chain_valid_locally'] is False


def test_project_policy_and_node_policy_mutual_consent(setup,tmp_path):
    from polyc.submission import submission_compatibility
    _,_,node,_,_=setup
    submission,private=project_with_owner_key(tmp_path)
    signer=sign_submission(submission,str(private)).signer_pubkey
    node['spec']['content']['allow_categories'].append('creative_rendering')
    node['spec']['trust']['trusted_signers'].append(signer)
    assert submission_compatibility(submission,node,'cat-one')==[]
    submission.polic.spec.participation.excluded_node_ids.append('cat-one')
    assert 'project explicitly excludes this contributor' in submission_compatibility(submission,node,'cat-one')
    submission.polic.spec.participation.excluded_node_ids.clear()
    submission.polic.spec.participation.eligible_jurisdictions=['FI']
    assert 'project jurisdiction rule lacks matching verified jurisdiction' in submission_compatibility(submission,node,'cat-one')
    assert submission_compatibility(submission,node,'cat-one',verified_jurisdiction='FI')==[]
    node['spec']['ethos']['exclude_projects_with_declared_purposes'].append('open_animation')
    assert 'declared purpose conflicts with node ethos' in submission_compatibility(submission,node,'cat-one',verified_jurisdiction='FI')
