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


def main():
    ap = argparse.ArgumentParser(prog='polyc', description='PolyC@home v0.1 CPU pilot')
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
    pause = sub.add_parser('pause', help='pause locally regardless of coordinator status')
    pause.add_argument('--config', required=True)
    pause.add_argument('--resume', action='store_true')

    args = ap.parse_args()
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
