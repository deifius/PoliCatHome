"""Identity != authority: opt-in pseudonymous identities for the PoliC pilot.

This module intentionally never reads or mutates worker constitutions, trusted
creator keys, project approvals, Catbox controls or operator privileges.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from urllib.parse import urlencode

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519, padding, rsa
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import Literal

CHALLENGE_TTL = 180
SESSION_TTL = 60 * 60 * 24 * 7
GOOGLE_STATE_TTL = 300
GOOGLE_AUTHORIZE = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN = 'https://oauth2.googleapis.com/token'
GOOGLE_KEYS = 'https://www.googleapis.com/oauth2/v3/certs'


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def _unb64(data: str) -> bytes:
    if not isinstance(data, str) or len(data) > 8192:
        raise ValueError('invalid base64url')
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4))


def _identity_id() -> str:
    return 'plc_' + secrets.token_hex(16)


def _public_identity(row: sqlite3.Row) -> dict:
    return {'id': row['id'], 'alias': row['alias'],
            'default_landing': row['default_landing']}


class ChallengeRequest(BaseModel):
    purpose: Literal['register', 'login', 'link-key']
    public_key: str = Field(pattern=r'^[0-9a-f]{64}$')


class ProofRequest(BaseModel):
    challenge_id: str = Field(min_length=24, max_length=96)
    signature: str = Field(pattern=r'^[0-9a-f]{128}$')


class PreferencesRequest(BaseModel):
    default_landing: Literal['bloom', 'workspace']


class AliasRequest(BaseModel):
    alias: str = Field(min_length=2, max_length=40)


class IdentityStore:
    """Separate tables in the coordinator's SQLite database and lock domain."""
    def __init__(self, store):
        self.store = store
        with store.lock:
            store.db.executescript('''
            CREATE TABLE IF NOT EXISTS identities (
              id TEXT PRIMARY KEY, alias TEXT NOT NULL, default_landing TEXT NOT NULL
              DEFAULT 'workspace', created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS identity_keys (
              pubkey TEXT PRIMARY KEY, identity_id TEXT NOT NULL,
              created_at REAL NOT NULL, FOREIGN KEY(identity_id) REFERENCES identities(id));
            CREATE INDEX IF NOT EXISTS idx_identity_keys_owner ON identity_keys(identity_id);
            CREATE TABLE IF NOT EXISTS identity_providers (
              provider TEXT NOT NULL, subject TEXT NOT NULL,
              identity_id TEXT NOT NULL, created_at REAL NOT NULL,
              PRIMARY KEY(provider,subject), FOREIGN KEY(identity_id) REFERENCES identities(id));
            CREATE INDEX IF NOT EXISTS idx_identity_providers_owner ON identity_providers(identity_id);
            CREATE TABLE IF NOT EXISTS identity_challenges (
              id_digest TEXT PRIMARY KEY, purpose TEXT NOT NULL, pubkey TEXT NOT NULL,
              account_id TEXT, message TEXT NOT NULL, expires_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS identity_sessions (
              token_digest TEXT PRIMARY KEY, identity_id TEXT NOT NULL,
              expires_at REAL NOT NULL, created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_identity_sessions_owner ON identity_sessions(identity_id);
            CREATE TABLE IF NOT EXISTS identity_google_states (
              state_digest TEXT PRIMARY KEY, verifier TEXT NOT NULL, nonce TEXT NOT NULL,
              identity_id TEXT, expires_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS identity_rate_events (
              peer_digest TEXT NOT NULL, created_at REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_identity_rate ON identity_rate_events(peer_digest,created_at);
            ''')

    def _create(self):
        account = _identity_id()
        self.store.db.execute('INSERT INTO identities(id,alias,created_at) VALUES(?,?,?)',
                              (account, 'Cat ' + account[-6:], time.time()))
        return account

    def account(self, identity_id):
        with self.store.lock:
            return self.store.db.execute('SELECT * FROM identities WHERE id=?', (identity_id,)).fetchone()

    def find_key(self, pubkey):
        with self.store.lock:
            result = self.store.db.execute('SELECT identity_id FROM identity_keys WHERE pubkey=?', (pubkey,)).fetchone()
            return result['identity_id'] if result else None

    def limit_challenges(self, peer_digest):
        """Small DB-level abuse brake. Public ingress still needs a real rate limiter."""
        now = time.time()
        with self.store.lock:
            self.store.db.execute('DELETE FROM identity_rate_events WHERE created_at<?', (now - 3600,))
            attempts = self.store.db.execute('SELECT COUNT(*) FROM identity_rate_events WHERE peer_digest=?', (peer_digest,)).fetchone()[0]
            if attempts >= 40:
                raise HTTPException(429, 'Too many identity attempts. Please try later.')
            self.store.db.execute('INSERT INTO identity_rate_events VALUES(?,?)', (peer_digest, now))

    def issue(self, purpose, pubkey, account_id, hostname):
        challenge_id = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        # Explicit domain+purpose separation: a signature cannot authorize other API actions.
        message = '\n'.join(('PoliC identity proof v1', hostname.lower(), purpose, nonce))
        with self.store.lock:
            self.store.db.execute('DELETE FROM identity_challenges WHERE expires_at<?', (time.time(),))
            self.store.db.execute('INSERT INTO identity_challenges VALUES(?,?,?,?,?,?)',
                                  (_hash(challenge_id), purpose, pubkey, account_id, message, time.time() + CHALLENGE_TTL))
        return {'challenge_id':challenge_id,'message':message,'expires_in':CHALLENGE_TTL}

    def challenge_purpose(self, challenge_id):
        with self.store.lock:
            row=self.store.db.execute('SELECT purpose FROM identity_challenges WHERE id_digest=?', (_hash(challenge_id),)).fetchone()
            return row['purpose'] if row else None

    def prove(self, challenge_id, signature, session_account_id=None):
        """Consume before checking proof, and fail closed on replay or concurrency."""
        with self.store.lock:
            entry = self.store.db.execute('SELECT * FROM identity_challenges WHERE id_digest=?',
                                          (_hash(challenge_id),)).fetchone()
            self.store.db.execute('DELETE FROM identity_challenges WHERE id_digest=?', (_hash(challenge_id),))
            if not entry or entry['expires_at'] < time.time():
                raise HTTPException(401, 'Identity proof expired or already used')
            try:
                key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(entry['pubkey']))
                key.verify(bytes.fromhex(signature), entry['message'].encode('utf-8'))
            except (ValueError, InvalidSignature) as exc:
                raise HTTPException(401, 'Invalid identity proof') from exc
            purpose = entry['purpose']
            if purpose == 'link-key' and entry['account_id'] != session_account_id:
                raise HTTPException(401, 'Identity session changed before linking')
            owner = self.find_key(entry['pubkey'])
            if purpose == 'register':
                if owner:
                    raise HTTPException(409, 'Key is already registered; sign in instead')
                identity_id = self._create()
                self.store.db.execute('INSERT INTO identity_keys VALUES(?,?,?)',
                                      (entry['pubkey'], identity_id, time.time()))
                return identity_id, purpose
            if purpose == 'login':
                if not owner:
                    raise HTTPException(401, 'No identity registered with this key')
                return owner, purpose
            if purpose == 'link-key':
                if not entry['account_id']:
                    raise HTTPException(401, 'An active identity is required')
                if owner:
                    raise HTTPException(409, 'This key already belongs to an identity')
                if not self.account(entry['account_id']):
                    raise HTTPException(401, 'Identity not found')
                self.store.db.execute('INSERT INTO identity_keys VALUES(?,?,?)',
                                      (entry['pubkey'], entry['account_id'], time.time()))
                return entry['account_id'], purpose
            raise HTTPException(400, 'Unsupported proof')

    def start_session(self, identity_id):
        raw = secrets.token_urlsafe(48)
        with self.store.lock:
            self.store.db.execute('INSERT INTO identity_sessions VALUES(?,?,?,?)',
                                  (_hash(raw), identity_id, time.time() + SESSION_TTL, time.time()))
        return raw

    def active(self, raw):
        if not raw or len(raw) > 256:
            return None
        with self.store.lock:
            row = self.store.db.execute('''SELECT i.* FROM identity_sessions AS s
                      JOIN identities AS i ON s.identity_id=i.id
                      WHERE s.token_digest=? AND s.expires_at>?''', (_hash(raw),time.time())).fetchone()
            return row

    def recent_session(self, raw, max_age=600):
        if not raw or len(raw) > 256:
            return False
        with self.store.lock:
            row = self.store.db.execute('SELECT created_at, expires_at FROM identity_sessions WHERE token_digest=?', (_hash(raw),)).fetchone()
            return bool(row and row['expires_at'] > time.time() and row['created_at'] > time.time()-max_age)

    def logout(self, raw):
        if raw:
            with self.store.lock:
                self.store.db.execute('DELETE FROM identity_sessions WHERE token_digest=?', (_hash(raw),))

    def update_landing(self, identity_id, preference):
        with self.store.lock:
            self.store.db.execute('UPDATE identities SET default_landing=? WHERE id=?', (preference,identity_id))

    def update_alias(self, identity_id, alias):
        with self.store.lock:
            self.store.db.execute('UPDATE identities SET alias=? WHERE id=?', (alias, identity_id))

    def methods(self, identity_id):
        with self.store.lock:
            keys = self.store.db.execute('SELECT COUNT(*) FROM identity_keys WHERE identity_id=?', (identity_id,)).fetchone()[0]
            google = self.store.db.execute("SELECT COUNT(*) FROM identity_providers WHERE identity_id=? AND provider='google'", (identity_id,)).fetchone()[0]
            return {'independent_keys':keys, 'google_linked':bool(google)}

    def identity_export(self, identity_id):
        with self.store.lock:
            account = self.account(identity_id)
            keys = [row['pubkey'] for row in self.store.db.execute('SELECT pubkey FROM identity_keys WHERE identity_id=?', (identity_id,))]
            providers = [dict(row) for row in self.store.db.execute('SELECT provider,subject FROM identity_providers WHERE identity_id=?', (identity_id,))]
            return {'format':'polyc-identity-export/v1', 'account':_public_identity(account),
                    'public_keys':keys,'linked_providers':providers,
                    'warning':'This is account data, not a private-key backup or a transferable login credential.'}

    def provider_owner(self, provider, subject):
        with self.store.lock:
            row = self.store.db.execute('SELECT identity_id FROM identity_providers WHERE provider=? AND subject=?', (provider,subject)).fetchone()
            return row['identity_id'] if row else None

    def provider_connect(self, provider, subject, account_id):
        with self.store.lock:
            existing = self.provider_owner(provider,subject)
            if existing and existing != account_id:
                raise HTTPException(409, 'This provider identity is linked to another account')
            if not existing:
                self.store.db.execute('INSERT INTO identity_providers VALUES(?,?,?,?)',
                                      (provider,subject,account_id,time.time()))

    def provider_unlink(self, provider, account_id):
        with self.store.lock:
            providers = self.store.db.execute('SELECT COUNT(*) FROM identity_providers WHERE identity_id=?', (account_id,)).fetchone()[0]
            keys = self.store.db.execute('SELECT COUNT(*) FROM identity_keys WHERE identity_id=?', (account_id,)).fetchone()[0]
            if providers + keys <= 1:
                raise HTTPException(409,'Add an independent key before removing your last login method')
            self.store.db.execute('DELETE FROM identity_providers WHERE identity_id=? AND provider=?', (account_id,provider))


