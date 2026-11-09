"""Pilot credit CLI. Keys remain on the owner's machine; no payment credentials."""
from __future__ import annotations
import json
import secrets
import time
from pathlib import Path
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import canonical
from .credits import (CreditOffer, WalletAction, WalletEnrollment, WalletTerms,
                      SignedCreditOffer, AcceptedCreditTransfer, SignedWalletAction,
                      acceptance_payload, WalletViewRequest)

SERVER = 'http://127.0.0.1:8765'
ASSET = 'polyc.compute.test.v1'


def add_parser(sub):
    def parser(name,desc,server=False,admin=False):
        p=sub.add_parser(name,help=desc)
        if server:
            p.add_argument('--server',default=SERVER)
        if admin:
            p.add_argument('--admin-token-file',required=True)
        return p
    parser('credit-network', 'print stable credit-ledger identity to bind all signed requests', True)
    p=parser('credit-asset', 'operator registers noncash, unbacked test asset',True,True)
    p.add_argument('--asset-id',default=ASSET)
    p.add_argument('--issuer-id',default='pilot-coop')
    p.add_argument('--description',default='No cash value or compute guarantee: test credits only')
    p.add_argument('--max-supply',type=int,required=True)

    p=parser('credit-enroll-sign','owner signs own opt-in wallet enrollment')
    p.add_argument('--wallet-id',required=True)
    p.add_argument('--ledger-id',required=True,help='from credit-network; never sign for an unknown ledger')
    p.add_argument('--role',required=True,choices=('node','project'))
    p.add_argument('--node-id')
    p.add_argument('--asset-id',default=ASSET)
    p.add_argument('--private',required=True)
    p.add_argument('--max-transfer',type=int,default=1000)
    p.add_argument('--out',required=True)

    p=parser('credit-enroll-submit','operator registers signed wallet enrollment',True,True)
    p.add_argument('--signed',required=True)

    p=parser('credit-issue','operator mints one unbacked TEST unit per verified volunteer task',True,True)
    p.add_argument('--asset-id',default=ASSET)
    p.add_argument('--project-id',required=True)
    p.add_argument('--task-id',required=True)
    p.add_argument('--wallet-id',required=True)

    p=parser('credit-wallet','owner views own wallet using private-key proof, or administrator token',True)
    p.add_argument('--wallet-id',required=True)
    p.add_argument('--private',help='owner Ed25519 key; no admin credentials required')
    p.add_argument('--admin-token-file',help='operator alternative')

    p=parser('credit-offer','sender signs a bilateral transfer offer')
    p.add_argument('--ledger-id',required=True)
    p.add_argument('--from-wallet',required=True)
    p.add_argument('--to-wallet',required=True)
    p.add_argument('--asset-id',default=ASSET)
    p.add_argument('--units',type=int,required=True)
    p.add_argument('--nonce',type=int,required=True)
    p.add_argument('--sender-terms-sha',required=True)
    p.add_argument('--recipient-terms-sha',required=True)
    p.add_argument('--private',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--memo',default='')

    p=parser('credit-accept','recipient signs the exact offer without modifying it')
    p.add_argument('--offer',required=True)
    p.add_argument('--private',required=True)
    p.add_argument('--out',required=True)

    p=parser('credit-send','submit mutually signed test-credit transfer',True)
    p.add_argument('--accepted',required=True)

    for action in ('reserve','release'):
        p=parser('credit-'+action,'sign a '+action+' of project test-credit budget')
        p.add_argument('--ledger-id',required=True)
        p.add_argument('--wallet-id',required=True)
        p.add_argument('--job-id',required=True)
        p.add_argument('--reservation-id',required=True)
        p.add_argument('--asset-id',default=ASSET)
        p.add_argument('--units',type=int,required=True)
        p.add_argument('--nonce',type=int,required=True)
        p.add_argument('--private',required=True)
        p.add_argument('--out',required=True)

    p=parser('credit-action-submit','submit signed reserve/release action',True)
    p.add_argument('--signed',required=True)
    p=parser('credit-settle','operator pays out verified completed test work',True,True)
    p.add_argument('--reservation-id',required=True)
    parser('credit-audit','verify local double-entry journal hash chain',True,True)


def private_key(path):
    k=serialization.load_pem_private_key(Path(path).read_bytes(),password=None)
    if not isinstance(k,Ed25519PrivateKey):
        raise ValueError('Ed25519 key required')
    return k


def sign(k,payload):
    return k.sign(canonical(payload)).hex()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path,data):
    Path(path).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    print('signed file:',path)


