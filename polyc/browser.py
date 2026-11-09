"""Opt-in browser Catnap and Create a Cat APIs. Not a general code execution service."""
from __future__ import annotations
import secrets
import hashlib
import hmac
import os
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import Depends, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .crypto import verify_project
from .models import NodeRegistration, SignedProject
from .policy import ConstitutionError, validate_constitution


class InvitationRequest(BaseModel):
    kind: Literal['catnap', 'create_cat']
    count: int = Field(default=1, ge=1, le=20)
    ttl_seconds: int = Field(default=3600, ge=300, le=86400)


class EnrollmentRequest(BaseModel):
    invitation: str | None = Field(default=None, min_length=24, max_length=256)
    accepted_browser_limitations: bool = False
    node: NodeRegistration


class NativeCatboxEnrollmentRequest(BaseModel):
    accepted_resource_disclosure: bool = False
    node: NodeRegistration


class CatProposalRequest(BaseModel):
    invitation: str = Field(min_length=24, max_length=256)
    signed_project: SignedProject


class ReviewRequest(BaseModel):
    approve: bool
    note: str = Field(default='', max_length=250)


def mount_browser(app, store, admin_token, admin, bearer):
    web_dir = Path(__file__).resolve().parent / 'web'
    if not web_dir.is_dir():
        raise RuntimeError('browser assets are missing; rebuild package with polyc/web included')

    @app.get('/', include_in_schema=False)
    def web_home():
        return FileResponse(web_dir / 'index.html', headers={'Cache-Control':'no-store'})

    app.mount('/web', StaticFiles(directory=web_dir), name='polyc-web')

    @app.post('/api/catnap/invitations', dependencies=[Depends(admin)])
    def issue_invitations(req: InvitationRequest):
        return {'kind':req.kind, 'invitations':store.issue_invites(req.kind,req.count,req.ttl_seconds),
                'ttl_seconds':req.ttl_seconds, 'one_use':True}

    @app.get('/api/catnap/constitution-template')
    def constitution_template():
        from .demo import constitution
        result = constitution('0'*64)
        result['spec']['trust']['trusted_signers'] = []
        result['spec']['nice_plus']['cpu_percent_max'] = 25
        result['spec']['nice_plus']['task_runtime_seconds_max'] = 20
        result['spec']['reporting']['catnap_enabled'] = True
        return {'constitution':result, 'note':'Browser policy is cooperative, not OS-enforced. Add trusted signer keys before joining.'}

    # Explicit opt-in. For loopback local Docker pilot set POLYC_SELF_ENROLL=1;
    # not a substitute for TLS, ingress limits, bot protection or public deployment review.
    self_enroll_enabled = os.environ.get('POLYC_SELF_ENROLL', '0').lower() in ('1', 'true', 'yes')

    @app.get('/api/catnap/enrollment-options')
    def enrollment_options():
        return {'self_enroll': self_enroll_enabled, 'invite_supported': True,
                'pilot': True, 'note': 'Joining alone never starts CPU work; trust approved Cats and press Start Catnap.'}

    @app.get('/api/catnap/catalog')
    def approved_cat_catalog():
        return JSONResponse({'cats': store.public_cat_catalog(), 'note': 'These are creator-declared attributes of approved built-in tasks, not independent content audits.'}, headers={'Cache-Control':'no-store'})

    @app.post('/api/catnap/enroll')
    def enroll(req: EnrollmentRequest, request: Request):
        c = req.node.constitution
        try:
            validate_constitution(c)
            spec = c['spec']
            if spec.get('thermal', {}).get('cpu_package_c_max') is not None:
                raise ConstitutionError('browser cannot enforce temperature policy; use native Catnap')
            if spec.get('energy', {}).get('require_meter'):
                raise ConstitutionError('browser cannot enforce energy metering')
            if spec.get('nice_plus', {}).get('gpu_utilization_percent_max'):
                raise ConstitutionError('browser cannot enforce GPU limits')
            if spec.get('financial'):
                raise ConstitutionError('browser test-credit settlement is not yet supported')
            signers = spec.get('trust', {}).get('trusted_signers', [])
            if len(signers) > 20 or any(
                not isinstance(x,str) or len(x) != 64 or any(c not in '0123456789abcdef' for c in x)
                for x in signers):
                raise ConstitutionError('trusted creator keys must be 64-character hexadecimal values (empty means no tasks are authorized)')
            if not 1 <= spec['nice_plus']['task_runtime_seconds_max'] <= 25:
                raise ConstitutionError('browser runtime ceiling must be <=25 seconds (lease lifetime)')
            if req.invitation:
                store.enroll_browser(req.invitation,req.node)
            else:
                if not self_enroll_enabled:
                    raise HTTPException(403,'self-enrollment is disabled on this Commons; use an operator invitation')
                if not req.accepted_browser_limitations:
                    raise HTTPException(422,'explicit acknowledgement of browser CPU, energy, heat and non-enforced limits required')
                # Request.client.host is the directly connected peer. Do not trust
                # spoofable X-Forwarded-For headers. Proxies must enforce their own
                # upstream limits as many visitors otherwise share one peer address.
                peer = request.client.host if request.client else 'unknown'
                peer_digest = hmac.new(admin_token.encode(),peer.encode(),hashlib.sha256).hexdigest()
                store.self_enroll_browser(req.node,peer_digest)
        except (ConstitutionError, KeyError, TypeError) as ex:
            raise HTTPException(422,str(ex)) from ex
        except ValueError as ex:
            if str(ex).startswith(('self-enrollment limit','the pilot Commons')):
                raise HTTPException(429,str(ex)) from ex
            raise HTTPException(403,str(ex)) from ex
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409,'node ID already enrolled') from ex
        return {'node_id':req.node.node_id, 'enrolled':True, 'compute_started':False,
                'constraints':'Browser best-effort CPU pacing only. No thermal, power, OS niceness or GPU controls.'}

    @app.post('/api/catbox/enroll')
    def native_catbox_enroll(req: NativeCatboxEnrollmentRequest, request: Request):
        """Opt-in for the separate, built-in-only Docker Catbox pilot (no admin token)."""
        if not self_enroll_enabled:
            raise HTTPException(403, 'self-enrollment is disabled on this Commons')
        if not req.accepted_resource_disclosure:
            raise HTTPException(422, 'native Catbox resource disclosure and explicit consent are required')
        try:
            validate_constitution(req.node.constitution)
            spec = req.node.constitution['spec']
            if (spec.get('thermal', {}).get('cpu_package_c_max') is not None or
                spec.get('energy', {}).get('require_meter') or
                spec['nice_plus'].get('gpu_utilization_percent_max') or
                spec.get('financial')):
                raise ConstitutionError('the pilot Catbox cannot enforce thermal, GPU, energy metering or financial conditions')
            if spec['nice_plus']['memory_mib_max'] > 512 or spec['nice_plus']['cpu_percent_max'] > 50:
                raise ConstitutionError('Catbox pilot policy exceeds its 512 MiB task / 50% CPU ceiling')
            if not 1 <= spec['nice_plus']['task_runtime_seconds_max'] <= 20:
                raise ConstitutionError('Catbox task runtime must be 1–20 seconds')
            signers = spec.get('trust', {}).get('trusted_signers', [])
            if len(signers) > 20 or any(not isinstance(x, str) or len(x) != 64 or
                any(ch not in '0123456789abcdef' for ch in x) for x in signers):
                raise ConstitutionError('trusted keys must be lowercase 64-character hex (empty means idle)')
            peer = request.client.host if request.client else 'unknown'
            peer_digest = hmac.new(admin_token.encode(), peer.encode(), hashlib.sha256).hexdigest()
            store.self_enroll_browser(req.node, peer_digest)
        except (ConstitutionError, KeyError, TypeError) as ex:
            raise HTTPException(422, str(ex)) from ex
        except ValueError as ex:
            if str(ex).startswith(('self-enrollment limit', 'the pilot Commons')):
                raise HTTPException(429, str(ex)) from ex
            raise HTTPException(403, str(ex)) from ex
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409, 'node ID already enrolled') from ex
        return {'node_id': req.node.node_id, 'enrolled': True, 'compute_started': False,
                'scope': 'native-built-in-only',
                'constraints': 'Docker cgroup CPU/memory caps; no host temperature sensor, GPU or general OCI workloads'}

    @app.post('/api/workshop/cats')
    def create_cat(req: CatProposalRequest):
        if not verify_project(req.signed_project,[req.signed_project.signer_pubkey]):
            raise HTTPException(422,'invalid creator signature')
        try:
            store.propose_cat(req.invitation,req.signed_project)
        except ValueError as ex:
            raise HTTPException(403,str(ex)) from ex
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409,'Cat ID already proposed') from ex
        return {'project_id':req.signed_project.project.project_id,'state':'staged',
                'executable':False, 'requires_operator_review':True,
                'requires_contributor_trust':True}

    @app.get('/api/workshop/cats', dependencies=[Depends(admin)])
    def list_cats():
        return {'cats':store.list_cat_proposals()}

    @app.get('/api/workshop/cats/{project_id}', dependencies=[Depends(admin)])
    def cat_details(project_id: str):
        value = store.get_cat_proposal(project_id)
        if value is None:
            raise HTTPException(404,'Cat proposal not found')
        return value

    @app.post('/api/workshop/cats/{project_id}/review', dependencies=[Depends(admin)])
    def review(project_id: str, req: ReviewRequest):
        try:
            store.review_cat(project_id,req.approve,req.note)
        except KeyError as ex:
            raise HTTPException(404,str(ex)) from ex
        except ValueError as ex:
            raise HTTPException(409,str(ex)) from ex
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409,'approved work ID already exists') from ex
        return {'project_id':project_id,'state':'approved' if req.approve else 'rejected',
                'executable':req.approve,'note':'Approval does not override individual Catnap consent'}

    @app.get('/api/catnap/snapshot')
    def snapshot(node_id: str | None = Query(default=None,max_length=64),
                 token: str = Depends(bearer)):
        is_admin = secrets.compare_digest(token,admin_token)
        if node_id:
            if not is_admin and not store.is_node_authorized(node_id,token):
                raise HTTPException(403,'node not authorized')
        elif not is_admin:
            raise HTTPException(403,'overview requires operator authorization')
        data = store.catnap_snapshot(node_id)
        return JSONResponse(data,headers={'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'})

    @app.middleware('http')
    async def browser_security_headers(request, call_next):
        response = await call_next(request)
        if request.url.path == '/' or request.url.path.startswith('/web/'):
            response.headers['Content-Security-Policy'] = (
                "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                "connect-src 'self'; worker-src 'self'; font-src 'self'; object-src 'none'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'no-referrer'
            # Avoid stale UI assets after rebuilding the local Docker image.
            if request.url.path.endswith(('.js', '.css')):
                response.headers['Cache-Control'] = 'no-store'
        return response
