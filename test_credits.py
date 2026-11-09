"""v0.3 credit accounting: no external payments; no tokens with real value."""
from __future__ import annotations
import copy
import time
import pytest
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives import serialization
from polyc.api import create_app
from polyc.crypto import canonical, create_keypair, sign_project
from polyc.credits import (CreditOffer, WalletEnrollment, WalletTerms, WalletAction,
                            CreditError, CreditLedger, TestCreditAsset)
from polyc.demo import constitution
from polyc.models import Project
from polyc.policy import policy_digest
from polyc.compute import compute_chain

ADMIN = 'M'*32
ROOT = {'Authorization':'Bearer '+ADMIN}
ASSET = 'polyc.compute.test.v1'


def key(tmp_path,name):
    private,public=tmp_path/(name+'.pem'),tmp_path/(name+'.pub')
    create_keypair(str(private),str(public))
    return private,public.read_text()


def sig(private, payload):
    k=serialization.load_pem_private_key(private.read_bytes(),password=None)
    return k.sign(canonical(payload)).hex()


def ok(r):
    assert r.status_code == 200, (r.status_code,r.text)
    return r.json()


@pytest.fixture
def econ(tmp_path):
    owner,owner_pub=key(tmp_path,'project')
    node1,node1_pub=key(tmp_path,'cat1')
    node2,node2_pub=key(tmp_path,'cat2')
    app=create_app(str(tmp_path/'economy.sqlite'),ADMIN)
    with TestClient(app) as client:
        assert client.get('/api/credits/audit').status_code == 401
        ok(client.post('/api/credits/assets',headers=ROOT,json={
            'asset_id':ASSET,'issuer_id':'pilot-coop',
            'description':'Unbacked test-only credits for verified CPU tasks',
            'max_supply':30}))
        ledger_id=ok(client.get('/api/credits/network'))['ledger_id']
        keys={'cat-one':(node1,node1_pub),'cat-two':(node2,node2_pub),
              'project-wallet':(owner,owner_pub)}
        cs={}
        for node_id in ('cat-one','cat-two'):
            priv,pub=keys[node_id]
            c=constitution(owner_pub,wallet_pubkey=pub)
            c['metadata']['name']=node_id
            cs[node_id]=c
            ok(client.post('/api/nodes',headers=ROOT,json={
                'node_id':node_id,'token':node_id+'-'+'t'*40,'constitution':c}))
        for wallet_id,(priv,pub) in keys.items():
            role='project' if wallet_id=='project-wallet' else 'node'
            e=WalletEnrollment(ledger_id=ledger_id,wallet_id=wallet_id,role=role,node_id=None if role=='project' else wallet_id,
                pubkey=pub,terms=WalletTerms(test_credit_disclaimer_accepted=True,accepted_assets=[ASSET],
                                                max_transfer_units=30))
            ok(client.post('/api/credits/wallets',headers=ROOT,json={
                'enrollment':e.model_dump(mode='json'),'signature':sig(priv,e.model_dump(mode='json'))}))
        def project(pid, tasks=2, paid=False):
            return sign_project(Project(project_id=pid,title='Cooperating cats',
                source_repo='https://example.org/cats',source_commit='f'*40,
                category='open_science',purposes=['open_knowledge'],
                financial={'model':'test_credits','asset_id':ASSET,'credits_per_verified_task':1} if paid else None,
                work={'tasks':tasks,'iterations':70,'seed':'gift'}),str(owner))
        def submit(pid,tasks=2,paid=False):
            return ok(client.post('/api/jobs',headers=ROOT,json=project(pid,tasks,paid).model_dump(mode='json')))
        def complete(pid,node_id='cat-one'):
            n=cs[node_id];token={'Authorization':'Bearer '+node_id+'-'+'t'*40}
            a=ok(client.post('/api/lease',headers=token,json={
                'node_id':node_id,'constitution_digest':policy_digest(n)}))['assignment']
            assert a is not None
            d=compute_chain('gift',a['task_index'],70)
            ok(client.post('/api/tasks/'+a['task_id']+'/complete',headers=token,json={
                'node_id':node_id,'lease_id':a['lease_id'],'digest':d,'duration_seconds':.02}))
            return a['task_id']
        def issue(task_id,pid='volunteer-kittens',wallet_id='cat-one'):
            return client.post('/api/credits/issue',headers=ROOT,json={
                'asset_id':ASSET,'project_id':pid,'task_id':task_id,'wallet_id':wallet_id})
        def wallet(wallet_id):
            return ok(client.get('/api/credits/wallets/'+wallet_id,headers=ROOT))
        def transfer(src,dst,units,transfer_id='cat-transfer-001',change=None):
            from polyc.credits import SignedCreditOffer, acceptance_payload
            sender=wallet(src);recipient=wallet(dst)
            offer=CreditOffer(ledger_id=ledger_id,transfer_id=transfer_id,asset_id=ASSET,from_wallet=src,to_wallet=dst,
                units=units,nonce=sender['next_nonce'],expires_at=int(time.time())+120,
                from_terms_sha256=sender['terms_digest'],to_terms_sha256=recipient['terms_digest'])
            packet={'offer':offer.model_dump(mode='json'),
                    'sender_signature':sig(keys[src][0],offer.model_dump(mode='json'))}
            packet['recipient_signature']=sig(keys[dst][0],acceptance_payload(SignedCreditOffer.model_validate(packet)))
            if change:
                change(packet)
            return client.post('/api/credits/transfers',json=packet),packet
        def action(kind,job_id,reservation_id,units, action_id, wallet_id='project-wallet'):
            a=WalletAction(ledger_id=ledger_id,action_id=action_id,kind=kind,wallet_id=wallet_id,job_id=job_id,
                reservation_id=reservation_id,asset_id=ASSET,units=units,
                nonce=wallet(wallet_id)['next_nonce'],expires_at=int(time.time())+120)
            return {'action':a.model_dump(mode='json'),'signature':sig(keys[wallet_id][0],a.model_dump(mode='json'))}
        yield locals()
    app.state.store.db.close()


