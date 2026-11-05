"""Star-network pilot coordinator. Bind localhost by default; HTTP is not Internet-safe."""
from __future__ import annotations
import secrets
import sqlite3
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from .models import NodeRegistration, SignedProject, LeaseRequest, TaskComplete, TaskFail
from .submission import SignedSubmission, verify_submission, submission_digest
from .policy import validate_constitution, ConstitutionError
from .crypto import verify_project
from .store import Store


def create_app(db_path: str, admin_token: str) -> FastAPI:
    if len(admin_token) < 24:
        raise ValueError('admin token must have at least 24 characters')
    app = FastAPI(title='PolyC@home pilot coordinator', version='0.2.0')
    store = Store(db_path)
    app.state.store = store

    def bearer(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, 'Bearer token required')
        return authorization[7:]

    def admin(token: str = Depends(bearer)):
        if not secrets.compare_digest(token, admin_token):
            raise HTTPException(403, 'administrator authorization required')

    def node_auth(node_id: str, token: str):
        if not store.is_node_authorized(node_id, token):
            raise HTTPException(403, 'node not authorized or consent revoked')

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'polyc-coordinator', 'pilot': True}

    @app.post('/api/nodes', dependencies=[Depends(admin)])
    def register(n: NodeRegistration):
        try:
            validate_constitution(n.constitution)
            store.add_node(n.node_id, n.token, n.constitution)
            return {'node_id': n.node_id, 'registered': True}
        except ConstitutionError as ex:
            raise HTTPException(422, str(ex)) from ex
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409, 'node ID already exists') from ex

    @app.post('/api/jobs', dependencies=[Depends(admin)])
    def submit(sp: SignedProject):
        # Verification at submission, again by every worker at execution time.
        if not verify_project(sp, [sp.signer_pubkey]):
            raise HTTPException(422, 'invalid project signature')
        try:
            store.add_job(sp)
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409, 'job ID already exists') from ex
        return {'job_id': sp.project.project_id, 'accepted': True, 'tasks': sp.project.work.tasks}

    @app.post('/api/submissions', dependencies=[Depends(admin)])
    def stage_submission(signed: SignedSubmission):
        # This is **not** /api/jobs. It stages OCI project paperwork for later review.
        # Artifact, registry, source, SBOM and claimed purpose are NOT fetched/verified.
        if not verify_submission(signed):
            raise HTTPException(422, 'invalid project submission signature')
        try:
            store.stage_submission(signed)
        except sqlite3.IntegrityError as ex:
            raise HTTPException(409, 'project submission revision already staged') from ex
        return {'project_id': signed.submission.manifest.metadata.project_id,
                'revision': signed.submission.manifest.metadata.revision,
                'bundle_digest': submission_digest(signed.submission),
                'state': 'staged', 'executable': False}

    @app.get('/api/submissions/{project_id}/{revision}', dependencies=[Depends(admin)])
    def submission_status(project_id: str, revision: int):
        record = store.get_submission(project_id, revision)
        if record is None:
            raise HTTPException(404, 'submission not found')
        return {'project_id':record['id'],'revision':record['revision'],
                'bundle_digest':record['bundle_digest'],'state':record['state'],
                'staged_at':record['staged_at'],'executable':False}

    @app.get('/api/ledger/{project_id}', dependencies=[Depends(admin)])
    def contribution_ledger(project_id: str):
        return store.ledger(project_id)

    @app.post('/api/lease')
    def lease(req: LeaseRequest, token: str = Depends(bearer)):
        node_auth(req.node_id, token)
        try:
            return {'assignment': store.lease(req.node_id, req.constitution_digest)}
        except ValueError as ex:
            raise HTTPException(409, str(ex)) from ex

    @app.get('/api/tasks/{task_id}/status')
    def task_status(task_id: str, node_id: str, token: str = Depends(bearer)):
        node_auth(node_id, token)
        task = store.task_status(task_id)
        if not task or task['node_id'] != node_id:
            raise HTTPException(404, 'task not assigned to this node')
        return {'active': task['status'] == 'leased' and task['job_status'] == 'open',
                'lease_until': task['lease_until']}

    @app.post('/api/tasks/{task_id}/complete')
    def complete(task_id: str, result: TaskComplete, token: str = Depends(bearer)):
        node_auth(result.node_id, token)
        try:
            store.finish(task_id, result.node_id, result.lease_id, result.digest, result.duration_seconds)
        except ValueError as ex:
            raise HTTPException(409, str(ex)) from ex
        return {'recorded': True}

    @app.post('/api/tasks/{task_id}/fail')
    def fail(task_id: str, result: TaskFail, token: str = Depends(bearer)):
        node_auth(result.node_id, token)
        try:
            store.finish(task_id, result.node_id, result.lease_id, reason=result.reason)
        except ValueError as ex:
            raise HTTPException(409, str(ex)) from ex
        return {'requeued': True}

    @app.get('/api/jobs/{job_id}', dependencies=[Depends(admin)])
    def summary(job_id: str):
        r = store.job_summary(job_id)
        if not r:
            raise HTTPException(404, 'no such job')
        return r

    @app.post('/api/jobs/{job_id}/cancel', dependencies=[Depends(admin)])
    def cancel(job_id: str):
        if not store.cancel_job(job_id):
            raise HTTPException(404, 'no open job')
        return {'cancelled': True}

    @app.post('/api/nodes/{node_id}/revoke')
    def revoke(node_id: str, token: str = Depends(bearer)):
        node_auth(node_id, token)
        store.revoke_node(node_id)
        return {'revoked': True}

    @app.get('/api/chronicle/{node_id}')
    def chronicle(node_id: str, token: str = Depends(bearer)):
        if not secrets.compare_digest(token, admin_token):
            node_auth(node_id, token)
        return store.chronicle(node_id)

    @app.get('/metrics', response_class=PlainTextResponse, dependencies=[Depends(admin)])
    def metrics():
        m = store.metrics()
        return '# HELP polyc_nodes Active consenting nodes\n# TYPE polyc_nodes gauge\n' + f'polyc_nodes {m["nodes"]}\n' + ''.join(
            f'polyc_tasks{{state="{key[6:]}"}} {value}\n' for key, value in sorted(m.items()) if key.startswith('tasks_')
        )

    return app
