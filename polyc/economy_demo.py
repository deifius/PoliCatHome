"""An entirely local, test-only five-owner credit experiment. No cash, no Docker."""
from __future__ import annotations
import argparse
import json
import secrets
import tempfile
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from .api import create_app
from .crypto import canonical, create_keypair, sign_project
from .credits import CreditOffer, WalletAction
from .demo import constitution
from .models import Project
from .compute import compute_chain
from .policy import policy_digest

ASSET='polyc.compute.test.v1'


def _signature(private_path, payload):
    key=serialization.load_pem_private_key(Path(private_path).read_bytes(),password=None)
    return key.sign(canonical(payload)).hex()


def run_economy_demo(workdir=None) -> dict:
    """Five independent identities, 25 volunteer credits, transfers, funded settlement."""
    temporary = tempfile.TemporaryDirectory(prefix='polyc-economy-') if workdir is None else None
    root=Path(temporary.name if temporary else workdir)
    root.mkdir(parents=True,exist_ok=True)
    root.chmod(0o700)  # demo stores private signing keys here
    if list(root.glob('*')):
        raise ValueError('economy demo requires an empty workdir')
    secret=secrets.token_urlsafe(32)
    db=root/'economy.sqlite'
    app=create_app(str(db),secret)
    root_auth={'Authorization':'Bearer '+secret}
    def priv_key(label):
        keyfile=root/(label+'.pem')
        pubfile=root/(label+'.pub')
        create_keypair(str(keyfile),str(pubfile))
        return keyfile,pubfile.read_text()
    try:
        with TestClient(app) as client:
            def send(path, body, headers=None):
                r=client.post(path,json=body,headers=headers)
                if r.status_code!=200:
                    raise RuntimeError(f'{path}: {r.status_code} {r.text}')
                return r.json()
            def get(path):
                r=client.get(path,headers=root_auth)
                r.raise_for_status()
                return r.json()
            ledger_id=get('/api/credits/network')['ledger_id']
            project_priv,project_pub=priv_key('film-maker')
            keys={'project-wallet':(project_priv,project_pub)}
            node_consts={}
            for n in range(1,6):
                node_id=f'cat-{n}'
                keys[node_id]=priv_key(node_id)
                c=constitution(project_pub,wallet_pubkey=keys[node_id][1])
                c['metadata']['name']=node_id
                node_consts[node_id]=c
            send('/api/credits/assets',{'asset_id':ASSET,'issuer_id':'pilot-coop',
                 'description':'Unbacked and nonmonetary test-only compute credits',
                 'max_supply':25},root_auth)
            from .credits import WalletEnrollment, WalletTerms
            for node_id,c in node_consts.items():
                send('/api/nodes',{'node_id':node_id,'token':node_id+'-'+('x'*32),
                                   'constitution':c},root_auth)
            for wallet_id,(private,pub) in keys.items():
                role='project' if wallet_id=='project-wallet' else 'node'
                e=WalletEnrollment(ledger_id=ledger_id,wallet_id=wallet_id,role=role,node_id=wallet_id if role=='node' else None,
                    pubkey=pub,terms=WalletTerms(test_credit_disclaimer_accepted=True,
                                                accepted_assets=[ASSET], max_transfer_units=25))
                body=e.model_dump(mode='json')
                send('/api/credits/wallets',{'enrollment':body,'signature':_signature(private,body)},root_auth)
            def signed_project(project_id, tasks, paid):
                return sign_project(Project(project_id=project_id,title='The cats cooperate',
                    source_repo='https://example.org/learning', source_commit='e'*40,
                    category='open_science',purposes=['open_knowledge'],
                    financial={'model':'test_credits','asset_id':ASSET,'credits_per_verified_task':1} if paid else None,
                    work={'tasks':tasks,'iterations':70,'seed':'purring'}),str(project_priv))
            def work_one(node_id):
                authorization={'Authorization':'Bearer '+node_id+'-'+('x'*32)}
                assignment=send('/api/lease',{'node_id':node_id,
                                  'constitution_digest':policy_digest(node_consts[node_id])},authorization)['assignment']
                if not assignment:
                    raise RuntimeError('expected task for '+node_id)
                sha=compute_chain('purring',assignment['task_index'],70)
                send('/api/tasks/'+assignment['task_id']+'/complete',{
                    'node_id':node_id,'lease_id':assignment['lease_id'],'digest':sha,'duration_seconds':.01},authorization)
                return assignment['task_id']
            send('/api/jobs',signed_project('volunteer-cats',25,False).model_dump(mode='json'),root_auth)
            for _ in range(5):
                for i in range(1,6):
                    node_id=f'cat-{i}'
                    task=work_one(node_id)
                    send('/api/credits/issue',{'asset_id':ASSET,'project_id':'volunteer-cats',
                                               'task_id':task,'wallet_id':node_id},root_auth)
            balances_before={name:get('/api/credits/wallets/'+name)['balances'][ASSET] for name in keys}
            from .credits import SignedCreditOffer, acceptance_payload
            for i in range(1,6):
                wallet_id=f'cat-{i}'
                sender=get('/api/credits/wallets/'+wallet_id)
                target=get('/api/credits/wallets/project-wallet')
                offer=CreditOffer(ledger_id=ledger_id,transfer_id=f'five-cats-transfer-{i}',asset_id=ASSET,
                    from_wallet=wallet_id,to_wallet='project-wallet',units=1,
                    nonce=sender['next_nonce'],expires_at=int(time.time())+120,
                    from_terms_sha256=sender['terms_digest'],to_terms_sha256=target['terms_digest'])
                body={'offer':offer.model_dump(mode='json'),
                      'sender_signature':_signature(keys[wallet_id][0],offer.model_dump(mode='json'))}
                body['recipient_signature']=_signature(project_priv,
                                                       acceptance_payload(SignedCreditOffer.model_validate(body)))
                send('/api/credits/transfers',body)
            send('/api/jobs',signed_project('paid-cat-work',5,True).model_dump(mode='json'),root_auth)
            a=WalletAction(ledger_id=ledger_id,action_id='five-cats-budget-1',kind='reserve',wallet_id='project-wallet',
                 job_id='paid-cat-work',reservation_id='five-cats-reservation',asset_id=ASSET,
                 units=5,nonce=get('/api/credits/wallets/project-wallet')['next_nonce'],
                 expires_at=int(time.time())+120)
            send('/api/credits/reservations',{'action':a.model_dump(mode='json'),
                  'signature':_signature(project_priv,a.model_dump(mode='json'))})
            for i in range(1,6):
                work_one(f'cat-{i}')
            settled=send('/api/credits/reservations/five-cats-reservation/settle',{},root_auth)
            balances_after={name:get('/api/credits/wallets/'+name)['balances'][ASSET] for name in keys}
            audit=get('/api/credits/audit')
            report={'test_only':True,'no_money_or_compute_entitlement':True,
                    'volunteer':get('/api/jobs/volunteer-cats'),
                    'credit_funded':get('/api/jobs/paid-cat-work'),
                    'balances_after_volunteering':balances_before,
                    'balances_after_settlement':balances_after,
                    'settlement':settled,'supply':get('/api/credits/assets/'+ASSET),
                    'audit':audit}
            assert report['volunteer']['task_counts']['done']==25
            assert report['credit_funded']['task_counts']['done']==5
            assert len(report['volunteer']['contributors'])==5
            assert len(report['credit_funded']['contributors'])==5
            assert all(balances_before[f'cat-{i}']==5 for i in range(1,6))
            assert all(balances_after[f'cat-{i}']==5 for i in range(1,6))
            assert balances_after['project-wallet']==0
            assert report['supply']['issued_units']==25 and report['audit']['valid_locally']
            (root/'public-demo-report.json').write_text(json.dumps(report,indent=2)+'\n')
            return report
    finally:
        app.state.store.db.close()
        if temporary:
            temporary.cleanup()


def main():
    parser=argparse.ArgumentParser(description='Five-cat test-credit simulation (no real money or transferable entitlement)')
    parser.add_argument('--workdir',help='empty private directory for SQLite and signing keys')
    args=parser.parse_args()
    result=run_economy_demo(args.workdir)
    print(json.dumps({'completed_volunteer_tasks':result['volunteer']['task_counts']['done'],
           'completed_paid_test_tasks':result['credit_funded']['task_counts']['done'],
           'contributing_nodes':len(result['credit_funded']['contributors']),
           'credits_issued':result['supply']['issued_units'],
           'settled_credits':result['settlement']['credits_paid'],
           'wallet_balances':result['balances_after_settlement'],
           'audit_valid_locally':result['audit']['valid_locally'],
           'no_monetary_value':True},indent=2))


if __name__=='__main__':
    main()