def test_wallet_opt_in_and_signing_required(econ):
    c=econ['client'];priv,pub=econ['keys']['cat-one']
    wrong={'enrollment':{'ledger_id':econ['ledger_id'],'wallet_id':'intruder','role':'project','pubkey':pub,
            'terms':{'test_credit_disclaimer_accepted':True,'accepted_assets':[ASSET]}},
            'signature':'0'*128}
    assert c.post('/api/credits/wallets',headers=ROOT,json=wrong).status_code==409
    assert c.post('/api/credits/wallets',json=wrong).status_code==401
    assert econ['wallet']('cat-one')['next_nonce']==1
    supply=ok(c.get('/api/credits/assets/'+ASSET,headers=ROOT))
    assert supply['issued_units']==0 and supply['guaranteed_compute'] is False


def test_issue_requires_verified_work_once_and_uses_cap(econ):
    c=econ['client'];econ['submit']('volunteer-kittens')
    t1=econ['complete']('volunteer-kittens')
    result=ok(econ['issue'](t1))
    assert result['issued_units']==1
    assert econ['issue'](t1).status_code==409
    assert econ['issue'](t1,wallet_id='cat-two').status_code==409
    assert econ['wallet']('cat-one')['balances'][ASSET]==1
    audit=ok(c.get('/api/credits/audit',headers=ROOT))
    assert audit['valid_locally'] and audit['transaction_count']==1