def _verify_google_id_token(token, client_id, nonce, jwks):
    """Strict RS256 verifier for Google ID tokens; never accept client-supplied claims."""
    try:
        pieces = token.split('.')
        if len(pieces) != 3:
            raise ValueError('JWT parts')
        header = json.loads(_unb64(pieces[0]))
        claims = json.loads(_unb64(pieces[1]))
        if header.get('alg') != 'RS256' or header.get('typ','JWT') != 'JWT':
            raise ValueError('algorithm')
        key = next(k for k in jwks['keys'] if k.get('kid') == header.get('kid') and k.get('kty') == 'RSA' and k.get('use','sig') == 'sig')
        n = int.from_bytes(_unb64(key['n']), 'big')
        e = int.from_bytes(_unb64(key['e']), 'big')
        pub = rsa.RSAPublicNumbers(e, n).public_key()
        pub.verify(_unb64(pieces[2]), (pieces[0]+'.'+pieces[1]).encode('ascii'), padding.PKCS1v15(), hashes.SHA256())
        now = time.time()
        if (claims.get('iss') not in ('https://accounts.google.com','accounts.google.com')
            or claims.get('aud') != client_id
            or claims.get('nonce') != nonce
            or not isinstance(claims.get('exp'), (float,int)) or claims['exp'] <= now-60
            or not isinstance(claims.get('iat'), (float,int)) or claims['iat'] > now + 60
            or not isinstance(claims.get('sub'), str) or not 1 <= len(claims['sub']) <= 255):
            raise ValueError('invalid claims')
        return claims['sub']
    except (ValueError, KeyError, StopIteration, InvalidSignature, TypeError) as exc:
        raise HTTPException(401,'Google identity verification failed') from exc


