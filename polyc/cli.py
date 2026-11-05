"""Owner and operator CLI."""
import argparse
import json
import logging
import os
import httpx
from pathlib import Path
import yaml
from .api import create_app
from .crypto import create_keypair, sign_project
from .models import Project
from .worker import Worker
from .provision import provision
from .chronicle import describe
from .submission import load_submission, submission_digest, sign_submission, SignedSubmission, verify_submission


def main():
    ap = argparse.ArgumentParser(prog='polyc', description='PolyC@home v0.3 CPU pilot and OCI declaration intake')
    sub = ap.add_subparsers(dest='command', required=True)
    serve = sub.add_parser('serve')
    serve.add_argument('--db', default='runtime/pilot.sqlite')
    serve.add_argument('--host', default='127.0.0.1')
    serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--insecure-http-on-lan', action='store_true', help='explicitly accept token exposure risk; testing ONLY')
    worker = sub.add_parser('worker')
    worker.add_argument('--config', required=True)
    worker.add_argument('--server', default='http://127.0.0.1:8765')
    worker.add_argument('--pause-file')
    worker.add_argument('--interval', type=float, default=.5)
    keys = sub.add_parser('keygen')
    keys.add_argument('--private', required=True)
    keys.add_argument('--public', required=True)
    sign = sub.add_parser('sign')
    sign.add_argument('--project', required=True)
    sign.add_argument('--private', required=True)
    sign.add_argument('--out', required=True)
    init = sub.add_parser('init-pilot', help='offline generation of five independent owner configs')
    init.add_argument('--out', required=True)
    init.add_argument('--nodes', type=int, default=5)
    reg = sub.add_parser('register', help='operator enrolls one consenting node')
    reg.add_argument('--config', required=True)
    reg.add_argument('--server', default='http://127.0.0.1:8765')
    reg.add_argument('--admin-token-file', required=True)
    send = sub.add_parser('submit', help='submit Ed25519-signed built-in project')
    send.add_argument('--signed', required=True)
    send.add_argument('--server', default='http://127.0.0.1:8765')
    send.add_argument('--admin-token-file', required=True)
    chron = sub.add_parser('chronicle', help='what did the cats do while I was gone?')
    chron.add_argument('--config', required=True)
    chron.add_argument('--server', default='http://127.0.0.1:8765')
    val = sub.add_parser('validate-submission', help='validate project.yaml + polic.yaml offline; NO image verification')
    val.add_argument('--dir', required=True)
    sig = sub.add_parser('sign-submission', help='sign both project.yaml and polic.yaml as a single immutable contract')
    sig.add_argument('--dir', required=True)
    sig.add_argument('--private', required=True)
    sig.add_argument('--out', required=True)
    send_bundle = sub.add_parser('submit-submission', help='stage signed OCI project metadata only; never runs images')
    send_bundle.add_argument('--signed', required=True)
    send_bundle.add_argument('--server', default='http://127.0.0.1:8765')
    send_bundle.add_argument('--admin-token-file', required=True)
    audit = sub.add_parser('ledger', help='read coordinator hash-linked provisional contribution receipts')
    audit.add_argument('--project-id', required=True)
    audit.add_argument('--server', default='http://127.0.0.1:8765')
    audit.add_argument('--admin-token-file', required=True)
    pause = sub.add_parser('pause', help='pause locally regardless of coordinator status')
    pause.add_argument('--config', required=True)
    pause.add_argument('--resume', action='store_true')

    from .economy_cli import add_parser as add_economy_parser
    add_economy_parser(sub)
    sub.add_parser('economy-demo', help='run five-cat test-credit pilot locally; no real money')

    args = ap.parse_args()
    if args.command == 'economy-demo':
        from .economy_demo import run_economy_demo
        r=run_economy_demo()
        print(json.dumps({'volunteer_tasks':25,'paid_test_tasks':5,
            'issued_credits':r['supply']['issued_units'],
            'wallet_balances':r['balances_after_settlement'],
            'audit_valid_locally':r['audit']['valid_locally']},indent=2))
        return
    if args.command.startswith('credit-'):
        from .economy_cli import execute as execute_economy
        execute_economy(args)
        return
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
    if args.command == 'serve':
        import uvicorn
        token = os.environ.get('POLYC_ADMIN_TOKEN', '')
        if len(token) < 24:
            ap.error('POLYC_ADMIN_TOKEN environment variable must have at least 24 characters')
        if args.host not in ('127.0.0.1', 'localhost', '::1') and not args.insecure_http_on_lan:
            ap.error('non-loopback HTTP binding denied; use a TLS reverse proxy, SSH tunnel or VPN, or explicitly pass --insecure-http-on-lan for isolated testing')
        if args.host not in ('127.0.0.1', 'localhost', '::1'):
            print('WARNING: development HTTP server has no TLS; bearer tokens may be stolen in transit!')
        uvicorn.run(create_app(args.db, token), host=args.host, port=args.port, log_level='info')
    elif args.command == 'worker':
        w = Worker(args.config, args.server, args.pause_file)
        try:
            w.loop(interval=args.interval)
        except KeyboardInterrupt:
            w.request_stop()
    elif args.command == 'keygen':
        create_keypair(args.private, args.public)
        print('public:', Path(args.public).read_text())
    elif args.command == 'init-pilot':
        print('Created private pilot files at:', provision(args.out,args.nodes))
    elif args.command == 'register':
        c=yaml.safe_load(Path(args.config).read_text())
        token=Path(args.admin_token_file).read_text().strip()
        r=httpx.post(args.server+'/api/nodes',headers={'Authorization':f'Bearer {token}'},json={
            'node_id':c['node_id'],'token':c['token'],'constitution':c['constitution']},timeout=5)
        r.raise_for_status()
        print(json.dumps(r.json(),indent=2))
    elif args.command == 'submit':
        token=Path(args.admin_token_file).read_text().strip()
        r=httpx.post(args.server+'/api/jobs',headers={'Authorization':f'Bearer {token}'},
            json=json.loads(Path(args.signed).read_text()),timeout=5)
        r.raise_for_status()
        print(json.dumps(r.json(),indent=2))
    elif args.command == 'chronicle':
        c=yaml.safe_load(Path(args.config).read_text())
        r=httpx.get(args.server+f'/api/chronicle/{c["node_id"]}',
            headers={'Authorization':f'Bearer {c["token"]}'},timeout=5)
        r.raise_for_status()
        print(describe(r.json()))
    elif args.command == 'validate-submission':
        bundle = load_submission(args.dir)
        print(json.dumps({'valid_schema': True, 'bundle_digest': submission_digest(bundle),
                          'image':bundle.manifest.artifact.image,
                          'artifact_verified':False, 'execution_enabled':False},indent=2))
    elif args.command == 'sign-submission':
        bundle = load_submission(args.dir)
        signed = sign_submission(bundle,args.private)
        Path(args.out).write_text(signed.model_dump_json(indent=2)+'\n')
        print('signed:', args.out, 'bundle_digest:', submission_digest(bundle))
    elif args.command == 'submit-submission':
        signed = SignedSubmission.model_validate_json(Path(args.signed).read_text())
        if not verify_submission(signed):
            ap.error('signature invalid; refused to submit')
        token=Path(args.admin_token_file).read_text().strip()
        r=httpx.post(args.server+'/api/submissions',headers={'Authorization':f'Bearer {token}'},
                     json=signed.model_dump(mode='json'),timeout=5)
        r.raise_for_status()
        print(json.dumps(r.json(),indent=2))
    elif args.command == 'ledger':
        token=Path(args.admin_token_file).read_text().strip()
        r=httpx.get(args.server+'/api/ledger/'+args.project_id,
                    headers={'Authorization':f'Bearer {token}'},timeout=5)
        r.raise_for_status()
        print(json.dumps(r.json(),indent=2))
    elif args.command == 'pause':
        c=yaml.safe_load(Path(args.config).read_text())
        flag=Path(c.get('pause_file',f'runtime/{c["node_id"]}.pause'))
        if args.resume:
            flag.unlink(missing_ok=True)
            print('Resumed local willingness to accept tasks:',c['node_id'])
        else:
            flag.parent.mkdir(parents=True,exist_ok=True)
            flag.touch()
            print('Local pause requested:',c['node_id'])
    elif args.command == 'sign':
        data = yaml.safe_load(Path(args.project).read_text())
        signed = sign_project(Project.model_validate(data), args.private)
        Path(args.out).write_text(signed.model_dump_json(indent=2)+'\n')
        print('signed:', args.out)

if __name__ == '__main__':
    main()