def test_transfer_two_signatures_replay_overdraft_and_mutation(econ):
    econ['submit']('volunteer-kittens',tasks=3)
    for _ in range(3):
        ok(econ['issue'](econ['complete']('volunteer-kittens')))
    bad,payload=econ['transfer']('cat-one','project-wallet',4)
    assert bad.status_code==409 and 'insufficient' in bad.text
    tamper,packet=econ['transfer']('cat-one','project-wallet',2,change=lambda p:p['offer'].__setitem__('units',3))
    assert tamper.status_code==409 and 'signature' in tamper.text
    good,packet=econ['transfer']('cat-one','project-wallet',2)
    assert good.status_code==200,good.text
    assert econ['wallet']('cat-one')['balances'][ASSET]==1
    assert econ['wallet']('project-wallet')['balances'][ASSET]==2
    assert econ['client'].post('/api/credits/transfers',json=packet).status_code==409
    assert econ['wallet']('cat-one')['next_nonce']==2
    audit=ok(econ['client'].get('/api/credits/audit',headers=ROOT))
    assert audit['valid_locally']
    assert audit['transaction_count']==4


def test_credit_funded_job_requires_reservation_then_settles(econ):
    c=econ['client'];econ['submit']('volunteer-kittens',tasks=2)
    for _ in range(2):
        ok(econ['issue'](econ['complete']('volunteer-kittens')))
    ok(econ['transfer']('cat-one','project-wallet',2)[0])
    econ['submit']('paid-cats',tasks=2,paid=True)
    node={'Authorization':'Bearer cat-one-'+'t'*40}
    request={'node_id':'cat-one','constitution_digest':policy_digest(econ['cs']['cat-one'])}
    assert ok(c.post('/api/lease',headers=node,json=request))['assignment'] is None
    reservation=econ['action']('reserve','paid-cats','reserve-cats-001',2,'reserve-event-001')
    ok(c.post('/api/credits/reservations',json=reservation))
    assert econ['wallet']('project-wallet')['balances'][ASSET]==0
    assert c.post('/api/credits/reservations/reserve-cats-001/settle',headers=ROOT).status_code==409
    econ['complete']('paid-cats','cat-one')
    econ['complete']('paid-cats','cat-two')
    settlement=ok(c.post('/api/credits/reservations/reserve-cats-001/settle',headers=ROOT))
    assert settlement['credits_paid']==2 and settlement['refund_units']==0
    assert econ['wallet']('cat-one')['balances'][ASSET]==1
    assert econ['wallet']('cat-two')['balances'][ASSET]==1
    assert c.post('/api/credits/reservations/reserve-cats-001/settle',headers=ROOT).status_code==409
    assert ok(c.get('/api/credits/audit',headers=ROOT))['valid_locally']
    assert ok(c.get('/api/credits/assets/'+ASSET,headers=ROOT))['issued_units']==2


def test_release_refunds_unspent_and_preserves_earned(econ):
    c=econ['client'];econ['submit']('volunteer-kittens',tasks=3)
    for _ in range(3):
        ok(econ['issue'](econ['complete']('volunteer-kittens')))
    ok(econ['transfer']('cat-one','project-wallet',3)[0])
    econ['submit']('partpaid',tasks=3,paid=True)
    ok(c.post('/api/credits/reservations',json=econ['action'](
        'reserve','partpaid','part-reserve-001',3,'reserve-event-002')))
    econ['complete']('partpaid','cat-two')
    released=ok(c.post('/api/credits/reservations/release',json=econ['action'](
        'release','partpaid','part-reserve-001',3,'release-event-001')))
    assert released['credits_paid']==1 and released['refund_units']==2
    assert econ['wallet']('project-wallet')['balances'][ASSET]==2
    assert econ['wallet']('cat-two')['balances'][ASSET]==1
    assert c.get('/api/jobs/partpaid',headers=ROOT).json()['status']=='cancelled'
    assert c.post('/api/credits/reservations/release',json=econ['action'](
        'release','partpaid','part-reserve-001',3,'release-event-003')).status_code==409