def mount_identity(app, store, admin_token):
    ids = IdentityStore(store)
    app.state.identities = ids

    google_client_id = os.getenv('POLYC_GOOGLE_CLIENT_ID','').strip()
    google_secret = os.getenv('POLYC_GOOGLE_CLIENT_SECRET','').strip()
    google_redirect = os.getenv('POLYC_GOOGLE_REDIRECT_URI','').strip()
    google_enabled = bool(google_client_id and google_secret and google_redirect)
    if any((google_client_id, google_secret, google_redirect)) and not google_enabled:
        raise ValueError('Configure all three POLYC_GOOGLE_CLIENT_ID, CLIENT_SECRET, REDIRECT_URI or none')
    if google_enabled and not (google_redirect.startswith('https://') or google_redirect.startswith('http://localhost:')):
        raise ValueError('Google redirect must use HTTPS (except localhost development)')

    def allowed_transport(request: Request):
        if request.url.scheme == 'https':
            return
        if request.url.scheme == 'http' and request.url.hostname in ('localhost','127.0.0.1','::1','testserver'):
            return
        raise HTTPException(503,'Identity sign-in requires HTTPS')

    def same_origin(request: Request):
        # All browser state changes must send Origin; SameSite is defense in depth.
        origin = request.headers.get('origin','')
        expected = f'{request.url.scheme}://{request.url.netloc}'
        if not secrets.compare_digest(origin, expected):
            raise HTTPException(403,'Same-origin request required')
        if request.headers.get('content-type','').split(';')[0].lower() != 'application/json':
            raise HTTPException(415,'JSON request required')

    def cookie_name(request: Request, state=False):
        base = 'polyc_google_state' if state else 'polyc_identity_session'
        return '__Host-' + base if request.url.scheme == 'https' else base + '_dev'

    def set_cookie(response, request, raw, state=False, max_age=SESSION_TTL):
        response.set_cookie(cookie_name(request,state),raw,httponly=True, secure=request.url.scheme=='https',
                            samesite='lax',path='/',max_age=max_age)

    def clear_cookie(response, request, state=False):
        response.delete_cookie(cookie_name(request,state),path='/',secure=request.url.scheme=='https',samesite='lax')

    def raw_session(request):
        return request.cookies.get(cookie_name(request))

    def current(request):
        return ids.active(raw_session(request))

    def require_identity(request):
        row = current(request)
        if not row:
            raise HTTPException(401,'Sign in first')
        return row

    @app.get('/api/identity/config')
    def identity_config():
        return JSONResponse({'google_enabled':google_enabled, 'key_identity_enabled':True,
                 'identity_is_not_consent':True}, headers={'Cache-Control':'no-store'})

    @app.get('/api/identity/me')
    def me(request: Request):
        row = current(request)
        return JSONResponse({'authenticated': bool(row),
                             'identity':_public_identity(row) if row else None,
                             'login_methods':ids.methods(row['id']) if row else None,
                             'compute_authorized':False,
                             'note':'Identity authentication never grants Catnap or operator permissions.'},
                            headers={'Cache-Control':'no-store'})

    @app.post('/api/identity/challenge')
    def issue_identity_challenge(req: ChallengeRequest, request: Request):
        allowed_transport(request); same_origin(request)
        owner = current(request)
        if req.purpose == 'link-key' and not owner:
            raise HTTPException(401,'Sign in to link an independent key')
        if req.purpose == 'link-key' and not ids.recent_session(raw_session(request)):
            raise HTTPException(403,'Please sign in again before changing login methods')
        peer = request.client.host if request.client else 'unknown'
        peer_digest = hmac.new(admin_token.encode(), peer.encode(), hashlib.sha256).hexdigest()
        ids.limit_challenges(peer_digest)
        return ids.issue(req.purpose,req.public_key,owner['id'] if req.purpose=='link-key' else None, request.url.netloc)

    @app.post('/api/identity/prove')
    def prove_identity(req: ProofRequest, request: Request):
        allowed_transport(request); same_origin(request)
        signed_in = current(request)
        # Credential changes are high-risk and require a recently established session.
        if ids.challenge_purpose(req.challenge_id) == 'link-key' and not ids.recent_session(raw_session(request)):
            raise HTTPException(403,'Please sign in again before changing login methods')
        identity_id, purpose = ids.prove(req.challenge_id,req.signature, signed_in['id'] if signed_in else None)
        response = JSONResponse({'authenticated':True,'identity':_public_identity(ids.account(identity_id)),
                                 'purpose':purpose,'compute_authorized':False},headers={'Cache-Control':'no-store'})
        # Fresh session after cryptographic login. Linking a key does not grant new privileges.
        if purpose != 'link-key':
            ids.logout(raw_session(request))
            set_cookie(response,request,ids.start_session(identity_id))
        return response

    @app.post('/api/identity/logout')
    def logout_identity(request: Request):
        allowed_transport(request); same_origin(request)
        ids.logout(raw_session(request))
        response = JSONResponse({'authenticated':False},headers={'Cache-Control':'no-store'})
        clear_cookie(response,request)
        return response

    @app.patch('/api/identity/preferences')
    def identity_preferences(req: PreferencesRequest,request: Request):
        allowed_transport(request); same_origin(request)
        actor = require_identity(request)
        ids.update_landing(actor['id'],req.default_landing)
        return {'identity':_public_identity(ids.account(actor['id']))}

    @app.patch('/api/identity/alias')
    def identity_alias(req: AliasRequest,request: Request):
        allowed_transport(request); same_origin(request)
        actor = require_identity(request)
        alias = req.alias.strip()
        if len(alias) < 2 or any(ord(c)<32 for c in alias):
            raise HTTPException(422,'Invalid alias')
        ids.update_alias(actor['id'],alias)
        return {'identity':_public_identity(ids.account(actor['id']))}

    @app.get('/api/identity/export')
    def identity_export(request: Request):
        allowed_transport(request)
        actor = require_identity(request)
        return JSONResponse(ids.identity_export(actor['id']),headers={'Cache-Control':'no-store',
            'Content-Disposition':'attachment; filename="polyc-identity-export.json"'})

    @app.delete('/api/identity/providers/google')
    def unlink_google(request: Request):
        allowed_transport(request)
        origin = request.headers.get('origin','')
        if origin != f'{request.url.scheme}://{request.url.netloc}':
            raise HTTPException(403,'Same-origin request required')
        actor = require_identity(request)
        if not ids.recent_session(raw_session(request)):
            raise HTTPException(403,'Please sign in again before changing login methods')
        ids.provider_unlink('google',actor['id'])
        return {'unlinked':True}

    def make_google_authorization(request, account_id=None, redirect=True):
        allowed_transport(request)
        if not google_enabled:
            raise HTTPException(404,'Google sign-in not configured')
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        nonce = secrets.token_urlsafe(32)
        challenge = _b64(hashlib.sha256(verifier.encode()).digest())
        with store.lock:
            store.db.execute('DELETE FROM identity_google_states WHERE expires_at<?', (time.time(),))
            store.db.execute('INSERT INTO identity_google_states VALUES(?,?,?,?,?)',
                             (_hash(state),verifier,nonce,account_id,time.time()+GOOGLE_STATE_TTL))
        url = GOOGLE_AUTHORIZE+'?'+urlencode({'client_id':google_client_id,'redirect_uri':google_redirect,
           'response_type':'code','scope':'openid','state':state,'nonce':nonce,
           'code_challenge':challenge,'code_challenge_method':'S256'})
        response = (RedirectResponse(url, status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
                    if redirect else JSONResponse({'url':url},headers={'Cache-Control':'no-store'}))
        set_cookie(response,request,state,state=True,max_age=GOOGLE_STATE_TTL)
        return response

    @app.get('/api/identity/google/start')
    def google_start(request: Request):
        if current(request):
            raise HTTPException(409, 'Use the explicit link action when already signed in')
        return make_google_authorization(request)

    @app.post('/api/identity/google/link/start')
    def google_link_start(request: Request):
        allowed_transport(request); same_origin(request)
        actor = require_identity(request)
        if not ids.recent_session(raw_session(request)):
            raise HTTPException(403,'Please sign in again before changing login methods')
        return make_google_authorization(request,account_id=actor['id'],redirect=False)

    @app.get('/api/identity/google/callback')
    async def google_callback(request: Request, state: str = '', code: str = '', error: str = ''):
        allowed_transport(request)
        if not google_enabled:
            raise HTTPException(404,'Google sign-in not configured')
        state_cookie = request.cookies.get(cookie_name(request,True),'')
        if not state or not secrets.compare_digest(state,state_cookie):
            raise HTTPException(403,'Google login state mismatch')
        with store.lock:
            entry = store.db.execute('SELECT * FROM identity_google_states WHERE state_digest=?', (_hash(state),)).fetchone()
            store.db.execute('DELETE FROM identity_google_states WHERE state_digest=?', (_hash(state),))
        if not entry or entry['expires_at'] < time.time() or error or not code:
            raise HTTPException(401,'Google sign-in was cancelled or expired')
        if entry['identity_id'] and (not current(request) or current(request)['id'] != entry['identity_id']):
            raise HTTPException(403,'Identity changed during Google link')
        # Fixed Google endpoints. Do not retain authorization codes, tokens, user email or profile data.
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                exchange = await client.post(GOOGLE_TOKEN,data={
                    'code':code,'client_id':google_client_id,'client_secret':google_secret,
                    'redirect_uri':google_redirect,'grant_type':'authorization_code','code_verifier':entry['verifier']})
                exchange.raise_for_status()
                id_token = exchange.json()['id_token']
                keys = await client.get(GOOGLE_KEYS)
                keys.raise_for_status()
                jwks = keys.json()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise HTTPException(502,'Unable to verify Google authentication') from exc
        subject = _verify_google_id_token(id_token,google_client_id,entry['nonce'],jwks)
        existing = ids.provider_owner('google',subject)
        if entry['identity_id']:
            identity_id = entry['identity_id']
            if existing and existing != identity_id:
                raise HTTPException(409,'Google account already linked to another identity')
        else:
            identity_id = existing
            if identity_id is None:
                with store.lock:
                    identity_id = ids._create()
        ids.provider_connect('google',subject,identity_id)
        ids.logout(raw_session(request))
        response = RedirectResponse('/',status_code=303,headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
        clear_cookie(response,request,state=True)
        set_cookie(response,request,ids.start_session(identity_id))
        return response
