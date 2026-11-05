"""PoliC v0.3 test-credit clearing: signed, double-entry, local-SQLite only.

Credit assets have NO monetary value, backing, guaranteed compute, or conversion.
A coordinator is trusted to order transactions, verify work, and operate the journal.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
import time
from typing import Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import Field, model_validator

from .crypto import canonical, digest
from .models import Strict, SignedProject

ASSET_RE = r'^[a-z][a-z0-9._-]{3,79}$'
WALLET_RE = r'^[a-z][a-z0-9-]{2,63}$'
HEX64 = r'^[0-9a-f]{64}$'
HEX128 = r'^[0-9a-f]{128}$'


class CreditError(ValueError):
    pass


class TestCreditAsset(Strict):
    __test__ = False  # pytest must not confuse this domain model with a test case
    asset_id: str = Field(pattern=ASSET_RE)
    issuer_id: str = Field(pattern=WALLET_RE)
    description: str = Field(min_length=5, max_length=240)
    max_supply: int = Field(ge=1, le=1_000_000)
    test_only: Literal[True] = True
    redeemable_for_fiat: Literal[False] = False
    externally_convertible: Literal[False] = False
    guaranteed_compute: Literal[False] = False
    transferable: Literal[True] = True
    credit_units_per_verified_volunteer_task: Literal[1] = 1


class WalletTerms(Strict):
    test_credit_disclaimer_accepted: Literal[True]
    accepted_assets: list[str] = Field(min_length=1, max_length=20)
    may_send: bool = True
    may_receive: bool = True
    may_receive_settlement: bool = True
    max_transfer_units: int = Field(ge=1, le=1_000_000, default=1000)
    mutual_transfer_signatures_required: Literal[True] = True


class WalletEnrollment(Strict):
    ledger_id: str = Field(pattern=HEX64)
    wallet_id: str = Field(pattern=WALLET_RE)
    role: Literal['node', 'project']
    node_id: str | None = Field(default=None, pattern=WALLET_RE)
    pubkey: str = Field(pattern=HEX64)
    terms: WalletTerms

    @model_validator(mode='after')
    def role_consistency(self):
        if (self.role == 'node') != (self.node_id is not None):
            raise ValueError('node wallets require a node_id; project wallets cannot have one')
        if len(set(self.terms.accepted_assets)) != len(self.terms.accepted_assets):
            raise ValueError('duplicate asset in wallet terms')
        return self


class SignedWalletEnrollment(Strict):
    enrollment: WalletEnrollment
    signature: str = Field(pattern=HEX128)


class CreditOffer(Strict):
    ledger_id: str = Field(pattern=HEX64)
    transfer_id: str = Field(pattern=WALLET_RE)
    asset_id: str = Field(pattern=ASSET_RE)
    from_wallet: str = Field(pattern=WALLET_RE)
    to_wallet: str = Field(pattern=WALLET_RE)
    units: int = Field(ge=1, le=1_000_000)
    nonce: int = Field(ge=1)
    expires_at: int = Field(gt=0)
    from_terms_sha256: str = Field(pattern=HEX64)
    to_terms_sha256: str = Field(pattern=HEX64)
    memo: str = Field(default='', max_length=160)

    @model_validator(mode='after')
    def different_people(self):
        if self.from_wallet == self.to_wallet:
            raise ValueError('sender and recipient must differ')
        return self


class SignedCreditOffer(Strict):
    offer: CreditOffer
    sender_signature: str = Field(pattern=HEX128)


class AcceptedCreditTransfer(SignedCreditOffer):
    recipient_signature: str = Field(pattern=HEX128)


class WalletViewRequest(Strict):
    ledger_id: str = Field(pattern=HEX64)
    wallet_id: str = Field(pattern=WALLET_RE)
    expires_at: int = Field(gt=0)


class SignedWalletView(Strict):
    request: WalletViewRequest
    signature: str = Field(pattern=HEX128)


class WalletAction(Strict):
    ledger_id: str = Field(pattern=HEX64)
    action_id: str = Field(pattern=WALLET_RE)
    kind: Literal['reserve', 'release']
    wallet_id: str = Field(pattern=WALLET_RE)
    job_id: str = Field(pattern=WALLET_RE)
    reservation_id: str = Field(pattern=WALLET_RE)
    asset_id: str = Field(pattern=ASSET_RE)
    units: int = Field(ge=1, le=1_000_000)
    nonce: int = Field(ge=1)
    expires_at: int = Field(gt=0)


class SignedWalletAction(Strict):
    action: WalletAction
    signature: str = Field(pattern=HEX128)


class IssueVerifiedCredit(Strict):
    asset_id: str = Field(pattern=ASSET_RE)
    project_id: str = Field(pattern=WALLET_RE)
    task_id: str = Field(pattern=r'^[a-z0-9-]{3,100}$')
    wallet_id: str = Field(pattern=WALLET_RE)


def signature_ok(public_key: str, signature: str, payload) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(signature), canonical(payload))
        return True
    except (InvalidSignature, ValueError):
        return False


def acceptance_payload(signed: SignedCreditOffer) -> dict:
    return {'offer': signed.offer.model_dump(mode='json'), 'sender_signature': signed.sender_signature}


class CreditLedger:
    """Shares Store's connection/lock. All mutations are BEGIN IMMEDIATE atomic."""

    def __init__(self, store):
        self.store = store
        self.db = store.db
        self.lock = store.lock
        with self.lock:
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS credit_network (
              row_id INTEGER PRIMARY KEY CHECK(row_id=1), ledger_id TEXT UNIQUE NOT NULL);
            CREATE TABLE IF NOT EXISTS credit_assets (
              asset_id TEXT PRIMARY KEY, issuer_id TEXT NOT NULL, terms_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS credit_wallets (
              wallet_id TEXT PRIMARY KEY, role TEXT NOT NULL, node_id TEXT UNIQUE,
              pubkey TEXT NOT NULL, terms_json TEXT NOT NULL,
              terms_digest TEXT NOT NULL, last_nonce INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS credit_transactions (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, tx_id TEXT NOT NULL UNIQUE,
              asset_id TEXT NOT NULL, kind TEXT NOT NULL, ref TEXT NOT NULL,
              evidence_json TEXT NOT NULL, timestamp REAL NOT NULL,
              previous_hash TEXT NOT NULL, entry_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS credit_postings (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, tx_id TEXT NOT NULL,
              asset_id TEXT NOT NULL, account_id TEXT NOT NULL, units INTEGER NOT NULL,
              FOREIGN KEY(tx_id) REFERENCES credit_transactions(tx_id));
            CREATE INDEX IF NOT EXISTS idx_credit_balances ON credit_postings(asset_id,account_id);
            CREATE TABLE IF NOT EXISTS credit_issuances (
              asset_id TEXT NOT NULL, task_id TEXT NOT NULL, tx_id TEXT NOT NULL UNIQUE,
              PRIMARY KEY(asset_id,task_id));
            CREATE TABLE IF NOT EXISTS credit_reservations (
              reservation_id TEXT PRIMARY KEY, job_id TEXT NOT NULL UNIQUE,
              wallet_id TEXT NOT NULL, asset_id TEXT NOT NULL,
              units INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'reserved',
              final_tx_id TEXT);
            ''')
            self.db.execute('INSERT OR IGNORE INTO credit_network(row_id,ledger_id) VALUES(1,?)',
                            (secrets.token_hex(32),))
            self.ledger_id = self.db.execute('SELECT ledger_id FROM credit_network WHERE row_id=1').fetchone()[0]

    def _atomic(self, fn):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                result = fn()
                self.db.execute('COMMIT')
                return result
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def _wallet(self, wallet_id):
        row = self.db.execute('SELECT * FROM credit_wallets WHERE wallet_id=?', (wallet_id,)).fetchone()
        if not row:
            raise CreditError('wallet does not exist')
        return dict(row)

    def _asset(self, asset_id):
        row = self.db.execute('SELECT * FROM credit_assets WHERE asset_id=?', (asset_id,)).fetchone()
        if not row:
            raise CreditError('unknown credit asset')
        return TestCreditAsset.model_validate_json(row['terms_json'])

    def _balance(self, account, asset):
        return self.db.execute('SELECT COALESCE(SUM(units),0) FROM credit_postings WHERE asset_id=? AND account_id=?',
                               (asset, account)).fetchone()[0]

    def _authorized_time(self, expires):
        now = time.time()
        if expires < now or expires > now+600:
            raise CreditError('authorization expired or expires too far in the future')

    def _authorize(self, wallet, payload, signature, nonce, expires):
        self._authorized_time(expires)
        if not signature_ok(wallet['pubkey'], signature, payload):
            raise CreditError('wallet signature invalid')
        if nonce != wallet['last_nonce'] + 1:
            raise CreditError('replayed, missing, or out-of-order wallet nonce')

    def _spend_nonce(self, wallet):
        self.db.execute('UPDATE credit_wallets SET last_nonce=last_nonce+1 WHERE wallet_id=?', (wallet['wallet_id'],))

    def _record(self, tx_id, asset, kind, ref, postings: dict[str, int], evidence: dict):
        if not postings or any(v == 0 or type(v) is not int for v in postings.values()) or sum(postings.values()) != 0:
            raise CreditError('journal postings must be integral, nonzero and sum to zero')
        if self.db.execute('SELECT 1 FROM credit_transactions WHERE tx_id=?', (tx_id,)).fetchone():
            raise CreditError('transaction ID already used')
        prev = self.db.execute('SELECT entry_hash FROM credit_transactions ORDER BY seq DESC LIMIT 1').fetchone()
        prev_hash = prev['entry_hash'] if prev else '0'*64
        timestamp = time.time()
        record = {'tx_id':tx_id,'asset_id':asset,'kind':kind,'reference':ref,
                  'timestamp':timestamp,'postings':sorted(postings.items()),'evidence':evidence}
        entry_hash = digest({'previous':prev_hash,'transaction':record})
        self.db.execute('INSERT INTO credit_transactions(tx_id,asset_id,kind,ref,evidence_json,timestamp,previous_hash,entry_hash) '
                        'VALUES(?,?,?,?,?,?,?,?)',
                        (tx_id,asset,kind,ref,json.dumps(evidence,sort_keys=True),timestamp,prev_hash,entry_hash))
        for account, amount in sorted(postings.items()):
            self.db.execute('INSERT INTO credit_postings(tx_id,asset_id,account_id,units) VALUES(?,?,?,?)',
                            (tx_id,asset,account,amount))
        return {'tx_id':tx_id,'kind':kind,'asset_id':asset,'reference':ref,'hash':entry_hash}

    def create_asset(self, asset: TestCreditAsset):
        def f():
            self.db.execute('INSERT INTO credit_assets(asset_id,issuer_id,terms_json) VALUES(?,?,?)',
                            (asset.asset_id, asset.issuer_id, asset.model_dump_json()))
            return {'asset_id':asset.asset_id,'test_only':True,'max_supply':asset.max_supply}
        return self._atomic(f)

    def enroll(self, signed: SignedWalletEnrollment):
        e = signed.enrollment
        if e.ledger_id != self.ledger_id:
            raise CreditError('wallet enrollment bound to another credit ledger')
        if not signature_ok(e.pubkey, signed.signature, e.model_dump(mode='json')):
            raise CreditError('wallet enrollment signature invalid')
        def f():
            for asset in e.terms.accepted_assets:
                self._asset(asset)
            if e.role == 'node':
                n = self.store.node(e.node_id)
                if not n or n['revoked']:
                    raise CreditError('node is not active')
                policy = json.loads(n['constitution']).get('spec',{}).get('financial',{})
                if (policy.get('test_credits_enabled') is not True or
                    policy.get('wallet_pubkey') != e.pubkey or
                    not set(e.terms.accepted_assets).issubset(set(policy.get('accepted_assets', [])))):
                    raise CreditError('node constitution does not authorize this wallet and credit asset')
            self.db.execute('INSERT INTO credit_wallets(wallet_id,role,node_id,pubkey,terms_json,terms_digest) '
                            'VALUES(?,?,?,?,?,?)',
                            (e.wallet_id,e.role,e.node_id,e.pubkey,e.terms.model_dump_json(),digest(e.terms.model_dump(mode='json'))))
            return {'wallet_id':e.wallet_id,'role':e.role,'policy_digest':digest(e.terms.model_dump(mode='json'))}
        return self._atomic(f)

    def wallet_info(self, wallet_id):
        with self.lock:
            w=self._wallet(wallet_id)
            balances={r['asset_id']: self._balance(wallet_id,r['asset_id']) for r in self.db.execute('SELECT asset_id FROM credit_assets')}
            return {'wallet_id':wallet_id,'ledger_id':self.ledger_id,'role':w['role'],'node_id':w['node_id'],
                    'pubkey':w['pubkey'],'terms_digest':w['terms_digest'],
                    'next_nonce':w['last_nonce']+1,'balances':balances}

    def authorized_wallet_view(self, signed: SignedWalletView):
        with self.lock:
            if signed.request.ledger_id != self.ledger_id:
                raise CreditError('wallet view bound to another ledger')
            wallet=self._wallet(signed.request.wallet_id)
            self._authorized_time(signed.request.expires_at)
            if not signature_ok(wallet['pubkey'],signed.signature,signed.request.model_dump(mode='json')):
                raise CreditError('wallet balance view signature invalid')
            return self.wallet_info(wallet['wallet_id'])

    def issue_from_receipt(self, req: IssueVerifiedCredit):
        def f():
            asset=self._asset(req.asset_id)
            w=self._wallet(req.wallet_id)
            if w['role'] != 'node':
                raise CreditError('verified volunteer credits may only be issued to the contributor wallet')
            if req.asset_id not in WalletTerms.model_validate_json(w['terms_json']).accepted_assets:
                raise CreditError('wallet has not accepted this asset')
            if self.db.execute('SELECT 1 FROM credit_issuances WHERE asset_id=? AND task_id=?',
                               (req.asset_id,req.task_id)).fetchone():
                raise CreditError('receipt already issued credits')
            task=self.db.execute('SELECT t.*,j.signed_project FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.id=?',
                                 (req.task_id,)).fetchone()
            if not task or task['job_id'] != req.project_id or task['status'] != 'done' or task['node_id'] != w['node_id']:
                raise CreditError('verified task does not belong to wallet node')
            project=SignedProject.model_validate_json(task['signed_project']).project
            if project.financial and project.financial.model != 'volunteer':
                raise CreditError('paid compute cannot generate additional issuance')
            receipt=self.db.execute('SELECT receipt_json FROM contribution_receipts WHERE project_id=? ORDER BY seq',
                                    (req.project_id,)).fetchall()
            if not self.store.ledger(req.project_id)['chain_valid_locally']:
                raise CreditError('contribution receipt chain corrupted')
            if not any(json.loads(r['receipt_json'])['task_id'] == req.task_id and
                       json.loads(r['receipt_json'])['node_id'] == w['node_id'] for r in receipt):
                raise CreditError('matching verified contribution receipt missing')
            minted=-self._balance('supply:'+req.asset_id,req.asset_id)
            units=asset.credit_units_per_verified_volunteer_task
            if minted+units > asset.max_supply:
                raise CreditError('issuance would exceed supply limit')
            tx_id='mint-'+secrets.token_hex(12)
            result=self._record(tx_id,req.asset_id,'issue_verified',req.task_id,
                                {'supply:'+req.asset_id:-units,req.wallet_id:units},
                                {'project_id':req.project_id,'node_id':w['node_id'],'verification':'builtin_reference'})
            self.db.execute('INSERT INTO credit_issuances(asset_id,task_id,tx_id) VALUES(?,?,?)',
                            (req.asset_id,req.task_id,tx_id))
            return {**result,'wallet_id':req.wallet_id,'issued_units':units,'total_issued':minted+units}
        return self._atomic(f)

    def transfer(self, signed: AcceptedCreditTransfer):
        offer=signed.offer
        if offer.ledger_id != self.ledger_id:
            raise CreditError('transfer offer bound to another ledger')
        def f():
            self._asset(offer.asset_id)
            src=self._wallet(offer.from_wallet)
            dst=self._wallet(offer.to_wallet)
            src_terms=WalletTerms.model_validate_json(src['terms_json'])
            dst_terms=WalletTerms.model_validate_json(dst['terms_json'])
            if (offer.from_terms_sha256 != src['terms_digest'] or offer.to_terms_sha256 != dst['terms_digest']):
                raise CreditError('wallet consent terms changed')
            if offer.asset_id not in src_terms.accepted_assets or offer.asset_id not in dst_terms.accepted_assets:
                raise CreditError('asset not accepted by both wallet constitutions')
            if not src_terms.may_send or not dst_terms.may_receive:
                raise CreditError('transfer prohibited by wallet constitution')
            if offer.units > min(src_terms.max_transfer_units, dst_terms.max_transfer_units):
                raise CreditError('transfer exceeds wallet constitutional limits')
            self._authorize(src,offer.model_dump(mode='json'),signed.sender_signature,offer.nonce,offer.expires_at)
            if not signature_ok(dst['pubkey'],signed.recipient_signature, acceptance_payload(signed)):
                raise CreditError('recipient has not accepted the exact signed offer')
            if self._balance(src['wallet_id'],offer.asset_id) < offer.units:
                raise CreditError('insufficient available credit')
            tx=self._record(offer.transfer_id,offer.asset_id,'transfer',offer.to_wallet,
                            {offer.from_wallet:-offer.units,offer.to_wallet:offer.units},
                            {'transfer_sha256':digest(signed.model_dump(mode='json')),
                             'from_terms_sha256':src['terms_digest'],'to_terms_sha256':dst['terms_digest']})
            self._spend_nonce(src)
            return {**tx,'units':offer.units,'sender_balance':self._balance(src['wallet_id'],offer.asset_id),
                    'recipient_balance':self._balance(dst['wallet_id'],offer.asset_id)}
        return self._atomic(f)

    def reserve(self, signed: SignedWalletAction):
        a=signed.action
        if a.kind != 'reserve':
            raise CreditError('expected reserve action')
        if a.ledger_id != self.ledger_id:
            raise CreditError('reservation bound to another ledger')
        def f():
            self._asset(a.asset_id)
            payer=self._wallet(a.wallet_id)
            self._authorize(payer,a.model_dump(mode='json'),signed.signature,a.nonce,a.expires_at)
            if payer['role'] != 'project':
                raise CreditError('only project owner wallets can reserve for a job')
            j=self.db.execute('SELECT * FROM jobs WHERE id=?', (a.job_id,)).fetchone()
            if not j or j['status'] != 'open':
                raise CreditError('job not open')
            project=SignedProject.model_validate_json(j['signed_project'])
            fterms=project.project.financial
            if (not fterms or fterms.model != 'test_credits' or fterms.asset_id != a.asset_id or
                fterms.credits_per_verified_task*project.project.work.tasks != a.units):
                raise CreditError('reservation does not match immutable signed project terms')
            if project.signer_pubkey != payer['pubkey']:
                raise CreditError('wallet does not belong to signing project owner')
            if a.asset_id not in WalletTerms.model_validate_json(payer['terms_json']).accepted_assets:
                raise CreditError('payer constitution does not accept this asset')
            if self._balance(a.wallet_id,a.asset_id) < a.units:
                raise CreditError('insufficient credit to fund job')
            escrow='escrow:'+a.reservation_id
            tx=self._record(a.action_id,a.asset_id,'reserve',a.job_id,
                            {a.wallet_id:-a.units,escrow:a.units},
                            {'authorization_sha256':digest(signed.model_dump(mode='json'))})
            self.db.execute('INSERT INTO credit_reservations(reservation_id,job_id,wallet_id,asset_id,units) '
                            'VALUES(?,?,?,?,?)', (a.reservation_id,a.job_id,a.wallet_id,a.asset_id,a.units))
            self._spend_nonce(payer)
            return {**tx,'reservation_id':a.reservation_id,'state':'reserved','units':a.units}
        return self._atomic(f)

    def job_funded(self, job_id: str, asset_id: str, required: int) -> bool:
        with self.lock:
            row=self.db.execute('SELECT * FROM credit_reservations WHERE job_id=? AND state=?',
                                (job_id,'reserved')).fetchone()
            return bool(row and row['asset_id']==asset_id and row['units']==required and
                        self._balance('escrow:'+row['reservation_id'],asset_id)==required)

    def _finalize(self, reservation_id, release=False):
        r=self.db.execute('SELECT * FROM credit_reservations WHERE reservation_id=?', (reservation_id,)).fetchone()
        if not r or r['state'] != 'reserved':
            raise CreditError('no active reservation')
        j=self.db.execute('SELECT * FROM jobs WHERE id=?', (r['job_id'],)).fetchone()
        project=SignedProject.model_validate_json(j['signed_project']).project
        tasks=self.db.execute('SELECT node_id,COUNT(*) n FROM tasks WHERE job_id=? AND status=? GROUP BY node_id',
                              (r['job_id'],'done')).fetchall()
        done=sum(t['n'] for t in tasks)
        if not release and done != project.work.tasks:
            raise CreditError('cannot settle until all results have been verified')
        price=project.financial.credits_per_verified_task
        credits_due=done*price
        refund=r['units']-credits_due
        if refund < 0:
            raise CreditError('work exceeds reserved budget')
        if self._balance('escrow:'+r['reservation_id'],r['asset_id']) != r['units']:
            raise CreditError('escrow journal balance does not match reservation; deny settlement')
        postings={'escrow:'+r['reservation_id']:-r['units']}
        for t in tasks:
            w=self.db.execute('SELECT * FROM credit_wallets WHERE node_id=? AND role=?',
                              (t['node_id'],'node')).fetchone()
            if not w:
                raise CreditError('contributing node has no enrolled wallet; funds must stay reserved')
            terms=WalletTerms.model_validate_json(w['terms_json'])
            if r['asset_id'] not in terms.accepted_assets or not terms.may_receive_settlement:
                raise CreditError('contributor has not consented to settlement')
            postings[w['wallet_id']]=postings.get(w['wallet_id'],0)+t['n']*price
        if refund:
            postings[r['wallet_id']]=postings.get(r['wallet_id'],0)+refund
        postings={k:v for k,v in postings.items() if v}
        tx_id='settle-'+secrets.token_hex(12)
        record=self._record(tx_id,r['asset_id'],'release_and_settle' if release else 'settle',r['job_id'],postings,
                            {'verified_tasks':done,'credits_paid':credits_due,'refund_units':refund,
                             'reservation_id':reservation_id})
        self.db.execute('UPDATE credit_reservations SET state=?,final_tx_id=? WHERE reservation_id=?',
                        ('closed_early' if release else 'settled',tx_id,reservation_id))
        return {**record,'verified_tasks':done,'credits_paid':credits_due,'refund_units':refund}

    def settle(self, reservation_id):
        return self._atomic(lambda: self._finalize(reservation_id))

    def release(self, signed: SignedWalletAction):
        a=signed.action
        if a.kind != 'release':
            raise CreditError('expected release action')
        if a.ledger_id != self.ledger_id:
            raise CreditError('release bound to another ledger')
        def f():
            r=self.db.execute('SELECT * FROM credit_reservations WHERE reservation_id=?', (a.reservation_id,)).fetchone()
            if not r or (r['wallet_id'],r['job_id'],r['asset_id'],r['units']) != (
                a.wallet_id,a.job_id,a.asset_id,a.units):
                raise CreditError('reservation mismatch')
            wallet=self._wallet(a.wallet_id)
            self._authorize(wallet,a.model_dump(mode='json'),signed.signature,a.nonce,a.expires_at)
            # Stop new leases atomically before refunding anything.
            self.db.execute('UPDATE jobs SET status=? WHERE id=? AND status=?',('cancelled',a.job_id,'open'))
            result=self._finalize(a.reservation_id,release=True)
            self._spend_nonce(wallet)
            return result
        return self._atomic(f)

    def reservation(self, reservation_id):
        with self.lock:
            r=self.db.execute('SELECT * FROM credit_reservations WHERE reservation_id=?', (reservation_id,)).fetchone()
            return dict(r) if r else None

    def audit(self):
        """Detect local journal corruption. Operator still controls database and hash-chain head."""
        with self.lock:
            prev='0'*64
            total_by_asset={}
            valid=True
            records=[]
            rows=self.db.execute('SELECT * FROM credit_transactions ORDER BY seq').fetchall()
            for r in rows:
                postings=[(x['account_id'],x['units']) for x in self.db.execute(
                    'SELECT account_id,units FROM credit_postings WHERE tx_id=? ORDER BY account_id',(r['tx_id'],))]
                evidence=json.loads(r['evidence_json'])
                payload={'tx_id':r['tx_id'],'asset_id':r['asset_id'],'kind':r['kind'],'reference':r['ref'],
                         'timestamp':r['timestamp'],'postings':postings,'evidence':evidence}
                check=digest({'previous':prev,'transaction':payload})
                if check != r['entry_hash'] or prev != r['previous_hash'] or sum(x[1] for x in postings) != 0:
                    valid=False
                for account,units in postings:
                    if account.startswith('supply:'):
                        continue
                    total_by_asset[(r['asset_id'],account)]=total_by_asset.get((r['asset_id'],account),0)+units
                prev=r['entry_hash']
                records.append({'tx_id':r['tx_id'],'kind':r['kind'],'asset_id':r['asset_id'],'hash':r['entry_hash']})
            if any(v<0 for v in total_by_asset.values()):
                valid=False
            for a in self.db.execute('SELECT asset_id,terms_json FROM credit_assets'):
                issued=-self._balance('supply:'+a['asset_id'],a['asset_id'])
                maximum=TestCreditAsset.model_validate_json(a['terms_json']).max_supply
                if issued < 0 or issued > maximum:
                    valid=False
                held=sum(units for (asset,account),units in total_by_asset.items() if asset==a['asset_id'])
                if issued != held:
                    valid=False
            return {'ledger_id':self.ledger_id,'valid_locally':valid,'head_sha256':prev,'transaction_count':len(rows),
                    'externally_anchored':False,'monetary_value':False,'transactions':records}

    def supply(self, asset_id):
        with self.lock:
            asset=self._asset(asset_id)
            issued=-self._balance('supply:'+asset_id,asset_id)
            return {'asset_id':asset_id,'issued_units':issued,'max_supply':asset.max_supply,
                    'credit_type':'noncash_unbacked_test_only','guaranteed_compute':False}