def test_audit_detects_tampered_journal(econ):
    econ['submit']('volunteer-kittens')
    ok(econ['issue'](econ['complete']('volunteer-kittens')))
    with econ['app'].state.store.lock:
        econ['app'].state.store.db.execute('UPDATE credit_postings SET units=77 WHERE account_id=?',('cat-one',))
    audit=ok(econ['client'].get('/api/credits/audit',headers=ROOT))
    assert not audit['valid_locally']


def test_deny_revenue_conversion_and_unbacked_guarantees():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TestCreditAsset(asset_id=ASSET, issuer_id='pilot-coop',description='A real monetary guarantee',
                        max_supply=100, redeemable_for_fiat=True)
    with pytest.raises(ValidationError):
        TestCreditAsset(asset_id=ASSET, issuer_id='pilot-coop',description='A guarantee',
                        max_supply=100,guaranteed_compute=True)


def test_wallet_view_does_not_require_admin_token(econ):
    from polyc.credits import WalletViewRequest
    wallet_id='cat-one'
    priv,pub=econ['keys'][wallet_id]
    view=WalletViewRequest(ledger_id=econ['ledger_id'],wallet_id=wallet_id,expires_at=int(time.time())+90)
    payload=view.model_dump(mode='json')
    signed={'request':payload,'signature':sig(priv,payload)}
    result=ok(econ['client'].post('/api/credits/wallet-view',json=signed))
    assert result['wallet_id']==wallet_id and result['next_nonce']==1
    signed['signature']=sig(econ['keys']['cat-two'][0],payload)
    assert econ['client'].post('/api/credits/wallet-view',json=signed).status_code==409
    expired=WalletViewRequest(ledger_id=econ['ledger_id'],wallet_id=wallet_id,expires_at=int(time.time())-10)
    signed={'request':expired.model_dump(mode='json'), 'signature':sig(priv,expired.model_dump(mode='json'))}
    assert econ['client'].post('/api/credits/wallet-view',json=signed).status_code==409


def test_two_concurrent_spends_with_one_nonce_only_one_accepted(econ):
    from concurrent.futures import ThreadPoolExecutor
    from polyc.credits import SignedCreditOffer, acceptance_payload, AcceptedCreditTransfer
    econ['submit']('volunteer-kittens')
    t=econ['complete']('volunteer-kittens')
    ok(econ['issue'](t))
    wallet=econ['wallet']('cat-one')
    targets=['project-wallet','cat-two']
    payloads=[]
    for index,target_id in enumerate(targets):
        target=econ['wallet'](target_id)
        offer=CreditOffer(ledger_id=econ['ledger_id'],transfer_id=f'concurrent-{index}-test',asset_id=ASSET,
                          from_wallet='cat-one',to_wallet=target_id,units=1,nonce=1,
                          expires_at=int(time.time())+120,from_terms_sha256=wallet['terms_digest'],
                          to_terms_sha256=target['terms_digest'])
        unsigned={'offer':offer.model_dump(mode='json'),
                  'sender_signature':sig(econ['keys']['cat-one'][0],offer.model_dump(mode='json'))}
        unsigned['recipient_signature']=sig(econ['keys'][target_id][0],
            acceptance_payload(SignedCreditOffer.model_validate(unsigned)))
        payloads.append(AcceptedCreditTransfer.model_validate(unsigned))
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(econ['app'].state.store.credits.transfer,p) for p in payloads]
        results=[]
        for future in futures:
            try:
                results.append(future.result())
            except CreditError:
                results.append('rejected')
    assert len([r for r in results if isinstance(r,dict)])==1
    assert results.count('rejected')==1
    assert econ['wallet']('cat-one')['balances'][ASSET]==0
    assert econ['wallet']('project-wallet')['balances'][ASSET]+econ['wallet']('cat-two')['balances'][ASSET]==1
    assert econ['app'].state.store.credits.audit()['valid_locally']


