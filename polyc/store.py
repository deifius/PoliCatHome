"""Durable SQLite star coordinator; narrow API, never trusted as host authority."""
from __future__ import annotations
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path
from .models import SignedProject
from .crypto import digest
from .policy import compatible
from .compute import compute_chain


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Store:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS nodes (
               id TEXT PRIMARY KEY, token_digest TEXT NOT NULL, constitution TEXT NOT NULL,
               constitution_digest TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
               created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS jobs (
               id TEXT PRIMARY KEY, signed_project TEXT NOT NULL,
               status TEXT NOT NULL DEFAULT 'open', created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks (
               id TEXT PRIMARY KEY, job_id TEXT NOT NULL, task_index INTEGER NOT NULL,
               status TEXT NOT NULL DEFAULT 'pending', node_id TEXT, lease_id TEXT,
               lease_until REAL, digest TEXT, duration REAL, result_time REAL,
               fail_reason TEXT,
               FOREIGN KEY(job_id) REFERENCES jobs(id));
            CREATE INDEX IF NOT EXISTS idx_tasks_queue ON tasks(status, job_id);
            CREATE TABLE IF NOT EXISTS events (
               id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
               node_id TEXT, job_id TEXT, kind TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS submissions (
               id TEXT NOT NULL, revision INTEGER NOT NULL, bundle_digest TEXT NOT NULL,
               signed_bundle TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'staged',
               staged_at REAL NOT NULL, PRIMARY KEY(id,revision));
            CREATE TABLE IF NOT EXISTS contribution_receipts (
               seq INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL,
               receipt_json TEXT NOT NULL, prev_sha256 TEXT NOT NULL, receipt_sha256 TEXT NOT NULL,
               UNIQUE(project_id,receipt_sha256));
            CREATE INDEX IF NOT EXISTS idx_receipts_project ON contribution_receipts(project_id,seq);
            ''')
        from .credits import CreditLedger
        self._credits = CreditLedger(self)

    # Deliberately separate financial ledger with the same SQLite transaction boundary.
    @property
    def credits(self):
        return self._credits

    def event(self, kind: str, detail: str, node_id: str | None = None, job_id: str | None = None):
        self.db.execute('INSERT INTO events(at,node_id,job_id,kind,detail) VALUES(?,?,?,?,?)',
                        (time.time(), node_id, job_id, kind, detail[:300]))

    def node(self, node_id):
        with self.lock:
            x = self.db.execute('SELECT * FROM nodes WHERE id=?', (node_id,)).fetchone()
            return dict(x) if x else None

    def add_node(self, node_id, token, constitution):
        with self.lock:
            self.db.execute('INSERT INTO nodes(id,token_digest,constitution,constitution_digest,created_at) VALUES(?,?,?,?,?)',
                            (node_id, token_digest(token), json.dumps(constitution, sort_keys=True), digest(constitution), time.time()))
            self.event('node_joined', 'Node consent registered', node_id=node_id)

    def add_job(self, sp: SignedProject):
        p = sp.project
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.db.execute('INSERT INTO jobs(id,signed_project,created_at) VALUES(?,?,?)',
                                (p.project_id, sp.model_dump_json(), time.time()))
                for i in range(p.work.tasks):
                    self.db.execute('INSERT INTO tasks(id,job_id,task_index) VALUES(?,?,?)',
                                    (f'{p.project_id}-{i:04d}', p.project_id, i))
                self.event('job_submitted', f'{p.title}: {p.work.tasks} deterministic tasks', job_id=p.project_id)
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def is_node_authorized(self, node_id, token):
        with self.lock:
            n = self.node(node_id)
            return bool(n and not n['revoked'] and secrets.compare_digest(n['token_digest'], token_digest(token)))

    def reclaim_expired(self):
        expired = self.db.execute('SELECT id,node_id,job_id FROM tasks WHERE status="leased" AND lease_until<?', (time.time(),)).fetchall()
        for t in expired:
            self.db.execute('UPDATE tasks SET status="pending",node_id=NULL,lease_id=NULL,lease_until=NULL WHERE id=?', (t['id'],))
            self.event('lease_expired', f'{t["id"]} returned to queue', node_id=t['node_id'], job_id=t['job_id'])

    def lease(self, node_id: str, constitution_digest: str, seconds: int = 25):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                n = self.node(node_id)
                if not n or n['revoked'] or n['constitution_digest'] != constitution_digest:
                    raise ValueError('node is revoked or local constitution differs from registered consent')
                self.reclaim_expired()
                constitution = json.loads(n['constitution'])
                jobs = self.db.execute('SELECT * FROM jobs WHERE status="open" ORDER BY created_at,id').fetchall()
                selected = None
                for j in jobs:
                    signed = SignedProject.model_validate_json(j['signed_project'])
                    if compatible(constitution, signed.project, node_id):
                        continue
                    financial = signed.project.financial
                    if financial and financial.model == 'test_credits':
                        if not self.credits.job_funded(j['id'], financial.asset_id,
                              financial.credits_per_verified_task * signed.project.work.tasks):
                            continue
                    # Cooperative fairness: nodes with fewer allocated or completed tasks go first.
                    counts = self.db.execute('''SELECT n.id, COUNT(t.id) cnt FROM nodes n
                        LEFT JOIN tasks t ON t.node_id=n.id AND t.job_id=?
                        WHERE n.revoked=0 GROUP BY n.id''', (j['id'],)).fetchall()
                    eligible_counts = []
                    for item in counts:
                        peer = self.node(item['id'])
                        if compatible(json.loads(peer['constitution']), signed.project, peer['id']):
                            eligible_counts.append((peer['id'], item['cnt']))
                    least = min((ct for _, ct in eligible_counts), default=0)
                    mine = next((ct for nid, ct in eligible_counts if nid == node_id), 0)
                    if mine > least:
                        continue
                    t = self.db.execute('SELECT * FROM tasks WHERE job_id=? AND status="pending" ORDER BY task_index LIMIT 1', (j['id'],)).fetchone()
                    if t:
                        selected = (signed, t)
                        break
                if not selected:
                    self.db.execute('COMMIT')
                    return None
                signed, task = selected
                lease_id = secrets.token_urlsafe(24)
                self.db.execute('UPDATE tasks SET status="leased",node_id=?,lease_id=?,lease_until=? WHERE id=?',
                                (node_id, lease_id, time.time()+seconds, task['id']))
                self.event('task_leased', task['id'], node_id=node_id, job_id=signed.project.project_id)
                self.db.execute('COMMIT')
                return {'task_id': task['id'], 'task_index': task['task_index'], 'lease_id': lease_id,
                        'lease_seconds': seconds, 'signed_project': signed.model_dump(mode='json')}
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def task_status(self, task_id: str):
        with self.lock:
            t = self.db.execute('SELECT t.*,j.status job_status FROM tasks t JOIN jobs j ON j.id=t.job_id WHERE t.id=?', (task_id,)).fetchone()
            return dict(t) if t else None

    def finish(self, task_id, node_id, lease_id, digest_value=None, duration=None, reason=None):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                t = self.task_status(task_id)
                if not t or t['status'] != 'leased' or t['node_id'] != node_id or not secrets.compare_digest(t['lease_id'] or '', lease_id):
                    raise ValueError('not current task lease holder')
                if t['lease_until'] < time.time() or t['job_status'] != 'open':
                    raise ValueError('lease expired or job cancelled')
                if reason is None:
                    signed_row = self.db.execute('SELECT signed_project FROM jobs WHERE id=?', (t['job_id'],)).fetchone()
                    sp = SignedProject.model_validate_json(signed_row['signed_project'])
                    correct = compute_chain(sp.project.work.seed, t['task_index'], sp.project.work.iterations)
                    if not secrets.compare_digest(correct, digest_value or ''):
                        raise ValueError('computed result did not match deterministic reference task')
                    self.db.execute('UPDATE tasks SET status="done",digest=?,duration=?,result_time=? WHERE id=?',
                                    (digest_value, duration, time.time(), task_id))
                    self.event('task_completed', task_id, node_id, t['job_id'])
                    self._record_contribution(t['job_id'], task_id, node_id, digest_value,
                                              duration, signed_row['signed_project'])
                else:
                    self.db.execute('UPDATE tasks SET status="pending",node_id=NULL,lease_id=NULL,lease_until=NULL,fail_reason=? WHERE id=?',
                                    (reason[:200], task_id))
                    self.event('task_requeued', f'{task_id}: {reason}', node_id, t['job_id'])
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def cancel_job(self, job_id):
        with self.lock:
            result = self.db.execute('UPDATE jobs SET status="cancelled" WHERE id=? AND status="open"', (job_id,))
            self.event('job_cancelled', 'Project owner revoked consent', job_id=job_id)
            return result.rowcount > 0

    def revoke_node(self, node_id):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.db.execute('UPDATE nodes SET revoked=1 WHERE id=?', (node_id,))
                tasks = self.db.execute('SELECT * FROM tasks WHERE node_id=? AND status="leased"', (node_id,)).fetchall()
                for t in tasks:
                    self.db.execute('UPDATE tasks SET status="pending",node_id=NULL,lease_id=NULL,lease_until=NULL WHERE id=?', (t['id'],))
                self.event('node_revoked', 'Owner withdrew consent', node_id=node_id)
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def job_summary(self, job_id):
        with self.lock:
            j = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not j:
                return None
            counts = {x['status']: x['cnt'] for x in self.db.execute('SELECT status,COUNT(*) cnt FROM tasks WHERE job_id=? GROUP BY status', (job_id,))}
            contributors = [dict(x) for x in self.db.execute('''SELECT node_id, COUNT(*) tasks,ROUND(SUM(duration),3) cpu_worker_wall_seconds
                 FROM tasks WHERE job_id=? AND status="done" GROUP BY node_id ORDER BY node_id''', (job_id,))]
            return {'job_id': job_id, 'title': SignedProject.model_validate_json(j['signed_project']).project.title,
                    'status': j['status'], 'task_counts': counts, 'contributors': contributors}

    def chronicle(self, node_id):
        with self.lock:
            counts = [dict(x) for x in self.db.execute('''SELECT job_id,COUNT(*) tasks,ROUND(SUM(duration),3) worker_wall_seconds
             FROM tasks WHERE node_id=? AND status="done" GROUP BY job_id ORDER BY job_id''',(node_id,))]
            events = [dict(x) for x in self.db.execute('SELECT at,kind,detail,job_id FROM events WHERE node_id=? ORDER BY id DESC LIMIT 25', (node_id,))]
            return {'node_id': node_id, 'projects': counts, 'events': events,
                    'note': 'Durations are measured wall-clock time inside the process worker, not billed GPU-hours, electricity, or verified useful heat.'}

    def metrics(self):
        with self.lock:
            rows = self.db.execute('SELECT status,COUNT(*) cnt FROM tasks GROUP BY status').fetchall()
            n = self.db.execute('SELECT COUNT(*) FROM nodes WHERE revoked=0').fetchone()[0]
            return {'nodes': n, **{f'tasks_{r["status"]}': r['cnt'] for r in rows}}

    def stage_submission(self, signed):
        """Store a signed declaration for review; does NOT queue or execute OCI work."""
        from .submission import submission_digest
        project = signed.submission.manifest
        with self.lock:
            self.db.execute('INSERT INTO submissions(id,revision,bundle_digest,signed_bundle,staged_at) '
                            'VALUES(?,?,?,?,?)',
                            (project.metadata.project_id, project.metadata.revision,
                             submission_digest(signed.submission), signed.model_dump_json(), time.time()))
            self.event('submission_staged', f'{project.metadata.project_id}: rev {project.metadata.revision}',
                       job_id=project.metadata.project_id)

    def get_submission(self, project_id: str, revision: int):
        with self.lock:
            row = self.db.execute('SELECT id,revision,bundle_digest,state,staged_at,signed_bundle '
                                  'FROM submissions WHERE id=? AND revision=?', (project_id,revision)).fetchone()
            return dict(row) if row else None

    def _record_contribution(self, project_id, task_id, node_id, result, duration_reported, signed_project_json):
        """Coordinator-authored provisional credit; not payment, not cryptographic compute proof."""
        from .crypto import digest
        last = self.db.execute('SELECT receipt_sha256 FROM contribution_receipts '
                               'WHERE project_id=? ORDER BY seq DESC LIMIT 1', (project_id,)).fetchone()
        prev = last['receipt_sha256'] if last else '0'*64
        entry = {'schema':'polyc.contribution/v0alpha1',
                 'project_id':project_id, 'task_id':task_id, 'node_id':node_id,
                 'timestamp':time.time(), 'verified_result_sha256':result,
                 'verification':'independent_builtin_reference',
                 'seconds_self_reported':duration_reported,
                 'credit_units_provisional':1,
                 'signed_project_sha256':digest(json.loads(signed_project_json)),
                 'note':'No money; duration is not independently metered'}
        receipt_hash = digest({'previous':prev,'entry':entry})
        self.db.execute('INSERT INTO contribution_receipts(project_id,receipt_json,prev_sha256,receipt_sha256) '
                        'VALUES(?,?,?,?)', (project_id,json.dumps(entry,sort_keys=True),prev,receipt_hash))

    def ledger(self, project_id):
        """Verify the local hash chain against current DB contents. Externally anchor roots for tamper evidence."""
        from .crypto import digest
        with self.lock:
            rows=self.db.execute('SELECT receipt_json,prev_sha256,receipt_sha256 '
                                 'FROM contribution_receipts WHERE project_id=? ORDER BY seq', (project_id,)).fetchall()
            prev='0'*64
            entries=[]
            valid=True
            for r in rows:
                try:
                    e=json.loads(r['receipt_json'])
                    if r['prev_sha256'] != prev or r['receipt_sha256'] != digest({'previous':prev,'entry':e}):
                        valid=False
                    prev=r['receipt_sha256']
                    entries.append({'receipt':e,'prev_sha256':r['prev_sha256'], 'receipt_sha256':prev})
                except (ValueError, TypeError):
                    valid=False
            return {'project_id':project_id, 'credits_provisional':sum(x['receipt'].get('credit_units_provisional',0)
                        for x in entries), 'receipts':entries, 'chain_valid_locally':valid,
                    'root_sha256':prev, 'externally_anchored':False, 'monetary_settlement':'not_implemented'}