def request(args,method,path,payload=None,admin=False):
    auth={'Authorization':'Bearer '+Path(args.admin_token_file).read_text().strip()} if admin else {}
    with httpx.Client(timeout=10) as client:
        response=client.request(method,args.server+path,headers=auth,json=payload)
        response.raise_for_status()
        print(json.dumps(response.json(),indent=2))


def execute(args):
    name=args.command
    if name=='credit-network':
        request(args,'GET','/api/credits/network')
    elif name=='credit-asset':
        request(args,'POST','/api/credits/assets',{'asset_id':args.asset_id,'issuer_id':args.issuer_id,
            'description':args.description,'max_supply':args.max_supply},True)
    elif name=='credit-enroll-sign':
        key=private_key(args.private)
        pub=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw).hex()
        terms=WalletTerms(test_credit_disclaimer_accepted=True,accepted_assets=[args.asset_id],
                          max_transfer_units=args.max_transfer)
        e=WalletEnrollment(ledger_id=args.ledger_id,wallet_id=args.wallet_id,role=args.role,node_id=args.node_id,
                            pubkey=pub,terms=terms)
        payload=e.model_dump(mode='json')
        write(args.out,{'enrollment':payload,'signature':sign(key,payload)})
    elif name=='credit-enroll-submit':
        request(args,'POST','/api/credits/wallets',read(args.signed),True)
    elif name=='credit-issue':
        request(args,'POST','/api/credits/issue',{'asset_id':args.asset_id,'project_id':args.project_id,
                'task_id':args.task_id,'wallet_id':args.wallet_id},True)
    elif name=='credit-wallet':
        if args.private:
            net=httpx.get(args.server+'/api/credits/network',timeout=5)
            net.raise_for_status()
            req=WalletViewRequest(ledger_id=net.json()['ledger_id'],wallet_id=args.wallet_id,expires_at=int(time.time())+120)
            payload=req.model_dump(mode='json')
            request(args,'POST','/api/credits/wallet-view',
                    {'request':payload,'signature':sign(private_key(args.private),payload)})
        elif args.admin_token_file:
            request(args,'GET','/api/credits/wallets/'+args.wallet_id,admin=True)
        else:
            raise ValueError('provide --private (owner) or --admin-token-file (operator)')
    elif name=='credit-offer':
        offer=CreditOffer(ledger_id=args.ledger_id,transfer_id='credit-'+secrets.token_hex(12),asset_id=args.asset_id,
                          from_wallet=args.from_wallet,to_wallet=args.to_wallet,units=args.units,
                          nonce=args.nonce,expires_at=int(time.time())+120,
                          from_terms_sha256=args.sender_terms_sha,to_terms_sha256=args.recipient_terms_sha,
                          memo=args.memo)
        payload=offer.model_dump(mode='json')
        write(args.out,{'offer':payload,'sender_signature':sign(private_key(args.private),payload)})
    elif name=='credit-accept':
        packet=SignedCreditOffer.model_validate(read(args.offer))
        payload=acceptance_payload(packet)
        write(args.out,{**packet.model_dump(mode='json'),
                        'recipient_signature':sign(private_key(args.private),payload)})
    elif name=='credit-send':
        packet=AcceptedCreditTransfer.model_validate(read(args.accepted))
        request(args,'POST','/api/credits/transfers',packet.model_dump(mode='json'))
    elif name in ('credit-reserve','credit-release'):
        kind=name.removeprefix('credit-')
        a=WalletAction(ledger_id=args.ledger_id,action_id='action-'+secrets.token_hex(12),kind=kind,
                        wallet_id=args.wallet_id,job_id=args.job_id,reservation_id=args.reservation_id,
                        asset_id=args.asset_id,units=args.units,nonce=args.nonce,
                        expires_at=int(time.time())+120)
        payload=a.model_dump(mode='json')
        write(args.out,{'action':payload,'signature':sign(private_key(args.private),payload)})
    elif name=='credit-action-submit':
        signed=SignedWalletAction.model_validate(read(args.signed))
        endpoint='/api/credits/reservations' if signed.action.kind=='reserve' else '/api/credits/reservations/release'
        request(args,'POST',endpoint,signed.model_dump(mode='json'))
    elif name=='credit-settle':
        request(args,'POST','/api/credits/reservations/'+args.reservation_id+'/settle',{},True)
    elif name=='credit-audit':
        request(args,'GET','/api/credits/audit',admin=True)
    else:
        raise ValueError('unsupported economic command: '+name)