def test_financial_revenue_disclosures_required_for_share():
    from pathlib import Path
    from polyc.submission import load_submission, Submission
    from pydantic import ValidationError
    root=Path(__file__).parents[1]/'projects'/'example-render'
    p=load_submission(root)
    assert p.polic.spec.financial_disclosure.real_payment_execution=='not_implemented'
    raw=p.model_dump(mode='json')
    raw['polic']['spec']['distribution']['mode']='revenue_share'
    raw['polic']['spec']['distribution']['credit_per_verified_task']=0
    raw['polic']['spec']['distribution']['revenue_basis']='gross_receipts'
    raw['polic']['spec']['distribution']['revenue_pool_percent']=20
    Submission.model_validate(raw)
    raw['polic']['spec']['financial_disclosure']=None
    with pytest.raises(ValidationError):
        Submission.model_validate(raw)


def test_economy_demo_proves_five_distinct_wallets():
    from polyc.economy_demo import run_economy_demo
    report=run_economy_demo()
    assert report['volunteer']['task_counts']['done']==25
    assert report['credit_funded']['task_counts']['done']==5
    assert len(report['credit_funded']['contributors'])==5
    assert report['supply']['issued_units']==25
    assert report['settlement']['credits_paid']==5
    assert report['audit']['valid_locally']


def test_credit_registry_survives_restart(tmp_path):
    from polyc.store import Store
    db=tmp_path/'persistent.sqlite'
    s=Store(str(db))
    s.credits.create_asset(TestCreditAsset(asset_id=ASSET,issuer_id='pilot-coop',
         description='Only for development and testing',max_supply=123))
    s.db.close()
    s=Store(str(db))
    assert s.credits.supply(ASSET)['max_supply']==123
    assert s.credits.audit()['valid_locally']
    s.db.close()


def test_provider_catalogue_has_no_live_money_actions(econ):
    r=ok(econ['client'].get('/api/finance/providers'))
    providers={provider['provider_id'] for provider in r['providers']}
    assert {'paypal','patreon','zelle_manual','other','bank_transfer_manual'} <= providers
    assert not r['automatic_money_movement']
    assert not r['actual_payouts']
    assert not any(p['automated_money_movement_available_here'] for p in r['providers'])


def test_cross_coordinator_replay_rejected(econ):
    from polyc.credits import WalletViewRequest
    c=econ['client']
    wrong_ledger='f'*64 if econ['ledger_id']!='f'*64 else 'e'*64
    own=econ['keys']['cat-one'][0]
    view=WalletViewRequest(ledger_id=wrong_ledger,wallet_id='cat-one',expires_at=int(time.time())+120)
    packet={'request':view.model_dump(mode='json'),'signature':sig(own,view.model_dump(mode='json'))}
    r=c.post('/api/credits/wallet-view',json=packet)
    assert r.status_code==409 and 'another ledger' in r.text


def test_v02_signed_submission_remains_valid_without_financial_disclosure(tmp_path):
    from pathlib import Path
    from polyc.submission import load_submission, Submission, SignedSubmission, verify_submission
    root=Path(__file__).parents[1]/'projects'/'example-render'
    raw=load_submission(root).model_dump(mode='json')
    raw['polic']['spec'].pop('financial_disclosure')
    private,pub=key(tmp_path,'legacy-owner')
    raw['polic']['spec']['project_owner_pubkey']=pub
    legacy_sig=sig(private,raw)
    signed=SignedSubmission(submission=Submission.model_validate(raw),signer_pubkey=pub,signature=legacy_sig)
    assert verify_submission(signed)


def test_credit_ledger_id_stable_after_db_restart(tmp_path):
    from polyc.store import Store
    db=tmp_path/'stable-ledger.sqlite'
    first=Store(str(db))
    old=first.credits.ledger_id
    first.db.close()
    second=Store(str(db))
    assert second.credits.ledger_id == old
    second.db.close()
