"""Executable five-user star-topology demonstration on one Linux host."""
from __future__ import annotations
import argparse
import json
import logging
import secrets
import socket
import tempfile
import threading
import time
from pathlib import Path
import httpx
import uvicorn
import yaml
from .api import create_app
from .crypto import create_keypair, sign_project
from .models import Project
from .worker import Worker


def constitution(public_key: str, cpu_sensor_required=False) -> dict:
    return {
        'apiVersion': 'polic.home/v0alpha1', 'kind': 'NodeConstitution',
        'metadata': {'name': 'pilot-node', 'revision': 1},
        'spec': {
            'sovereignty': {'local_workloads_first': True, 'owner_can_revoke_immediately': True,
                            'require_mutual_consent': True, 'pause_on_local_activity': True},
            'nice_plus': {'level': 30, 'cpu_percent_max': 70, 'memory_mib_max': 768,
                          'task_runtime_seconds_max': 15, 'gpu_utilization_percent_max': 0},
            'local_activity': {},
            'thermal': {'cpu_package_c_max': 80 if cpu_sensor_required else None,
                        'missing_sensor_action': 'deny'},
            'energy': {'require_meter': False},
            'content': {'require_public_repository': True, 'require_pinned_source_commit': True,
                        'require_signed_artifacts': True,
                        'allow_categories': ['open_science', 'open_media', 'climate_research'],
                        'deny_categories': ['violent_extremist_propaganda', 'targeted_harassment']},
            'ethos': {'exclude_projects_with_declared_purposes': ['ethnic_cleansing', 'racial_supremacy'],
                      'allow_commercial_projects': False},
            'trust': {'trusted_signers': [public_key]},
            'reporting': {'chronicle_frequency': 'weekly', 'catnap_enabled': False}
        }
    }


def run_demo(workdir: str | None = None, timeout: int = 35):
    if workdir is None:
        td = tempfile.TemporaryDirectory(prefix='polyc-five-')
        root = Path(td.name)
    else:
        td = None
        root = Path(workdir) / f'run-{time.strftime("%Y%m%d-%H%M%S")}-{secrets.token_hex(3)}'
        root.mkdir(parents=True, exist_ok=False)
    (root/'keys').mkdir(exist_ok=True)
    create_keypair(str(root/'keys'/'project.pem'), str(root/'keys'/'project.pub'))
    public_key = (root/'keys'/'project.pub').read_text()
    admin = secrets.token_urlsafe(32)
    app = create_app(str(root/'pilot.sqlite'), admin)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    url = f'http://127.0.0.1:{port}'
    config = uvicorn.Config(app, host='127.0.0.1', port=port, log_level='error')
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    clients = []
    threads = []
    try:
        with httpx.Client(timeout=2) as client:
            for _ in range(100):
                try:
                    if client.get(url+'/health').status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.05)
            else:
                raise RuntimeError('coordinator did not start')
            for idx in range(1, 6):
                node_id = f'cat-{idx}'
                token = secrets.token_urlsafe(32)
                const = constitution(public_key)
                const['metadata']['name'] = node_id
                local = {'node_id': node_id, 'token': token, 'constitution': const,
                         'pause_file': str(root/f'{node_id}.pause')}
                path = root/f'{node_id}.yaml'
                path.write_text(yaml.safe_dump(local, sort_keys=False))
                path.chmod(0o600)
                r = client.post(url+'/api/nodes', headers={'Authorization': f'Bearer {admin}'},
                                json={'node_id': node_id, 'token': token, 'constitution': const})
                r.raise_for_status()
                worker = Worker(str(path), url)
                clients.append(worker)
            proj = Project(project_id='five-cats-open-science', title='Five Cats Compute Together',
                           source_repo='https://github.com/example/public-open-science',
                           source_commit='a'*40, category='open_science',
                           purposes=['open_knowledge'], commercial=False,
                           work={'kind': 'sha256_chain_v1', 'tasks': 25,
                                 'iterations': 5000, 'seed': 'catnap'})
            signed = sign_project(proj, str(root/'keys'/'project.pem'))
            response = client.post(url+'/api/jobs', headers={'Authorization': f'Bearer {admin}'},
                                   json=signed.model_dump(mode='json'))
            response.raise_for_status()
            for worker in clients:
                t = threading.Thread(target=worker.loop, kwargs={'interval': .08, 'max_seconds': timeout}, daemon=True)
                t.start()
                threads.append(t)
            end = time.monotonic()+timeout
            summary = None
            while time.monotonic() < end:
                time.sleep(.2)
                r = client.get(url+'/api/jobs/'+proj.project_id, headers={'Authorization': f'Bearer {admin}'})
                r.raise_for_status()
                summary = r.json()
                if summary['task_counts'].get('done', 0) == proj.work.tasks:
                    break
            for worker in clients:
                worker.request_stop()
            for t in threads:
                t.join(timeout=4)
            report = {'summary': summary, 'chronicles': []}
            for worker in clients:
                r = client.get(url+f'/api/chronicle/{worker.node_id}',
                               headers={'Authorization': f'Bearer {worker.token}'})
                r.raise_for_status()
                report['chronicles'].append(r.json())
            if workdir:
                (root/'demo-results.json').write_text(json.dumps(report, indent=2))
                print('Run artifacts (keep private):', root)
            print(json.dumps(report['summary'], indent=2))
            print('Independent contributors:', ', '.join(x['node_id'] for x in summary['contributors']))
            if summary['task_counts'].get('done', 0) != 25 or len(summary['contributors']) != 5:
                raise RuntimeError('five-node proof did not meet acceptance criteria')
            return report
    finally:
        for worker in clients:
            worker.request_stop()
        for t in threads:
            t.join(timeout=2)
        server.should_exit = True
        thread.join(timeout=3)
        app.state.store.db.close()
        if td:
            td.cleanup()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workdir', default=None, help='save credentials, SQLite activity records and reports here (private)')
    ap.add_argument('--timeout', type=int, default=35)
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
    run_demo(args.workdir, args.timeout)

if __name__ == '__main__':
    main()
